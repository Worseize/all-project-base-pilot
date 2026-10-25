# Release

Версия 0.9.22 · 22.10.2026

Релиз — это не «код готов», а набор доказательств. Чек-лист ниже фиксирует
их до тега.

## Перед релизом

- [ ] `project.json.version` и `date` обновлены.
- [ ] Версии в `RULES.md`, `STRATEGY.md`, `PROCESS.md`, `docs/adr/0000-template.md` совпадают.
- [ ] В `CHANGELOG.md` есть запись версии.
- [ ] В `JOURNAL.md` есть решение с «почему».
- [ ] `python verify.py` — зелёный.
- [ ] `python verify.py --close-task` — зелёный.
- [ ] `python -m unittest discover -s tests` — зелёный.
- [ ] `go test ./...` — зелёный.
- [ ] `go run ./cmd/deadcode` — без находок.
- [ ] `python verify.py --update-schemes` выполнен; SVG обновлены.
- [ ] Выбранные CI-контуры зелёные, либо `ci: ["none"]` осознанно.
- [ ] Branch protection требует `verify` (если платформа используется).
- [ ] Лицензия выбрана: [LICENSE](../LICENSE) (MIT).

## Как поднять версию

1. Обновить `version` и `date` в `project.json` — это источник для схем и gate.
2. Обновить версии в `RULES.md`, `STRATEGY.md`, `PROCESS.md`, `docs/adr/0000-template.md`.
3. Добавить запись в `CHANGELOG.md` и `JOURNAL.md`.
4. Выполнить `python verify.py --update-schemes`.
5. Прогнать `verify.py`, тесты gate, Go-тесты и пример.
6. Закоммитить всё вместе — код, документы, схемы, lock.

## Тег

Если используете Git:

```bash
git tag -a vX.Y.Z -m "X.Y.Z"
git push origin main --tags
```

Без Git — зафиксируйте версию в артефакте/снапшоте вашей VCS.

## Если релиз плохой

- Откатить тег и деплой по плану отката из `FEATURE.md`.
- Не переписывать историю; выпустить patch-версию.
- Записать инцидент в `JOURNAL.md`: что сломалось, почему, что меняем.

## Что не автоматизировано

- Branch protection — настройка платформы.
- Лицензия — юридическое решение.
- Внешние бэкапы — проверяются процедурой, а не `verify.py`.
