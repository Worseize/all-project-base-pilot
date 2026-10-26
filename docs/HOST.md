# Админ-узел

Версия 0.9.46 · 25.10.2026

Этот шаблон разворачивает **админ-узел**, а не продукт. Админ держит
гейт, принимает правки агентов, следит за firewall, журналами и бэкапом.
Продукты живут отдельными проектами.

## Что делает админ

- запускает `python verify.py` и `--close-task`;
- принимает `review` в `main` и закрывает findings-issue;
- разворачивает изоляцию через `deploy/bootstrap-project.sh`;
- держит `ufw`, `fail2ban`, `journald`, `logrotate` и timezone;
- проверяет узел через `deploy/audit-drift.sh`.

## Чего не делает

- не пишет продуктовый код и не держит `cmd/app`, `app.service`, `bin/app`;
- не запускает продуктовый сервис и не хранит данные продукта;
- не даёт агенту shell, sudo, `main` или чужие проекты;
- не ослабляет `verify.py`, хуки и проверки изоляции.

## Baseline

```bash
sudo deploy/host-baseline.sh
sudo deploy/install-auto-merge.sh
sudo deploy/audit-drift.sh projects.json
```

`host-baseline.sh` идемпотентно настраивает:

- `ufw`: deny incoming, allow outgoing, `limit` на SSH, 80/443;
- `fail2ban`: jail `sshd`, file backend `/var/log/auth.log`;
- sysctl: rp_filter, syncookies, redirects, dmesg/kptr;
- journald: `SystemMaxUse=200M`, `RuntimeMaxUse=50M`, retention 1 month;
- logrotate: `/var/log/git/*.log`, 100 КБ × 5, copytruncate;
- timezone (`TIMEZONE`, по умолчанию UTC);
- `git`, `curl` — базовые; `caddy` — если у проектов есть сайт;
- `python3-venv` — если проекты используют `python3 -m venv` в `deps`;
- снимки данных — `/var/backups/<id>`, tar+sha256, 7 дней;
  секреты в снимок не входят;
- `proj-backup@<id>.timer` — ежедневно, KEEP 14, `Persistent=true`,
  случайная задержка; онбординг включает таймер и проверяет restore;
- `deploy/check-backups.sh 26` — свежесть/читаемость; вызывается из
  `selftest` и онбординга, старый снимок — красный.

`install-auto-merge.sh` ставит timer: review → main только по зелёной
метке гейта, затем deploy и restart; при сбое main откатывается.
`install-watchdog.sh` ставит `watchdog-health.timer`: health каждого
проекта раз в минуту, алерты с подавлением, восстановление.

## Проверка здоровья

`audit-drift.sh` краснеет, если:

- ufw не active или нет SSH-limit;
- fail2ban jail не активен;
- нет sysctl/journald/logrotate-файлов;
- timezone не совпадает;
- реестр и `/srv` расходятся в любую сторону.

## Границы

- Linux + systemd; Windows для live-проверки не подходит.
- Пакеты `ufw`/`fail2ban` должны быть установлены; baseline их не ставит.
- Caddy — единственный вход; продуктовые порты наружу не публикуются.
- Rule #11 не добавляется: политика в `PROJECT.md`, `ISOLATION.md`,
  `HOST.md` и `PROCESS.md`.
