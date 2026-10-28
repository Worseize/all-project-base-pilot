#!/usr/bin/env python3
"""Reject personal data in the template: real IPs, e-mails, home paths, tokens.

Placeholders (example.test, 192.0.2.x, /home/agent) pass; a real address,
mailbox, private path or token is red.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", "mailbox", "tests", "var", "ci-logs", "bin", "node_modules"}
SKIP_PATHS = {"docs/acceptance", "docs/AGENTS-ARCHIVE.md"}
SUFFIXES = {".md", ".py", ".sh", ".json", ".yml", ".yaml", ".service", ".timer", ".conf", ".txt", ".example", ".gitignore", ""}
IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
HOME = re.compile(r"/home/([A-Za-z0-9_.-]+)")
TOKEN = re.compile(
    r"\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9]{20,}|xoxb-[A-Za-z0-9-]{10,})\b"
)
ALLOW_IP = ("127.", "0.0.0.0", "255.", "192.0.2.", "198.51.100.", "203.0.113.")
ALLOW_EMAIL = ("example.com", "example.test", "example.org", "example.invalid", "agents.invalid")
ALLOW_HOME = {"example", "user", "agent", "runner", "project"}


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative in SKIP_PATHS or any(relative.startswith(item + "/") for item in SKIP_PATHS):
            continue
        if path.suffix not in SUFFIXES:
            continue
        yield path, relative


def scan_line(relative: str, number: int, line: str) -> list[str]:
    errors: list[str] = []
    for match in IPV4.finditer(line):
        address = match.group(0)
        if not address.startswith(ALLOW_IP):
            errors.append(f"{relative}:{number}: адрес {address}")
    for match in EMAIL.finditer(line):
        if match.group(1).lower() not in ALLOW_EMAIL:
            errors.append(f"{relative}:{number}: почта {match.group(0)}")
    for match in HOME.finditer(line):
        if match.group(1) not in ALLOW_HOME:
            errors.append(f"{relative}:{number}: путь {match.group(0)}")
    for match in TOKEN.finditer(line):
        errors.append(f"{relative}:{number}: токен {match.group(0)[:8]}…")
    return errors


def check_personal_data(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path, relative in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            errors.extend(scan_line(relative, number, line))
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else ROOT
    errors = check_personal_data(root)
    for error in errors[:20]:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
