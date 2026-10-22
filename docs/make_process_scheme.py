# -*- coding: utf-8 -*-
"""Рисует схему процесса: красный не проходит.

    python docs/make_process_scheme.py

Результат:
    docs/scheme-process.png — правила → тест → изменение → verify →
    деплой только на зелёном → журнал решений.

Зачем: процесс должен быть виден на одном экране. Красный — это не «почти
готово», а запрет на деплой; зелёный — доказательство, а не обещание.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scheme_config import DATE, VERSION, font_path

DOCS = Path(__file__).resolve().parent
FONT = font_path(False)
FONT_BOLD = font_path(True)

BG = "#f6f7f9"
INK = "#0f172a"
MUTED = "#475569"
SOFT = "#64748b"
LINE = "#94a3b8"
HAIR = "#e2e8f0"

BLUE = ("#eff6ff", "#60a5fa")
GREEN = ("#ecfdf5", "#34d399")
YELLOW = ("#fffbeb", "#fbbf24")
RED = ("#fef2f2", "#f87171")
VIOLET = ("#f5f3ff", "#a78bfa")
GRAY = ("#f8fafc", "#cbd5e1")

DARK_GREEN = "#059669"
DARK_RED = "#dc2626"

W, H = 1600, 1040
M = 44

CARD_W, CARD_H, CARD_GAP = 232, 180, 16
CARD_Y = 160

PANEL_Y, PANEL_H, PANEL_W = 530, 300, 744


def load(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


F_KICK = load(FONT_BOLD, 14)
F_TITLE = load(FONT_BOLD, 38)
F_SUB = load(FONT, 18)
F_SECTION = load(FONT_BOLD, 19)
F_NOTE = load(FONT, 14)
F_NOTE_S = load(FONT, 12)
F_CARD_NUM = load(FONT_BOLD, 12)
F_CARD_TITLE = load(FONT_BOLD, 17)
F_CARD_TEXT = load(FONT, 13)
F_PILL = load(FONT_BOLD, 10)
F_RED_TITLE = load(FONT_BOLD, 14)
F_RED_TEXT = load(FONT, 13)
F_ITEM = load(FONT, 14)
F_STRIP_TITLE = load(FONT_BOLD, 12)
F_STRIP = load(FONT, 17)
F_FOOT = load(FONT, 13)


def card(draw, x, y, w, h, fill="#ffffff", border=HAIR, width=1, radius=14):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius,
                           fill=fill, outline=border, width=width)


def right(draw, right_x, y, text, font, fill):
    draw.text((right_x - draw.textlength(text, font=font), y), text, font=font, fill=fill)


def centered(draw, cx, cy, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text((cx - tw / 2 - box[0], cy - th / 2 - box[1]), text, font=font, fill=fill)


def pill(draw, x, y, w, text, colors, font=F_PILL, h=22):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=7,
                           fill=colors[0], outline=colors[1], width=1)
    centered(draw, x + w / 2, y + h / 2, text, font, INK)


def arrow(draw, x1, y1, x2, y2, color=LINE):
    draw.line((x1, y1, x2, y2), fill=color, width=2)
    if x1 == x2:
        direction = 1 if y2 > y1 else -1
        draw.polygon([(x2 - 5, y2 - direction * 7), (x2 + 5, y2 - direction * 7), (x2, y2)],
                     fill=color)
    else:
        direction = 1 if x2 > x1 else -1
        draw.polygon([(x2 - direction * 7, y2 - 5), (x2 - direction * 7, y2 + 5), (x2, y2)],
                     fill=color)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    # --- заголовок
    draw.text((M, 26), "ПРОЦЕСС  ·  RED GATE", font=F_KICK, fill=MUTED)
    right(draw, W - M, 26, f"v{VERSION}  ·  {DATE}", F_NOTE, SOFT)
    draw.text((M, 46), "Красный не проходит", font=F_TITLE, fill=INK)
    draw.text((M, 100),
              "Правила → тест → изменение → verify → деплой только на 0 → журнал. "
              "Процесс держит даже неидеальный код.",
              font=F_SUB, fill=MUTED)

    # --- конвейер
    stages = [
        ("01", "ПРАВИЛА", ["RULES.md, AGENTS.md", "10 правил и 7 ворот", "что нельзя нарушать"], VIOLET),
        ("02", "ТЕСТ", ["поведение + запреты", "падает на поломке", "до или вместе с кодом"], BLUE),
        ("03", "ИЗМЕНЕНИЕ", ["микроблок, один диф", "копия → замена", "план отката"], BLUE),
        ("04", "VERIFY", ["build, tests, secrets", "схемы, размеры, fmt", "0 = зелёный"], YELLOW),
        ("05", "ДЕПЛОЙ", ["только на 0", "иначе стоп", "живая проверка после"], GREEN),
        ("06", "ЖУРНАЛ", ["ADR + JOURNAL", "решение, альтернативы", "схема факта"], GREEN),
    ]

    for index, (num, title, lines, colors) in enumerate(stages):
        x = 64 + index * (CARD_W + CARD_GAP)
        card(draw, x, CARD_Y, CARD_W, CARD_H)
        draw.text((x + 16, CARD_Y + 14), num, font=F_CARD_NUM, fill=colors[1])
        draw.text((x + 16, CARD_Y + 32), title, font=F_CARD_TITLE, fill=INK)
        for line_index, line in enumerate(lines):
            draw.text((x + 16, CARD_Y + 66 + line_index * 17), line,
                      font=F_CARD_TEXT, fill=MUTED)

        if index < len(stages) - 1:
            ax = x + CARD_W + CARD_GAP / 2
            draw.polygon([(ax - 3, CARD_Y + 85), (ax + 5, CARD_Y + 90), (ax - 3, CARD_Y + 95)],
                         fill=LINE)

    # --- зелёный путь: verify → deploy
    deploy_x = 64 + 4 * (CARD_W + CARD_GAP)
    verify_x = 64 + 3 * (CARD_W + CARD_GAP)
    pill(draw, deploy_x + CARD_W - 76, CARD_Y + 12, 60, "GREEN", GREEN, F_PILL, 20)

    # --- красная ветка
    red_x = verify_x
    red_y = 370
    red_w, red_h = CARD_W, 130
    card(draw, red_x, red_y, red_w, red_h, fill=RED[0], border=RED[1], width=2)
    draw.text((red_x + 14, red_y + 14), "RED: verify ≠ 0", font=F_RED_TITLE, fill=DARK_RED)
    for line_index, line in enumerate(["не деплоить", "отчёт: сделано /", "не сделано", "назад в изменение"]):
        draw.text((red_x + 14, red_y + 40 + line_index * 16), line,
                  font=F_RED_TEXT, fill=MUTED)

    arrow(draw, verify_x + CARD_W / 2, CARD_Y + CARD_H, verify_x + CARD_W / 2, red_y)

    # петля назад в изменение
    change_center = 64 + 2 * (CARD_W + CARD_GAP) + CARD_W / 2
    draw.line((red_x, red_y + 65, change_center, red_y + 65), fill=RED[1], width=2)
    draw.line((change_center, red_y + 65, change_center, CARD_Y + CARD_H + 10),
              fill=RED[1], width=2)
    draw.polygon([(change_center - 5, CARD_Y + CARD_H + 17),
                  (change_center + 5, CARD_Y + CARD_H + 17),
                  (change_center, CARD_Y + CARD_H + 7)], fill=RED[1])

    # --- что проверяет verify
    sx, sy = M, PANEL_Y
    card(draw, sx, sy, PANEL_W, PANEL_H)
    draw.text((sx + 24, sy + 18), "VERIFY ПРОВЕРЯЕТ", font=F_SECTION, fill=INK)
    right(draw, sx + PANEL_W - 24, sy + 23, "0 = зелёный, ≠ 0 = стоп", F_NOTE, SOFT)
    draw.line((sx + 24, sy + 50, sx + PANEL_W - 24, sy + 50), fill=HAIR, width=1)

    checks = [
        "build: команда стека",
        "test: команда стека",
        "секреты в диффе",
        "схемы и PNG",
        "размеры, fmt, мусор",
        "deadcode: go/ast",
        "npm и сторонние зависимости",
    ]
    for index, line in enumerate(checks):
        iy = sy + 66 + index * 30
        draw.ellipse((sx + 26, iy + 5, sx + 34, iy + 13), fill=GREEN[1])
        draw.text((sx + 46, iy), line, font=F_ITEM, fill=INK)
    draw.text((sx + 26, sy + 282), "verify.py — stdlib, без зависимостей",
              font=F_NOTE_S, fill=SOFT)

    # --- что фиксирует журнал
    gx = M + PANEL_W + 24
    card(draw, gx, sy, PANEL_W, PANEL_H)
    draw.text((gx + 24, sy + 18), "ЖУРНАЛ ФИКСИРУЕТ", font=F_SECTION, fill=INK)
    right(draw, gx + PANEL_W - 24, sy + 23, "одно решение = одна запись", F_NOTE, SOFT)
    draw.line((gx + 24, sy + 50, gx + PANEL_W - 24, sy + 50), fill=HAIR, width=1)

    journal = [
        "решение и дата",
        "альтернативы и почему отвергли",
        "последствия и цена",
        "ссылки: схемы, тесты, PR",
    ]
    for index, line in enumerate(journal):
        iy = sy + 66 + index * 36
        draw.ellipse((gx + 26, iy + 5, gx + 34, iy + 13), fill=GREEN[1])
        draw.text((gx + 46, iy), line, font=F_ITEM, fill=INK)
    draw.text((gx + 26, sy + 232), "ADR — значимое, JOURNAL — текущее.",
              font=F_NOTE, fill=SOFT)
    draw.text((gx + 26, sy + 258), "Без записи решение живёт только в голове.",
              font=F_NOTE, fill=SOFT)

    # --- почему работает
    card(draw, M, 860, 1512, 100, fill=INK, border="#334155", width=3)
    draw.text((M + 28, 878), "ПОЧЕМУ ЭТО РАБОТАЕТ", font=F_STRIP_TITLE, fill=YELLOW[1])
    draw.text((M + 28, 900),
              "Процесс проверяет факты, а не красоту кода: красный тест, живой результат, откат и запись решения.",
              font=F_STRIP, fill="#cbd5e1")
    draw.text((M + 28, 924),
              "Правило 1 снижает вероятность ошибки; процесс ловит то, что оно пропустило.",
              font=F_STRIP, fill="#cbd5e1")

    # --- подвал
    draw.line((M, 990, W - M, 990), fill=HAIR, width=1)
    draw.text((M, 1014),
              f"Процесс · {DATE} · PROCESS.md — текст, scheme-process.png — схема",
              font=F_FOOT, fill=SOFT)
    right(draw, W - M, 1014, "перерисовать: python docs/make_process_scheme.py",
          F_FOOT, SOFT)

    out = DOCS / "scheme-process.png"
    image.save(out)
    print("  готово:", out, "|", out.stat().st_size, "байт")
    return 0


if __name__ == "__main__":
    sys.exit(main())
