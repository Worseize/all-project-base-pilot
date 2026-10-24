# CHANGELOG

## 0.9.10 — 2026-10-24

- Канал команд: приватный findings, публичный файл приёмки.
- `docs/acceptance/`, `check_acceptance`, тесты на утечки.
- `PROCESS.md`/`ISOLATION.md` описывают канал и историю.

## 0.9.9 — 2026-10-22

- Доверенный gate: `pre-receive` запускает `verify.py` из main; gate-файлы
  менять нельзя.
- `PATH` с Go; `nologin`; журнал приёмки с ACL и logrotate.
- Проверка портов через pid; selftest для одного проекта; `run` в unit.
- ADR-0005; обновлены ISOLATION/LOGGING/SCHEME.
- Имена: `id`/`display`, `projects.example.json`, `check_projects`,
  `audit-drift.sh`; рабочий `projects.json` в `.gitignore`.

## 0.9.8 — 2026-10-22

- Многопроектная изоляция: один хост, несколько агентов, root — ограничитель.
- `docs/ISOLATION.md`, `docs/scheme-isolation.svg`, ADR-0004.
- `deploy/`: systemd unit, pre-receive, bootstrap, selftest.
- `verify.py` проверяет матрицу прав; тесты на неё.
- Агент пушит только в `review`; main двигает root.

## 0.9.7 — 2026-10-22

- Схемы переведены на SVG, генератор — Go stdlib `cmd/schemes`.
- Удалены Python-генераторы, Pillow, шрифты и `schemes.lock.json`.
- `verify.py` сравнивает SVG с docs через `go run ./cmd/schemes -check`.
- `--update-schemes` запускает Go-генератор; lock не нужен.

## 0.9.6 — 2026-10-22

- Закрытый долг удаляется из `docs/DEBT.md`, а не хранится в «Закрытом».
- `verify.py` → `check_debt`: секция закрытого долга — красный.
- Тесты на debt; правило 1 и процесс обновлены.

## 0.9.5 — 2026-10-22

- Лимиты: 100 КБ на страницу, 5 страниц на поток.
- `check_logs` проверяет размер и число страниц.
- Тесты на лимиты; `docs/LOGGING.md` описывает имена страниц.
- Правило 10 и схема обновлены.

## 0.9.4 — 2026-10-22

- Логи разделены: `tests/test.log`, `var/log/app.log`, `JOURNAL.md` — решения.
- `verify.py` проверяет разные пути и `.gitignore`.
- `docs/LOGGING.md`; тесты на `check_logs`.
- Правило 10 и схема правил обновлены.

## 0.9.3 — 2026-10-22

- `verify.py --close-task`: красный, если `cmd/**`/`deploy/**` изменены
  без `features/**`, `docs/adr/**`, `docs/DEBT.md` или `JOURNAL.md`.
- Добавлен `docs/DEBT.md`; CI запускает close-task.
- Тесты на close-task; `fetch-depth: 0` для diff.

## 0.9.2 — 2026-10-22

- PNG-схемы убраны из git: генерируются локально, `.gitignore`.
- `verify.py` пропускает проверку схем, если PNG нет.
- CI генерирует схемы и проверяет drift `docs/schemes.lock.json`.
- Ссылки на PNG заменены на команду генерации.
- Репозиторий public; branch protection включён: PR + два `verify`-чека.
- AGENTS: обязательная таблица «правило → как выполнено» до первой правки
  и отчёт по DoD с доказательствами перед «готово».

## 0.9.1 — 2026-10-22

- `.gitattributes`: LF для текста, binary для изображений/архивов.
- Исправлен Windows CI: CRLF ломал `schemes lock`, `gofmt` и `fmt`.
- `.gitattributes` добавлен в обязательные файлы.
- GitHub Actions: Ubuntu + Windows success; local pre-receive gate
  отклоняет красный push, удаление и force push.

## 0.9.0 — 2026-10-22

- Пилотная фича `deadcode -json`: машиночитаемый вывод, тест JSON.
- Карточка `features/0001-deadcode-json.md`; `docs/PILOT.md`.
- Пилот: 78 с до фичи, 109 с полный цикл, 0 ошибок, 0 откатов,
  1 drift поймал, 0 пропустил.
- `project.json.ci` — `["github"]` для пилота.
- Версия 0.9.0; схемы и lock обновлены после проверки drift.

## 0.8.0 — 2026-10-22

- `docs/DEPENDENCIES.md`: продукт / инструменты / инфраструктура.
- CI по умолчанию `["none"]`; Git и CI — опциональные контуры.
- Release: git-тег только если Git используется.

## 0.7.9 — 2026-10-22

- MIT LICENSE; файл добавлен в обязательные.
- Release checklist закрывает выбор лицензии.

## 0.7.8 — 2026-10-22

- Операционные процедуры: release, backup/restore, migrations, secrets.
- `.env.example`; `.env` в `.gitignore`.
- `project.json` требует процедуры; `verify.py` проверяет их наличие.

## 0.7.7 — 2026-10-22

- Azure DevOps: `azure-pipelines.yml`.
- `project.json.ci` — список контуров: github/gitlab/azure/none.
- `verify.py` проверяет выбранные CI-файлы.
- Branch protection: добавлен Azure DevOps.

## 0.7.6 — 2026-10-22

- `cmd/deadcode` проверяет unexported-методы: селекторы и имена интерфейсов
  считаются использованием; рефлексия — через `// deadcode:keep`.
- Тесты на методы и интерфейсы.

## 0.7.5 — 2026-10-22

- `project.json.ci`: `github`, `gitlab`, `both`, `none`.
- Добавлен `.gitlab-ci.yml`; `verify.py` проверяет выбранный CI-файл.
- README/PROCESS описывают оба контура.

## 0.7.4 — 2026-10-22

- `cmd/deadcode` расширен на unexported-типы, переменные и константы.
- Добавлены тесты на types/vars/consts.
- Методы по-прежнему не проверяются: возможны интерфейсы и рефлексия.

## 0.7.3 — 2026-10-22

- AST-детектор мёртвого Go-кода: `cmd/deadcode`, только stdlib.
- Ловит неиспользуемые unexported-функции; `// deadcode:keep` — исключение;
  generated-файлы пропускаются.
- `verify.py` запускает `deadcode` как команду стека.
- Root `go.mod` без зависимостей.

## 0.7.2 — 2026-10-22

- Мультистек: `verify.py` запускает `build/test/lint/fmt` из `project.json`
  для любого стека; Go-специфичные проверки пропускаются.
- `project.json#render`: изменения команд не требуют перерисовки схем.
- README: раздел про другой zero-dep стек.

## 0.7.1 — 2026-10-22

- Secret scan: `.env` и высокая энтропия строк.
- `docs/BRANCH_PROTECTION.md`: настройка GitHub/GitLab.
- CI-матрица: Ubuntu + Windows.
- `verify.py` и тесты обновлены.

## 0.7.0 — 2026-10-22

- `project.json`: конфиг проекта, команд, обязательных файлов и схем.
- `README.md`, `PROJECT.md`, `FEATURE.md`, `.gitignore`.
- `verify.py` читает конфиг; добавлены проверки профиля, фичи, README,
  версий, ADR-разделов и lock схем.
- `docs/scheme_config.py`: кроссплатформенные шрифты и версия из конфига.
- `docs/schemes.lock.json`: source/image hash для схем.
- `tests/test_verify.py`, `examples/minimal-go`.
- Правила 3/6/10: тесты по блокам, лимиты 400/80, типы, бэкап и миграции.

## 0.6.7 — 2026-10-22

- Практики из продуктового чек-листа: размеры, типы, тесты по блокам,
  бэкап с восстановлением, append-only миграции.

## 0.6.6 — 2026-10-22

- `PROCESS.md`, `verify.py`, CI-workflow, ADR и журнал.

## 0.6.2 — 2026-10-18

- Go stdlib, ноль зависимостей, отказ от npm/Node.js.
