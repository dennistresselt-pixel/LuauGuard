"""Output formats: text, json and SARIF 2.1.0 (for GitHub code scanning)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .rules import Finding, Rule

_SARIF_LEVEL = {"high": "error", "medium": "warning", "low": "note", "info": "note"}


def to_text(findings: Sequence[Finding]) -> str:
    if not findings:
        return "LuauGuard: no findings at the selected threshold. A clean report is not proof of security."
    parts = []
    for f in findings:
        block = f"[{f.severity.upper()}] {f.rule_id} {f.file}:{f.line}\n  {f.message}\n  Recommendation: {f.recommendation}"
        if f.snippet:
            block += f"\n  Code: {f.snippet}"
        parts.append(block + "\n")
    parts.append(f"{len(findings)} finding(s). Review each finding manually.")
    return "\n".join(parts)


def to_json(findings: Sequence[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2)


def _uri(file: str) -> str:
    p = Path(file)
    try:
        p = p.resolve().relative_to(Path.cwd().resolve())
    except (ValueError, OSError):
        pass
    return p.as_posix()


def to_sarif(findings: Sequence[Finding], rules: Sequence[Rule], version: str) -> str:
    index = {r.rule_id: i for i, r in enumerate(rules)}
    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LuauGuard",
                        "version": version,
                        "rules": [
                            {
                                "id": r.rule_id,
                                "name": r.title,
                                "shortDescription": {"text": r.title},
                                "fullDescription": {"text": r.description},
                                "defaultConfiguration": {"level": _SARIF_LEVEL[r.severity]},
                            }
                            for r in rules
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": f.rule_id,
                        "ruleIndex": index[f.rule_id],
                        "level": _SARIF_LEVEL[f.severity],
                        "message": {"text": f"{f.message} {f.recommendation}"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": _uri(f.file)},
                                    "region": {"startLine": f.line},
                                }
                            }
                        ],
                    }
                    for f in findings
                ],
            }
        ],
    }
    return json.dumps(doc, indent=2)
