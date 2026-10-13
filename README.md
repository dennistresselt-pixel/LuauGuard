# LuauGuard

**A dependency free, heuristic security checker for Roblox Luau scripts.**

LuauGuard scans `.lua` and `.luau` files for patterns that deserve a security review, especially around the client/server boundary: unvalidated remotes, client controlled rewards, dynamic code, leaked secrets and more.

> **Limitations:** this is a static analysis tool built on a small lexer and regular expressions, not a full Luau parser or a security certification. It can miss vulnerabilities and report false positives. Review findings in context and test your game.

## Requirements

Python 3.10 or newer. No third party dependencies.

## Install and run

```bash
pip install .            # from a clone of this repository
luauguard src            # scan a folder
python -m luauguard src  # works without installing too
```

```bash
luauguard src game.server.luau          # several paths at once
luauguard src --format json
luauguard src --format sarif > luauguard.sarif
luauguard src --min-severity high
luauguard src --disable LG004,LG010
luauguard --list-rules
```

Exit codes: `0` no findings at the selected threshold, `1` findings, `2` path or usage error.

`Packages`, `ServerPackages`, `DevPackages`, `node_modules`, `.git` and virtual environments are skipped by default. Use `--include-packages` to scan them too.

## Rules

| ID | Severity | Check |
|---|---|---|
| LG001 | High | `loadstring()` usage |
| LG002 | Medium | `require()` argument that looks dynamic |
| LG003 | High | Client supplied reward or currency like parameter used in a server update |
| LG004 | Medium | `OnServerEvent` callback without obvious validation |
| LG005 | Medium | Currency like mutation in a likely client script |
| LG006 | Medium | `FireAllClients()` inside a client triggered server callback |
| LG007 | High | Hard coded secrets: API keys, tokens, `.ROBLOSECURITY` cookies, Discord webhooks |
| LG008 | Medium | Client parameter used as a loop bound, `string.rep` count or `table.create` size |
| LG009 | Medium | `OnServerInvoke` callback without obvious validation |
| LG010 | Low | `Touched` handler that damages or rewards without an obvious debounce |
| LG011 | High | Client parameter used in an `HttpService` request |

These are heuristics. LG004 may flag validation that is delegated to a helper, and LG007 may flag a harmless placeholder. The folders [`examples/vulnerable`](examples/vulnerable) and [`examples/safe`](examples/safe) show what each rule catches and what a defensive version looks like.

### How it works

A small lexer first blanks out comments and string contents while keeping every offset and line number intact, so `-- loadstring()` and `"loadstring("` are never reported. Remote callbacks are then matched to their real closing `end`, which means long handlers and nested functions are analysed as a whole.

### Suppressing a finding

Add a comment on the same line or on the line above:

```lua
local f = loadstring(code) -- luauguard: ignore LG001

-- luauguard: ignore LG004, LG009
remote.OnServerEvent:Connect(function(player, data)
```

`-- luauguard: ignore` without ids suppresses every rule on that line. Prefer fixing the problem over suppressing it.

## Use in GitHub Actions

Findings show up in the Security tab through code scanning:

```yaml
name: LuauGuard
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install git+https://github.com/dennistresselt-pixel/LuauGuard
      - run: luauguard src --format sarif > luauguard.sarif || true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: luauguard.sarif
```

## Suggested workflow

1. Scan your scripts.
2. Inspect each finding and the code around it.
3. Fix real defects rather than silencing warnings.
4. Test with multiple clients in Roblox Studio and in a published test place.
5. Add regression tests for bugs you find.

## Development

```bash
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Use synthetic examples; never publish private game code, credentials or personal data.

## License

MIT. See [LICENSE](LICENSE).

## References

- [Roblox Creator Hub: Client server boundary](https://create.roblox.com/docs/scripting/security/client-server-boundary)
- [Roblox Creator Hub: Security tactics](https://create.roblox.com/docs/scripting/security/security-tactics)
