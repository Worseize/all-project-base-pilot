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
MAIL_LINE_RE = re.compile(r"^почта:\s*(?:EMPTY|PENDING\s+\d+)\s+—\s+разобрано\s+\d+")
TOTAL_LINE_RE = re.compile(r"(?m)^Итого:\s*моих\s*(\d+),\s*у владельца\s*(\d+)\s*$")
BOARD_COLUMNS = ["#", "кому", "долг", "что разблокирует"]
COLUMN_LIMITS = (8, 18, 50, 60)
ROW_LIMIT = 149


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


def check_order(text: str, board: Path) -> list[str]:
    """Reply starts with the mail line and ends with the debt board section."""
    errors: list[str] = []
    lines = text.splitlines()
    first = next((line.strip() for line in lines if line.strip()), "")
    if not MAIL_LINE_RE.match(first):
        errors.append("первая строка — «почта: EMPTY|PENDING n — разобрано k»")
    headings = [
        (index, line) for index, line in enumerate(lines)
        if re.match(r"^#{2,4}\s", line)
    ]
    board_positions = [
        index for index, line in headings if "Доска долгов" in line
    ]
    if not board_positions:
        return [*errors, "нет раздела «Доска долгов» — доска обязана быть последней"]
    board_pos = board_positions[-1]
    if headings[-1][0] != board_pos:
        errors.append("после «Доска долгов» есть ещё раздел")
    errors.extend(check_board_section(lines[board_pos + 1:], board))
    total = TOTAL_LINE_RE.search(text)
    if not total:
        errors.append("нет строки «Итого: моих N, у владельца M»")
        return errors
    tags = board_tags(board)
    mine = sum(1 for tag in tags if tag.startswith("D"))
    owner = sum(1 for tag in tags if tag.startswith(("W", "L")))
    if (int(total.group(1)), int(total.group(2))) != (mine, owner):
        errors.append(
            f"итог в ответе {total.group(1)}/{total.group(2)}, "
            f"на доске {mine}/{owner}"
        )
    return errors


def check_board_section(lines: list[str], board: Path) -> list[str]:
    """Four columns for the chat window, one line per debt, bounded widths."""
    errors: list[str] = []
    rows = [line.rstrip() for line in lines if line.startswith("|")]
    if len(rows) < 2:
        return ["доска в ответе пуста"]
    header = [cell.lower() for cell in cells(rows[0])]
    if header != BOARD_COLUMNS:
        errors.append("доска в ответе — четыре колонки: #, Кому, Долг, Что разблокирует")
    data = rows[1:]
    if data and set(cells(data[0])) == {"---"}:
        data = data[1:]
    seen: set[str] = set()
    for row in data:
        parts = cells(row)
        if len(parts) != len(BOARD_COLUMNS):
            errors.append(f"строка «{parts[0] if parts else '?'}»: {len(parts)} полей, нужно 4")
            continue
        for index, limit in enumerate(COLUMN_LIMITS):
            if len(parts[index]) > limit:
                errors.append(f"«{parts[0]}»: колонка {index + 1} длиннее {limit}")
        if len(row) > ROW_LIMIT:
            errors.append(f"«{parts[0]}»: строка {len(row)} > {ROW_LIMIT}")
        if TAG_RE.fullmatch(parts[0]):
            seen.add(parts[0])
    known = set(board_tags(board))
    if seen != known:
        missing = ", ".join(sorted(known - seen)) or "—"
        extra = ", ".join(sorted(seen - known)) or "—"
        errors.append(f"доска в ответе не совпадает с файлом: нет {missing}, лишние {extra}")
    return errors


def check_reply(text: str, board: Path = DEFAULT_BOARD) -> list[str]:
    text = text.lstrip("\ufeff")
    debt_check = load_debt_check()
    board_errors = debt_check.check_board(board)
    if board_errors:
        return [f"доска: {error}" for error in board_errors[:3]]
    known = set(board_tags(board))
    items = not_done_items(text)
    errors: list[str] = check_order(text, board)
    if not items:
        if known:
            errors.append("нет раздела «не сделано» или он пуст, а на доске есть долги")
        return errors
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
