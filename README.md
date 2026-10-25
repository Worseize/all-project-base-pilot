# all-project-base

Шаблон **админ-узла и приёмки**, а не приложения. Он держит гейт,
принимает правки агентов и изолирует проекты. Продукты живут отдельными
проектами и не входят в этот репозиторий.

Лицензия — [MIT](LICENSE).

## Быстрый старт: разверни админ-узел

1. Скопируйте репозиторий на Linux-хост с systemd.
2. Проверьте сам шаблон:

```bash
python verify.py
```

3. Разверните базовую обвязку узла:

```bash
sudo deploy/host-baseline.sh
sudo deploy/install-auto-merge.sh
sudo deploy/install-watchdog.sh
```

4. Создайте рабочий реестр вне git и первого проекта из скелета:

```bash
cp projects.example.json projects.json
sudo deploy/init-project.sh proj-a
```

Скелет — `skeleton/project`: `run`, `PROJECT.md`, `test.sh`,
`.gitignore`, `README.md`. Контракт агента —
[docs/AGENT-CONTRACT.md](docs/AGENT-CONTRACT.md).

5. Проверьте узел и изоляцию:

```bash
sudo deploy/audit-drift.sh projects.json
sudo REGISTRY=projects.json deploy/selftest-isolation.sh proj-a
```

`review` мержит `main` автоматически по метке гейта (`proj-auto-merge.timer`),
затем доставляет код в runtime. Пути проекта ограничены allowlist:

```bash
sudo deploy/allow-path.sh proj-a docs/
```

6. Закройте задачу по процессу:

```bash
python verify.py --close-task
```

## Продукт — отдельным проектом

Шаблон не содержит `cmd/app`, `app.service`, `bin/app` и продуктовых
данных. Продукт создаётся отдельным проектом:

- свой `id`, пользователь и `/srv/<id>`;
- свой агент, который пушит только в `review`;
- свой деплой и свой сервис;
- админ узла принимает правки и закрывает issue.

`verify.py` → `check_no_product` краснеет, если продукт пытаются вернуть
в шаблон.

## Что внутри

| Файл | Зачем |
| --- | --- |
| `RULES.md` | десять правил и проверки |
| `PROJECT.md` | профиль админ-узла |
| `PROCESS.md` | команда → правка → приёмка → conductor |
| `STRATEGY.md` | стратегия и очередь улучшений |
| `verify.py` | red gate админ-узла |
| `docs/ISOLATION.md` | роли, права, изоляция |
| `docs/HOST.md` | здоровье узла |
| `docs/acceptance/` | публичная история команд |
| `docs/scheme-*.svg` | схемы в git, генерируются Go |
| `deploy/` | baseline, bootstrap, hooks, CI |

## Требования

- Linux с systemd, `ufw`, `fail2ban`, `git`.
- Python 3.11+ — только `verify.py`.
- Go — инструменты `cmd/schemes` и `cmd/deadcode`.
- Git и CI — отдельные контуры; сторонних зависимостей нет.

## Роли

- **Админ узла** — гейт, firewall, журналы, бэкап, merge в `main`.
- **Агент проекта** — только свой проект и `review`.
- **Продукт** — отдельный проект; в этом репозитории его нет.

Подробно: [docs/ISOLATION.md](docs/ISOLATION.md),
[docs/HOST.md](docs/HOST.md), [docs/acceptance/README.md](docs/acceptance/README.md).

## CI

- `verify` — red gate шаблона.
- `isolation` — bootstrap двух проектов и полная приёмка изоляции.

CI не деплоит продукт: у админ-узла продукта нет.
