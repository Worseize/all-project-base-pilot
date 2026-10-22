# all-project-base

Шаблон архитектуры крупного проекта: десять правил, процесс с red-gate,
схемы, ADR и журнал решений. Стек по умолчанию — Go, только стандартная
библиотека; у продукта нет сторонних зависимостей.

Лицензия — [MIT](LICENSE).

## Быстрый старт

1. Скопируйте папку/репозиторий под новый проект.
2. Заполните `project.json`: имя, версия, стек, команды, обязательные файлы.
3. Заполните `PROJECT.md`: назначение, границы, данные, окружения, исключения.
4. Скопируйте `FEATURE.md` в карточку конкретной фичи.
5. Проверьте шаблон:

```bash
python verify.py
```

6. Если меняли правила или схемы:

```bash
python verify.py --update-schemes
```

7. Включите branch protection и потребуйте проверку `verify`.

## Что внутри

| Файл | Зачем |
| --- | --- |
| `RULES.md` | десять правил и проверки |
| `PROJECT.md` | профиль конкретного проекта |
| `FEATURE.md` | шаблон карточки фичи |
| `PROCESS.md` | правила → тест → verify → деплой → журнал |
| `STRATEGY.md` | видение, слои, дорожная карта |
| `verify.py` | red gate: 0 — зелёный, иначе деплой запрещён |
| `JOURNAL.md` | короткие решения с «почему» |
| `docs/adr/` | значимые архитектурные решения |
| `docs/scheme-*.png` | схемы генерируются локально, в git не хранятся |

## Зависимости

Продукт — ноль сторонних зависимостей. Go toolchain, Python, Pillow, Git
и CI — отдельные контуры: инструменты и инфраструктура, не поставка.
Подробно: [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md). Git и CI не обязательны.

## Требования

- **Go** — для продукта; `verify.py` запускает `go vet`, `go test`, `go build`,
  `gofmt`, если есть `go.mod`.
- **Python 3.11+** — для `verify.py` и генераторов схем.
- **Pillow** — только для перерисовки схем, не для продукта:
  `python -m pip install pillow`.
- **Шрифт** — `docs/fonts/DejaVuSans.ttf` или системный Arial/DejaVu.
  Подробнее: [docs/fonts/README.md](docs/fonts/README.md).

PNG не коммитятся: `python verify.py --update-schemes` создаёт их локально,
они перечислены в `.gitignore`. Без PNG `verify.py` пропускает проверку
схем; CI генерирует их и проверяет drift lock.

## Другой стек

По умолчанию шаблон Go-центричен, но `project.json` поддерживает другой
zero-dep стек:

```json
{
  "stack": "python",
  "commands": {
    "test": "python -m unittest",
    "lint": "python -m compileall ."
  }
}
```

`verify.py` запустит эти команды, а Go-специфичные проверки (`go.mod`,
размеры Go-файлов, `gofmt`) пропустит. Правило 4 требует, чтобы у языка
тоже был ноль зависимостей; исключение фиксируется в ADR. Запрет npm
остаётся, пока `forbid_npm` не выключен явно.

## Операции

- [Release checklist](docs/RELEASE.md)
- [Backup и restore](docs/BACKUP.md)
- [Миграции](docs/MIGRATIONS.md)
- [Секреты](docs/SECRETS.md)
- [Branch protection](docs/BRANCH_PROTECTION.md)

## CI

`project.json.ci` — список контуров. По умолчанию `["none"]`; проект
включает нужные:

```json
"ci": ["github", "gitlab", "azure"]
```

- `github` — [.github/workflows/verify.yml](.github/workflows/verify.yml);
- `gitlab` — [.gitlab-ci.yml](.gitlab-ci.yml);
- `azure` — [azure-pipelines.yml](azure-pipelines.yml);
- `none` — CI отключён.

Один и тот же `verify.py` запускается во всех контурах, плюс тесты gate
и `examples/minimal-go`.

## Главные команды

```bash
python verify.py                 # red gate
python verify.py --update-schemes  # перерисовать схемы и обновить lock
python -m unittest discover -s tests
go run ./cmd/deadcode            # unexported func/type/var/const
go run ./cmd/deadcode -json      # то же в JSON для CI/отчётов
```

`cmd/deadcode` — консервативный AST-детектор: проверяет unexported-функции,
типы, переменные, константы и методы; методы — по селекторам и именам
интерфейсов. Generated-файлы пропускаются, `// deadcode:keep` — исключение.
Это не полный type-check: при рефлексии/`go:linkname` используйте keep.

## Правила и бюджет

Правил всегда десять. Новое правило должно вобрать старое или доказать,
что без него рвётся контур. Проектные особенности — в `PROJECT.md`,
а не в `RULES.md`.

## Релиз шаблона

- `python verify.py` — зелёный.
- `python -m unittest discover -s tests` — зелёный.
- `go run ./cmd/deadcode` — зелёный.
- `examples/minimal-go` проходит `go test`.
- Схемы перерисованы, `docs/schemes.lock.json` обновлён.
- Branch protection требует `verify`: [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md).

Версия шаблона — `project.json.version`.
