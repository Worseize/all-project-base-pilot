import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))

spec = importlib.util.spec_from_file_location(
    "check_personal_data", DEPLOY / "check-personal-data.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PersonalDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_placeholders_pass(self):
        self.write("docs/PERSONAL-DATA.md", "домен example.test, адрес 192.0.2.10, /home/agent, ci@example.invalid\n")
        self.assertEqual(checker.check_personal_data(self.root), [])

    def test_real_address_fails(self):
        self.write("docs/HOST.md", "сервер 8.8.8.8\n")
        self.assertTrue(checker.check_personal_data(self.root))

    def test_real_email_fails(self):
        self.write("docs/HOST.md", "почта boss@real-host.ru\n")
        self.assertTrue(checker.check_personal_data(self.root))

    def test_private_home_fails(self):
        self.write("docs/HOST.md", "конфиг /home/alice/.secrets\n")
        self.assertTrue(checker.check_personal_data(self.root))

    def test_token_fails(self):
        self.write("docs/HOST.md", "token " + "ghp_" + "a" * 24 + "\n")
        self.assertTrue(checker.check_personal_data(self.root))

    def test_tests_and_acceptance_are_skipped(self):
        self.write("tests/fixture.md", "8.8.8.8\n")
        self.write("docs/acceptance/history.md", "8.8.8.8\n")
        self.assertEqual(checker.check_personal_data(self.root), [])


if __name__ == "__main__":
    unittest.main()
