# Конструктор PDF шаблону заявки ПММ

## Що реалізовано

- Версіоновані HTML→PDF шаблони для бланка заявки.
- Редактор колонок таблиці (додати/видалити/переставити/дублювати/показувати).
- Службовий блок (перемикачі службових полів).
- Preview PDF по вибраній заявці.
- Публікація версій (тільки `PUBLISHED` використовується для друку).
- Snapshot друку в заявці (`request_print_snapshots`) для незмінності історичних друків.
- Збереження PDF-артефактів (`print_artifacts`) і повторне використання кешу.

## Де в UI

- `Адмін → PDF шаблони` (`/admin/settings/pdf-templates`) — список шаблонів.
- `Адмін → PDF шаблони → Відкрити` (`/admin/settings/pdf-templates/:id`) — редактор версії.

## Типовий потік

1. Відкрити `PDF шаблони`.
2. Створити шаблон або відкрити існуючий.
3. Створити нову версію (`Нова версія`).
4. Налаштувати колонки таблиці:
   - назва,
   - джерело даних,
   - ширина,
   - вирівнювання,
   - формат,
   - видимість.
5. Увімкнути/вимкнути службові поля.
6. Вибрати заявку для превʼю і натиснути `Оновити превʼю`.
7. Зберегти версію.
8. Опублікувати версію (`Опублікувати`).

## Друк заявки

- З картки заявки кнопка `Друк` викликає:
  - `POST /api/v1/requests/{id}/print/pdf` (створення/отримання артефакту),
  - `GET /api/v1/print-artifacts/{artifact_id}/download` (завантаження PDF).
- Якщо артефакт для `request_id + template_version_id` вже існує і `force_regenerate=false`, повертається кешований файл.

## Snapshot друку

Під час першого друку по конкретній опублікованій версії шаблону:

- створюється `request_print_snapshot` з:
  - структурою шаблону (layout/columns/mapping/rules/service),
  - зібраним контекстом заявки (шапка/рядки/підсумки/службові дані).

Це гарантує, що зміни шаблону в майбутньому не змінять вже зафіксовані друки для старих заявок.

## API (ADMIN)

- `GET /api/v1/admin/pdf-templates`
- `POST /api/v1/admin/pdf-templates`
- `GET /api/v1/admin/pdf-templates/{id}`
- `POST /api/v1/admin/pdf-templates/{id}/versions`
- `PATCH /api/v1/admin/pdf-template-versions/{version_id}`
- `POST /api/v1/admin/pdf-template-versions/{version_id}/publish`
- `POST /api/v1/admin/pdf-template-versions/{version_id}/preview`

## API (друк)

- `POST /api/v1/requests/{id}/print/pdf`
- `GET /api/v1/print-artifacts/{artifact_id}/download`
- Legacy-сумісність: `GET /api/v1/requests/{id}/print`

## Джерела даних колонок

Дозволені тільки поля з allowlist (без довільних виразів), зокрема:

- `request.*`
- `department.*`
- `item.*`
- `computed.*`
- `issue.*`
- `system.*`

## Правила видимості

- `ALWAYS`
- `IF_STATUS_IN([...])`
- `IF_DEBT_GT_0`
- `IF_ROLE_IS_ADMIN`
