#!/usr/bin/env python3
"""Print the open debt board. The first column is always #."""
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "DEBTS.md"
HEADER = "| # | Долг | Кому | Почему открыт | Что разблокирует | Приоритет | С какой версии |"


def main() -> int:
    if not BOARD.is_file():
        print("DEBTS.md missing", file=sys.stderr)
        return 1
    print(HEADER)
    print("| --- | --- | --- | --- | --- | --- | --- |")
    in_open = False
    rows = 0
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        if line.strip() == "## Открытые":
            in_open = True
            continue
        if line.startswith("## "):
            in_open = False
        if in_open and line.startswith("| D"):
            print(line)
            rows += 1
    if rows == 0:
        print("| — | долгов нет | — | — | — | — | — |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
