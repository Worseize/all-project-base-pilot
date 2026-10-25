#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red gate шаблона: один ненулевой код — и деплой запрещён.

    python verify.py
    python verify.py --close-task [--base <ref>]
    python verify.py --update-schemes

Проверки читают project.json: обязательные файлы, команды, ADR, схемы.
Только стандартная библиотека Python; это build-time инструмент, не продукт.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date as date_type
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "project.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
VERSION = str(CONFIG.get("version", "0.0.0"))
DATE = str(CONFIG.get("date", ""))
REQUIRED = list(CONFIG.get("required", []))
SCHEMES = dict(CONFIG.get("schemes", {}))

TEXT_EXT = {
    ".md", ".py", ".go", ".yml", ".yaml", ".json", ".svg",
    ".ps1", ".sh", ".txt", ".mod", ".sum", ".toml",
}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "dist", "build", "bin", "vendor"}

SECRETS = [
    ("aws", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key", re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?" + "PRIVATE KEY-----")),
    ("github", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("telegram", re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("openai", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("assignment", re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}[\"']")),
]


class Gate:
    def __init__(self) -> None:
        self.failed = 0
        self.skipped = 0

    def ok(self, name: str, detail: str = "") -> None:
        print(f"  [ok]   {name}" + (f" — {detail}" if detail else ""))

    def skip(self, name: str, detail: str = "") -> None:
        self.skipped += 1
        print(f"  [skip] {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str = "") -> None:
        self.failed += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def check_required(gate: Gate) -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        gate.fail("required files", ", ".join(missing))
    else:
        gate.ok("required files", f"{len(REQUIRED)} файлов")


def check_no_npm(gate: Gate) -> None:
    if not CONFIG.get("forbid_npm", True):
        gate.skip("no npm artifacts", "разрешено конфигом")
        return
    bad = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if "node_modules" in dirnames:
            bad.append(str(Path(dirpath) / "node_modules"))
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"}:
                bad.append(str(Path(dirpath) / name))
    if bad:
        gate.fail("no npm artifacts", ", ".join(bad[:5]))
    else:
        gate.ok("no npm artifacts")


def check_go_mod(gate: Gate) -> None:
    gomod = ROOT / "go.mod"
    if not gomod.exists():
        gate.skip("go.mod", "инструментов на Go ещё нет")
        return
    text = gomod.read_text(encoding="utf-8", errors="replace")
    bad = [line.strip() for line in text.splitlines()
           if re.match(r"\s*(require|replace|exclude)\b", line)]
    if bad:
        gate.fail("go.mod", "сторонние директивы: " + "; ".join(bad[:3]))
        return
    if (ROOT / "go.sum").exists():
        gate.fail("go.mod", "go.sum существует — проверь зависимости")
        return
    gate.ok("go.mod", "без сторонних require/replace/exclude")


def shannon(text: str) -> float:
    if not text:
        return 0.0
    counts = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def check_secrets(gate: Gate) -> None:
    findings = []
    for path in walk_files():
        rel = str(path.relative_to(ROOT))
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            findings.append(f"{rel} (.env)")
            continue
        if path.suffix.lower() not in TEXT_EXT:
            continue
        if path.name.endswith(".lock.json") or path.name == "go.sum":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SECRETS:
                if pattern.search(line):
                    findings.append(f"{rel}:{number} ({label})")
                    break
            else:
                for token in re.findall(r"[A-Za-z0-9_\-+/=]{32,}", line):
                    if len(set(token)) >= 8 and shannon(token) >= 4.5:
                        findings.append(f"{rel}:{number} (entropy)")
                        break
    if findings:
        gate.fail("secrets", ", ".join(findings[:5]))
    else:
        gate.ok("secrets", "чисто")


def check_junk(gate: Gate) -> None:
    names = {".DS_Store", "Thumbs.db"}
    suffixes = {".tmp", ".bak", ".orig", ".rej", ".swp", ".swo"}
    bad = []
    for path in walk_files():
        if path.name in names or path.suffix.lower() in suffixes or path.name.endswith("~"):
            bad.append(str(path.relative_to(ROOT)))
    if bad:
        gate.fail("junk", ", ".join(bad[:5]))
    else:
        gate.ok("junk", "временных файлов нет")


def check_schemes(gate: Gate) -> None:
    if not SCHEMES:
        gate.fail("schemes", "в project.json нет схем")
        return
    missing = [image for image in SCHEMES if not (ROOT / image).is_file()]
    if missing:
        gate.fail("schemes", "нет SVG: " + ", ".join(missing))
        return
    go = shutil.which("go")
    if not go:
        gate.skip("schemes", "go не установлен")
        return
    result = subprocess.run(
        [go, "run", "./cmd/schemes", "-check"],
        cwd=ROOT, text=True, capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()
        gate.fail("schemes", " | ".join(tail[-4:]))
    else:
        gate.ok("schemes", f"{len(SCHEMES)} SVG")


def check_rules(gate: Gate) -> None:
    text = (ROOT / "RULES.md").read_text(encoding="utf-8", errors="replace")
    headings = [line for line in text.splitlines() if line.startswith("### ")]
    expected = int(CONFIG.get("rules_count", 10))
    if len(headings) != expected:
        gate.fail("rules", f"ожидалось {expected} правил, найдено {len(headings)}")
        return
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    if f"{expected}. " not in agents:
        gate.fail("rules", "AGENTS.md не содержит полный индекс")
        return
    required_agents = [
        "## Обязательный старт сессии",
        "## Обязательное закрытие",
        "## Определение готовности",
    ]
    missing_agents = [token for token in required_agents if token not in agents]
    if missing_agents:
        gate.fail("rules", "AGENTS.md: нет " + ", ".join(missing_agents))
        return
    if "## Определение готовности" not in text:
        gate.fail("rules", "RULES.md: нет раздела «Определение готовности»")
        return
    gate.ok("rules", f"{expected} правил + AGENTS-протокол")


def check_sections(gate: Gate, path: str, sections: list[str], name: str) -> None:
    file = ROOT / path
    if not file.is_file():
        gate.fail(name, f"нет {path}")
        return
    text = file.read_text(encoding="utf-8", errors="replace")
    missing = [section for section in sections if f"## {section}" not in text]
    if missing:
        gate.fail(name, "нет разделов: " + ", ".join(missing))
    else:
        gate.ok(name, f"{len(sections)} разделов")


def check_project(gate: Gate) -> None:
    check_sections(gate, "PROJECT.md", list(CONFIG.get("project_sections", [])), "project")
    check_sections(gate, "FEATURE.md", list(CONFIG.get("feature_sections", [])), "feature")


def check_readme(gate: Gate) -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    if "## Быстрый старт" not in text:
        gate.fail("readme", "нет раздела «Быстрый старт»")
    else:
        gate.ok("readme", "быстрый старт")


def check_journal(gate: Gate) -> None:
    text = (ROOT / "JOURNAL.md").read_text(encoding="utf-8", errors="replace")
    entries = re.findall(r"^## \d{4}-\d{2}-\d{2}", text, re.MULTILINE)
    missing = [token for token in ("**Решение:**", "**Почему:**", "**Последствия:**") if token not in text]
    if not entries:
        gate.fail("journal", "нет ни одной записи")
    elif missing:
        gate.fail("journal", "нет полей: " + ", ".join(missing))
    else:
        gate.ok("journal", f"{len(entries)} записей")


def log_pages(path: Path) -> list[Path]:
    if path.name == "JOURNAL.md":
        candidates = [path] + sorted(path.parent.glob("JOURNAL.*.md"))
    else:
        candidates = [path] + sorted(path.parent.glob(path.name + ".*"))
    return [item for item in candidates if item.is_file()]


def check_logs(gate: Gate) -> None:
    logs = CONFIG.get("logs", {})
    test_log = str(logs.get("test", "")).strip()
    app_log = str(logs.get("app", "")).strip()
    decisions = str(logs.get("decisions", "")).strip()
    max_bytes = int(logs.get("max_bytes", 102400))
    max_pages = int(logs.get("max_pages", 5))
    if not test_log or not app_log or not decisions:
        gate.fail("logs", "в project.json нет logs.test/app/decisions")
        return
    if max_bytes <= 0 or max_pages <= 0:
        gate.fail("logs", "max_bytes и max_pages должны быть больше нуля")
        return
    if len({test_log, app_log, decisions}) != 3:
        gate.fail("logs", "тестовый, прод- и рабочий журнал должны быть разными")
        return
    if not (ROOT / decisions).is_file():
        gate.fail("logs", f"нет журнала решений: {decisions}")
        return
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace")
    missing = []
    for path in (test_log, app_log):
        parent = str(Path(path).parent).replace("\\", "/") + "/"
        if path not in ignore and "*.log" not in ignore and parent not in ignore:
            missing.append(path)
    if missing:
        gate.fail("logs", "логи не в .gitignore: " + ", ".join(missing))
        return
    over_pages = []
    over_size = []
    for path in (test_log, app_log, decisions):
        pages = log_pages(ROOT / path)
        if len(pages) > max_pages:
            over_pages.append(f"{path}: {len(pages)} > {max_pages}")
        for page in pages:
            if page.stat().st_size > max_bytes:
                over_size.append(
                    f"{page.relative_to(ROOT)}: {page.stat().st_size} > {max_bytes}"
                )
    if over_pages or over_size:
        gate.fail("logs", "; ".join(over_pages + over_size))
    else:
        gate.ok(
            "logs",
            f"test -> {test_log}, app -> {app_log}, decisions -> {decisions}; "
            f"≤{max_bytes} Б, ≤{max_pages} страниц",
        )


def check_debt(gate: Gate) -> None:
    path = ROOT / "docs" / "DEBT.md"
    if not path.is_file():
        gate.fail("debt", "нет docs/DEBT.md")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if "## Закрытый долг" in text or "## Закрытые долги" in text:
        gate.fail("debt", "закрытый долг остался в DEBT.md — удали его")
        return
    if "## Открытый долг" not in text:
        gate.fail("debt", "нет раздела «Открытый долг»")
        return
    gate.ok("debt", "закрытые долги удаляются")


ISOLATION_ACTIONS = [
    "Читать свой код",
    "Читать чужой проект",
    "Писать в свой каталог",
    "Писать в `/etc`, юниты, хуки",
    "Пушить в `review`",
    "Пушить в `main`",
    "Деплоить и перезапускать",
    "Секреты своего проекта",
    "Секреты чужого проекта",
    "Порты наружу",
]


PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,19}$")
RESERVED_PROJECTS = {
    "root", "app", "caddy", "watchdog", "admin", "system", "debian",
    "ubuntu", "nobody", "daemon", "bin", "sys", "mail", "www", "git", "ssh",
}
PROJECT_FIELDS = {"display", "agent", "domain", "port", "status", "allowed_paths"}
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
)


def validate_projects(data, allowed_ids=None) -> list[str]:
    errors = []
    if not isinstance(data, dict) or set(data) != {"projects"}:
        return ["верхний уровень должен содержать только projects"]
    projects = data["projects"]
    if not isinstance(projects, dict):
        return ["projects должен быть объектом"]
    if allowed_ids is not None and set(projects) != set(allowed_ids):
        errors.append("пример должен содержать только proj-a и proj-b")
    domains = set()
    ports = set()
    for project_id, item in projects.items():
        if not PROJECT_ID_RE.fullmatch(project_id):
            errors.append(f"{project_id}: id не соответствует ^[a-z][a-z0-9-]{{2,19}}$")
        if "--" in project_id or project_id.endswith("-"):
            errors.append(f"{project_id}: недопустимые дефисы")
        if project_id in RESERVED_PROJECTS:
            errors.append(f"{project_id}: зарезервированное имя")
        if not isinstance(item, dict):
            errors.append(f"{project_id}: должен быть объектом")
            continue
        if set(item) != PROJECT_FIELDS:
            errors.append(f"{project_id}: поля должны быть ровно {sorted(PROJECT_FIELDS)}")
            continue
        display = item["display"]
        agent = item["agent"]
        domain = item["domain"]
        port = item["port"]
        status = item["status"]
        allowed_paths = item["allowed_paths"]
        if not isinstance(display, str) or not 1 <= len(display) <= 64:
            errors.append(f"{project_id}: display 1–64")
        if not isinstance(agent, str) or not 1 <= len(agent) <= 64:
            errors.append(f"{project_id}: agent 1–64")
        if not isinstance(domain, str) or (domain and not DOMAIN_RE.fullmatch(domain)):
            errors.append(f"{project_id}: domain пустой или поддомен")
        elif domain:
            if domain in domains:
                errors.append(f"{project_id}: domain повторяется")
            domains.add(domain)
        if isinstance(port, bool) or not isinstance(port, int):
            errors.append(f"{project_id}: port должен быть числом")
        elif port != 0 and not 1024 <= port <= 65535:
            errors.append(f"{project_id}: port 0 или 1024–65535")
        elif port != 0:
            if port in ports:
                errors.append(f"{project_id}: port повторяется")
            ports.add(port)
        if status not in {"active", "paused", "planned"}:
            errors.append(f"{project_id}: status active/paused/planned")
        if not isinstance(allowed_paths, list) or not allowed_paths:
            errors.append(f"{project_id}: allowed_paths должен быть непустым списком")
        else:
            for allowed in allowed_paths:
                if (
                    not isinstance(allowed, str)
                    or not allowed
                    or allowed.startswith("/")
                    or ".." in allowed.split("/")
                    or "\\" in allowed
                ):
                    errors.append(f"{project_id}: некорректный allowed_path: {allowed}")
    return errors


def check_no_product(gate: Gate) -> None:
    errors = []
    deploy = ROOT / "deploy"
    for path in sorted(deploy.rglob("*")):
        if path.is_file() and path.suffix == ".service" and "app" in path.name:
            errors.append(f"product unit: {path.relative_to(ROOT)}")
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\bbin/app\b", text):
                errors.append(f"bin/app: {path.relative_to(ROOT)}")
            if "/etc/sudoers.d/" in text and re.search(r"systemctl\s+(?:restart|reload)", text):
                errors.append(f"sudoers restart: {path.relative_to(ROOT)}")
    if (ROOT / "cmd" / "app").exists():
        errors.append("cmd/app")
    if errors:
        gate.fail("no-product", "; ".join(errors[:5]))
    else:
        gate.ok("no-product", "шаблон без продукта")


def check_projects(gate: Gate) -> None:
    path = ROOT / "projects.example.json"
    if not path.is_file():
        gate.fail("projects", "нет projects.example.json")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        gate.fail("projects", f"projects.example.json: {exc}")
        return
    errors = validate_projects(data, {"proj-a", "proj-b"})
    if errors:
        gate.fail("projects", "; ".join(errors[:5]))
        return
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace")
    if "projects.json" not in {line.strip() for line in ignore.splitlines()}:
        gate.fail("projects", "projects.json не в .gitignore")
        return
    working = ROOT / "projects.json"
    if working.is_file():
        try:
            working_data = json.loads(working.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            gate.fail("projects", f"projects.json: {exc}")
            return
        errors = validate_projects(working_data)
        if errors:
            gate.fail("projects", "; ".join(errors[:5]))
            return
    gate.ok("projects", "пример валиден, projects.json игнорируется")


ACCEPTANCE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
ACCEPTANCE_LEAKS = [
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("host-path", re.compile(r"(?:^|\s)/(?:srv|etc|home)/")),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("ssh-key", re.compile(r"\bssh-[A-Za-z0-9-]+")),
]


def check_acceptance(gate: Gate) -> None:
    directory = ROOT / "docs" / "acceptance"
    if not directory.is_dir():
        gate.fail("acceptance", "нет docs/acceptance/")
        return
    files = sorted(path for path in directory.glob("*.md") if path.name != "README.md")
    errors = []
    for path in files:
        match = ACCEPTANCE_RE.fullmatch(path.name)
        if not match:
            errors.append(f"{path.name}: имя YYYY-MM-DD-<slug>.md")
            continue
        try:
            date_type.fromisoformat(match.group(1))
        except ValueError:
            errors.append(f"{path.name}: неверная дата")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        refusal = text.lstrip().startswith("Отказ:")
        if refusal:
            first = text.lstrip().splitlines()[0]
            if not first[len("Отказ:"):].strip():
                errors.append(f"{path.name}: пустой отказ")
        else:
            if not re.search(r"(?m)^Версия:\s*\S+", text):
                errors.append(f"{path.name}: нет Версия:")
            if not re.search(r"(?m)^Ссылка:\s*findings#\d+", text):
                errors.append(f"{path.name}: нет Ссылка: findings#N")
            body = re.sub(r"(?m)^(?:#.*|Версия:.*|Ссылка:.*)$", "", text).strip()
            if not body:
                errors.append(f"{path.name}: пустой блок приёмки")
        for label, pattern in ACCEPTANCE_LEAKS:
            scan = text
            for safe in ("/etc/sudoers.d/", "/etc/systemd/system/proj@.service", "/srv/%i/current"):
                scan = scan.replace(safe, "")
            if pattern.search(scan):
                errors.append(f"{path.name}: утечка {label}")
    if errors:
        gate.fail("acceptance", "; ".join(errors[:5]))
    else:
        gate.ok("acceptance", f"{len(files)} файлов, утечек нет")


def check_isolation(gate: Gate) -> None:
    path = ROOT / "docs" / "ISOLATION.md"
    if not path.is_file():
        gate.fail("isolation", "нет docs/ISOLATION.md")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if "| Действие | Агент проекта | Root |" not in text:
        gate.fail("isolation", "нет заголовка матрицы прав")
        return
    missing = [action for action in ISOLATION_ACTIONS if action not in text]
    if missing:
        gate.fail("isolation", "нет действий: " + ", ".join(missing))
        return
    keys = ("projects_root", "hooks_root", "secrets_root", "review_ref", "main_ref")
    absent = [key for key in keys if key not in CONFIG.get("isolation", {})]
    if absent:
        gate.fail("isolation", "в project.json нет isolation: " + ", ".join(absent))
        return
    gate.ok("isolation", f"{len(ISOLATION_ACTIONS)} действий, матрица полная")


def check_adr(gate: Gate) -> None:
    adr = ROOT / "docs" / "adr"
    base = {"README.md", "0000-template.md"}
    missing = [name for name in sorted(base) if not (adr / name).is_file()]
    if missing:
        gate.fail("adr", ", ".join(missing))
        return
    files = sorted(p for p in adr.glob("[0-9][0-9][0-9][0-9]-*.md") if p.name != "0000-template.md")
    if len(files) < int(CONFIG.get("adr_min", 0)):
        gate.fail("adr", f"нужно минимум {CONFIG.get('adr_min', 0)} ADR, найдено {len(files)}")
        return
    required = ["## Контекст", "## Решение", "## Альтернативы", "## Последствия"]
    bad = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(section not in text for section in required):
            bad.append(path.name)
    if bad:
        gate.fail("adr", "неполные разделы: " + ", ".join(bad))
    else:
        gate.ok("adr", f"{len(files)} ADR")


def check_stop_rule(gate: Gate) -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    contract = (ROOT / "docs" / "AGENT-CONTRACT.md").read_text(encoding="utf-8", errors="replace")
    problems = []
    if "дважды" not in agents or "blocked" not in agents:
        problems.append("AGENTS: нет правила двух попыток/blocked")
    if "review" not in agents or "администратор" not in agents:
        problems.append("AGENTS: нет review/администратора")
    if "Две попытки" not in contract or "blocked" not in contract:
        problems.append("AGENT-CONTRACT: нет остановки")
    if problems:
        gate.fail("stop-rule", "; ".join(problems))
    else:
        gate.ok("stop-rule", "две попытки и blocked-отчёт")


def check_process(gate: Gate) -> None:
    text = (ROOT / "PROCESS.md").read_text(encoding="utf-8", errors="replace").lower()
    missing = [word for word in ("verify", "красн", "журнал", "деплой") if word not in text]
    if missing:
        gate.fail("process", "нет разделов: " + ", ".join(missing))
    elif "закрывает issue только conductor" not in text:
        gate.fail("process", "не зафиксировано: issue закрывает только conductor")
    elif "не пишет комментарии" not in text:
        gate.fail("process", "не зафиксировано: агент не пишет комментарии")
    else:
        gate.ok("process", "red gate, журнал и правило доски описаны")


def check_ci(gate: Gate) -> None:
    raw = CONFIG.get("ci", "github")
    if isinstance(raw, str):
        modes = [raw]
    elif isinstance(raw, list):
        modes = [str(item) for item in raw]
    else:
        gate.fail("ci", "ci должен быть строкой или списком")
        return
    if not modes:
        gate.fail("ci", "пустой список")
        return
    if "none" in modes:
        if len(modes) == 1:
            gate.skip("ci", "CI отключён конфигом")
        else:
            gate.fail("ci", "none нельзя комбинировать с другими режимами")
        return
    needed = []
    for mode in modes:
        if mode == "github":
            needed.append(".github/workflows/verify.yml")
        elif mode == "gitlab":
            needed.append(".gitlab-ci.yml")
        elif mode == "azure":
            needed.append("azure-pipelines.yml")
        else:
            gate.fail("ci", f"неизвестный режим: {mode}")
            return
    missing = [name for name in needed if not (ROOT / name).is_file()]
    if missing:
        gate.fail("ci", ", ".join(missing))
    else:
        gate.ok("ci", ", ".join(modes))


def check_versions(gate: Gate) -> None:
    bad = []
    for name in ("RULES.md", "STRATEGY.md", "PROCESS.md"):
        text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        if f"Версия {VERSION}" not in text:
            bad.append(name)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8", errors="replace")
    if f"## {VERSION}" not in changelog:
        bad.append("CHANGELOG.md")
    if bad:
        gate.fail("versions", "версия не совпадает: " + ", ".join(bad))
    else:
        gate.ok("versions", VERSION)


def go_files() -> list[Path]:
    return [path for path in walk_files() if path.suffix == ".go"]


def check_go_sizes(gate: Gate) -> None:
    files = go_files()
    if not files:
        gate.skip("go sizes", "Go-файлов ещё нет")
        return
    bad = []
    for path in files:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        rel = path.relative_to(ROOT)
        if len(lines) > 400:
            bad.append(f"{rel}: {len(lines)} строк (лимит 400)")
        index = 0
        while index < len(lines):
            if lines[index].startswith("func "):
                end = index
                for probe in range(index + 1, len(lines)):
                    if lines[probe] == "}":
                        end = probe
                        break
                length = end - index + 1
                if length > 80:
                    bad.append(f"{rel}:{index + 1}: функция {length} строк (лимит 80)")
                index = end
            index += 1
    if bad:
        gate.fail("go sizes", ", ".join(bad[:5]))
    else:
        gate.ok("go sizes", "файлы ≤ 400, функции ≤ 80")


def check_gofmt(gate: Gate) -> None:
    if not go_files():
        gate.skip("gofmt", "Go-файлов ещё нет")
        return
    gofmt = shutil.which("gofmt")
    if not gofmt:
        gate.skip("gofmt", "gofmt не установлен")
        return
    result = subprocess.run([gofmt, "-l", "."], cwd=ROOT, text=True, capture_output=True, timeout=60)
    changed = [line for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or changed:
        gate.fail("gofmt", ", ".join(changed[:5]) or "gofmt вернул ошибку")
    else:
        gate.ok("gofmt", "форматирование чистое")


def check_commands(gate: Gate) -> None:
    commands = CONFIG.get("commands", {})
    if not commands:
        gate.skip("commands", "в project.json нет команд")
        return
    for name in ("build", "vet", "test", "deadcode", "lint", "fmt"):
        command = commands.get(name)
        if not command:
            continue
        result = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, shell=True, timeout=180
        )
        if name == "fmt":
            changed = [line for line in result.stdout.splitlines() if line.strip()]
            if result.returncode != 0 or changed:
                gate.fail("fmt", ", ".join(changed[:5]) or "fmt вернул ошибку")
                return
        elif result.returncode != 0:
            tail = (result.stderr or result.stdout).strip().splitlines()
            gate.fail(name, " | ".join(tail[-3:]))
            return
    gate.ok("commands", "build/test/vet/deadcode/fmt")


CODE_ROOTS = ("cmd", "deploy")
EVIDENCE_ROOTS = ("features", "docs/adr")
EVIDENCE_FILES = {"docs/DEBT.md", "JOURNAL.md"}


def path_in(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def close_task_violation(files: list[str]) -> str | None:
    code = [name for name in files if path_in(name, CODE_ROOTS)]
    evidence = [
        name for name in files
        if path_in(name, EVIDENCE_ROOTS) or name in EVIDENCE_FILES
    ]
    if code and not evidence:
        return (
            "изменён код (" + ", ".join(code[:5]) + ") без features/**, "
            "docs/adr/**, docs/DEBT.md или JOURNAL.md"
        )
    return None


def ref_exists(ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=ROOT, text=True, capture_output=True,
    )
    return result.returncode == 0


def resolve_base(argv: list[str]) -> str:
    if "--base" in argv:
        index = argv.index("--base")
        if index + 1 >= len(argv):
            raise RuntimeError("--base требует ref")
        return argv[index + 1]
    for key in (
        "GITHUB_BASE_SHA",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA",
        "SYSTEM_PULLREQUEST_TARGETCOMMITID",
    ):
        value = os.environ.get(key)
        if value:
            return value
    ref = os.environ.get("GITHUB_BASE_REF") or os.environ.get(
        "CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    )
    if ref:
        for candidate in (f"origin/{ref}", ref):
            if ref_exists(candidate):
                return candidate
    for candidate in ("origin/main", "main"):
        if ref_exists(candidate):
            return candidate
    raise RuntimeError("не найден base; передай --base <ref>")


def changed_files(base: str) -> list[str]:
    if not shutil.which("git"):
        raise RuntimeError("git не установлен")
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or f"git diff {base}...HEAD не удался"
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def close_task(argv: list[str]) -> int:
    try:
        base = resolve_base(argv)
        files = changed_files(base)
    except RuntimeError as exc:
        print(f"RED: {exc}")
        return 1
    print(f"close-task {VERSION}  ·  base={base}  ·  changed={len(files)}")
    violation = close_task_violation(files)
    if violation:
        print(f"RED: {violation}")
        return 1
    print("GREEN: код не изменён без evidence-файла. Задача закрыта.")
    return 0


def update_schemes() -> int:
    if not CONFIG:
        print("RED: нет project.json")
        return 1
    go = shutil.which("go")
    if not go:
        print("RED: go не установлен")
        return 1
    result = subprocess.run(
        [go, "run", "./cmd/schemes", "-write"],
        cwd=ROOT, text=True, capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("RED: генератор SVG упал")
        return 1
    print(result.stdout.strip())
    print("GREEN: SVG обновлены; lock не нужен")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--close-task" in sys.argv:
        return close_task(sys.argv)
    if "--update-schemes" in sys.argv:
        return update_schemes()
    if not CONFIG:
        print("RED: project.json не найден")
        return 1

    print(f"verify {VERSION}  ·  {ROOT}")
    gate = Gate()
    for check in (
        check_required,
        check_no_npm,
        check_go_mod,
        check_secrets,
        check_junk,
        check_schemes,
        check_rules,
        check_project,
        check_readme,
        check_journal,
        check_logs,
        check_debt,
        check_isolation,
        check_projects,
        check_no_product,
        check_acceptance,
        check_adr,
        check_process,
        check_stop_rule,
        check_ci,
        check_versions,
        check_go_sizes,
        check_gofmt,
        check_commands,
    ):
        check(gate)

    print()
    if gate.failed:
        print(f"RED: {gate.failed} проверок не прошло. Деплой запрещён.")
        return 1
    print(f"GREEN: всё чисто. Пропущено: {gate.skipped}. Деплой разрешён.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
