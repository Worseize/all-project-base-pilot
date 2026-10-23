# Architecture Decision Records

ADR фиксирует значимое решение: контекст, выбор, альтернативы и последствия.
Одно решение — один файл. Мелкие решения — в [JOURNAL.md](../../JOURNAL.md).

## Индекс

| # | Решение | Статус |
| --- | --- | --- |
| 0001 | [Go stdlib, ноль зависимостей](0001-zero-dependencies-go.md) | Accepted |
| 0002 | [Red gate и журнал решений](0002-red-gate.md) | Accepted |
| 0003 | [SVG-схемы на Go](0003-svg-go-schemes.md) | Accepted |
| 0004 | [Многопроектная изоляция](0004-multi-agent-isolation.md) | Accepted |
| 0005 | [Изоляция: доверенный gate](0005-isolation-hardening.md) | Accepted |

## Когда писать ADR

- выбор стека или архитектурного слоя;
- смена контракта, которую нельзя откатить молча;
- отказ от зависимости, библиотеки или сервиса;
- решение, которое через месяц будут переспрашивать.

## Формат

Новый файл: `NNNN-короткое-имя.md`, начиная с `0003`.
Шаблон: [0000-template.md](0000-template.md).

Статусы: `Proposed`, `Accepted`, `Superseded`, `Rejected`.
