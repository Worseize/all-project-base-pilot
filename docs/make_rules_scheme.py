# -*- coding: utf-8 -*-
"""Рисует схему базовых правил крупного проекта.

    python docs/make_rules_scheme.py

Результат:
    docs/scheme-rules.png — десять правил, цикл из семи ворот,
    стоп-сигналы и определение готовности.

Зачем: правила должны быть не абзацем, который никто не перечитывает, а схемой
на один экран. Картинка и RULES.md — две проекции одного списка; при правке
правил обновляются обе, иначе карта начинает врать.
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

W, H = 1600, 1580
M = 44

BANNER_Y, BANNER_H = 188, 138
RULE_W, RULE_H = 492, 184
RULE_GAP = 16
RULES_Y = 344
RULE_COLORS = (VIOLET, BLUE, GREEN)

STEP_W, STEP_H, STEP_GAP = 200, 100, 13
BAND_Y, BAND_H = 980, 136
STEP_Y = 998

PANEL_Y, PANEL_H, PANEL_W = 1148, 340, 744


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
F_RULE_NUM = load(FONT_BOLD, 18)
F_RULE_TITLE = load(FONT_BOLD, 21)
F_RULE_BODY = load(FONT, 16)
F_PRICE = load(FONT, 14)
F_BANNER_KICK = load(FONT_BOLD, 12)
F_BANNER_NUM = load(FONT_BOLD, 20)
F_BANNER_TITLE = load(FONT_BOLD, 26)
F_BANNER_BODY = load(FONT, 17)
F_BANNER_PRICE = load(FONT, 14)
F_STEP_NUM = load(FONT_BOLD, 11)
F_STEP_TITLE = load(FONT_BOLD, 16)
F_STEP_DETAIL = load(FONT, 13)
F_PANEL_TITLE = load(FONT_BOLD, 20)
F_SIGNAL = load(FONT_BOLD, 15)
F_ITEM = load(FONT, 16)
F_REMEDY = load(FONT, 14)
F_FOOT = load(FONT, 13)


def card(draw, x, y, w, h, colors, radius=14):
    fill, border = colors
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=border, width=3)


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


def checkbox(draw, x, y, color):
    draw.rounded_rectangle((x, y, x + 18, y + 18), radius=4, fill="#ffffff", outline=color, width=2)
    draw.line((x + 4, y + 9, x + 8, y + 13), fill=color, width=2)
    draw.line((x + 8, y + 13, x + 14, y + 4), fill=color, width=2)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    # --- заголовок
    draw.text((M, 26), "ШАБЛОН АРХИТЕКТУРЫ  ·  ПРАВИЛА АГЕНТА", font=F_KICK, fill=MUTED)
    right(draw, W - M, 26, f"Go stdlib  ·  v{VERSION}  ·  {DATE}", F_NOTE, SOFT)
    draw.text((M, 46), "Как ведётся крупный проект", font=F_TITLE, fill=INK)

    subtitle = ("Десять правил действуют на каждом шаге  ·  семь ворот нельзя пропускать  ·  "
                "задача закрыта фактом, а не отчётом")
    draw.text((M, 100), subtitle, font=F_SUB, fill=MUTED)

    # --- правило первое: широкая карточка
    draw.text((M, 146), "ДЕСЯТЬ ПРАВИЛ — НА КАЖДОМ ШАГЕ", font=F_SECTION, fill=INK)
    right(draw, W - M, 152, "полный текст и проверки — RULES.md", F_NOTE, SOFT)

    banner_title = "Чистый код, имена и уборка"
    banner_body = [
        "Имя функции — глагол + объект: CreateUser, ParseConfig, SendReport. "
        "Имя переменной — существительное.",
        "Мёртвый код, комментарии, temp-файлы и debug — в корзину; старый код "
        "не комментируем, а удаляем: история — в репозитории.",
    ]
    banner_price = "имена-загадки и мусор: через месяц никто не знает, что живо"

    card(draw, M, BANNER_Y, 1512, BANNER_H, (INK, "#334155"), radius=16)

    badge = 38
    bx, by = M + 24, BANNER_Y + 22
    draw.rounded_rectangle((bx, by, bx + badge, by + badge), radius=10,
                           fill=YELLOW[1], outline=YELLOW[1])
    centered(draw, bx + badge / 2, by + badge / 2, "1", F_BANNER_NUM, INK)

    draw.text((M + 78, BANNER_Y + 20), "ПРАВИЛО ПЕРВОЕ", font=F_BANNER_KICK, fill=YELLOW[1])
    draw.text((M + 78, BANNER_Y + 36), banner_title, font=F_BANNER_TITLE, fill="#ffffff")

    for line_index, line in enumerate(banner_body):
        if draw.textlength(line, font=F_BANNER_BODY) > 1512 - 102:
            raise SystemExit(f"длинная строка правила 1: {line!r}")
        draw.text((M + 78, BANNER_Y + 78 + line_index * 24), line,
                  font=F_BANNER_BODY, fill="#cbd5e1")

    right(draw, M + 1512 - 24, BANNER_Y + 24, "цена: " + banner_price,
          F_BANNER_PRICE, "#fca5a5")

    # --- правила 2–10: сетка 3×3
    rules = [
        ("Все новые фичи — в схемах",
         "Новая фича сначала — на схеме плана (что должно быть), потом в коде, после — на схеме факта (что есть). Схемы и ADR — тем же шагом.",
         "фича есть, а на карте её нет — следующий шаг её не видит"),
        ("Тесты под каждую фичу",
         "Под каждую фичу — тест: поведение и запреты. Тесты — по блокам, не одним файлом; тест падает, если фича или инвариант сломаны.",
         "фича работает «на глаз», а завтра ломается молча"),
        ("Ноль зависимостей: Go",
         "Go stdlib: без сторонних модулей, npm и обновлений. ООП: структуры, интерфейсы, композиция; домен без БД и UI.",
         "зависимость притащила CVE, и сборка встала"),
        ("Схемы — источник истины",
         "Каждое правило или изменение шаблона — на схемах тем же шагом. Схема не иллюстрация, а источник истины: расхождение — дефект.",
         "схема врёт, и следующее изменение строят по ней"),
        ("Микроблоки и ООП",
         "Блок ≤ 400 строк, функция ≤ 80. ООП — база: инкапсуляция, интерфейсы, композиция. Данные — структуры, не map; без глобального состояния.",
         "блоки срослись, и правка тянет половину проекта"),
        ("Читать перед записью",
         "Целевой блок открывается целиком. Отступ и соседние строки берутся из файла, замена подтверждается проверкой.",
         "правка в чужом месте: код цел, но не тот"),
        ("Пять минут — стоп",
         "Одна причина — один диф. Копия → замена → сборка → откат. Больше 5 минут — стоп: что сделал, что нет, и остановись.",
         "контекст сгорел, а результата и состояния нет"),
        ("Проверять живо",
         "«Команда выполнена» — не доказательство. Смотри журнал, экран, страницу и фактическое число записей.",
         "отчёт зелёный, пользователь видит пустоту"),
        ("Данные и секреты",
         "Опасные операции — в песочнице. Секреты вне кода и логов. Бэкап без проверки восстановления — не бэкап; шаги миграций не удаляются.",
         "чужие данные стёрты, ключи утекли в историю"),
    ]

    for index, (title, body, price) in enumerate(rules):
        num = index + 2
        col, row = index % 3, index // 3
        colors = RULE_COLORS[row]
        x = M + col * (RULE_W + RULE_GAP)
        y = RULES_Y + row * (RULE_H + RULE_GAP)

        card(draw, x, y, RULE_W, RULE_H, colors)

        badge = 34
        bx, by = x + 20, y + 18
        draw.rounded_rectangle((bx, by, bx + badge, by + badge), radius=9,
                               fill=colors[1], outline=colors[1])
        centered(draw, bx + badge / 2, by + badge / 2, str(num), F_RULE_NUM, "#ffffff")

        if draw.textlength(title, font=F_RULE_TITLE) > RULE_W - 86:
            raise SystemExit(f"длинный заголовок правила: {title!r}")
        draw.text((x + 66, y + 22), title, font=F_RULE_TITLE, fill=INK)

        body_lines = lines_or_fail(draw, body, F_RULE_BODY, RULE_W - 44, 3, f"правило {num}")
        for line_index, line in enumerate(body_lines):
            draw.text((x + 22, y + 64 + line_index * 23), line, font=F_RULE_BODY, fill=MUTED)

        draw.line((x + 22, y + 142, x + RULE_W - 22, y + 142), fill=colors[1], width=1)
        draw.text((x + 22, y + 152), "цена: " + price, font=F_PRICE, fill=SOFT)

    # --- цикл шага
    draw.text((M, 946), "ЦИКЛ ШАГА: СЕМЬ ВОРОТ", font=F_SECTION, fill=INK)
    right(draw, W - M, 952, "ни одни ворота не пропускаются", F_NOTE, SOFT)

    draw.rounded_rectangle((M, BAND_Y, M + 1512, BAND_Y + BAND_H), radius=18,
                           fill="#e9eef5", outline="#dbe3ee", width=1)

    steps = [
        ("1", "ПОНЯТЬ", "цель, файлы, источник истины", VIOLET),
        ("2", "СПРОЕКТИРОВАТЬ", "контракт, слои, схема плана", VIOLET),
        ("3", "ИЗМЕНИТЬ", "один диф — одна причина", BLUE),
        ("4", "СОБРАТЬ", "компиляция, линт, типы", BLUE),
        ("5", "ПРОВЕРИТЬ", "тесты, инварианты, песочница", BLUE),
        ("6", "ДОКАЗАТЬ", "журнал, экран, данные", GREEN),
        ("7", "ЗАПИСАТЬ", "схемы, ADR, журнал", GREEN),
    ]

    for offset, (num, title, detail, colors) in enumerate(steps):
        x = 60 + offset * (STEP_W + STEP_GAP)
        draw.rounded_rectangle((x, STEP_Y, x + STEP_W, STEP_Y + STEP_H), radius=12,
                               fill="#ffffff", outline="#d7dfeb", width=1)
        draw.text((x + 14, STEP_Y + 10), num.zfill(2), font=F_STEP_NUM, fill=colors[1])
        if draw.textlength(title, font=F_STEP_TITLE) > STEP_W - 28:
            raise SystemExit(f"длинный заголовок шага: {title!r}")
        draw.text((x + 14, STEP_Y + 27), title, font=F_STEP_TITLE, fill=INK)

        detail_lines = lines_or_fail(draw, detail, F_STEP_DETAIL, STEP_W - 28, 2, f"шаг {num}")
        for line_index, line in enumerate(detail_lines):
            draw.text((x + 14, STEP_Y + 54 + line_index * 16), line, font=F_STEP_DETAIL, fill=SOFT)

        if offset < len(steps) - 1:
            cx = x + STEP_W + STEP_GAP / 2
            draw.polygon([(cx - 3, STEP_Y + 43), (cx + 3, STEP_Y + 48), (cx - 3, STEP_Y + 53)],
                         fill=LINE)

    # --- стоп-сигналы
    sx, sy = M, PANEL_Y
    card(draw, sx, sy, PANEL_W, PANEL_H, RED)
    draw.text((sx + 24, sy + 18), "СТОП-СИГНАЛЫ", font=F_PANEL_TITLE, fill=INK)
    right(draw, sx + PANEL_W - 24, sy + 24, "увидел — вернись на шаг назад", F_NOTE, SOFT)
    draw.line((sx + 24, sy + 50, sx + PANEL_W - 24, sy + 50), fill=RED[1], width=1)

    signals = [
        ("Правлю, не прочитав блок", "открыть блок целиком"),
        ("Срез по числу вместо разбора", "разбирать по смыслу"),
        ("Одна сущность в двух местах", "свести к источнику истины"),
        ("«Готово» без факта", "журнал, экран, данные"),
        ("Нет копии и плана отката", "сначала откат — потом правка"),
        ("Думаю больше 5 минут", "стоп: сделано / не сделано"),
        ("Секрет в коде или логе", "вынести в окружение"),
        ("Мёртвый код про запас", "удалить: история в репозитории"),
        ("Фича без теста", "тест на поведение и запреты"),
        ("Схема не обновлена", "карта — тем же шагом"),
    ]
    for item_index, (signal, remedy) in enumerate(signals):
        iy = sy + 62 + item_index * 27
        draw.ellipse((sx + 26, iy + 6, sx + 34, iy + 14), fill=RED[1])
        if draw.textlength(signal, font=F_SIGNAL) > 272:
            raise SystemExit(f"длинный стоп-сигнал: {signal!r}")
        draw.text((sx + 46, iy), signal, font=F_SIGNAL, fill=INK)
        draw.text((sx + 334, iy + 2), "→", font=F_REMEDY, fill=LINE)
        draw.text((sx + 356, iy + 2), remedy, font=F_REMEDY, fill=MUTED)

    # --- определение готовности
    gx = M + PANEL_W + 24
    card(draw, gx, sy, PANEL_W, PANEL_H, GREEN)
    draw.text((gx + 24, sy + 18), "ЗАДАЧА ЗАКРЫТА, КОГДА", font=F_PANEL_TITLE, fill=INK)
    right(draw, gx + PANEL_W - 24, sy + 24, "все пункты, не выборочно", F_NOTE, SOFT)
    draw.line((gx + 24, sy + 50, gx + PANEL_W - 24, sy + 50), fill=GREEN[1], width=1)

    done = [
        "Сборка и компиляция проходят без ошибок.",
        "Тесты на каждую фичу и инварианты зелёные.",
        "Живая проверка: журнал, экран, фактические данные.",
        "Откат возможен и проверен.",
        "Мёртвый код, временные файлы и отладочный вывод удалены.",
        "Схемы факта и плана, ADR и журнал обновлены.",
        "В диффе нет секретов, мусора и чужих правок.",
    ]
    for item_index, item in enumerate(done):
        iy = sy + 64 + item_index * 31
        checkbox(draw, gx + 26, iy + 1, GREEN[1])
        draw.text((gx + 54, iy), item, font=F_ITEM, fill=INK)

    draw.text((gx + 26, sy + 290), "→  «выполнено» — это увиденный результат, а не код возврата",
              font=F_NOTE, fill=MUTED)

    # --- подвал
    draw.line((M, 1522, W - M, 1522), fill=HAIR, width=1)
    draw.text((M, 1546),
              f"Схема создана {DATE}  ·  RULES.md — правила, docs/scheme-rules.png — схема",
              font=F_FOOT, fill=SOFT)
    right(draw, W - M, 1546, "перерисовать: python docs/make_rules_scheme.py", F_FOOT, SOFT)

    out = DOCS / "scheme-rules.png"
    image.save(out)
    print("  готово:", out, "|", out.stat().st_size, "байт")
    return 0


if __name__ == "__main__":
    sys.exit(main())
