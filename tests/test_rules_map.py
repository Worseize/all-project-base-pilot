import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))

spec = importlib.util.spec_from_file_location("rules_check", DEPLOY / "rules-check.py")
rules_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules_check)

HEADER = "| # | Правило | Проверка | Тип |"
SEP = "| --- | --- | --- | --- |"


def rule(index, check="`verify.py` — gofmt; `tests/test_verify.py`", kind="авто"):
    return f"| {index} | правило {index} | {check} | {kind} |"


def rules(rows=None) -> str:
    rows = rows if rows is not None else [rule(i) for i in range(1, 11)]
    return "# Карта\n\n" + HEADER + "\n" + SEP + "\n" + "\n".join(rows) + "\n"


class RulesMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "RULES-TESTS.md"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text):
        self.path.write_text(text, encoding="utf-8")
        return rules_check.check_map(self.path)

    def test_complete_map_passes(self):
        self.assertEqual(self.check(rules()), [])

    def test_missing_rule_fails(self):
        errors = self.check(rules([rule(i) for i in range(1, 10)]))
        self.assertTrue(any("10" in error for error in errors))

    def test_duplicate_rule_fails(self):
        self.assertTrue(self.check(rules([*[rule(i) for i in range(1, 10)], rule(1)])))

    def test_extra_rule_fails(self):
        self.assertTrue(self.check(rules([*[rule(i) for i in range(1, 11)], rule(11)])))

    def test_bad_type_fails(self):
        rows = [rule(i) for i in range(1, 10)] + [rule(10, kind="полуавто")]
        self.assertTrue(self.check(rules(rows)))

    def test_auto_check_without_file_fails(self):
        rows = [rule(i) for i in range(1, 10)] + [rule(10, check="`no/such/file.py`")]
        errors = self.check(rules(rows))
        self.assertTrue(any("не найден" in error for error in errors))

    def test_auto_check_without_test_fails(self):
        rows = [rule(i) for i in range(1, 10)] + [rule(10, check="`verify.py` — gofmt")]
        errors = self.check(rules(rows))
        self.assertTrue(any("нет теста" in error for error in errors))

    def test_manual_check_without_procedure_fails(self):
        rows = [rule(i) for i in range(1, 10)] + [rule(10, check="", kind="ручная")]
        self.assertTrue(self.check(rules(rows)))

    def test_repository_map_is_valid(self):
        self.assertEqual(rules_check.check_map(rules_check.MAP), [])


if __name__ == "__main__":
    unittest.main()
