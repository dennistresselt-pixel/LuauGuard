import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

import luauguard
from luauguard import RULES
from luauguard.cli import main

ROOT = Path(__file__).resolve().parent.parent
BAD = "local f = loadstring('x')\n"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name, text):
        p = self.dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_clean_file_exits_zero(self):
        self.write("a.luau", "local x = 1\n")
        code, out, _ = run(str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("no findings", out)

    def test_findings_exit_one_json(self):
        self.write("a.server.luau", BAD)
        code, out, _ = run(str(self.dir), "--format", "json")
        self.assertEqual(code, 1)
        self.assertEqual([f["rule_id"] for f in json.loads(out)], ["LG001"])

    def test_missing_path_exits_two(self):
        code, _, err = run(str(self.dir / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_no_path_is_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            main([])
        self.assertEqual(cm.exception.code, 2)

    def test_min_severity(self):
        self.write("a.server.luau", "r.OnServerEvent:Connect(function(p, x)\n\tgive(x)\nend)\n")
        self.assertEqual(run(str(self.dir))[0], 1)
        self.assertEqual(run(str(self.dir), "--min-severity", "high")[0], 0)

    def test_disable(self):
        self.write("a.server.luau", BAD)
        self.assertEqual(run(str(self.dir), "--disable", "LG001")[0], 0)

    def test_unknown_disable_id(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            main([str(self.dir), "--disable", "LG999"])
        self.assertEqual(cm.exception.code, 2)

    def test_packages_folder_skipped_by_default(self):
        self.write("Packages/Dep.luau", BAD)
        self.assertEqual(run(str(self.dir))[0], 0)
        self.assertEqual(run(str(self.dir), "--include-packages")[0], 1)

    def test_multiple_paths(self):
        a = self.write("a/x.server.luau", BAD)
        b = self.write("b/y.server.luau", BAD)
        _, out, _ = run(str(a), str(b), "--format", "json")
        self.assertEqual(len(json.loads(out)), 2)

    def test_list_rules(self):
        code, out, _ = run("--list-rules")
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)), len(RULES))

    def test_version(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(luauguard.__version__, out.getvalue())

    def test_sarif_shape(self):
        self.write("a.server.luau", BAD)
        code, out, _ = run(str(self.dir), "--format", "sarif")
        self.assertEqual(code, 1)
        doc = json.loads(out)
        self.assertEqual(doc["version"], "2.1.0")
        run0 = doc["runs"][0]
        self.assertEqual(len(run0["tool"]["driver"]["rules"]), len(RULES))
        [result] = run0["results"]
        self.assertEqual(result["ruleId"], "LG001")
        self.assertEqual(result["level"], "error")
        self.assertEqual(run0["tool"]["driver"]["rules"][result["ruleIndex"]]["id"], "LG001")
        loc = result["locations"][0]["physicalLocation"]
        self.assertEqual(loc["region"]["startLine"], 1)
        self.assertTrue(loc["artifactLocation"]["uri"].endswith("a.server.luau"))


class ExampleTests(unittest.TestCase):
    def test_safe_examples_are_clean(self):
        code, out, _ = run(str(ROOT / "examples" / "safe"))
        self.assertEqual(code, 0, out)

    def test_every_rule_has_a_vulnerable_example(self):
        _, out, _ = run(str(ROOT / "examples" / "vulnerable"), "--format", "json")
        seen = {f["rule_id"] for f in json.loads(out)}
        self.assertEqual(seen, {r.rule_id for r in RULES})


class PackagingTests(unittest.TestCase):
    def test_version_matches_pyproject(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), luauguard.__version__)


if __name__ == "__main__":
    unittest.main()
