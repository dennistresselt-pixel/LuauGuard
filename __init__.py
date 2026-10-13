"""LuauGuard: heuristic static security checks for Roblox Luau scripts."""

__version__ = "0.3.0"

from .cli import main  # noqa: E402
from .rules import RULES, Finding, Rule  # noqa: E402
from .scanner import scan_path, scan_text  # noqa: E402

__all__ = ["__version__", "main", "RULES", "Finding", "Rule", "scan_path", "scan_text"]
