# Логи

Версия 0.9.21 · 22.10.2026

Три разных журнала. Смешивать их нельзя: тестовый шум не должен попадать
в решения, а прод-ошибки — в тестовый лог.

| Поток | Куда | Кто пишет |
| --- | --- | --- |
| Тесты | `tests/test.log` | тестовый раннер/код тестов |
| Прод-ошибки | `var/log/app.log` | продукт в runtime |
| Решения | `JOURNAL.md` | человек/агент вручную |

## Правила

- `JOURNAL.md` — только решения: что, почему, последствия, ссылки.
  Код и тесты **не пишут** в него.
- `tests/test.log` — лог тестов; можно перезаписывать на каждом запуске.
- `var/log/app.log` — только runtime-ошибки и события прода; append-only.
- Оба лога в `.gitignore`; в репозиторий не коммитятся.
- Секреты и персональные данные в логи не попадают; ошибки редактируются.
- Каждый поток — не больше **100 КБ (102400 байт) на страницу**
  и не больше **5 страниц**.

## Страницы

Активная страница + архивы, всего не больше пяти:

```text
tests/test.log, test.log.1 ... test.log.4
var/log/app.log, app.log.1 ... app.log.4
JOURNAL.md, JOURNAL.1.md ... JOURNAL.4.md
```

При превышении 100 КБ активная страница уходит в `.1`, архивы сдвигаются,
самый старый (`*.5`) удаляется. Ротация — внешняя (logrotate/платформа),
не сторонняя библиотека.

## Проектные логи изоляции

`/var/log/git/<proj>.log` — журнал приёмки пушей (root:<proj>, 0660).
`host-baseline.sh` ставит **одно** правило `/etc/logrotate.d/proj-logs`
на `/var/log/git/*.log`: `size 100k`, `rotate 5`, `copytruncate`.
`bootstrap-project.sh` своё правило не ставит — иначе logrotate падает на
дубле.

## Go, stdlib

```go
// тест
f, _ := os.Create("tests/test.log")
logger := slog.New(slog.NewTextHandler(f, nil))

// прод
f, _ := os.OpenFile("var/log/app.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
logger := slog.New(slog.NewJSONHandler(f, nil))
```

`JOURNAL.md` не открывается кодом вообще: это Markdown-журнал решений.

## Проверка

`python verify.py` проверяет `project.json.logs`:

- три пути заданы и различаются;
- `docs/LOGGING.md` и `JOURNAL.md` существуют;
- `tests/test.log` и `var/log/app.log` покрыты `.gitignore`.

Нарушение — красный gate.
