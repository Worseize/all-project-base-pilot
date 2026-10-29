# Запросы владельца: что сделано

Один запрос — одна строка: что просили, что сделано, где доказательство.
Строка без пути, issue или вывода `verify.py` — не сделана; гейт
`verify.py` → `requests` краснеет.

| # | Запрос | Что сделано | Доказательство |
| --- | --- | --- | --- |
| findings#32 | Правила базы: тест под правило и слияние похожих | Карта, `rules-tests` с обязательным тестом, `rules-dupes`, шесть тестов | `docs/RULES-TESTS.md`, CI `ee01cf3` |
| 27.10 16:00 | Указание на правило или тест не теряется | `docs/REQUESTS.md` и гейт `requests` | `verify.py`, `tests/test_verify.py` |
| 27.10 16:20 | Доска — последним разделом ответа | `deploy/check-reply.py`: первая строка «почта:», `board_is_last`, итог | `tests/test_reply_format.py` |
| 27.10 10:15 | Новые практики узла — в шаблон | Заведено долгом `D28-1` | `DEBTS.md` |
| 27.10 15:40 | Коммиты привязать к issue | Сообщения коммитов с `findings#32` | `findings#32`, CI `ee01cf3` |
| 27.10 16:30 | Доска в чате — четыре колонки | `deploy/check-reply.py`: четыре колонки, лимиты 8/18/50/60, строка ≤ 149, сверка с файлом | `tests/test_reply_format.py` |
| 27.10 16:45 | Инструкция «где вписать личные данные», `findings#33` | `docs/PERSONAL-DATA.md`, сканер и гейт `personal-data`, шесть тестов | `findings#33`, `deploy/check-personal-data.py` |
| 27.10 17:00 | Внешние данные с подтверждением и откатом | `docs/EXTERNAL-DATA.md` и гейт `external-data` (снимок, подтверждение, откат) | `docs/EXTERNAL-DATA.md`, `verify.py` |
| 28.10 11:29 | Пробуждение по расписанию закрывает минимум один долг | `docs/WAKE-LOG.md`, гейт `wake-debts`, семь тестов | `verify.py`, `tests/test_verify.py` |
| 27.10 10:15 | Шина без суточных лимитов | `docs/BUS.md`, гейт `bus-limits` | `docs/BUS.md`, `verify.py` |
| 27.10 10:15 | Карта инфраструктуры | `docs/INFRA-MAP.md`, гейт `infra-map` | `docs/INFRA-MAP.md` |
| 27.10 10:15 | Ротация сессии | `docs/ROTATION.md`, гейт `rotation` | `docs/ROTATION.md` |
| 28.10 15:32 | Доска: колонка «Кто замедляет» | `deploy/check-reply.py`: колонка, лимит 14, связка тега и значения; 18 тестов | `tests/test_reply_format.py` |
| 29.10 14:40 | Расписание подписано именем чата | `docs/SCHEDULES.md`, правило в `AGENTS.md`, гейт `schedules`, три теста | `tests/test_verify.py`, `verify.py` |

Версия 0.9.55 · 29.10.2026
