# -*- coding: utf-8 -*-
"""Рисует две схемы стратегии шаблона.

    python docs/make_strategy_schemes.py

Результат:
    docs/scheme-strategy.png — видение, шесть слоёв и рабочий цикл.
    docs/scheme-roadmap.png  — дорожная карта 0.5 → 1.0 и очередь улучшений
                               в координатах impact / effort.

Зачем: стратегия без картинки превращается в документ, который не перечитывают.
Схемы и STRATEGY.md — две проекции одного плана; при правке плана обновляются обе.
"""

import math
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
DARK_BLUE = "#2563eb"
DARK_YELLOW = "#b45309"
DARK_RED = "#dc2626"

W1, H1 = 1600, 1380
W2, H2 = 1600, 1300
M = 44


def load(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


F_KICK = load(FONT_BOLD, 14)
F_TITLE = load(FONT_BOLD, 38)
F_SUB = load(FONT, 18)
F_SECTION = load(FONT_BOLD, 21)
F_NOTE = load(FONT, 14)
F_NOTE_S = load(FONT, 12)
F_VISION_KICK = load(FONT_BOLD, 12)
F_VISION = load(FONT, 19)
F_LAYER_NUM = load(FONT_BOLD, 15)
F_LAYER_TITLE = load(FONT_BOLD, 19)
F_LAYER_DESC = load(FONT, 14)
F_LAYER_ART = load(FONT, 13)
F_STATUS = load(FONT_BOLD, 12)
F_FLY_TITLE = load(FONT_BOLD, 19)
F_FLY_LABEL = load(FONT_BOLD, 12)
F_FLY_NUM = load(FONT_BOLD, 14)
F_FLY_CENTER = load(FONT_BOLD, 28)
F_FLY_CENTER_S = load(FONT, 13)
F_PRINCIPLE_NUM = load(FONT_BOLD, 13)
F_PRINCIPLE_TITLE = load(FONT_BOLD, 15)
F_PRINCIPLE_DESC = load(FONT, 13)
F_CARD_VERSION = load(FONT_BOLD, 12)
F_CARD_TITLE = load(FONT_BOLD, 17)
F_CARD_BULLET = load(FONT, 13)
F_CARD_EXIT = load(FONT, 12)
F_STATUS_S = load(FONT_BOLD, 11)
F_MATRIX_AXIS = load(FONT_BOLD, 12)
F_MATRIX_Q = load(FONT_BOLD, 11)
F_BUBBLE = load(FONT_BOLD, 12)
F_LIST_HEAD = load(FONT_BOLD, 19)
F_LIST_GROUP = load(FONT_BOLD, 11)
F_LIST_NUM = load(FONT_BOLD, 10)
F_LIST_TITLE = load(FONT_BOLD, 13)
F_LIST_WHY = load(FONT, 11)
F_STEP_NUM = load(FONT_BOLD, 15)
F_STEP_TITLE = load(FONT_BOLD, 17)
F_STEP_DESC = load(FONT, 13)
F_FOOT = load(FONT, 13)


def card(draw, x, y, w, h, fill="#ffffff", border=HAIR, width=1, radius=14):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius,
                           fill=fill, outline=border, width=width)


def wrap(draw, text, font, max_w):
    words = text.split()
    lines, current = [], ""
    for word in words:
        probe = (current + " " + word).strip()
        if draw.textlength(probe, font=font) <= max_w:
            current = probe
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def lines_or_fail(draw, text, font, max_w, max_lines, tag):
    lines = wrap(draw, text, font, max_w)
    if len(lines) > max_lines:
        raise SystemExit(f"{tag}: {len(lines)} строк вместо {max_lines} — {text!r}")
    return lines


def right(draw, right_x, y, text, font, fill):
    draw.text((right_x - draw.textlength(text, font=font), y), text, font=font, fill=fill)


def centered(draw, cx, cy, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text((cx - tw / 2 - box[0], cy - th / 2 - box[1]), text, font=font, fill=fill)


def pill(draw, x, y, w, text, colors, font=F_STATUS, h=26):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8,
                           fill=colors[0], outline=colors[1], width=1)
    centered(draw, x + w / 2, y + h / 2, text, font, INK)


def badge(draw, x, y, size, text, colors, font, text_fill="#ffffff"):
    draw.rounded_rectangle((x, y, x + size, y + size), radius=9,
                           fill=colors[1], outline=colors[1])
    centered(draw, x + size / 2, y + size / 2, str(text), font, text_fill)


def draw_header(draw, kicker, title, subtitle, right_text):
    draw.text((M, 26), kicker, font=F_KICK, fill=MUTED)
    right(draw, 1600 - M, 26, right_text, F_NOTE, SOFT)
    draw.text((M, 46), title, font=F_TITLE, fill=INK)
    draw.text((M, 100), subtitle, font=F_SUB, fill=MUTED)


def draw_footer(draw, width, height, name):
    draw.line((M, height - 60, width - M, height - 60), fill=HAIR, width=1)
    draw.text((M, height - 36),
              f"Стратегия шаблона · {DATE} · STRATEGY.md — текст, {name} — схема",
              font=F_FOOT, fill=SOFT)
    right(draw, width - M, height - 36,
          "перерисовать: python docs/make_strategy_schemes.py", F_FOOT, SOFT)


def draw_strategy():
    image = Image.new("RGB", (W1, H1), BG)
    draw = ImageDraw.Draw(image)

    draw_header(draw,
                "СТРАТЕГИЯ ШАБЛОНА  ·  СЛОЙ 0.6",
                "От правил — к операционной системе проекта",
                "Правило → артефакт → проверка → доказательство. Шаблон работает для агента и человека.",
                f"Go stdlib  ·  v{VERSION}  ·  {DATE}")

    # --- видение
    card(draw, M, 150, 1512, 112, fill=INK, border="#334155", width=3, radius=16)
    draw.text((M + 28, 168), "ВИДЕНИЕ", font=F_VISION_KICK, fill=YELLOW[1])
    draw.text((M + 28, 190),
              "Не папка правил, а замкнутый контур: правило превращается в артефакт,",
              font=F_VISION, fill="#e2e8f0")
    draw.text((M + 28, 216),
              "артефакт проверяется, проверка даёт доказательство — и меняет следующее правило.",
              font=F_VISION, fill="#cbd5e1")

    # --- слои
    draw.text((M, 292), "ШЕСТЬ СЛОЁВ: ОТ ПРАВИЛ К СИСТЕМЕ", font=F_SECTION, fill=INK)
    legend = [("готово", GREEN), ("в работе", YELLOW), ("следующий", BLUE), ("позже", GRAY)]
    widths = [8 + 6 + draw.textlength(label, font=F_NOTE_S) + 16 for label, _ in legend]
    lx = 1556 - sum(widths)
    for (label, colors), width in zip(legend, widths):
        draw.ellipse((lx, 300, lx + 8, 308), fill=colors[1])
        draw.text((lx + 12, 296), label, font=F_NOTE_S, fill=SOFT)
        lx += width

    layers = [
        ("1", "Инварианты", "10 правил, схема и AGENTS.md",
         "RULES.md + scheme-rules.png", "готово", GREEN),
        ("2", "Профиль проекта", "Go stdlib, команды, границы, владельцы",
         "PROJECT.md", "готово", GREEN),
        ("3", "Карты", "схемы факта и плана, карточка фичи",
         "docs/architecture/", "следующий", BLUE),
        ("4", "Контур проверки", "тесты на фичу, живая проверка, откат",
         "verify + PROCESS.md", "в работе", YELLOW),
        ("5", "Память", "ADR, журнал, changelog решений",
         "docs/adr/", "в работе", YELLOW),
        ("6", "Развитие", "автоматизация, версии, метрики, пилот",
         "CI + отчёт", "позже", GRAY),
    ]
    for index, (num, title, desc, artifact, status, colors) in enumerate(layers):
        y = 330 + index * 130
        card(draw, M, y, 900, 118)
        badge(draw, M + 18, y + 18, 30, num, colors, F_LAYER_NUM,
              text_fill=INK if colors in (YELLOW, GRAY) else "#ffffff")
        draw.text((M + 60, y + 18), title, font=F_LAYER_TITLE, fill=INK)
        if draw.textlength(desc, font=F_LAYER_DESC) > 650:
            raise SystemExit(f"длинное описание слоя: {desc!r}")
        draw.text((M + 60, y + 50), desc, font=F_LAYER_DESC, fill=MUTED)
        draw.text((M + 60, y + 80), "артефакт: " + artifact, font=F_LAYER_ART, fill=SOFT)
        pill(draw, M + 766, y + 16, 110, status, colors)

    # --- рабочий цикл
    card(draw, 980, 330, 576, 768)
    draw.text((1004, 348), "РАБОЧИЙ ЦИКЛ", font=F_FLY_TITLE, fill=INK)
    right(draw, 1532, 354, "семь шагов", F_NOTE, SOFT)

    cx, cy, radius = 1268, 710, 170
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 outline="#dbe3ee", width=2)

    cycle = [
        ("1", "ПРАВИЛА", VIOLET),
        ("2", "ПРОФИЛЬ", VIOLET),
        ("3", "ПЛАН", BLUE),
        ("4", "ФИЧА+ТЕСТ", BLUE),
        ("5", "ФАКТ", GREEN),
        ("6", "ПРОВЕРКА", YELLOW),
        ("7", "ПАМЯТЬ", GRAY),
    ]
    for index, (num, label, colors) in enumerate(cycle):
        angle = math.radians(-90 + index * 360 / 7)
        nx = cx + radius * math.cos(angle)
        ny = cy + radius * math.sin(angle)
        badge(draw, nx - 19, ny - 19, 38, num, colors, F_FLY_NUM,
              text_fill=INK if colors in (YELLOW, GRAY) else "#ffffff")

        lx = cx + (radius + 42) * math.cos(angle)
        ly = cy + (radius + 42) * math.sin(angle)
        centered(draw, lx, ly, label, F_FLY_LABEL, INK)

    for index in range(7):
        angle = math.radians(-90 + index * 360 / 7 + 360 / 14)
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        tx, ty = -math.sin(angle), math.cos(angle)
        draw.polygon([
            (px + tx * 7, py + ty * 7),
            (px - tx * 4 + math.cos(angle) * 4, py - ty * 4 + math.sin(angle) * 4),
            (px - tx * 4 - math.cos(angle) * 4, py - ty * 4 - math.sin(angle) * 4),
        ], fill=LINE)

    centered(draw, cx, cy - 36, "1 ШАГ", F_FLY_CENTER, INK)
    centered(draw, cx, cy + 4, "правило → артефакт", F_FLY_CENTER_S, MUTED)
    centered(draw, cx, cy + 24, "→ проверка → память", F_FLY_CENTER_S, MUTED)
    centered(draw, cx, cy + 46, "5 минут — стоп", F_FLY_CENTER_S, DARK_YELLOW)

    centered(draw, cx, 970, "Правило без артефакта и проверки — лозунг.", F_NOTE, SOFT)
    centered(draw, cx, 992, "Шаблон развивается по своим правилам.", F_NOTE, SOFT)

    # --- принципы
    draw.text((M, 1124), "ПРИНЦИПЫ, КОТОРЫЕ ДЕРЖАТ КОНТУР", font=F_SECTION, fill=INK)
    principles = [
        ("1", "Бюджет правил — 10",
         "Новое правило вбирает старое, иначе это чек-лист.", VIOLET),
        ("2", "Правило проверяемо",
         "Артефакт + автоматика или ручной шаг.", BLUE),
        ("3", "Ноль зависимостей",
         "Go stdlib; без npm и пакетов.", GREEN),
        ("4", "Карты — производные",
         "Где можно, генерируем; drift ловит CI.", YELLOW),
        ("5", "Пилот решает",
         "Одна фича важнее десяти идей.", GRAY),
    ]
    for index, (num, title, desc, colors) in enumerate(principles):
        x = M + index * (289 + 16)
        card(draw, x, 1160, 289, 110)
        badge(draw, x + 18, 1178, 26, num, colors, F_PRINCIPLE_NUM,
              text_fill=INK if colors in (YELLOW, GRAY) else "#ffffff")
        if draw.textlength(title, font=F_PRINCIPLE_TITLE) > 217:
            raise SystemExit(f"длинный заголовок принципа: {title!r}")
        draw.text((x + 54, 1176), title, font=F_PRINCIPLE_TITLE, fill=INK)
        for line_index, line in enumerate(
                lines_or_fail(draw, desc, F_PRINCIPLE_DESC, 253, 2, f"принцип {num}")):
            draw.text((x + 18, 1208 + line_index * 18), line,
                      font=F_PRINCIPLE_DESC, fill=MUTED)

    draw_footer(draw, W1, H1, "scheme-strategy.png")
    out = DOCS / "scheme-strategy.png"
    image.save(out)
    print("  готово:", out, "|", out.stat().st_size, "байт")


def draw_roadmap():
    image = Image.new("RGB", (W2, H2), BG)
    draw = ImageDraw.Draw(image)

    draw_header(draw,
                "ДОРОЖНАЯ КАРТА  ·  ОЧЕРЕДЬ УЛУЧШЕНИЙ",
                "Что делаем дальше и в каком порядке",
                "Сначала замкнутый контур, потом автоматизация и масштаб. Каждый шаг проверяем на пилоте.",
                f"Go stdlib  ·  v{VERSION}  ·  {DATE}")

    # --- дорожная карта
    draw.text((M, 146), "ДОРОЖНАЯ КАРТА 0.5 → 1.0", font=F_SECTION, fill=INK)
    right(draw, 1556, 152, "каждый шаг — с критерием выхода", F_NOTE, SOFT)

    milestones = [
        ("0.5", "Правила", ["10 правил + схема", "AGENTS.md"],
         "готово", GREEN, "правила читаются за 10 минут"),
        ("0.6", "Стратегия", ["видение и слои", "roadmap + очередь"],
         "сейчас", YELLOW, "решение о следующем слое"),
        ("0.7", "Профиль", ["PROJECT.md", "definition of ready"],
         "далее", BLUE, "агент стартует без вопросов"),
        ("0.8", "Карты", ["факт/план + ADR", "карточка фичи"],
         "далее", BLUE, "карта не врёт"),
        ("0.9", "Автоматизация", ["CI + hooks", "branch protection"],
         "в работе", YELLOW, "проверка одной командой"),
        ("1.0", "Пилот", ["реальная фича", "метрики и публикация"],
         "далее", GRAY, "контур доказан"),
    ]

    for index, (version, title, bullets, status, colors, exit_text) in enumerate(milestones):
        x = 50 + index * 252
        card(draw, x, 186, 240, 170)
        draw.text((x + 16, 200), version, font=F_CARD_VERSION, fill=colors[1])
        pill(draw, x + 150, 196, 74, status, colors, F_STATUS_S, h=22)
        draw.text((x + 16, 228), title, font=F_CARD_TITLE, fill=INK)
        for line_index, line in enumerate(bullets):
            draw.text((x + 16, 262 + line_index * 17), "• " + line,
                      font=F_CARD_BULLET, fill=MUTED)
        draw.line((x + 16, 300, x + 224, 300), fill=HAIR, width=1)
        draw.text((x + 16, 310), "выход: " + exit_text, font=F_CARD_EXIT, fill=colors[1])

        if index < len(milestones) - 1:
            gx = x + 240 + 2
            draw.polygon([(gx, 268), (gx + 8, 273), (gx, 278)], fill=LINE)

    # --- очередь улучшений
    draw.text((M, 390), "ОЧЕРЕДЬ УЛУЧШЕНИЙ: СНАЧАЛА РИСК, ПОТОМ СКОРОСТЬ",
              font=F_SECTION, fill=INK)
    right(draw, 1556, 396, "impact / effort", F_NOTE, SOFT)

    card(draw, M, 430, 900, 560)
    x0, x1, y0, y1 = 120, 840, 480, 950
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    draw.rectangle((x0, y0, mx, my), fill="#ecfdf5")
    draw.rectangle((mx, y0, x1, my), fill="#eff6ff")
    draw.rectangle((x0, my, mx, y1), fill="#fffbeb")
    draw.rectangle((mx, my, x1, y1), fill="#fef2f2")
    draw.line((mx, y0, mx, y1), fill="#ffffff", width=2)
    draw.line((x0, my, x1, my), fill="#ffffff", width=2)
    draw.rectangle((x0, y0, x1, y1), outline=HAIR, width=1)

    draw.text((60, 455), "ЭФФЕКТ ↑", font=F_MATRIX_AXIS, fill=MUTED)
    draw.text((760, 958), "УСИЛИЕ →", font=F_MATRIX_AXIS, fill=MUTED)
    draw.text((130, 494), "СДЕЛАТЬ СЕЙЧАС", font=F_MATRIX_Q, fill=DARK_GREEN)
    draw.text((560, 494), "ПЛАНИРОВАТЬ", font=F_MATRIX_Q, fill=DARK_BLUE)
    draw.text((130, 905), "БЫСТРО, НО МЕЛКО", font=F_MATRIX_Q, fill=DARK_YELLOW)
    draw.text((560, 905), "ПОЗЖЕ", font=F_MATRIX_Q, fill=DARK_RED)

    points = [
        (0.18, 0.86, 1, GREEN),
        (0.30, 0.78, 2, GREEN),
        (0.40, 0.84, 3, GREEN),
        (0.22, 0.66, 4, GREEN),
        (0.80, 0.82, 5, BLUE),
        (0.32, 0.54, 6, BLUE),
        (0.56, 0.58, 7, BLUE),
        (0.86, 0.74, 8, BLUE),
        (0.68, 0.40, 9, GRAY),
        (0.22, 0.34, 10, GRAY),
    ]
    for effort, impact, num, colors in points:
        bx = x0 + effort * (x1 - x0)
        by = y1 - impact * (y1 - y0)
        draw.ellipse((bx - 15, by - 15, bx + 15, by + 15),
                     fill=colors[1], outline="#ffffff", width=2)
        centered(draw, bx, by, str(num), F_BUBBLE, INK if num >= 9 else "#ffffff")

    # --- список очереди
    card(draw, 976, 430, 580, 560)
    draw.text((996, 446), "ОЧЕРЕДЬ", font=F_LIST_HEAD, fill=INK)
    right(draw, 1536, 452, "P0 → P1 → P2", F_NOTE_S, SOFT)

    groups = [
        ("P0 · СДЕЛАТЬ СЕЙЧАС", DARK_GREEN, [
            (1, "PROJECT.md", "Go stdlib, команды, границы, владельцы"),
            (2, "FEATURE.md", "цель, схема, тест, откат, DoD"),
            (3, "verify", "линт, тесты, секреты, drift"),
            (4, "ADR + журнал", "почему решили и что отвергли"),
        ]),
        ("P1 · СЛЕДОМ", DARK_BLUE, [
            (5, "Генераторы карт", "факт/план без ручной сборки"),
            (6, "Матрица rule→check", "ни одного правила без проверки"),
            (7, "Плейбуки", "старт фичи, баг, рефакторинг, релиз"),
            (8, "CI + drift", "проверка на каждом PR"),
        ]),
        ("P2 · ПОТОМ", SOFT, [
            (9, "Метрики", "время, дефекты, откаты, drift"),
            (10, "Версии и онбординг", "changelog и быстрый старт"),
        ]),
    ]

    y = 478
    for label, color, items in groups:
        draw.text((996, y), label, font=F_LIST_GROUP, fill=color)
        y += 22
        for num, title, why in items:
            draw.ellipse((996, y + 4, 1014, y + 22), fill=GRAY[1])
            centered(draw, 1005, y + 13, str(num), F_LIST_NUM, INK)
            draw.text((1024, y), title, font=F_LIST_TITLE, fill=INK)
            draw.text((1024, y + 16), why, font=F_LIST_WHY, fill=MUTED)
            y += 38
        y += 8

    # --- ближайшие шаги
    draw.text((M, 1020), "БЛИЖАЙШИЕ ТРИ ШАГА", font=F_SECTION, fill=INK)
    right(draw, 1556, 1026, "без них стратегия остаётся текстом", F_NOTE, SOFT)

    steps = [
        ("1", "PROJECT.md",
         "1 страница: Go stdlib, команды, границы, владельцы.", GREEN),
        ("2", "FEATURE.md + verify",
         "Шаблон фичи и одна команда: линт, тесты, секреты, drift.", BLUE),
        ("3", "Пилот",
         "Одна реальная фича: время, ошибки, drift, откат.", YELLOW),
    ]
    for index, (num, title, desc, colors) in enumerate(steps):
        x = M + index * (492 + 18)
        card(draw, x, 1056, 492, 130)
        badge(draw, x + 18, 1074, 30, num, colors, F_STEP_NUM,
              text_fill=INK if colors in (YELLOW, GRAY) else "#ffffff")
        draw.text((x + 58, 1074), title, font=F_STEP_TITLE, fill=INK)
        for line_index, line in enumerate(
                lines_or_fail(draw, desc, F_STEP_DESC, 456, 2, f"шаг {num}")):
            draw.text((x + 18, 1112 + line_index * 18), line,
                      font=F_STEP_DESC, fill=MUTED)

    draw_footer(draw, W2, H2, "scheme-roadmap.png")
    out = DOCS / "scheme-roadmap.png"
    image.save(out)
    print("  готово:", out, "|", out.stat().st_size, "байт")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    draw_strategy()
    draw_roadmap()
    return 0


if __name__ == "__main__":
    sys.exit(main())
