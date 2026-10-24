# nologin ломает push, а новый проект нельзя завести

Дефект 1. Пользователь создаётся с оболочкой `/usr/sbin/nologin`, чтобы у агента не было shell. После этого `git push` падает:

```
fatal: protocol error: bad line length character: This
```

Причина: sshd выполняет forced command через оболочку пользователя, а `nologin` печатает «This account is currently not available» и завершается — эти байты git читает как протокол. Ожидание: push работает, shell недоступен. Подходит `/usr/bin/git-shell`: он пропускает только git-команды.

Дефект 2. На свежем проекте хук отвечает `main branch is missing; root must initialize it`, но создать `main` нечем: отклонённый push не оставляет объектов (карантин удаляется), а `update-ref` требует существующий объект. Ожидание: онбординг создаёт `main` сам (например, `git fetch` из локального источника) или хук принимает первый push в `review` как создание `main`.

Версия шаблона: 0.9.10. Окружение: Ubuntu 24.04, git 2.43.

Версия: 0.9.11
Ссылка: findings#3
