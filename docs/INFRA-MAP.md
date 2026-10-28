# Карта инфраструктуры шаблона

| Слой | Что | Где |
| --- | --- | --- |
| Репозиторий | ветки, review/main | `docs/BRANCH_PROTECTION.md` |
| Хуки | приём в review | `deploy/git/pre-receive` |
| Онбординг проекта | bootstrap и init | `deploy/bootstrap-project.sh` |
| Доставка | deploy и site | `deploy/deploy-project.sh` |
| Юниты | сервис, бэкап, сторож | `deploy/systemd/proj@.service` |
| Данные | снимки и откат | `deploy/snapshot.sh` |
| Бэкап | снимок и проверка | `deploy/project-backup.sh` |
| Логи | тесты и прод | `var/log/app.log` |
| Почта | inbox/outbox/processed | `docs/BUS.md` |
| Личные данные | заглушки и замена | `docs/PERSONAL-DATA.md` |

## Проверка

`verify.py` → `infra-map`: каждый путь в обратных кавычках существует,
таблица непустая. Путь, которого нет, — красный: карта не должна врать.

Версия 0.9.52 · 28.10.2026
