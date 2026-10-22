# Branch protection

Файл не включает защиту ветки. Это настройка репозитория, а не код.
Пока она не включена, красный `verify` можно смержить.

## GitHub

Settings → Branches → Add branch protection rule:

- Branch name pattern: `main`.
- **Require a pull request before merging.**
- **Require status checks to pass before merging.**
  - Добавить проверку `verify`.
  - Включить **Require branches to be up to date**.
- **Do not allow force pushes.**
- **Do not allow deletions.**
- **Include administrators** — иначе правило можно обойти.
- Опционально: **Require linear history**.

## GitLab

Settings → Repository → Protected branches:

- `main` защищена.
- Merge разрешён только через merge request.
- Pipeline must succeed.
- Force push и удаление ветки запрещены.

## Azure DevOps

Repos → Branches → `main` → Branch policies:

- **Require a minimum number of reviewers.**
- **Build validation:** выбрать pipeline из `azure-pipelines.yml`.
- **Check for linked work items** — по желанию.
- Запретить direct push и force push.
- Включить политику для администраторов, если доступно.

## Проверка

1. Создайте PR с намеренно красным `verify`.
2. Убедитесь, что кнопка merge недоступна.
3. Попробуйте force-push в `main` — должен быть отклонён.

## Почему это не в `verify.py`

`verify.py` проверяет содержимое репозитория. Он не может изменить настройки
GitHub/GitLab без токена и прав администратора. Поэтому gate и branch
protection — два разных контура: первый даёт красный/зелёный, второй
не пускает красный в основную ветку.
