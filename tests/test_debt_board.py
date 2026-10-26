import sys
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))

import importlib

debt_check = importlib.import_module("debt-check")

HEADER = "| # | Долг | Кому | Почему открыт | Что разблокирует | Приоритет | С какой версии |"
SEP = "| --- | --- | --- | --- | --- | --- | --- |"


def board(open_rows=(), later_rows=(), wait_rows=()) -> str:
    parts = ["# Доска долгов", ""]
    for title, rows, total in (
        ("Открытые", open_rows, "открытых"),
        ("Отложено владельцем", later_rows, "отложенных"),
        ("Ждём владельца", wait_rows, "ждут владельца"),
    ):
        parts += [f"## {title}", "", HEADER, SEP, *rows, "", f"Итого {total}: {len(rows)}.", ""]
    return "\n".join(parts)


def row(tag="D-ONE", who="я", why="причина", unblock="действие", prio="P1", version="0.9.46"):
    return f"| {tag} | долг | {who} | {why} | {unblock} | {prio} | {version} |"


class DebtBoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "DEBTS.md"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text):
        self.path.write_text(text, encoding="utf-8")
        return debt_check.check_board(self.path)

    def test_valid_board_passes(self):
        self.assertEqual(self.check(board(open_rows=[row()])), [])

    def test_empty_board_with_zero_totals_passes(self):
        self.assertEqual(self.check(board()), [])

    def test_six_columns_fail(self):
        broken = "| D-ONE | долг | я | причина | действие | P1 |"
        self.assertTrue(self.check(board(open_rows=[broken])))

    def test_unknown_priority_fails(self):
        self.assertTrue(self.check(board(open_rows=[row(prio="P3")])))

    def test_empty_unblock_fails(self):
        self.assertTrue(self.check(board(open_rows=[row(unblock="")])))

    def test_unknown_recipient_fails(self):
        self.assertTrue(self.check(board(open_rows=[row(who="кто-то")])))

    def test_wait_tag_in_open_section_fails(self):
        self.assertTrue(self.check(board(open_rows=[row(tag="W-ONE", who="владелец")])))

    def test_wait_row_in_wait_section_passes(self):
        self.assertEqual(
            self.check(board(wait_rows=[row(tag="W-ONE", who="владелец")])), []
        )

    def test_duplicate_tag_fails(self):
        self.assertTrue(self.check(board(open_rows=[row(), row()])))

    def test_total_mismatch_fails(self):
        text = board(open_rows=[row()]).replace("Итого открытых: 1.", "Итого открытых: 0.")
        self.assertTrue(self.check(text))

    def test_missing_total_fails(self):
        text = board(open_rows=[row()]).replace("Итого открытых: 1.\n", "")
        errors = self.check(text)
        self.assertTrue(any("Итого" in error for error in errors))

    def test_closed_section_fails(self):
        text = board(open_rows=[row()]).replace("## Ждём владельца", "## Закрытые")
        self.assertTrue(self.check(text))

    def test_missing_file_fails(self):
        self.assertTrue(debt_check.check_board(Path(self.tmp.name) / "missing.md"))

    def test_repository_board_is_valid(self):
        self.assertEqual(debt_check.check_board(debt_check.BOARD), [])


if __name__ == "__main__":
    unittest.main()
