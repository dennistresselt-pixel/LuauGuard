"""Command line interface."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .report import to_json, to_sarif, to_text
from .rules import RANK, RULES, RULES_BY_ID
from .scanner import DEFAULT_EXCLUDES, scan_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="luauguard",
        description="Heuristic static security checks for Roblox Luau scripts.",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="One or more .lua/.luau files or directories")
    parser.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    parser.add_argument("--min-severity", choices=tuple(RANK), default="low")
    parser.add_argument("--disable", default="", metavar="IDS", help="Comma separated rule ids to skip, e.g. LG004,LG010")
    parser.add_argument("--include-packages", action="store_true", help="Also scan Packages, node_modules and similar folders")
    parser.add_argument("--list-rules", action="store_true")
    parser.add_argument("--version", action="version", version=f"luauguard {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        print(json.dumps([asdict(r) for r in RULES], indent=2))
        return 0
    if not args.paths:
        parser.error("at least one path is required unless --list-rules is used")

    disabled = [d.strip().upper() for d in args.disable.split(",") if d.strip()]
    unknown = [d for d in disabled if d not in RULES_BY_ID]
    if unknown:
        parser.error(f"unknown rule id(s) in --disable: {', '.join(unknown)}")

    for path in args.paths:
        if not path.exists():
            print(f"error: path does not exist: {path}", file=sys.stderr)
            return 2

    excludes = frozenset() if args.include_packages else DEFAULT_EXCLUDES
    findings = []
    for path in args.paths:
        findings.extend(scan_path(path, disabled=disabled, excludes=excludes))
    findings = [f for f in findings if RANK[f.severity] >= RANK[args.min_severity]]

    if args.format == "json":
        print(to_json(findings))
    elif args.format == "sarif":
        print(to_sarif(findings, RULES, __version__))
    else:
        print(to_text(findings))
    return 1 if findings else 0
