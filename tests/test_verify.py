import json
import sys
import tempfile
import unittest
from pathlib import Path

import verify

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.old_root = verify.ROOT
        self.old_config = verify.CONFIG
        self.old_version = verify.VERSION
        self.old_required = verify.REQUIRED
        self.old_schemes = verify.SCHEMES
        self.old_lock = verify.SCHEME_LOCK
        self.tmp = tempfile.TemporaryDirectory()
        verify.ROOT = Path(self.tmp.name)
        verify.CONFIG = {"stack": "go", "forbid_npm": True, "rules_count": 10}
        verify.VERSION = "0.7.9"
        verify.REQUIRED = []
        verify.SCHEMES = {}
        verify.SCHEME_LOCK = verify.ROOT / "docs" / "schemes.lock.json"

    def tearDown(self):
        verify.ROOT = self.old_root
        verify.CONFIG = self.old_config
        verify.VERSION = self.old_version
        verify.REQUIRED = self.old_required
        verify.SCHEMES = self.old_schemes
        verify.SCHEME_LOCK = self.old_lock
        self.tmp.cleanup()

    def test_required_fails_on_missing(self):
        verify.REQUIRED = ["RULES.md"]
        gate = verify.Gate()
        verify.check_required(gate)
        self.assertEqual(gate.failed, 1)

    def test_required_passes(self):
        (verify.ROOT / "RULES.md").write_text("x", encoding="utf-8")
        verify.REQUIRED = ["RULES.md"]
        gate = verify.Gate()
        verify.check_required(gate)
        self.assertEqual(gate.failed, 0)

    def test_npm_artifact_fails(self):
        (verify.ROOT / "package.json").write_text("{}", encoding="utf-8")
        gate = verify.Gate()
        verify.check_no_npm(gate)
        self.assertEqual(gate.failed, 1)

    def test_secret_fails(self):
        (verify.ROOT / "leak.md").write_text(
            "key = AKIA" + "A" * 16 + "\n", encoding="utf-8"
        )
        gate = verify.Gate()
        verify.check_secrets(gate)
        self.assertEqual(gate.failed, 1)

    def test_entropy_fails(self):
        token = "".join(["Zx9Qw8", "Er7Ty6", "Ui5Op4", "As3Df2", "Gh1Jk0", "LmN"])
        (verify.ROOT / "entropy.md").write_text(
            "token = " + token + "\n", encoding="utf-8"
        )
        gate = verify.Gate()
        verify.check_secrets(gate)
        self.assertEqual(gate.failed, 1)

    def test_env_file_fails(self):
        (verify.ROOT / ".env").write_text("TOKEN=1\n", encoding="utf-8")
        gate = verify.Gate()
        verify.check_secrets(gate)
        self.assertEqual(gate.failed, 1)

    def test_junk_fails(self):
        (verify.ROOT / "left.tmp").write_text("x", encoding="utf-8")
        gate = verify.Gate()
        verify.check_junk(gate)
        self.assertEqual(gate.failed, 1)

    def test_large_go_file_fails(self):
        (verify.ROOT / "big.go").write_text("package x\n" + "// line\n" * 400, encoding="utf-8")
        gate = verify.Gate()
        verify.check_go_sizes(gate)
        self.assertEqual(gate.failed, 1)

    def test_small_go_file_passes(self):
        (verify.ROOT / "small.go").write_text(
            "package x\n\nfunc DoThing() {}\n", encoding="utf-8"
        )
        gate = verify.Gate()
        verify.check_go_sizes(gate)
        self.assertEqual(gate.failed, 0)

    def test_commands_pass(self):
        verify.CONFIG = {
            "stack": "python",
            "commands": {"test": f'"{sys.executable}" -c "import sys; sys.exit(0)"'},
        }
        gate = verify.Gate()
        verify.check_commands(gate)
        self.assertEqual(gate.failed, 0)

    def test_commands_fail(self):
        verify.CONFIG = {
            "stack": "python",
            "commands": {"test": f'"{sys.executable}" -c "import sys; sys.exit(1)"'},
        }
        gate = verify.Gate()
        verify.check_commands(gate)
        self.assertEqual(gate.failed, 1)

    def test_ci_gitlab_missing(self):
        verify.CONFIG = {"ci": "gitlab"}
        gate = verify.Gate()
        verify.check_ci(gate)
        self.assertEqual(gate.failed, 1)

    def test_ci_github_present(self):
        path = verify.ROOT / ".github" / "workflows"
        path.mkdir(parents=True)
        (path / "verify.yml").write_text("name: verify\n", encoding="utf-8")
        verify.CONFIG = {"ci": "github"}
        gate = verify.Gate()
        verify.check_ci(gate)
        self.assertEqual(gate.failed, 0)

    def test_ci_azure_present(self):
        (verify.ROOT / "azure-pipelines.yml").write_text("trigger: [main]\n", encoding="utf-8")
        verify.CONFIG = {"ci": ["azure"]}
        gate = verify.Gate()
        verify.check_ci(gate)
        self.assertEqual(gate.failed, 0)

    def test_ci_list_missing(self):
        verify.CONFIG = {"ci": ["github", "gitlab"]}
        gate = verify.Gate()
        verify.check_ci(gate)
        self.assertEqual(gate.failed, 1)

    def test_ci_none(self):
        verify.CONFIG = {"ci": ["none"]}
        gate = verify.Gate()
        verify.check_ci(gate)
        self.assertEqual(gate.failed, 0)
        self.assertEqual(gate.skipped, 1)

    def test_project_sections(self):
        (verify.ROOT / "PROJECT.md").write_text(
            "## Назначение\n## Стек\n## Команды\n## Границы\n## Данные\n## Окружения\n## Исключения\n",
            encoding="utf-8",
        )
        gate = verify.Gate()
        verify.check_sections(
            gate,
            "PROJECT.md",
            ["Назначение", "Стек", "Команды", "Границы", "Данные", "Окружения", "Исключения"],
            "project",
        )
        self.assertEqual(gate.failed, 0)

    def _scheme_fixture(self) -> tuple[Path, Path]:
        docs = verify.ROOT / "docs"
        docs.mkdir()
        image = docs / "scheme.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10000)
        source = verify.ROOT / "RULES.md"
        source.write_text("rules", encoding="utf-8")
        return image, source

    def test_scheme_lock_detects_drift(self):
        image, _ = self._scheme_fixture()
        verify.SCHEMES = {"docs/scheme.png": ["RULES.md"]}
        lock = {
            "version": verify.VERSION,
            "schemes": {
                "docs/scheme.png": {
                    "source_sha": "wrong",
                    "image_sha": verify.sha256_file(image),
                }
            },
        }
        verify.SCHEME_LOCK.parent.mkdir(parents=True, exist_ok=True)
        verify.SCHEME_LOCK.write_text(json.dumps(lock), encoding="utf-8")
        gate = verify.Gate()
        verify.check_schemes(gate)
        self.assertEqual(gate.failed, 1)

    def test_scheme_lock_passes(self):
        image, _ = self._scheme_fixture()
        verify.SCHEMES = {"docs/scheme.png": ["RULES.md"]}
        lock = {
            "version": verify.VERSION,
            "schemes": {
                "docs/scheme.png": {
                    "source_sha": verify.source_hash(["RULES.md"]),
                    "image_sha": verify.sha256_file(image),
                }
            },
        }
        verify.SCHEME_LOCK.parent.mkdir(parents=True, exist_ok=True)
        verify.SCHEME_LOCK.write_text(json.dumps(lock), encoding="utf-8")
        gate = verify.Gate()
        verify.check_schemes(gate)
        self.assertEqual(gate.failed, 0)


    def test_logs_are_separate(self):
        (verify.ROOT / "JOURNAL.md").write_text("decisions", encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text("*.log\nvar/log/\n", encoding="utf-8")
        verify.CONFIG = {
            "logs": {
                "test": "tests/test.log",
                "app": "var/log/app.log",
                "decisions": "JOURNAL.md",
            }
        }
        gate = verify.Gate()
        verify.check_logs(gate)
        self.assertEqual(gate.failed, 0)

    def test_logs_cannot_use_journal(self):
        (verify.ROOT / "JOURNAL.md").write_text("decisions", encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text("*.log\n", encoding="utf-8")
        verify.CONFIG = {
            "logs": {
                "test": "JOURNAL.md",
                "app": "var/log/app.log",
                "decisions": "JOURNAL.md",
            }
        }
        gate = verify.Gate()
        verify.check_logs(gate)
        self.assertEqual(gate.failed, 1)

    def test_logs_must_be_ignored(self):
        (verify.ROOT / "JOURNAL.md").write_text("decisions", encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text("", encoding="utf-8")
        verify.CONFIG = {
            "logs": {
                "test": "tests/test.log",
                "app": "var/log/app.log",
                "decisions": "JOURNAL.md",
            }
        }
        gate = verify.Gate()
        verify.check_logs(gate)
        self.assertEqual(gate.failed, 1)

    def test_logs_size_limit(self):
        (verify.ROOT / "JOURNAL.md").write_text("decisions", encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (verify.ROOT / "tests").mkdir()
        (verify.ROOT / "tests" / "test.log").write_bytes(b"x" * 11)
        verify.CONFIG = {
            "logs": {
                "test": "tests/test.log",
                "app": "var/log/app.log",
                "decisions": "JOURNAL.md",
                "max_bytes": 10,
                "max_pages": 5,
            }
        }
        gate = verify.Gate()
        verify.check_logs(gate)
        self.assertEqual(gate.failed, 1)

    def test_logs_page_limit(self):
        (verify.ROOT / "JOURNAL.md").write_text("decisions", encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (verify.ROOT / "tests").mkdir()
        for index in range(6):
            name = "test.log" if index == 0 else f"test.log.{index}"
            (verify.ROOT / "tests" / name).write_text("x", encoding="utf-8")
        verify.CONFIG = {
            "logs": {
                "test": "tests/test.log",
                "app": "var/log/app.log",
                "decisions": "JOURNAL.md",
                "max_bytes": 102400,
                "max_pages": 5,
            }
        }
        gate = verify.Gate()
        verify.check_logs(gate)
        self.assertEqual(gate.failed, 1)

    def test_close_task_accepts_no_code(self):
        self.assertIsNone(verify.close_task_violation(["docs/README.md"]))

    def test_close_task_rejects_code_without_evidence(self):
        self.assertIsNotNone(verify.close_task_violation(["cmd/app/main.go"]))
        self.assertIsNotNone(verify.close_task_violation(["deploy/app.yaml"]))

    def test_close_task_accepts_features(self):
        files = ["cmd/app/main.go", "features/0001-feature.md"]
        self.assertIsNone(verify.close_task_violation(files))

    def test_close_task_accepts_adr_debt_journal(self):
        for evidence in ("docs/adr/0003-x.md", "docs/DEBT.md", "JOURNAL.md"):
            files = ["cmd/app/main.go", evidence]
            self.assertIsNone(verify.close_task_violation(files))

    def test_close_task_rejects_unrelated_docs(self):
        files = ["cmd/app/main.go", "README.md"]
        self.assertIsNotNone(verify.close_task_violation(files))


if __name__ == "__main__":
    unittest.main()
