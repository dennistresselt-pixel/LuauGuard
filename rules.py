"""Rule registry and the Finding type."""
from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("info", "low", "medium", "high")
RANK = {name: i for i, name in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    severity: str
    description: str


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    recommendation: str
    snippet: str


RULES = [
    Rule("LG001", "Dynamic code execution", "high", "Flags loadstring() calls."),
    Rule("LG002", "Potentially dynamic require", "medium", "Flags require() arguments that do not look like explicit module references."),
    Rule("LG003", "Client-supplied reward/currency", "high", "Detects client parameters used in reward-like updates inside remote callbacks."),
    Rule("LG004", "Remote event validation review", "medium", "Flags OnServerEvent callbacks without obvious validation markers."),
    Rule("LG005", "Client-side currency mutation", "medium", "Flags currency-like value mutations in likely client scripts."),
    Rule("LG006", "Broadcast from remote callback", "medium", "Flags FireAllClients() inside a client-triggered server callback."),
    Rule("LG007", "Potential hard-coded secret", "high", "Flags common token, key, cookie and webhook patterns; review false positives carefully."),
    Rule("LG008", "Client-controlled loop bound or allocation", "medium", "Flags a remote parameter controlling a loop bound, string.rep count or table.create size."),
    Rule("LG009", "Remote function validation review", "medium", "Flags OnServerInvoke callbacks without obvious validation markers."),
    Rule("LG010", "Touched handler without debounce", "low", "Flags Touched handlers that change state or health without an obvious debounce."),
    Rule("LG011", "Client data in outbound HTTP request", "high", "Flags a remote parameter used in an HttpService request."),
]

RULES_BY_ID = {r.rule_id: r for r in RULES}
