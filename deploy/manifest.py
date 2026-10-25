#!/usr/bin/env python3
"""Validate and read project.conf (key=value, no third-party packages)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

KEYS = {
    "run", "test", "health", "build", "deps", "migrate",
    "site", "domains", "redirects", "port", "memory", "cpu", "timezone",
}
DEFAULTS = {
    "run": "run", "test": "test.sh", "health": "health",
    "build": "", "deps": "", "migrate": "",
    "site": "none", "domains": "", "redirects": "",
    "port": "", "memory": "512M", "cpu": "50%", "timezone": "UTC",
}
SITES = {"none", "static", "proxy"}
SITE_PREFIX = ("static:", "proxy:")
MEMORY = re.compile(r"^[0-9]+[KMG]?$")
CPU = re.compile(r"^[0-9]+%$")
PORT = re.compile(r"^[0-9]+$")


def parse(path: Path) -> dict[str, str]:
    data = dict(DEFAULTS)
    if not path.is_file():
        return data
    seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in KEYS:
            raise ValueError(f"{path}:{number}: unknown key: {key}")
        if key in seen:
            raise ValueError(f"{path}:{number}: duplicate key: {key}")
        seen.add(key)
        data[key] = value
    return data


def check(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = parse(path)
    except ValueError as exc:
        return [str(exc)]
    if data["site"] not in SITES and not data["site"].startswith(SITE_PREFIX):
        errors.append(f"site must be none, static[:dir], proxy[:port]")
    if data["memory"] and not MEMORY.match(data["memory"]):
        errors.append("memory must look like 512M")
    if data["cpu"] and not CPU.match(data["cpu"]):
        errors.append("cpu must look like 50%")
    if data["port"] and not PORT.match(data["port"]):
        errors.append("port must be numeric")
    if data["timezone"] and not (Path("/usr/share/zoneinfo") / data["timezone"]).is_file():
        if data["timezone"] != "UTC":
            errors.append(f"unknown timezone: {data['timezone']}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: manifest.py get|check <project.conf> [key]", file=sys.stderr)
        return 2
    action, path = argv[1], Path(argv[2])
    if action == "check":
        errors = check(path)
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    if action == "get":
        if len(argv) != 4 or argv[3] not in KEYS:
            print("usage: manifest.py get <project.conf> <key>", file=sys.stderr)
            return 2
        try:
            print(parse(path).get(argv[3], ""))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    print(f"unknown action: {action}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
