"""The actual checks. Every rule runs on lexer-masked source."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .lexer import find_block_end, find_closing_paren, mask
from .rules import RULES_BY_ID, Finding

SUFFIXES = {".lua", ".luau"}
DEFAULT_EXCLUDES = frozenset(
    {".git", "Packages", "ServerPackages", "DevPackages", "node_modules", ".venv", "venv"}
)
_FALLBACK_BODY = 2400

_MONEY = r"cash|coin|gold|money|amount|reward|price|value|gem|xp|score|currency"
_CURRENCY_WORDS = re.compile(r"cash|coin|gold|money|gem|currency|leaderstats", re.I)
_VALIDATION = re.compile(
    r"\b(?:typeof|type|tonumber|math\.isfinite|math\.clamp|IsDescendantOf|IsA|Magnitude|"
    r"UserId|cooldown|rate.?limit|assert)\b|\ballow\w*\s*\(|\bif\s+not\b",
    re.I,
)
_DEBOUNCE = re.compile(
    r"\b(?:debounce\w*|db|cooldown|cd|busy|touched|cantouch|locked?)\b|"
    r"\bos\.(?:clock|time)\b|\btick\s*\(|:\s*Disconnect\s*\(",
    re.I,
)

_REMOTE = r"(?<![\w.:])(?P<remote>[\w.:]+(?:\([^()]*\)[\w.:]*)*)"
_EVENT = re.compile(
    _REMOTE + r"\s*\.\s*OnServerEvent\s*:\s*Connect\s*\(\s*function\s*\((?P<params>[^)]*)\)"
)
_INVOKE = re.compile(
    _REMOTE + r"\s*\.\s*OnServerInvoke\s*=\s*function\s*\((?P<params>[^)]*)\)"
)
_TOUCHED = re.compile(r"\.\s*Touched\s*:\s*Connect\s*\(\s*function\s*\([^)]*\)")

_SECRET_PATTERNS = [
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|private[_-]?key)\s*=\s*[\"'][^\"']{12,}[\"']", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+"),
    re.compile(r"_\|WARNING:-DO-NOT-SHARE-THIS"),
]

_IGNORE = re.compile(
    r"--.*?luauguard:\s*ignore(?:\s+(?P<ids>LG\d{3}(?:\s*,\s*LG\d{3})*))?", re.I
)


@dataclass
class _Callback:
    kind: str  # "event" or "function"
    remote: str
    client_params: list[str]
    start: int
    body_start: int
    body_end: int


def _param_names(raw: str) -> list[str]:
    names = []
    for part in raw.split(","):
        name = part.strip().split(":")[0].strip()
        names.append(name if re.fullmatch(r"[A-Za-z_]\w*", name) else "")
    return names


def _find_callbacks(code: str) -> list[_Callback]:
    found = []
    for kind, rx in (("event", _EVENT), ("function", _INVOKE)):
        for m in rx.finditer(code):
            names = _param_names(m.group("params"))
            end = find_block_end(code, m.end())
            if end is None:
                end = min(len(code), m.end() + _FALLBACK_BODY)
            client = [n for n in names[1:] if n]
            found.append(_Callback(kind, m.group("remote"), client, m.start(), m.end(), end))
    return sorted(found, key=lambda c: c.start)


def _is_client(path: Path, code: str) -> bool:
    lowered = str(path).lower()
    return "localscript" in lowered or "client" in lowered or bool(
        re.search(r"\bRunService\s*:\s*IsClient\s*\(", code)
    )


def _suppressions(source: str) -> dict[int, set[str] | None]:
    """Map line number to suppressed rule ids (None means every rule)."""
    out: dict[int, set[str] | None] = {}
    for n, line in enumerate(source.split("\n"), 1):
        m = _IGNORE.search(line)
        if not m:
            continue
        ids = {i.strip().upper() for i in m.group("ids").split(",")} if m.group("ids") else None
        targets = [n]
        if line.lstrip().startswith("--"):
            targets.append(n + 1)  # a standalone directive applies to the next line
        for t in targets:
            if t not in out:
                out[t] = ids
            elif out[t] is None or ids is None:
                out[t] = None
            else:
                out[t] = out[t] | ids  # type: ignore[operator]
    return out


class _Scan:
    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source
        masked = mask(source)
        self.code = masked.code
        self.text = masked.with_strings
        self.lines = source.split("\n")
        self.findings: list[Finding] = []

    def add(self, rule_id: str, offset: int, message: str, recommendation: str) -> None:
        rule = RULES_BY_ID[rule_id]
        line = self.source.count("\n", 0, offset) + 1
        snippet = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        self.findings.append(
            Finding(rule_id, rule.severity, str(self.path), line, message, recommendation, snippet)
        )

    def line_text(self, offset: int) -> str:
        start = self.text.rfind("\n", 0, offset) + 1
        end = self.text.find("\n", offset)
        return self.text[start : len(self.text) if end == -1 else end]

    # LG001
    def loadstring(self) -> None:
        for m in re.finditer(r"\bloadstring\s*\(", self.code):
            self.add("LG001", m.start(), "loadstring() is present.",
                     "Avoid executing dynamically supplied source unless there is a tightly controlled, justified use case.")

    # LG002
    def requires(self) -> None:
        for m in re.finditer(r"(?<![.:\w])require\s*\(", self.code):
            open_idx = m.end() - 1
            close = find_closing_paren(self.code, open_idx)
            if close is None:
                continue
            arg = self.text[open_idx + 1 : close].strip()
            if not arg:
                continue
            static = (
                re.fullmatch(r"\d+", arg)
                or re.fullmatch(r"\"[^\"]*\"|'[^']*'", arg)
                or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", arg)
                or re.search(r"\bgame\s*:|WaitForChild|FindFirstChild", arg)
            )
            if not static:
                self.add("LG002", m.start(), f"require() uses an argument that looks dynamic: {arg[:80]}",
                         "Prefer explicit, trusted ModuleScript references. Never let untrusted client input choose code to require.")

    # LG003, LG004, LG006, LG008, LG009, LG011
    def callbacks(self) -> None:
        for cb in _find_callbacks(self.code):
            body = self.code[cb.body_start : cb.body_end]
            self._reward(cb, body)
            if not _VALIDATION.search(body):
                if cb.kind == "event":
                    self.add("LG004", cb.start, "Could not find an obvious validation or rate-limit check in this OnServerEvent callback.",
                             "Review manually. Validate argument types, ranges, permissions, and game context on the server; rate-limit spam-prone actions.")
                else:
                    self.add("LG009", cb.start, "Could not find an obvious validation check in this OnServerInvoke callback.",
                             "Review manually. Validate argument types, ranges and permissions, and never return data the caller should not see.")
            if cb.kind == "event" and re.search(r"\bFireAllClients\s*\(", body):
                self.add("LG006", cb.start, "FireAllClients() appears inside a client-triggered server callback.",
                         "Validate authorization and payload before broadcasting; avoid relaying arbitrary client input.")
            self._bounds(cb, body)
            self._http(cb, body)

    def _reward(self, cb: _Callback, body: str) -> None:
        reward = next((p for p in cb.client_params if re.search(_MONEY, p, re.I)), None)
        if not reward:
            return
        r = re.escape(reward)
        update = rf"\+=\s*{r}\b|=\s*[^;\n]*\+\s*{r}\b|SetAttribute\s*\([^)]*\b{r}\b|\.Value\s*=\s*{r}\b"
        if re.search(update, body):
            self.add("LG003", cb.start, f"Remote callback appears to use client parameter {reward!r} in a reward/currency update.",
                     "Calculate rewards and prices on the server from trusted game state. Validate type, range, permission, and game context.")

    def _bounds(self, cb: _Callback, body: str) -> None:
        for p in cb.client_params:
            r = re.escape(p)
            if re.search(rf"\b{r}\s*=\s*math\.(?:clamp|min)\b", body):
                continue
            if (
                re.search(rf"\bfor\s+\w+\s*=\s*[\w.]+\s*,\s*{r}\b", body)
                or re.search(rf"\bstring\.rep\s*\([^)]*,\s*{r}\b", body)
                or re.search(rf"\btable\.create\s*\(\s*{r}\b", body)
            ):
                self.add("LG008", cb.start, f"Loop bound or allocation size appears to come directly from client parameter {p!r}.",
                         "Clamp client-controlled quantities to a small server-defined range before loops or allocations.")
                break

    def _http(self, cb: _Callback, body: str) -> None:
        for hm in re.finditer(r":\s*(?:GetAsync|PostAsync|RequestAsync)\s*\(", body):
            open_idx = hm.end() - 1
            close = find_closing_paren(body, open_idx)
            args = body[open_idx : close if close is not None else open_idx + 300]
            used = next((p for p in cb.client_params if re.search(rf"\b{re.escape(p)}\b", args)), None)
            if used:
                self.add("LG011", cb.body_start + hm.start(), f"Client parameter {used!r} is used in an outbound HTTP request.",
                         "Never build URLs or request bodies from client input. Use an allowlist of fixed endpoints and validate every value on the server.")

    # LG005
    def client_currency(self) -> None:
        if not _is_client(self.path, self.code):
            return
        pattern = r"\.Value\s*[+\-*/]?=(?!=)|SetAttribute\s*\("
        for m in re.finditer(pattern, self.code):
            if _CURRENCY_WORDS.search(self.line_text(m.start())):
                self.add("LG005", m.start(), "Client-side script appears to modify a currency-like value or attribute.",
                         "Keep authoritative currency and progression changes on the server. Clients should request actions and display server-confirmed results.")

    # LG007 (scans raw source: a key in a comment is still published)
    def secrets(self) -> None:
        for pattern in _SECRET_PATTERNS:
            for m in pattern.finditer(self.source):
                self.add("LG007", m.start(), "Source contains text matching a common hard-coded secret/token pattern.",
                         "Do not commit real credentials. Revoke exposed keys immediately and use appropriate secret storage or server-side configuration.")

    # LG010
    def touched(self) -> None:
        for m in _TOUCHED.finditer(self.code):
            end = find_block_end(self.code, m.end())
            if end is None:
                end = min(len(self.code), m.end() + _FALLBACK_BODY)
            body = self.code[m.end() : end]
            acts = re.search(
                r"\bTakeDamage\s*\(|\.Health\s*[+\-]?=(?!=)|\+=|\.Value\s*[+\-]?=(?!=)|:\s*Clone\s*\(|\bInstance\.new\b",
                body,
            )
            if acts and not _DEBOUNCE.search(body):
                self.add("LG010", m.start(), "Touched handler changes state without an obvious debounce.",
                         "Touched can fire many times per second. Add a per-player cooldown or a one-shot flag before rewarding, damaging or spawning.")


def scan_text(path: Path, source: str, *, disabled: Iterable[str] = ()) -> list[Finding]:
    """Scan one file's source. `disabled` is a collection of rule ids to skip."""
    scan = _Scan(path, source)
    scan.loadstring()
    scan.requires()
    scan.callbacks()
    scan.client_currency()
    scan.secrets()
    scan.touched()

    off = {d.upper() for d in disabled}
    suppressed = _suppressions(source)
    seen: set[tuple[str, str, int]] = set()
    result = []
    for f in scan.findings:
        if f.rule_id in off:
            continue
        ids = suppressed.get(f.line, False)
        if ids is None or (ids is not False and f.rule_id in ids):
            continue
        key = (f.rule_id, f.file, f.line)
        if key not in seen:
            seen.add(key)
            result.append(f)
    return sorted(result, key=lambda f: (f.file, f.line, f.rule_id))


def iter_scripts(path: Path, excludes: frozenset[str] = DEFAULT_EXCLUDES) -> Iterator[Path]:
    if path.is_file():
        if path.suffix.lower() in SUFFIXES:
            yield path
    elif path.is_dir():
        for p in sorted(path.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in SUFFIXES:
                continue
            if any(part in excludes for part in p.relative_to(path).parts[:-1]):
                continue
            yield p


def scan_path(
    path: Path,
    *,
    disabled: Iterable[str] = (),
    excludes: frozenset[str] = DEFAULT_EXCLUDES,
) -> list[Finding]:
    disabled = tuple(disabled)
    result: list[Finding] = []
    for script in iter_scripts(path, excludes):
        try:
            source = script.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            print(f"warning: cannot read {script}: {exc}", file=sys.stderr)
            continue
        result.extend(scan_text(script, source, disabled=disabled))
    return result
