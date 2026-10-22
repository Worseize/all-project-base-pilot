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

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "project.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
VERSION = str(CONFIG.get("version", "0.0.0"))
DATE = str(CONFIG.get("date", ""))
REQUIRED = list(CONFIG.get("required", []))
SCHEMES = dict(CONFIG.get("schemes", {}))
SCHEME_LOCK = ROOT / CONFIG.get("scheme_lock", "docs/schemes.lock.json")

TEXT_EXT = {
    ".md", ".py", ".go", ".yml", ".yaml", ".json",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hash(sources: list[str]) -> str:
    digest = hashlib.sha256()
    for source in sources:
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
        if source == "project.json#render":
            render = {key: CONFIG.get(key) for key in ("version", "date", "fonts")}
            digest.update(json.dumps(render, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        else:
            path = ROOT / source
            if path.is_file():
                digest.update(path.read_bytes())
            else:
                digest.update(b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


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
    if CONFIG.get("stack") != "go":
        gate.skip("go.mod", "стек не Go")
        return
    gomod = ROOT / "go.mod"
    if not gomod.exists():
        gate.skip("go.mod", "продукта ещё нет")
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
    present = [image for image in SCHEMES if (ROOT / image).is_file()]
    if not present:
        gate.skip("schemes", "PNG не сгенерированы; запусти --update-schemes")
        return
    bad = []
    for image in SCHEMES:
        path = ROOT / image
        if not path.is_file():
            bad.append(f"{image}: нет файла")
        elif path.stat().st_size < 10_000:
            bad.append(f"{image}: меньше 10 КБ")
        elif path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            bad.append(f"{image}: не PNG")
    if bad:
        gate.fail("schemes", ", ".join(bad))
        return

    if not SCHEME_LOCK.is_file():
        gate.fail("schemes lock", "нет lock; запусти python verify.py --update-schemes")
        return
    lock = json.loads(SCHEME_LOCK.read_text(encoding="utf-8"))
    if lock.get("version") != VERSION:
        gate.fail("schemes lock", f"lock версии {lock.get('version')}, шаблон {VERSION}")
        return
    drift = []
    for image, sources in SCHEMES.items():
        entry = lock.get("schemes", {}).get(image)
        if not entry:
            drift.append(f"{image}: нет в lock")
            continue
        if entry.get("source_sha") != source_hash(sources):
            drift.append(f"{image}: источники изменились")
    if drift:
        gate.fail("schemes lock", "; ".join(drift[:5]) + " — запусти --update-schemes")
    else:
        gate.ok("schemes lock", f"{len(SCHEMES)} схем")


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


def check_process(gate: Gate) -> None:
    text = (ROOT / "PROCESS.md").read_text(encoding="utf-8", errors="replace").lower()
    missing = [word for word in ("verify", "красн", "журнал", "деплой") if word not in text]
    if missing:
        gate.fail("process", "нет разделов: " + ", ".join(missing))
    else:
        gate.ok("process", "red gate и журнал описаны")


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
    if CONFIG.get("stack") != "go":
        gate.skip("go sizes", "стек не Go")
        return
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
    if CONFIG.get("stack") != "go":
        gate.skip("gofmt", "стек не Go")
        return
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
    if CONFIG.get("stack") == "go":
        if not (ROOT / "go.mod").exists():
            gate.skip("commands", "go.mod ещё нет")
            return
        if not shutil.which("go"):
            gate.skip("commands", "go не установлен")
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
    for script in CONFIG.get("scheme_generators", {}):
        print(f"  генерирую: {script}")
        result = subprocess.run([sys.executable, script], cwd=ROOT, text=True, capture_output=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            print(f"RED: генератор {script} упал")
            return 1
    lock = {"version": VERSION, "date": DATE, "schemes": {}}
    for image, sources in SCHEMES.items():
        path = ROOT / image
        if not path.is_file():
            print(f"RED: нет схемы {image}")
            return 1
        lock["schemes"][image] = {
            "source_sha": source_hash(sources),
        }
    SCHEME_LOCK.parent.mkdir(parents=True, exist_ok=True)
    SCHEME_LOCK.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"GREEN: схемы и lock обновлены ({SCHEME_LOCK.relative_to(ROOT)})")
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
        check_adr,
        check_process,
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
