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
        self.tmp = tempfile.TemporaryDirectory()
        verify.ROOT = Path(self.tmp.name)
        verify.CONFIG = {"stack": "go", "forbid_npm": True, "rules_count": 10}
        verify.VERSION = "0.7.9"
        verify.REQUIRED = []
        verify.SCHEMES = {}

    def tearDown(self):
        verify.ROOT = self.old_root
        verify.CONFIG = self.old_config
        verify.VERSION = self.old_version
        verify.REQUIRED = self.old_required
        verify.SCHEMES = self.old_schemes
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

    def test_debt_accepts_open_only(self):
        docs = verify.ROOT / "docs"
        docs.mkdir()
        (docs / "DEBT.md").write_text(
            "# DEBT\n\n## Открытый долг\n\nНет открытого долга.\n",
            encoding="utf-8",
        )
        gate = verify.Gate()
        verify.check_debt(gate)
        self.assertEqual(gate.failed, 0)

    def test_debt_rejects_closed_section(self):
        docs = verify.ROOT / "docs"
        docs.mkdir()
        (docs / "DEBT.md").write_text(
            "# DEBT\n\n## Открытый долг\n\n## Закрытый долг\n",
            encoding="utf-8",
        )
        gate = verify.Gate()
        verify.check_debt(gate)
        self.assertEqual(gate.failed, 1)

    def _projects(self):
        return {
            "projects": {
                "proj-a": {
                    "display": "Project A",
                    "agent": "agent-a",
                    "domain": "proj-a.example.org",
                    "port": 8011,
                    "status": "active",
                },
                "proj-b": {
                    "display": "Project B",
                    "agent": "agent-b",
                    "domain": "",
                    "port": 8012,
                    "status": "planned",
                },
            }
        }

    def _write_projects(self, data, ignore="projects.json\n"):
        (verify.ROOT / "projects.example.json").write_text(json.dumps(data), encoding="utf-8")
        (verify.ROOT / ".gitignore").write_text(ignore, encoding="utf-8")

    def test_projects_valid(self):
        self._write_projects(self._projects())
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 0)

    def test_projects_invalid_id(self):
        data = self._projects()
        data["projects"]["proj-a"].pop("display")
        data["projects"]["proj-a"]["extra"] = "x"
        self._write_projects(data)
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 1)

    def test_projects_duplicate_domain(self):
        data = self._projects()
        data["projects"]["proj-b"]["domain"] = "proj-a.example.org"
        self._write_projects(data)
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 1)

    def test_projects_duplicate_port(self):
        data = self._projects()
        data["projects"]["proj-b"]["port"] = 8011
        self._write_projects(data)
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 1)

    def test_projects_bad_status(self):
        data = self._projects()
        data["projects"]["proj-a"]["status"] = "unknown"
        self._write_projects(data)
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 1)

    def test_projects_registry_must_be_ignored(self):
        self._write_projects(self._projects(), ignore="")
        gate = verify.Gate()
        verify.check_projects(gate)
        self.assertEqual(gate.failed, 1)

    def _acceptance(self, name="2026-10-24-example.md", text=None):
        directory = verify.ROOT / "docs" / "acceptance"
        directory.mkdir(parents=True)
        body = text if text is not None else (
            "# Проверка\n\nСимптом и воспроизведение.\n\n"
            "Версия: 0.9.10\nСсылка: findings#1\n"
        )
        (directory / name).write_text(body, encoding="utf-8")

    def test_acceptance_valid(self):
        self._acceptance()
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 0)

    def test_acceptance_bad_name(self):
        self._acceptance("bad.md")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_missing_link(self):
        self._acceptance(text="# Проверка\n\nТекст.\n\nВерсия: 0.9.10\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_ipv4_leak(self):
        self._acceptance(text="# Проверка\n\nАдрес 192.168.1.10.\n\nВерсия: 0.9.10\nСсылка: findings#1\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_host_path_leak(self):
        self._acceptance(text="# Проверка\n\nПуть /srv/example.\n\nВерсия: 0.9.10\nСсылка: findings#1\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_email_leak(self):
        self._acceptance(text="# Проверка\n\nПочта user@example.org.\n\nВерсия: 0.9.10\nСсылка: findings#1\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_empty_body(self):
        self._acceptance(text="# Проверка\n\nВерсия: 0.9.10\nСсылка: findings#1\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def test_acceptance_refusal_valid(self):
        self._acceptance(text="Отказ: нет доступа к внешнему сервису\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 0)

    def test_acceptance_refusal_empty_reason(self):
        self._acceptance(text="Отказ:\n")
        gate = verify.Gate()
        verify.check_acceptance(gate)
        self.assertEqual(gate.failed, 1)

    def _no_product(self):
        deploy = verify.ROOT / "deploy"
        deploy.mkdir(parents=True)
        return deploy

    def test_no_product_app_service(self):
        deploy = self._no_product()
        (deploy / "systemd").mkdir()
        (deploy / "systemd" / "app.service").write_text("[Service]\n", encoding="utf-8")
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 1)

    def test_no_product_app_named_service(self):
        deploy = self._no_product()
        (deploy / "systemd").mkdir()
        (deploy / "systemd" / "my-app.service").write_text("[Service]\n", encoding="utf-8")
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 1)

    def test_no_product_cmd_app(self):
        (verify.ROOT / "cmd" / "app").mkdir(parents=True)
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 1)

    def test_no_product_bin_app(self):
        deploy = self._no_product()
        (deploy / "run.sh").write_text("exec bin/app\n", encoding="utf-8")
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 1)

    def test_no_product_sudoers_restart(self):
        deploy = self._no_product()
        (deploy / "sudoers").write_text(
            "/etc/sudoers.d/proj app ALL=(root) NOPASSWD: systemctl restart app\n",
            encoding="utf-8",
        )
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 1)

    def test_no_product_tools_allowed(self):
        (verify.ROOT / "cmd" / "schemes").mkdir(parents=True)
        (verify.ROOT / "cmd" / "deadcode").mkdir()
        gate = verify.Gate()
        verify.check_no_product(gate)
        self.assertEqual(gate.failed, 0)

    def test_isolation_ci_wired(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "isolation.yml").read_text(encoding="utf-8")
        script = (root / "deploy" / "ci" / "isolation.sh").read_text(encoding="utf-8")
        cleanup = (root / "deploy" / "ci" / "isolation-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn("ubuntu-24.04", workflow)
        self.assertIn("deploy/ci/isolation.sh", workflow)
        self.assertIn("deploy/ci/isolation-cleanup.sh", workflow)
        for word in ("git-shell", "refs/heads/main", "gate files changed", "CANARY", "sudo -n", "logrotate"):
            self.assertIn(word, script)
        self.assertIn("userdel", cleanup)

    def test_process_requires_conductor_board_rule(self):
        text = "verify красный журнал деплой\n"
        (verify.ROOT / "PROCESS.md").write_text(text, encoding="utf-8")
        gate = verify.Gate()
        verify.check_process(gate)
        self.assertEqual(gate.failed, 1)
        (verify.ROOT / "PROCESS.md").write_text(
            text + "Закрывает issue только conductor\n", encoding="utf-8"
        )
        gate = verify.Gate()
        verify.check_process(gate)
        self.assertEqual(gate.failed, 1)
        (verify.ROOT / "PROCESS.md").write_text(
            text + "Закрывает issue только conductor\nне пишет комментарии\n",
            encoding="utf-8",
        )
        gate = verify.Gate()
        verify.check_process(gate)
        self.assertEqual(gate.failed, 0)

    def test_bootstrap_uses_git_shell_and_seeds_main(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "deploy" / "bootstrap-project.sh").read_text(encoding="utf-8")
        self.assertIn("git-shell", script)
        self.assertIn("SOURCE_REPO", script)
        self.assertIn("refs/heads/main", script)
        self.assertIn("symbolic-ref", script)
        self.assertIn("fetch", script)
        self.assertNotIn("nologin", script)

    def test_pre_receive_uses_trusted_verify(self):
        root = Path(__file__).resolve().parents[1]
        hook = (root / "deploy" / "git" / "pre-receive").read_text(encoding="utf-8")
        self.assertIn("show refs/heads/main:verify.py", hook)
        self.assertIn("python3 .trusted-verify.py", hook)
        self.assertNotIn("python3 verify.py", hook)
        for path in ("verify\\.py", "project\\.json", "tests/", "cmd/schemes/", "cmd/deadcode/"):
            self.assertIn(path, hook)

    def test_isolation_matrix_complete(self):
        docs = verify.ROOT / "docs"
        docs.mkdir()
        rows = "\n".join(f"| {action} | да | да |" for action in verify.ISOLATION_ACTIONS)
        (docs / "ISOLATION.md").write_text(
            "| Действие | Агент проекта | Root |\n| --- | --- | --- |\n" + rows,
            encoding="utf-8",
        )
        verify.CONFIG = {
            "isolation": {
                "projects_root": "/srv",
                "hooks_root": "/etc/git-hooks",
                "secrets_root": "/etc",
                "review_ref": "refs/heads/review",
                "main_ref": "refs/heads/main",
            }
        }
        gate = verify.Gate()
        verify.check_isolation(gate)
        self.assertEqual(gate.failed, 0)

    def test_isolation_missing_action(self):
        docs = verify.ROOT / "docs"
        docs.mkdir()
        (docs / "ISOLATION.md").write_text(
            "| Действие | Агент проекта | Root |\n| --- | --- | --- |\n",
            encoding="utf-8",
        )
        verify.CONFIG = {
            "isolation": {
                "projects_root": "/srv",
                "hooks_root": "/etc/git-hooks",
                "secrets_root": "/etc",
                "review_ref": "refs/heads/review",
                "main_ref": "refs/heads/main",
            }
        }
        gate = verify.Gate()
        verify.check_isolation(gate)
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
