#!/usr/bin/env python3
"""Validate docs/RULES-TESTS.md: every rule has a check that exists."""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "RULES-TESTS.md"
HEADER = ["#", "Правило", "Проверка", "Тип"]
TYPES = {"авто", "ручная"}
PATH_RE = re.compile(r"`([^`]+)`")


def cells(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def path_tokens(check: str) -> list[str]:
    tokens = PATH_RE.findall(check)
    return [
        token for token in tokens
        if token.endswith((".py", ".sh", ".md", ".json", ".go")) or "/" in token
    ]


def check_map(path: Path) -> list[str]:
    if not path.is_file():
        return [f"нет файла {path.name}"]
    errors: list[str] = []
    rows: dict[int, list[str]] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.startswith("|"):
            continue
        row = cells(raw)
        if row == HEADER or set(row) == {"---"}:
            continue
        if len(row) != 4:
            errors.append(f"строка {number}: {len(row)} полей, нужно 4")
            continue
        rule, check, kind = row[1], row[2], row[3]
        try:
            index = int(row[0])
        except ValueError:
            errors.append(f"строка {number}: номер правила «{row[0]}» не число")
            continue
        if index in rows:
            errors.append(f"строка {number}: правило {index} повторяется")
            continue
        if not rule:
            errors.append(f"строка {number}: пустое правило")
        if kind not in TYPES:
            errors.append(f"строка {number}: тип «{kind}», нужно авто/ручная")
        elif kind == "ручная" and not check:
            errors.append(f"строка {number}: у ручной проверки нет процедуры")
        elif kind == "авто":
            paths = path_tokens(check)
            if not paths:
                errors.append(f"строка {number}: у авто-проверки нет файла в обратных кавычках")
            for item in paths:
                if not (ROOT / item).exists():
                    errors.append(f"строка {number}: файл проверки не найден: {item}")
        rows[index] = row
    missing = [str(index) for index in range(1, 11) if index not in rows]
    if missing:
        errors.append("нет проверки у правил: " + ", ".join(missing))
    extra = [str(index) for index in sorted(rows) if index > 10]
    if extra:
        errors.append("лишние правила: " + ", ".join(extra))
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else MAP
    errors = check_map(path)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
