# -*- coding: utf-8 -*-
"""Общий конфиг генераторов схем: версия, дата и кроссплатформенный шрифт."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
VERSION = CONFIG["version"]
DATE = CONFIG["date"]


def font_path(bold: bool = False) -> str:
    key = "bold" if bold else "regular"
    candidates = CONFIG.get("fonts", {}).get(key, [])
    for raw in candidates:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        if path.is_file():
            return str(path)
    raise SystemExit(
        f"Шрифт ({key}) не найден. Положите DejaVuSans"
        f"{'-Bold' if bold else ''}.ttf в docs/fonts/ "
        "или установите fonts-dejavu-core. См. docs/fonts/README.md."
    )
