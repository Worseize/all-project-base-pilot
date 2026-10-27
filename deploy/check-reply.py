#!/usr/bin/env python3
"""Check a reply to the owner: «не сделано» may contain only debt board rows.

A free sentence in the reply is work that lives nowhere; a board row missing
from the reply is work the owner cannot see. Both directions fail.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOARD = ROOT / "DEBTS.md"
TAG_RE = re.compile(r"\b([DWLN][A-Z0-9-]*[A-Z0-9])\b")
EMPTY_WORDS = {"пусто", "долгов нет", "ничего", "—", "-", "нет"}
HEADING_RE = re.compile(r"(?im)^#{2,4}\s*(?:что\s+)?не\s+сделано\s*:?\s*$")
TABLE_COLUMNS = ["сделано", "не сделано", "осталось"]


def load_debt_check():
    path = ROOT / "deploy" / "debt-check.py"
    spec = importlib.util.spec_from_file_location("debt_check", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cells(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def tables(lines: list[str]) -> list[list[str]]:
    found: list[list[str]] = []
    block: list[str] = []
    for line in lines + [""]:
        if line.startswith("|"):
            block.append(line)
            continue
        if len(block) >= 2:
            found.append(block)
        block = []
    return found


def not_done_items(text: str) -> list[str]:
    lines = text.splitlines()
    items: list[str] = []
    for index, line in enumerate(lines):
        if not HEADING_RE.match(line):
            continue
        for follow in lines[index + 1:]:
            if re.match(r"^#{1,4}\s", follow):
                break
            if follow.strip():
                items.append(follow)
    for block in tables(lines):
        header = [cell.lower() for cell in cells(block[0])]
        if header[:3] != TABLE_COLUMNS:
            continue
        for row in block[2:]:
            row_cells = cells(row)
            if len(row_cells) < 2:
                continue
            for part in re.split(r"<br\s*/?>|;|\n", row_cells[1]):
                if part.strip():
                    items.append(part)
    return [item.strip(" -*\t") for item in items if item.strip(" -*\t")]


def board_tags(path: Path) -> list[str]:
    tags: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            first = cells(line)[0]
            if TAG_RE.fullmatch(first):
                tags.append(first)
    return tags


def check_reply(text: str, board: Path = DEFAULT_BOARD) -> list[str]:
    debt_check = load_debt_check()
    board_errors = debt_check.check_board(board)
    if board_errors:
        return [f"доска: {error}" for error in board_errors[:3]]
    known = set(board_tags(board))
    items = not_done_items(text)
    if not items:
        return ["нет раздела «не сделано» или он пуст, а на доске есть долги"] if known else []
    errors: list[str] = []
    reply: set[str] = set()
    for item in items:
        found = TAG_RE.findall(item)
        if found:
            reply.update(found)
        elif item.lower() not in EMPTY_WORDS:
            errors.append(f"свободный пункт в «не сделано»: «{item}»")
    for tag in sorted(reply - known):
        errors.append(f"тег {tag} не строка доски")
    for tag in sorted(known - reply):
        errors.append(f"строка {tag} забыта в «не сделано»")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else None
    if path is None:
        print("usage: check-reply.py <reply.md> [board.md]", file=sys.stderr)
        return 2
    board = Path(argv[2]) if len(argv) > 2 else DEFAULT_BOARD
    errors = check_reply(path.read_text(encoding="utf-8"), board)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
