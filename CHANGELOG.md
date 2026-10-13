# Changelog

## 0.3.0

- Restructured into an installable package (`luauguard`) with a `luauguard` command and `python -m luauguard`.
- Added a Luau lexer. Comments, long comments, strings, long strings and interpolated strings are masked before any rule runs, so text inside them no longer triggers findings.
- Remote callbacks are now matched to their real closing `end`. Previously the body was cut at the first `end)` or after 2400 characters, which caused missed validation and false LG004 findings.
- Added LG009 (OnServerInvoke without validation), LG010 (Touched without debounce) and LG011 (client data in an HttpService request).
- LG003 now also covers `OnServerInvoke` and `.Value = param`.
- LG005 only fires when the line mentions a currency like word, instead of on every `.Value` assignment in a client script.
- LG002 no longer flags plain string literal requires.
- LG007 now detects Discord webhooks and `.ROBLOSECURITY` cookies, and scans comments too, since a key in a comment is still published.
- LG008 also covers `string.rep` and `table.create`, and accepts a `math.clamp` on the parameter.
- Added SARIF 2.1.0 output (`--format sarif`) for GitHub code scanning.
- Added `-- luauguard: ignore [IDS]` comments and `--disable`.
- Several paths per run. `Packages`, `node_modules` and similar folders are skipped by default (`--include-packages` to override).
- Added `--version`, GitHub Actions workflow, runnable `examples/` and 65 tests. A test ensures every rule has a vulnerable example.

## 0.2.0: prototype hardening

- Added rule registry and rule list output.
- Added heuristic checks for common secret patterns and client controlled loop bounds.
- Added severity filtering and expanded tests.
- Improved contribution and security reporting guidance.
- Clarified limitations of text based static analysis.
