"""Tiny Luau lexer: blank out comments and string contents.

The rules in this project are regular expressions. Running them on raw source
produces false positives for text inside comments and strings, so every rule works
on a masked copy instead. Masking replaces characters with spaces and keeps
newlines, so offsets and line numbers still point into the original source.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Masked", "mask", "find_block_end", "find_closing_paren"]

_LONG_OPEN = re.compile(r"\[(=*)\[")
_KEEP = "\r\n"


@dataclass(frozen=True)
class Masked:
    """Two masked views of one source file, both the same length as the original."""

    code: str  # comments blanked, string contents blanked (quotes are kept)
    with_strings: str  # comments blanked, string contents kept


def _blank(chars: list[str], start: int, end: int) -> None:
    for k in range(start, end):
        if chars[k] not in _KEEP:
            chars[k] = " "


def _quoted_end(source: str, start: int) -> tuple[int, bool]:
    """Return (end offset, terminated) for a '...' or "..." string."""
    quote = source[start]
    n = len(source)
    j = start + 1
    while j < n:
        ch = source[j]
        if ch == "\\":
            j += 2
            continue
        if ch == quote:
            return j + 1, True
        if ch == "\n":
            return j, False  # unterminated: stop at the end of the line
        j += 1
    return n, False


def _interpolated(source: str, start: int) -> tuple[int, list[tuple[int, int]]]:
    """Return (end offset, text ranges) for a Luau `interpolated {expr}` string.

    Only the literal text parts are returned; code inside {} stays visible.
    """
    n = len(source)
    j = start + 1
    text_start = j
    ranges: list[tuple[int, int]] = []
    while j < n:
        ch = source[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "`":
            ranges.append((text_start, j))
            return j + 1, ranges
        if ch == "{":
            ranges.append((text_start, j))
            depth = 1
            j += 1
            while j < n and depth:
                if source[j] == "{":
                    depth += 1
                elif source[j] == "}":
                    depth -= 1
                j += 1
            text_start = j
            continue
        j += 1
    ranges.append((text_start, n))
    return n, ranges


def mask(source: str) -> Masked:
    n = len(source)
    code = list(source)
    keep = list(source)
    i = 0
    while i < n:
        ch = source[i]
        if ch == "-" and source.startswith("--", i):
            m = _LONG_OPEN.match(source, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                found = source.find(close, m.end())
                end = n if found == -1 else found + len(close)
            else:
                found = source.find("\n", i)
                end = n if found == -1 else found
            _blank(code, i, end)
            _blank(keep, i, end)
            i = end
        elif ch in "\"'":
            end, closed = _quoted_end(source, i)
            _blank(code, i + 1, end - 1 if closed else end)
            i = end
        elif ch == "[":
            m = _LONG_OPEN.match(source, i)
            if m:
                close = "]" + m.group(1) + "]"
                found = source.find(close, m.end())
                if found == -1:
                    end = inner_end = n
                else:
                    end = found + len(close)
                    inner_end = found
                _blank(code, m.end(), inner_end)
                i = end
            else:
                i += 1
        elif ch == "`":
            end, ranges = _interpolated(source, i)
            for a, b in ranges:
                _blank(code, a, b)
            i = end
        else:
            i += 1
    return Masked("".join(code), "".join(keep))


_BLOCK = re.compile(r"\b(function|if|do|end)\b")
# An `if` right after one of these starts an if-expression (no matching `end`).
_IF_EXPR_PREV = re.compile(r"(?:[=(,{\[+*/%^]|\.\.|\b(?:return|and|or|not|in)\b)\s*$")


def find_block_end(code: str, start: int, depth: int = 1) -> int | None:
    """Offset of the `end` that closes a block opened just before `start`.

    `code` must be masked. Counts function, if and do (for and while use `do`).
    `repeat ... until` has no `end` and if-expressions are skipped. Returns None
    when the source is unbalanced.
    """
    for m in _BLOCK.finditer(code, start):
        word = m.group(1)
        if word == "end":
            depth -= 1
            if depth == 0:
                return m.start()
        elif word == "if":
            before = code[max(0, m.start() - 16) : m.start()]
            if not _IF_EXPR_PREV.search(before):
                depth += 1
        else:
            depth += 1
    return None


def find_closing_paren(code: str, open_idx: int) -> int | None:
    """Offset of the `)` matching the `(` at `open_idx` in masked code."""
    depth = 0
    for k in range(open_idx, len(code)):
        c = code[k]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return k
    return None
