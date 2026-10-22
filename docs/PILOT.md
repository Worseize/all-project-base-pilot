# PILOT: deadcode -json

Версия 0.9.2 · 22.10.2026

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

GitHub Free для private-репозитория вернул `403`:

> Upgrade to GitHub Pro or make this repository public to enable this feature.

Это касается и branch protection, и rulesets. Поэтому:

- **remote branch protection не включён** — нужен public-репозиторий или GitHub Pro;
- локально проверен эквивалент: bare-репозиторий + `pre-receive` + `denyDeletes`/`denyNonFastForwards`.

| Сценарий | Результат |
| --- | --- |
| Зелёный push в `main` | принят, 3.20 с |
| Красный push в `main` | отклонён, 1.96 с |
| Удаление `main` | отклонено |
| Force push в `main` | отклонён |

## Наблюдения

- Фича маленькая: `-json` + один тест; 78 секунд — не показатель для
  крупной продуктовой фичи.
- Drift-проверка сработала ровно один раз и с понятным сообщением;
  после `--update-schemes` gate позеленел.
- CI `github` реально запущен: оба job’а зелёные после LF-фикса.
- Remote branch protection заблокирован тарифом GitHub Free; локальный
  серверный gate доказал, что красный push, удаление и force push
  действительно отсекаются.
- Деплой для шаблона — сборка `bin/deadcode.exe`; продуктового сервиса
  и реального стенда нет.
- Итог: процесс и gate проходят; для remote protection нужно решение
  по видимости репозитория или GitHub Pro.

