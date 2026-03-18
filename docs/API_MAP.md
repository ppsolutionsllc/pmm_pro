# API_MAP

Ниже карта рабочих API PMM_ONLINE_2(MVP): endpoint → роль → эффект → статусы → идемпотентность.

## 1) Auth
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `POST /api/v1/token` | Public | Логин, выдача JWT | 200/400 | Да |
| `GET /api/v1/me` | ADMIN/OPERATOR/DEPT_USER | Профиль текущего пользователя | 200/401 | Да |

## 2) Requests workflow
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `POST /api/v1/requests` | DEPT_USER | Создать draft | 200/400/403 | Нет |
| `POST /api/v1/requests/admin` | ADMIN | Создать заявку от админа | 200/400 | Нет |
| `PUT /api/v1/requests/{id}` | DEPT_USER | Обновить draft | 200/400/403/404 | Нет |
| `DELETE /api/v1/requests/{id}` | ADMIN/DEPT_USER | Удалить draft | 200/400/403/404 | Да |
| `POST /api/v1/requests/{id}/items` | DEPT_USER | Добавить строку | 200/400/403 | Нет |
| `DELETE /api/v1/requests/{id}/items/{item_id}` | DEPT_USER | Удалить строку | 200/400/403/404 | Да |
| `POST /api/v1/requests/{id}/submit` | DEPT_USER | DRAFT→SUBMITTED | 200/409 | Условно |
| `POST /api/v1/requests/{id}/approve` | ADMIN | SUBMITTED→APPROVED | 200/400/409 | Условно |
| `POST /api/v1/requests/{id}/issue` | OPERATOR | APPROVED→ISSUED_BY_OPERATOR | 200/400/403/409 | Условно |
| `POST /api/v1/requests/{id}/confirm` | DEPT_USER | Складовое проведение + debt | 200/409/500 | **Да (Idempotency-Key/posting_session)** |
| `POST /api/v1/requests/{id}/reject` | ADMIN | Возврат в DRAFT + причина | 200/400/409 | Условно |
| `POST /api/v1/requests/{id}/reverse` | ADMIN | Коригування/реверс | 200/400/409 | Да (через session/key) |
| `POST /api/v1/requests/admin/month-end-confirm` | ADMIN | Ручное подтверждение просроченных | 200/400/409 | Да (через session/key) |
| `GET /api/v1/requests` | ADMIN/OPERATOR/DEPT_USER | Список заявок (RBAC) | 200/403 | Да |
| `GET /api/v1/requests/{id}` | ADMIN/OPERATOR/DEPT_USER | Детали заявки (RBAC) | 200/403/404 | Да |
| `GET /api/v1/requests/{id}/audit` | ADMIN/OPERATOR/DEPT_USER | Audit trail | 200/403/404 | Да |
| `GET /api/v1/requests/{id}/posting-sessions` | ADMIN/OPERATOR/DEPT_USER | История posting попыток | 200/403/404 | Да |
| `GET /api/v1/requests/{id}/snapshots` | ADMIN/OPERATOR/DEPT_USER | Snapshot по этапам | 200/403/404 | Да |
| `GET /api/v1/posting-sessions/{id}` | ADMIN/OPERATOR/DEPT_USER | Статус сессии | 200/403/404 | Да |

## 3) Stock
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `POST /api/v1/stock/receipts` | ADMIN | Приход топлива | 200/400 | Нет |
| `GET /api/v1/stock/receipts` | ADMIN | Список приходов | 200 | Да |
| `GET /api/v1/stock/balance` | ADMIN/OPERATOR | Остатки по топливу | 200 | Да |
| `GET /api/v1/stock/ledger` | ADMIN | Журнал движений | 200 | Да |
| `POST /api/v1/stock/adjustments` | ADMIN | Акт корректировки | 200/400/409 | Да (key/session) |
| `GET /api/v1/stock/adjustments` | ADMIN | Список корректировок | 200 | Да |
| `GET /api/v1/stock/adjustments/{id}` | ADMIN | Детали корректировки | 200/404 | Да |
| `GET /api/v1/stock/reconcile` | ADMIN | Текущее сравнение склада | 200 | Да |

## 4) Incidents
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `GET /api/v1/admin/incidents` | ADMIN | Список инцидентов, фильтры | 200 | Да |
| `GET /api/v1/admin/incidents/unresolved_count` | ADMIN | Счетчик нерешенных | 200 | Да |
| `GET /api/v1/admin/incidents/{id}` | ADMIN | Детали + связки request/session/job | 200/404 | Да |
| `PATCH /api/v1/admin/incidents/{id}` | ADMIN | NEW/IN_PROGRESS/RESOLVED | 200/400 | Условно |
| `POST /api/v1/admin/incidents/{id}/retry` | ADMIN | Повтор операции | 200/409/400 | Да (через session/job) |

## 5) Jobs / Exports / Reports
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `GET /api/v1/reports/vehicle-consumption` | ADMIN/DEPT_USER | Отчет ТЗ | 200/403 | Да |
| `POST /api/v1/jobs/reconcile` | ADMIN | Старт reconcile job | 200 | Нет |
| `POST /api/v1/jobs/exports/requests` | ADMIN/DEPT_USER | Экспорт заявок | 200 | Нет |
| `POST /api/v1/jobs/exports/debts` | ADMIN/DEPT_USER | Экспорт долгов | 200 | Нет |
| `POST /api/v1/jobs/exports/vehicle-report` | ADMIN/DEPT_USER | Экспорт отчета ТЗ | 200 | Нет |
| `GET /api/v1/jobs/{job_id}` | ADMIN/DEPT_USER | Статус job | 200/403/404 | Да |
| `GET /api/v1/jobs/{job_id}/download` | ADMIN/DEPT_USER | Скачать артефакт | 200/403/404 | Да |

## 6) Backups / Logs (admin tools)
| Endpoint | Роль | Эффект | Коды | Идемпотентность |
|---|---|---|---|---|
| `GET /api/v1/settings/logs` | ADMIN | Логи ошибок | 200 | Да |
| `POST /api/v1/settings/logs/clear` | ADMIN | Очистка буфера логов | 200 | Да |
| `GET /api/v1/settings/logs/export` | ADMIN | Экспорт логов | 200 | Да |
| `POST /api/v1/settings/backups/create` | ADMIN | `pg_dump` backup | 200/400 | Нет |
| `GET /api/v1/settings/backups` | ADMIN | Список dump | 200 | Да |
| `POST /api/v1/settings/backups/{file}/verify` | ADMIN | `pg_restore --list` | 200/400 | Да |
| `POST /api/v1/settings/backups/{file}/restore` | ADMIN | Восстановление из dump | 200/400 | Нет |
| `POST /api/v1/settings/backups/upload` | ADMIN | Загрузка dump | 200/400 | Нет |
| `POST /api/v1/settings/backups/upload-and-restore` | ADMIN | Загрузка + restore | 200/400 | Нет |
| `DELETE /api/v1/settings/backups/{file}` | ADMIN | Удаление dump | 200/400 | Да |
| `GET /api/v1/settings/backups/{file}/download` | ADMIN | Скачать dump | 200/404 | Да |

### Deprecated / legacy compatibility
| Endpoint | Статус | Примечание |
|---|---|---|
| `GET /api/v1/settings/backup` | Deprecated | Отключен по умолчанию (`404`), включается только через `ENABLE_LEGACY_JSON_RESTORE=true` |
| `POST /api/v1/settings/backup` | Deprecated | Отключен по умолчанию (`404`), потенциально destructive |
| `/api/v1/settings/incidents*` | Alias | Совместимость со старым UI, актуальный контур — `/api/v1/admin/incidents*` |

## 7) PDF templates / printing
| Endpoint | Роль | Эффект |
|---|---|---|
| `GET/POST /api/v1/admin/pdf-templates*` | ADMIN | Управление шаблонами |
| `PATCH /api/v1/admin/pdf-template-versions/{id}` | ADMIN | Редактирование формы |
| `POST /api/v1/admin/pdf-template-versions/{id}/preview` | ADMIN | Превью PDF |
| `POST /api/v1/requests/{id}/print/pdf` | ADMIN/OPERATOR/DEPT_USER | Генерация артефакта печати |
| `GET /api/v1/print-artifacts/{artifact_id}/download` | ADMIN/OPERATOR/DEPT_USER | Скачивание по RBAC |

## 8) Health
| Endpoint | Назначение |
|---|---|
| `/health` | Liveness (процесс жив) |
| `/ready` | Readiness (проверка БД `SELECT 1`) |
| `/healthz` | Liveness (процесс жив) |
| `/readyz` | Readiness (проверка БД `SELECT 1`) |

## 9) Справочники и настройки
| Endpoint | Роль | Эффект |
|---|---|---|
| `/api/v1/departments*` | ADMIN (+ чтение DEPT/OPERATOR) | Подразделения |
| `/api/v1/users*` | ADMIN | Пользователи/роли |
| `/api/v1/vehicles*` | ADMIN/DEPT_USER | Транспорт |
| `/api/v1/vehicle-change-requests*` | ADMIN/DEPT_USER | Заявки на изменения ТЗ |
| `/api/v1/routes*` | ADMIN/DEPT_USER | Маршруты |
| `/api/v1/route-change-requests*` | ADMIN/DEPT_USER | Заявки на изменения маршрутов |
| `/api/v1/settings/density*` | ADMIN | Густина/коэффициенты |
| `/api/v1/settings/planned-activities*` | ADMIN (+чтение DEPT/OPERATOR) | Справочник мероприятий |
| `/api/v1/settings/support*` | Public/Admin | Ссылка поддержки |
| `/api/v1/settings/pwa*` | ADMIN | PWA настройки/иконки |
| `/api/v1/settings/features*` | ADMIN | Feature flags |
| `/api/v1/system/updates*` | ADMIN | Проверка/запуск/статус обновлений |
