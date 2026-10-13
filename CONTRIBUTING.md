# Contributing

Thanks for helping improve LuauGuard.

- Search existing issues before opening a new one.
- For a new rule, explain the threat model and likely false positives.
- Include a small synthetic `.lua` or `.luau` example.
- Add tests for positive and negative cases.
- Run `python -m unittest discover -s tests -v`.
- Keep dependencies at zero unless a change is discussed first.

## Adding a rule

1. Add a `Rule` to `RULES` in `luauguard/rules.py` with the next free `LGxxx` id.
2. Implement the check as a method on `_Scan` in `luauguard/scanner.py` and call it from `scan_text`. Work on `self.code` (comments and strings blanked) unless the rule needs string contents, in which case use `self.text`.
3. Add a vulnerable example to `examples/vulnerable/`. A test fails if any rule has no example.
4. Add positive and negative tests to `tests/test_rules.py`. Make sure `examples/safe/` stays clean.
5. Document the rule in the README table and in `CHANGELOG.md`.

Be respectful and constructive. Never upload credentials, private game code, personal data, or private game assets without permission. Use fabricated sample values.
