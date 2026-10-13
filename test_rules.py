import unittest
from pathlib import Path

from luauguard import scan_text


def ids(src, name="Test.server.luau", **kw):
    return [f.rule_id for f in scan_text(Path(name), src, **kw)]


class DynamicCodeTests(unittest.TestCase):
    def test_loadstring_flagged(self):
        self.assertEqual(ids('local f = loadstring("return 1")'), ["LG001"])

    def test_loadstring_in_comment_or_string_ignored(self):
        self.assertEqual(ids('-- loadstring("x")\nlocal s = "loadstring(x)"'), [])

    def test_dynamic_require_flagged(self):
        self.assertEqual(ids("local m = require(modules[name])"), ["LG002"])

    def test_static_requires_not_flagged(self):
        src = (
            "require(script.Parent.Util)\n"
            'require(game:GetService("ReplicatedStorage").Shared)\n'
            'require(ReplicatedStorage:WaitForChild("Shared"))\n'
            'require("@pkg/thing")\n'
            "require(123456)\n"
        )
        self.assertEqual(ids(src), [])

    def test_method_named_require_ignored(self):
        self.assertEqual(ids("obj:require(modules[name])"), [])


class RemoteCallbackTests(unittest.TestCase):
    def test_reward_parameter(self):
        src = "r.OnServerEvent:Connect(function(player, amount)\n\tplayer.leaderstats.Coins.Value += amount\nend)"
        self.assertIn("LG003", ids(src))

    def test_reward_name_unused_is_fine(self):
        src = "r.OnServerEvent:Connect(function(player, amount)\n\tif typeof(amount) ~= 'number' then return end\n\tprint(amount)\nend)"
        self.assertEqual(ids(src), [])

    def test_missing_validation_flagged_and_typeof_accepted(self):
        bad = "r.OnServerEvent:Connect(function(player, item)\n\tgive(player, item)\nend)"
        good = "r.OnServerEvent:Connect(function(player, item)\n\tif typeof(item) ~= 'string' then return end\n\tgive(player, item)\nend)"
        self.assertEqual(ids(bad), ["LG004"])
        self.assertEqual(ids(good), [])

    def test_nested_function_does_not_cut_the_body_short(self):
        src = (
            "r.OnServerEvent:Connect(function(player, amount)\n"
            "\ttask.spawn(function() print('x') end)\n"
            "\tif typeof(amount) ~= 'number' then return end\n"
            "end)"
        )
        self.assertEqual(ids(src), [])

    def test_long_body_still_sees_late_validation(self):
        filler = "\tlocal x = 1\n" * 400
        src = f"r.OnServerEvent:Connect(function(player, item)\n{filler}\tassert(typeof(item) == 'string')\nend)"
        self.assertEqual(ids(src), [])

    def test_remote_found_through_waitforchild_chain(self):
        src = 'game.ReplicatedStorage:WaitForChild("Buy").OnServerEvent:Connect(function(player, item)\n\tgive(item)\nend)'
        self.assertEqual(ids(src), ["LG004"])

    def test_typed_parameters(self):
        src = "r.OnServerEvent:Connect(function(player: Player, amount: number)\n\tplayer.Cash.Value += amount\nend)"
        self.assertIn("LG003", ids(src))

    def test_fire_all_clients(self):
        src = "r.OnServerEvent:Connect(function(player, msg)\n\tr:FireAllClients(msg)\nend)"
        self.assertEqual(ids(src), ["LG004", "LG006"])

    def test_loop_bound_allocation_and_clamp(self):
        loop = "r.OnServerEvent:Connect(function(player, n)\n\tfor i = 1, n do spawn() end\nend)"
        rep = "r.OnServerEvent:Connect(function(player, n)\n\tlocal s = string.rep('a', n)\nend)"
        create = "r.OnServerEvent:Connect(function(player, n)\n\tlocal t = table.create(n)\nend)"
        clamped = "r.OnServerEvent:Connect(function(player, n)\n\tn = math.clamp(n, 1, 10)\n\tfor i = 1, n do spawn() end\nend)"
        for src in (loop, rep, create):
            self.assertIn("LG008", ids(src))
        self.assertNotIn("LG008", ids(clamped))

    def test_remote_function(self):
        bad = "r.OnServerInvoke = function(player, id)\n\treturn data[id]\nend"
        good = "r.OnServerInvoke = function(player, id)\n\tif typeof(id) ~= 'string' then return end\n\treturn data[id]\nend"
        self.assertEqual(ids(bad), ["LG009"])
        self.assertEqual(ids(good), [])

    def test_http_with_client_parameter(self):
        src = 'r.OnServerInvoke = function(player, q)\n\tif typeof(q) ~= "string" then return end\n\treturn Http:GetAsync("https://x.test/?q=" .. q)\nend'
        self.assertEqual(ids(src), ["LG011"])

    def test_http_with_fixed_url_is_fine(self):
        src = 'r.OnServerInvoke = function(player, q)\n\tif typeof(q) ~= "string" then return end\n\treturn Http:GetAsync("https://x.test/fixed")\nend'
        self.assertEqual(ids(src), [])


class ClientTests(unittest.TestCase):
    def test_currency_mutation_in_client_script(self):
        self.assertEqual(ids("player.leaderstats.Coins.Value += 5", "Shop.client.luau"), ["LG005"])

    def test_same_code_on_server_is_fine(self):
        self.assertEqual(ids("player.leaderstats.Coins.Value += 5"), [])

    def test_ui_value_assignment_is_fine(self):
        self.assertEqual(ids("slider.Value = 5", "Ui.client.luau"), [])

    def test_comparison_is_not_assignment(self):
        self.assertEqual(ids("if coins.Value == 5 then end", "Ui.client.luau"), [])

    def test_runservice_isclient_marks_client(self):
        src = "if RunService:IsClient() then\n\tplayer.leaderstats.Cash.Value = 9\nend"
        self.assertEqual(ids(src), ["LG005"])


class SecretTests(unittest.TestCase):
    def test_patterns(self):
        cases = [
            'local api_key = "abcdefghijklmnop"',
            'local t = "ghp_abcdefghijklmnopqrstuvwxyz"',
            'local k = "sk-abcdefghijklmnopqrstuvwxyz"',
            'local h = "https://discord.com/api/webhooks/123456/abc-DEF_ghi"',
            'local c = "_|WARNING:-DO-NOT-SHARE-THIS.--stuff"',
        ]
        for src in cases:
            self.assertEqual(ids(src), ["LG007"], src)

    def test_short_values_ignored(self):
        self.assertEqual(ids('local api_key = "short"'), [])

    def test_secret_in_comment_is_still_reported(self):
        self.assertEqual(ids('-- api_key = "abcdefghijklmnop"'), ["LG007"])


class TouchedTests(unittest.TestCase):
    def test_touched_without_debounce(self):
        src = "p.Touched:Connect(function(hit)\n\tlocal h = hit.Parent:FindFirstChild('Humanoid')\n\th:TakeDamage(5)\nend)"
        self.assertEqual(ids(src), ["LG010"])

    def test_touched_with_debounce(self):
        src = "p.Touched:Connect(function(hit)\n\tif debounce then return end\n\tdebounce = true\n\thit.Parent.Humanoid:TakeDamage(5)\nend)"
        self.assertEqual(ids(src), [])

    def test_touched_without_state_change_is_fine(self):
        self.assertEqual(ids("p.Touched:Connect(function(hit)\n\tprint(hit)\nend)"), [])


class SuppressionTests(unittest.TestCase):
    BAD = "loadstring('x')"

    def test_same_line(self):
        self.assertEqual(ids(self.BAD + " -- luauguard: ignore"), [])

    def test_previous_line_directive(self):
        self.assertEqual(ids("-- luauguard: ignore LG001\n" + self.BAD), [])

    def test_specific_id_only(self):
        self.assertEqual(ids(self.BAD + " -- luauguard: ignore LG002"), ["LG001"])

    def test_directive_does_not_leak_to_later_lines(self):
        self.assertEqual(ids("-- luauguard: ignore\nlocal a = 1\n" + self.BAD), ["LG001"])

    def test_disabled_rules(self):
        self.assertEqual(ids(self.BAD, disabled=["lg001"]), [])


class FindingShapeTests(unittest.TestCase):
    def test_line_numbers_and_snippet(self):
        src = "local a = 1\n\nlocal f = loadstring('x')\n"
        [f] = scan_text(Path("A.server.luau"), src)
        self.assertEqual((f.rule_id, f.line, f.severity), ("LG001", 3, "high"))
        self.assertEqual(f.snippet, "local f = loadstring('x')")


if __name__ == "__main__":
    unittest.main()
