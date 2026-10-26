# 0006. Watchdog: root с hardening

- **Статус:** Accepted
- **Дата:** 2026-10-26
- **Версия шаблона:** 0.9.38
- **Связанные:** deploy/systemd/watchdog-health.service, deploy/health-check.sh

## Контекст

`health-check.sh` запускает `runuser -u <project>` для каждого проекта.
Пользователь `app` без root/sudo этого не может. Packet #12 предлагал
`User=app`, но это требует sudoers-файла на `runuser`, который расширяет
поверхность и требует отдельного сопровождения.

## Решение

`watchdog-health.service` работает от root с:

- `ProtectSystem=strict`
- `ReadWritePaths=/var/lib/watchdog`
- `PrivateTmp=yes`
- `NoNewPrivileges=yes`
- `EnvironmentFile=-/etc/app/watchdog.env` для `TELEGRAM_TOKEN_FILE` и
  `TELEGRAM_CHAT_ID`

## Альтернативы

`User=app` + sudoers на `runuser -u proj-*` — отклонена: файл привилегий
надо поддерживать, он расширяет поверхность и не даёт выигрыша для
oneshot-проверки.

## Последствия

Непривилегированный запуск — отдельная задача с sudoers-файлом и тестом,
а не правка на ходу.

## Ссылки

- [deploy/systemd/watchdog-health.service](../../deploy/systemd/watchdog-health.service)
- [deploy/health-check.sh](../../deploy/health-check.sh)
