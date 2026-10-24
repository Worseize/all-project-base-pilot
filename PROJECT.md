# PROJECT: all-project-base

Профиль **админ-узла**, а не приложения. Шаблон даёт правила, гейт, приёмку
и изоляцию; продукты живут отдельными проектами.

## Назначение

Админ-узел держит `verify.py`, принимает правки агентов, ведёт журнал и
обеспечивает изоляцию проектов. Своего продукта, сервиса и порта у узла
нет: продукт — отдельный проект со своим агентом и деплоем.

## Стек

- bash + systemd — эксплуатация узла.
- Python 3.11+ — только `verify.py`.
- Go stdlib — инструменты `cmd/schemes` и `cmd/deadcode`; не продукт.
- SVG-схемы — Go stdlib; без Pillow/шрифтов.
- npm, Node.js, `node_modules` не используются.

## Команды

```bash
python verify.py
python verify.py --close-task
python -m unittest discover -s tests
go run ./cmd/schemes -write
go run ./cmd/deadcode
sudo deploy/host-baseline.sh
sudo deploy/audit-drift.sh
sudo deploy/bootstrap-project.sh proj-a
sudo deploy/deploy-project.sh proj-a
```

## Границы

- Админ держит гейт, review/main, firewall, журналы и бэкап.
- Админ не пишет продукт, не запускает продуктовый сервис и не держит
  продуктовые данные.
- Агент проекта правит только свой проект и пушит только в `review`.
- Продукт приходит отдельным проектом; шаблон не возвращает `cmd/app`,
  `app.service` или `bin/app`.

## Данные

- Состояние гейта, `projects.json`, журналы приёмки и `JOURNAL.md`.
- Продуктовых данных, БД и пользовательских записей здесь нет.
- Секреты — вне репозитория; ключи и env не попадают в git.
- Бэкап узла — конфиги, реестр и журналы; восстановление проверяется.

## Окружения

- `local` — рабочая машина администратора.
- `ci` — GitHub Actions: `verify` и `isolation`.
- `prod` — Linux-узел с systemd, ufw, fail2ban и Caddy.

## Исключения

- SVG-схемы — Go stdlib, build-time; без Pillow и внешних шрифтов.
- `cmd/schemes` и `cmd/deadcode` — инструменты, а не продукт.
- Другой стек продукта — только в отдельном проекте и с ADR.

## Изоляция

- Один хост — несколько проектов; у каждого свой пользователь и `/srv/<id>`.
- Агент пушит только в `review`; `main` двигает root через `update-ref`.
- Матрица прав — [docs/ISOLATION.md](docs/ISOLATION.md).

## Локальные правила

Проектные правила и проверки добавляются в `project.json`, но не
увеличивают десять инвариантов из `RULES.md`.
