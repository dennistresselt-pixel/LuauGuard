import unittest

from luauguard.lexer import find_block_end, find_closing_paren, mask


class MaskTests(unittest.TestCase):
    def test_line_comment_is_blanked(self):
        m = mask('local x = 1 -- loadstring("a")')
        self.assertNotIn("loadstring", m.code)
        self.assertNotIn("loadstring", m.with_strings)

    def test_long_comment_with_levels(self):
        src = "--[==[ loadstring( ]] still comment ]==] local y = 2"
        m = mask(src)
        self.assertNotIn("loadstring", m.code)
        self.assertIn("local y = 2", m.code)

    def test_string_contents_blanked_but_quotes_kept(self):
        m = mask('local s = "loadstring(" local t = 1')
        self.assertNotIn("loadstring", m.code)
        self.assertIn('"           "', m.code)
        self.assertIn("loadstring(", m.with_strings)
        self.assertIn("local t = 1", m.code)

    def test_comment_marker_inside_string_is_not_a_comment(self):
        m = mask('local s = "a -- b" local z = 1')
        self.assertIn("local z = 1", m.code)

    def test_escaped_quote(self):
        m = mask('local s = "a\\"b -- c" local z = 1')
        self.assertIn("local z = 1", m.code)

    def test_long_string(self):
        m = mask("local s = [[ -- not a comment loadstring( ]] local z = 1")
        self.assertNotIn("loadstring", m.code)
        self.assertIn("local z = 1", m.code)

    def test_interpolated_string_keeps_expressions(self):
        m = mask("local s = `hello {name} loadstring(` local z = 1")
        self.assertIn("name", m.code)
        self.assertNotIn("loadstring", m.code)
        self.assertIn("local z = 1", m.code)

    def test_unterminated_string_stops_at_line_end(self):
        m = mask('local a = "oops\nlocal b = loadstring("x")')
        self.assertIn("loadstring(", m.code)

    def test_offsets_and_newlines_preserved(self):
        src = 'local a = "x"\n--[[ one\ntwo ]]\nlocal b = [[\nthree]]\n`t {a}`\n'
        m = mask(src)
        for view in (m.code, m.with_strings):
            self.assertEqual(len(view), len(src))
            self.assertEqual([i for i, c in enumerate(view) if c == "\n"],
                             [i for i, c in enumerate(src) if c == "\n"])


class BlockTests(unittest.TestCase):
    def end_of(self, src, marker="("):
        code = mask(src).code
        start = src.index(marker) + 1
        end = find_block_end(code, start)
        self.assertIsNotNone(end)
        return src[end:]

    def test_nested_blocks(self):
        src = "local f = function(a)\n if a then b() end\n for i = 1, 3 do c() end\n return 1\nend\nafter()"
        self.assertTrue(self.end_of(src).startswith("end\nafter()"))

    def test_if_expression_has_no_end(self):
        src = "local f = function(a) local x = if a then 1 else 2 return x end tail()"
        self.assertTrue(self.end_of(src).startswith("end tail()"))

    def test_while_and_repeat(self):
        src = "local f = function() while true do x() end repeat y() until z() end tail()"
        self.assertTrue(self.end_of(src).startswith("end tail()"))

    def test_keywords_in_strings_and_comments_are_ignored(self):
        src = 'local f = function() print("end") -- end\nend tail()'
        self.assertTrue(self.end_of(src).startswith("end tail()"))

    def test_unbalanced_returns_none(self):
        self.assertIsNone(find_block_end(mask("function() if x then").code, 0))


class ParenTests(unittest.TestCase):
    def test_matching_paren(self):
        code = mask('f(a, g(b), "(")').code
        self.assertEqual(find_closing_paren(code, 1), len(code) - 1)

    def test_unbalanced(self):
        self.assertIsNone(find_closing_paren("f(a", 1))


if __name__ == "__main__":
    unittest.main()
