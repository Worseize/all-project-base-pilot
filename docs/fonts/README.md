# Шрифты для схем

Генераторы ищут шрифт в таком порядке:

1. `docs/fonts/DejaVuSans.ttf` и `docs/fonts/DejaVuSans-Bold.ttf` — рекомендуется:
   положите файлы сюда, и схемы будут одинаковыми на Windows, Linux и macOS.
2. Системный Arial на Windows.
3. DejaVu Sans / Liberation Sans на Linux.
4. Arial на macOS.

Если ни один шрифт не найден, генератор завершится с понятной ошибкой,
а не нарисует схему дефолтным мелким шрифтом.

## Установка

- **Windows:** Arial уже есть; для переносимости скопируйте DejaVu в `docs/fonts/`.
- **Ubuntu/Debian:** `sudo apt-get install fonts-dejavu-core`.
- **macOS:** Arial обычно есть; можно положить DejaVu в `docs/fonts/`.

DejaVu Sans распространяется по свободной лицензии; Arial — нет, поэтому
в репозиторий его не кладём.
