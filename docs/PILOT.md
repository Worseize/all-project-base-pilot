# PILOT: deadcode -json

Версия 0.9.39 · 22.10.2026

## Задача

Провести одну реальную фичу через правила → тест → verify → деплой → журнал.

- Фича: [features/0001-deadcode-json.md](../features/0001-deadcode-json.md).
- Старт: 2026-10-22 17:39:14 +03:00.
- CI: `github` (workflow готов).
- Branch protection: не включён — нужен удалённый репозиторий и права
  администратора. Локальный gate — `python verify.py`.

## Метрики

| Метрика | Значение |
| --- | --- |
| Время до готовой фичи | 78 секунд (17:39:14 → 17:40:32) |
| Полный пилот | 109 секунд (до финального gate, 17:41:03) |
| Ошибки/падения | 1 — Windows CRLF; исправлено `.gitattributes` |
| Откаты | 0 |
| Drift: обнаружено | 1 (lock 0.8.0 ≠ шаблон 0.9.0) |
| Drift: пропущено | 0 |
| Время `verify.py` | 1.30 с — красный drift; 0.83 с — зелёный |
| Remote CI | Ubuntu + Windows — success (run 39821365979) |
| Локальный зелёный gate | 3.20 с, push принят |
| Локальный красный gate | 1.96 с, push отклонён |

## GitHub Actions

Первый run `39802188954`: Ubuntu — success, Windows — failure.
Причина: Git checkout сделал CRLF, сломались `schemes lock` и `gofmt`.
Исправлено `.gitattributes` (`eol=lf`), версия 0.9.1.
Повторный run `39821365979`: **Ubuntu и Windows — success**.

## Branch protection

Репозиторий переведён в public, после чего protection включился:

- обязательный PR;
- обязательные checks: `verify (ubuntu-latest)`, `verify (windows-latest)`;
- force push и удаление `main` запрещены;
- администраторы не обходят.

Прямой push в `main` отклонён:

```text
GH006: Protected branch update failed
- Changes must be made through a pull request.
- 2 of 2 required status checks are expected.
```

Локально также проверен эквивалент: bare-репозиторий + `pre-receive` +
`denyDeletes`/`denyNonFastForwards`.

| Сценарий | Результат |
| --- | --- |
| Зелёный push в `main` (local) | принят, 3.20 с |
| Красный push в `main` (local) | отклонён, 1.96 с |
| Удаление `main` (local) | отклонено |
| Force push в `main` (local) | отклонён |
| Прямой push в GitHub `main` | отклонён GH006 |

## Наблюдения

- Фича маленькая: `-json` + один тест; 78 секунд — не показатель для
  крупной продуктовой фичи.
- Drift-проверка сработала ровно один раз и с понятным сообщением;
  после `--update-schemes` gate позеленел.
- CI `github` реально запущен: оба job’а зелёные после LF-фикса.
- Remote branch protection включён после перевода репозитория в public;
  прямой push отклоняется, локальный серверный gate тоже проверен.
- Деплой для шаблона — сборка `bin/deadcode.exe`; публичного сервиса
  и реального стенда нет.
- Итог: процесс и gate проходят; остался реальный продуктовый сервис.

