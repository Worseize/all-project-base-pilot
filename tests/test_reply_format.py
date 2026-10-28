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

HEADER = "| # | Долг | Кому | Почему открыт | Что разблокирует | Приоритет | С какой версии |"
SEP = "| --- | --- | --- | --- | --- | --- | --- |"


def board(*tags: str) -> str:
    rows = [f"| {tag} | долг | я | причина | действие | P1 | 0.9.49 |" for tag in tags]
    return (
        "# Доска\n\n## Открытые\n\n" + "\n".join([HEADER, SEP, *rows])
        + f"\n\nИтого открытых: {len(tags)}.\n\n"
        "## Отложено владельцем\n\n" + HEADER + "\n" + SEP
        + "\n\nИтого отложенных: 0.\n\n"
        "## Ждём владельца\n\n" + HEADER + "\n" + SEP
        + "\n\nИтого ждут владельца: 0.\n"
    )


def board_block(tags) -> str:
    rows = [f"| {tag} | я | долг | действие |" for tag in tags]
    mine = sum(1 for tag in tags if tag.startswith("D"))
    owner = sum(1 for tag in tags if tag.startswith(("W", "L")))
    table = "\n".join(
        ["| # | Кому | Долг | Что разблокирует |", "| --- | --- | --- | --- |", *rows]
    )
    return f"## Доска долгов\n\n{table}\n\nИтого: моих {mine}, у владельца {owner}\n"


def reply(not_done: str, tags, total: str = "auto", tail: str = "") -> str:
    mine = sum(1 for tag in tags if tag.startswith("D"))
    owner = sum(1 for tag in tags if tag.startswith(("W", "L")))
    if total == "auto":
        total = f"Итого: моих {mine}, у владельца {owner}"
    body = board_block(tags).rsplit("Итого:", 1)[0]
    return (
        "почта: EMPTY — разобрано 0\n\n"
        "| Сделано | Не сделано | Осталось |\n"
        "| --- | --- | --- |\n"
        f"| готово | {not_done} | ждём |\n\n"
        + body + total + "\n" + tail
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
        tags = ("D-ONE", "D-TWO")
        self.assertEqual(self.check(reply("`D-ONE`; `D-TWO`", tags), board(*tags)), [])

    def test_free_sentence_fails(self):
        tags = ("D-ONE",)
        errors = self.check(reply("`D-ONE`; ещё допишу отчёт", tags), board(*tags))
        self.assertTrue(any("свободный пункт" in error for error in errors))

    def test_forgotten_row_fails(self):
        tags = ("D-ONE", "D-TWO")
        errors = self.check(reply("`D-ONE`", tags), board(*tags))
        self.assertTrue(any("D-TWO" in error and "забыта" in error for error in errors))

    def test_unknown_tag_fails(self):
        tags = ("D-ONE",)
        errors = self.check(reply("`D-ONE`; `D-GHOST`", tags), board(*tags))
        self.assertTrue(any("D-GHOST" in error for error in errors))

    def test_heading_section_passes(self):
        tags = ("D-ONE", "D-TWO")
        text = (
            "почта: EMPTY — разобрано 0\n\n## Не сделано\n\n- `D-ONE` — валидатор\n"
            "- `D-TWO` — карта\n\n" + board_block(tags)
        )
        self.assertEqual(self.check(text, board(*tags)), [])

    def test_empty_board_passes(self):
        text = reply("пусто", ())
        self.assertEqual(self.check(text, board()), [])

    def test_missing_board_section_fails(self):
        errors = self.check("почта: EMPTY — разобрано 0\n\nИтог без доски.\n", board("D-ONE"))
        self.assertTrue(any("Доска долгов" in error for error in errors))

    def test_board_not_last_fails(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags, tail="\n## После доски\n\nещё раздел\n")
        errors = self.check(text, board(*tags))
        self.assertTrue(any("после «Доска долгов»" in error for error in errors))

    def test_wrong_total_fails(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags, total="Итого: моих 5, у владельца 5")
        errors = self.check(text, board(*tags))
        self.assertTrue(any("итог в ответе" in error for error in errors))

    def test_missing_mail_line_fails(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags).split("\n", 1)[1]
        errors = self.check(text, board(*tags))
        self.assertTrue(any("первая строка" in error for error in errors))

    def test_tag_in_done_column_does_not_count(self):
        tags = ("D-ONE", "D-TWO")
        text = (
            "почта: EMPTY — разобрано 0\n\n"
            "| Сделано | Не сделано | Осталось |\n| --- | --- | --- |\n"
            "| `D-ONE` готов | `D-TWO` | ждём |\n\n" + board_block(tags)
        )
        errors = self.check(text, board(*tags))
        self.assertTrue(any("D-ONE" in error for error in errors))

    def test_bom_prefix_passes(self):
        tags = ("D-ONE",)
        text = "\ufeff" + reply("`D-ONE`", tags)
        self.assertEqual(self.check(text, board(*tags)), [])

    def test_seven_column_board_fails(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags).replace("| # | Кому | Долг | Что разблокирует |", HEADER)
        errors = self.check(text, board(*tags))
        self.assertTrue(any("четыре колонки" in error for error in errors))

    def test_long_cell_fails(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags).replace(
            "| D-ONE | я | долг |", "| D-ONE | я | " + "д" * 51 + " |"
        )
        errors = self.check(text, board(*tags))
        self.assertTrue(any("длиннее" in error for error in errors))

    def test_reply_board_must_match_file(self):
        tags = ("D-ONE",)
        text = reply("`D-ONE`", tags).replace("| D-ONE |", "| D-TWO |")
        errors = self.check(text, board(*tags))
        self.assertTrue(any("не совпадает" in error for error in errors))

    def test_broken_board_fails(self):
        errors = self.check(reply("`D-ONE`", ("D-ONE",)), "# доска без разделов\n")
        self.assertTrue(any("доска" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
