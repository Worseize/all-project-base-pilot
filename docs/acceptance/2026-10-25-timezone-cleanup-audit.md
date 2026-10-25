# Пояс проекта UTC по умолчанию, уборка таймеров, аудит обновлений

**1. Пояс проекта по умолчанию — UTC.** `manifest.py` подставлял `UTC`, `deploy-project.sh` писал `Environment=TZ=UTC`. Проект без `project.conf` получал чужой пояс. Исправлено: `timezone` по умолчанию пустой; `TZ` не пишется, проект наследует пояс хоста; если задан — проверяется `zoneinfo`.

**2. Уборка приёмки.** `isolation-cleanup.sh` теперь делает `systemctl disable --now proj-backup@<id>.timer`, удаляет симлинк, `/var/backups/<id>`, deploy sha и делает `daemon-reload`.

**3. Аудит.** `audit-drift.sh` проверяет:
- `TZ` работающих `proj@*.service` пустой или равен поясу хоста;
- `apt-daily.timer`, `apt-daily-upgrade.timer`, `unattended-upgrades` включены;
- каждый `proj-backup@<id>.timer` имеет `/srv/<id>/repo.git`.

Критерий: проект без `project.conf` работает в поясе хоста; после приёмки нет backup-таймеров и `/var/backups/proj-*`; аудит краснеет на выключенных обновлениях и чужом `TZ`.

Версия: 0.9.36
Ссылка: findings#27
