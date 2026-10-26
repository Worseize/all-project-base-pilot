# blocked: фикстура manifest на Ubuntu CI

**Что проверял:** `isolation` на ветке `fix/manifest-gate` (0.9.45) — сценарии
манифеста на отдельном проекте `proj-m` из скелета.

**Точный текст ошибки (второй прогон, `3b34546`):**

```text
remote:   File "run", line 2
remote:     exit 0
remote:          ^
remote: SyntaxError: invalid syntax
remote: review rejected: test.sh failed for df179b99e41e783910db7ceef0ea649880be7fb3
FAIL: restore default run
FAIL: build=false push
FAIL: build did not run
FAIL: manifest scenarios
ISOLATION CI: RED
```

**Две попытки:**

1. `28a83cc`: фикстура работала в своём клоне, а `deploy-project.sh` — в
   каталоге доставки; проверка `built.txt` смотрела не туда.
   Результат: `FAIL: build did not run`.
2. `3b34546`: каталог доставки выбран верно; заглушка `run` написана как
   `bash`, а `test.sh` из `main` компилирует `run` как Python.
   Результат: push `restore default run` отклонён гейтом, дальше каскад.

**Причина установлена:** фикстура сама ломает контракт скелета: `run` —
Python-файл, `write_entry` пишет `#!/usr/bin/env bash`.

**Готовая правка (не прогнана — правило двух падений):**

- восстанавливать `run` из `BASE_MAIN:run`, а не заглушкой;
- сценарий `run=app` проверяет только приём push, без deploy: юнит узла
  по-прежнему запускает `current/run` (отдельный долг, не этот).

**Чего не хватает:** разрешения на третий прогон `isolation` — проверка
уже падала дважды, по правилу остановки третий запуск не делаю.

**Решение:** чинить фикстуру тем же дифом в следующем ходе; проверку
`100755` и `test=...` из `project.conf` не ослаблять.

Версия: 0.9.45
Ссылка: findings#37
