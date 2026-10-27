import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))

spec = importlib.util.spec_from_file_location("check_reply", DEPLOY / "check-reply.py")
check_reply = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_reply)

BOARD_HEADER = "| # | Долг | Кому | Почему открыт | Что разблокирует | Приоритет | С какой версии |"
BOARD_SEP = "| --- | --- | --- | --- | --- | --- | --- |"


def board(*tags: str) -> str:
    rows = [
        f"| {tag} | долг | я | причина | действие | P1 | 0.9.47 |" for tag in tags
    ]
    return (
        "# Доска\n\n## Открытые\n\n" + "\n".join([BOARD_HEADER, BOARD_SEP, *rows])
        + f"\n\nИтого открытых: {len(tags)}.\n\n"
        "## Отложено владельцем\n\n" + BOARD_HEADER + "\n" + BOARD_SEP
        + "\n\nИтого отложенных: 0.\n\n"
        "## Ждём владельца\n\n" + BOARD_HEADER + "\n" + BOARD_SEP
        + "\n\nИтого ждут владельца: 0.\n"
    )


def table_reply(not_done: str, done: str = "сделано") -> str:
    return (
        "Итог.\n\n| Сделано | Не сделано | Осталось |\n"
        "| --- | --- | --- |\n"
        f"| {done} | {not_done} | ждём |\n"
    )


class ReplyFormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.board = Path(self.tmp.name) / "DEBTS.md"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text, board_text):
        self.board.write_text(board_text, encoding="utf-8")
        return check_reply.check_reply(text, self.board)

    def test_all_rows_in_table_pass(self):
        self.assertEqual(self.check(table_reply("`D-ONE`; `D-TWO`"), board("D-ONE", "D-TWO")), [])

    def test_free_sentence_fails(self):
        errors = self.check(table_reply("`D-ONE`; ещё допишу отчёт"), board("D-ONE"))
        self.assertTrue(any("свободный пункт" in error for error in errors))

    def test_forgotten_row_fails(self):
        errors = self.check(table_reply("`D-ONE`"), board("D-ONE", "D-TWO"))
        self.assertTrue(any("D-TWO" in error and "забыта" in error for error in errors))

    def test_unknown_tag_fails(self):
        errors = self.check(table_reply("`D-ONE`; `D-GHOST`"), board("D-ONE"))
        self.assertTrue(any("D-GHOST" in error for error in errors))

    def test_heading_section_passes(self):
        reply = "## Не сделано\n\n- `D-ONE` — валидатор\n- `D-TWO` — карта\n"
        self.assertEqual(self.check(reply, board("D-ONE", "D-TWO")), [])

    def test_empty_board_with_word_pusto_passes(self):
        self.assertEqual(self.check(table_reply("пусто"), board()), [])

    def test_empty_board_without_section_passes(self):
        self.assertEqual(self.check("Просто отчёт без раздела.", board()), [])

    def test_board_rows_without_section_fail(self):
        errors = self.check("Просто отчёт без раздела.", board("D-ONE"))
        self.assertTrue(any("нет раздела" in error for error in errors))

    def test_tag_in_done_column_does_not_count(self):
        reply = (
            "| Сделано | Не сделано | Осталось |\n| --- | --- | --- |\n"
            "| `D-ONE` готов | `D-TWO` | ждём |\n"
        )
        errors = self.check(reply, board("D-ONE", "D-TWO"))
        self.assertTrue(any("D-ONE" in error for error in errors))

    def test_broken_board_fails(self):
        errors = self.check(table_reply("`D-ONE`"), "# доска без разделов\n")
        self.assertTrue(any("доска" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
