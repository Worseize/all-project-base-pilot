# 0004. Многопроектная изоляция и агент только с review

- **Статус:** Accepted
- **Дата:** 2026-10-22
- **Версия шаблона:** 0.9.8
- **Связанные:** docs/ISOLATION.md, PROCESS.md, deploy/

## Контекст

На одном хосте живут несколько проектов. Каждый ведёт внешний агент.
Агенту нельзя давать shell, sudo, чтение чужих каталогов и доступ к main.
Нужна модель, которую можно проверить, не добавляя Docker и пакеты.

## Решение

- Отдельный пользователь и `/srv/<proj>` на проект.
- SSH-ключ агента с forced command `git-receive-pack`, без pty/forwarding.
- Хуки в `/etc/git-hooks/<proj>` (root:root, 0755); агент не может их
  подменить.
- `pre-receive` принимает только `refs/heads/review`, запрещает delete и
  force push, запускает `verify.py`.
- `main` двигает только root через `git update-ref`; это акт одобрения.
- `proj@<proj>.service`: `User=%i`, `ProtectSystem=strict`,
  `ProtectHome=yes`, `ProtectProc=invisible`, `PrivateTmp=yes`,
  `NoNewPrivileges=yes`, лимиты CPU/RAM/Tasks.
- `deploy/selftest-isolation.sh` проверяет canary, sudo, порты, хуки и unit.

## Альтернативы

- Docker на проект: новая зависимость и слой эксплуатации.
- Дать агенту shell и sudo: теряется граница; отказ.
- Общий репозиторий на все проекты: агент видит чужой код; отказ.
- Хуки внутри `repo.git/hooks`: агент может заменить; отказ.

## Последствия

- **Плюс:** проверяемая граница без новых зависимостей.
- **Минус:** Linux/systemd/sshd; Windows-хост не подходит для live-проверки.
- **Проверка:** `verify.py`, `--close-task`, canary/selftest на Linux.
- **Риск:** root остаётся единственной точкой одобрения; его ошибка
  двигает main. Это осознанно.

## Реестр имён

`id` — полный токен (`proj-a`), из него выводятся пользователь, каталог,
юнит, лог и поддомен. Второй источник имени запрещён. В шаблоне лежит
только `projects.example.json` (`proj-a`, `proj-b`); рабочий
`projects.json` живёт на хосте и в `.gitignore`. Валидатор
`check_projects` проверяет схему, уникальность доменов/портов и отсутствие
лишних полей.

## Ссылки

- [docs/ISOLATION.md](../ISOLATION.md)
- [deploy/bootstrap-project.sh](../../deploy/bootstrap-project.sh)
- [deploy/git/pre-receive](../../deploy/git/pre-receive)
