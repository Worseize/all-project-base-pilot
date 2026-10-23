# 0005. Изоляция: доверенный gate и журнал приёмки

- **Статус:** Accepted
- **Дата:** 2026-10-22
- **Версия шаблона:** 0.9.9
- **Связанные:** docs/ISOLATION.md, deploy/git/pre-receive

## Контекст

Живая приёмка 0.9.8 показала: агент мог ослабить `verify.py` в своём пуше,
`PATH` без Go давал skip, проверка портов не работала, у пользователя был
shell, журнал приёмки отсутствовал.

## Решение

- `pre-receive` запускает `verify.py` из `refs/heads/main`, а не из pushed
  tree; изменения `verify.py`, `project.json`, `tests/`, `cmd/schemes`,
  `cmd/deadcode` отклоняются.
- Хук выставляет `PATH` с `/usr/local/go/bin`.
- Пользователь — `nologin`; ключ всё равно с forced command.
- `/var/log/git/<proj>.log` root:<proj> 0640 + ACL; logrotate 100k × 5.
- `selftest-isolation.sh` работает с одним или двумя проектами.
- `ExecStart=/srv/%i/run`; `systemd-analyze verify` — только на живом юните.
- `/srv` 0711 — предупреждение в `docs/ISOLATION.md`.

## Альтернативы

- Доверять pushed `verify.py`: обход gate (отказ).
- Запретить весь `cmd/**`: блокирует продуктовый код.
- Хранить журнал в `/srv`: агент может подменить; отказ.

## Последствия

- Push с подменой gate — RED; неотформатированный Go — RED.
- Пользователь без shell; логи ротируются.
- Live-приёмка требует Linux; Windows проверяет только синтаксис.

## Ссылки

- [docs/ISOLATION.md](../ISOLATION.md)
- [deploy/git/pre-receive](../../deploy/git/pre-receive)
- [deploy/selftest-isolation.sh](../../deploy/selftest-isolation.sh)
