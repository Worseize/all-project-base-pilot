#!/usr/bin/env python3
"""Validate DEBTS.md: sections, seven columns, tags, priorities, totals.

Exit 0 when the board is well formed, 1 with one line per defect.
The board is the owner-facing registry; a silent break costs a whole turn.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "DEBTS.md"
SECTIONS = ("Открытые", "Отложено владельцем", "Ждём владельца")
SECTION_TAG = {"D": "Открытые", "N": "Открытые", "W": "Ждём владельца", "L": "Отложено владельцем"}
WHO = {"я", "владелец", "владелец (позже)", "узел"}
PRIORITIES = {"P0", "P1", "P2"}
HEADER = ["#", "Долг", "Кому", "Почему открыт", "Что разблокирует", "Приоритет", "С какой версии"]
TAG_RE = re.compile(r"^(D|W|L|N)[A-Z0-9-]+$")
TOTAL_RE = re.compile(r"^Итого ([^:]+): (\d+)\.$")
TOTAL_LABEL = {"Открытые": "открытых", "Отложено владельцем": "отложенных", "Ждём владельца": "ждут владельца"}


def cells(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def check_rows(number: int, section: str, row: list[str], seen: set[str]) -> list[str]:
    errors: list[str] = []
    if row == HEADER:
        return errors
    if row and set(row) == {"---"}:
        return errors
    tag = row[0] if row else ""
    if not TAG_RE.fullmatch(tag):
        return [f"строка {number}: тег «{tag}» не D…/W…/L…/N…"]
    if len(row) != len(HEADER):
        return [f"строка {number}: {len(row)} полей, нужно {len(HEADER)}"]
    if tag in seen:
        errors.append(f"строка {number}: тег «{tag}» повторяется")
    seen.add(tag)
    expected = SECTION_TAG[tag[0]]
    if section != expected:
        errors.append(f"строка {number}: тег «{tag}» не в разделе «{expected}»")
    title, who, why, unblock, priority, version = (part.strip() for part in row[1:])
    if not title:
        errors.append(f"строка {number}: пустой «Долг»")
    if who not in WHO:
        errors.append(f"строка {number}: «Кому» = «{who}», нужно я/владелец/владелец (позже)/узел")
    if not why:
        errors.append(f"строка {number}: пустой «Почему открыт»")
    if not unblock:
        errors.append(f"строка {number}: пустой «Что разблокирует» — это жалоба, а не долг")
    if priority not in PRIORITIES:
        errors.append(f"строка {number}: приоритет «{priority}», нужно P0/P1/P2")
    if not version:
        errors.append(f"строка {number}: пустой «С какой версии»")
    return errors


def check_board(path: Path) -> list[str]:
    if not path.is_file():
        return [f"нет файла {path.name}"]
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    found = [line[3:].strip() for line in lines if line.startswith("## ")]
    if found != list(SECTIONS):
        errors.append("разделы должны быть ровно: " + ", ".join(SECTIONS) + " — и в этом порядке")
    section = ""
    rows = {name: 0 for name in SECTIONS}
    totals: dict[str, int] = {}
    seen: set[str] = set()
    for number, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|"):
            match = TOTAL_RE.match(line.strip())
            if match:
                totals[section] = int(match.group(2))
            continue
        if section not in SECTIONS:
            errors.append(f"строка {number}: строка таблицы вне разделов")
            continue
        row = cells(line)
        row_errors = check_rows(number, section, row, seen)
        errors.extend(row_errors)
        if not row_errors and row and TAG_RE.fullmatch(row[0]):
            rows[section] += 1
    for name in SECTIONS:
        if name not in totals:
            errors.append(f"раздел «{name}»: нет строки «Итого {TOTAL_LABEL[name]}: N.»")
        elif totals[name] != rows[name]:
            errors.append(f"раздел «{name}»: итог {totals[name]}, строк {rows[name]}")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else BOARD
    errors = check_board(path)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
