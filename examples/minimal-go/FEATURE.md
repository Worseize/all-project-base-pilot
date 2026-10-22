# FEATURE: minimal-go

## Цель

Показать, что микроблок проходит тест и red gate.

## Схема плана

Один пакет `microblock`, без зависимостей.

## Контракт

`NewUser(name string) User`, `User.DisplayName() string`.

## Тесты

`TestNewUser` проверяет поведение.

## Откат

Удалить пакет; данных нет.

## Готовность

- [ ] `go test ./...` зелёный.
- [ ] `python verify.py` зелёный.
