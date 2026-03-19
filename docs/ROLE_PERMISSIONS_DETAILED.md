# PMM Online: Детальна Матриця Прав Доступу

_Згенеровано: 2026-03-19 00:22:15_

## 1. Ролі системи

- `ADMIN`: повний контроль системи, довідників, складу, користувачів, звітів, оновлень, backup/restore, шаблонів друку.
- `OPERATOR`: операційна роль видачі ПММ, перегляд погоджених заявок, проведення етапу видачі.
- `DEPT_USER`: роль підрозділу, створення/редагування своїх заявок (до подання), підтвердження отримання, робота зі своїм ТЗ/маршрутами.

## 2. Що хто бачить у UI

### ADMIN
- Дашборд, Заявки, Склад (прихід/баланс/журнал/коригування/перевірка), Інциденти.
- Звіти: `Звіт ТЗ`, `Звіт по підрозділах`.
- Довідники: підрозділи, транспорт, маршрути, густина, оператори, налаштування заявок.
- Система, PDF шаблони, Підтримка, Профіль.

### OPERATOR
- `Готово до видачі`, `Видано`, Профіль, Підтримка.
- У заявках оператор працює тільки зі статусами, допустимими для видачі.

### DEPT_USER
- `Мої заявки`, `Створити заявку`, `Транспорт`, `Маршрути`, Профіль, Підтримка.
- Доступ обмежений тільки власним підрозділом.

## 3. Бізнес-обмеження (критичні)

- Підрозділ не може працювати із заявками іншого підрозділу.
- OPERATOR не має адмінських доступів; видача робиться лише в допустимому життєвому циклі заявки.
- Підтвердження підрозділом формує акт видачі (`issue_doc_no`) і проводить рух по складу.
- Експортні jobs для `DEPT_USER` обмежені лише власними jobs.
- Більшість системних/конфігураційних endpoint-ів доступні тільки `ADMIN`.

## 4. Повна API-матриця доступу

| Module | Method | Path | Access | Function | Додаткові перевірки |
|---|---|---|---|---|---|
| `auth` | `GET` | `/api/v1/me` | `AUTHENTICATED` | `get_me` | — |
| `auth` | `POST` | `/api/v1/token` | `PUBLIC` | `login_for_access_token` | — |
| `departments` | `GET` | `/api/v1/departments` | `ADMIN, DEPT_USER, OPERATOR` | `list_departments` | — |
| `departments` | `POST` | `/api/v1/departments` | `ADMIN` | `create_department` | — |
| `departments` | `GET` | `/api/v1/departments/me/print-signatures` | `DEPT_USER` | `get_my_department_print_signatures` | — |
| `departments` | `PUT` | `/api/v1/departments/me/print-signatures` | `DEPT_USER` | `set_my_department_print_signatures` | — |
| `departments` | `DELETE` | `/api/v1/departments/{dept_id}` | `ADMIN` | `delete_department` | — |
| `departments` | `GET` | `/api/v1/departments/{dept_id}` | `ADMIN, DEPT_USER, OPERATOR` | `get_department` | — |
| `departments` | `PATCH` | `/api/v1/departments/{dept_id}` | `ADMIN` | `update_department` | — |
| `departments` | `GET` | `/api/v1/departments/{dept_id}/print-signatures` | `ADMIN` | `get_department_print_signatures` | — |
| `departments` | `PUT` | `/api/v1/departments/{dept_id}/print-signatures` | `ADMIN` | `set_department_print_signatures` | — |
| `incidents` | `GET` | `/api/v1/admin/incidents` | `ADMIN` | `list_admin_incidents` | — |
| `incidents` | `GET` | `/api/v1/admin/incidents/unresolved_count` | `ADMIN` | `get_unresolved_incidents_count` | — |
| `incidents` | `GET` | `/api/v1/admin/incidents/{incident_id}` | `ADMIN` | `get_admin_incident_detail` | — |
| `incidents` | `PATCH` | `/api/v1/admin/incidents/{incident_id}` | `ADMIN` | `patch_admin_incident` | — |
| `incidents` | `POST` | `/api/v1/admin/incidents/{incident_id}/retry` | `ADMIN` | `retry_admin_incident` | — |
| `jobs` | `POST` | `/api/v1/jobs/exports/debts` | `ADMIN, DEPT_USER` | `create_debts_export_job` | — |
| `jobs` | `POST` | `/api/v1/jobs/exports/requests` | `ADMIN, DEPT_USER` | `create_requests_export_job` | — |
| `jobs` | `POST` | `/api/v1/jobs/exports/vehicle-report` | `ADMIN, DEPT_USER` | `create_vehicle_report_export_job` | — |
| `jobs` | `POST` | `/api/v1/jobs/reconcile` | `ADMIN` | `create_reconcile_job` | — |
| `jobs` | `GET` | `/api/v1/jobs/{job_id}` | `ADMIN, DEPT_USER` | `get_job` | DEPT_USER: лише власні export jobs; Є окрема логіка/скоуп для DEPT_USER |
| `jobs` | `GET` | `/api/v1/jobs/{job_id}/download` | `ADMIN, DEPT_USER` | `download_job_result` | DEPT_USER: лише власні export jobs; Є окрема логіка/скоуп для DEPT_USER |
| `jobs` | `GET` | `/api/v1/reports/departments` | `ADMIN, DEPT_USER` | `get_departments_report` | Є окрема логіка/скоуп для DEPT_USER |
| `jobs` | `GET` | `/api/v1/reports/vehicle-consumption` | `ADMIN, DEPT_USER` | `get_vehicle_consumption_report` | Є окрема логіка/скоуп для DEPT_USER |
| `jobs` | `GET` | `/api/v1/stock/reconcile` | `ADMIN` | `get_stock_reconcile_now` | — |
| `logs` | `GET` | `/api/v1/settings/alerts` | `ADMIN` | `list_admin_alerts` | — |
| `logs` | `POST` | `/api/v1/settings/alerts/{alert_id}/resolve` | `ADMIN` | `resolve_admin_alert` | — |
| `logs` | `GET` | `/api/v1/settings/backup` | `ADMIN` | `get_backup` | — |
| `logs` | `POST` | `/api/v1/settings/backup` | `ADMIN` | `restore_backup` | — |
| `logs` | `GET` | `/api/v1/settings/backups` | `ADMIN` | `list_real_backups` | — |
| `logs` | `GET` | `/api/v1/settings/backups/config` | `ADMIN` | `get_real_backup_config` | — |
| `logs` | `POST` | `/api/v1/settings/backups/config` | `ADMIN` | `set_real_backup_config` | — |
| `logs` | `POST` | `/api/v1/settings/backups/create` | `ADMIN` | `create_real_backup` | — |
| `logs` | `POST` | `/api/v1/settings/backups/upload` | `ADMIN` | `upload_real_backup` | — |
| `logs` | `POST` | `/api/v1/settings/backups/upload-and-restore` | `ADMIN` | `upload_and_restore_real_backup` | — |
| `logs` | `DELETE` | `/api/v1/settings/backups/{filename}` | `ADMIN` | `delete_real_backup` | — |
| `logs` | `GET` | `/api/v1/settings/backups/{filename}/download` | `ADMIN` | `download_real_backup` | — |
| `logs` | `POST` | `/api/v1/settings/backups/{filename}/restore` | `ADMIN` | `restore_real_backup` | — |
| `logs` | `POST` | `/api/v1/settings/backups/{filename}/verify` | `ADMIN` | `verify_real_backup` | — |
| `logs` | `GET` | `/api/v1/settings/incidents` | `ADMIN` | `list_admin_alerts` | — |
| `logs` | `POST` | `/api/v1/settings/incidents/{alert_id}/resolve` | `ADMIN` | `resolve_admin_alert` | — |
| `logs` | `GET` | `/api/v1/settings/logs` | `ADMIN` | `get_logs` | — |
| `logs` | `POST` | `/api/v1/settings/logs/clear` | `ADMIN` | `clear_logs` | — |
| `logs` | `GET` | `/api/v1/settings/logs/export` | `ADMIN` | `export_logs` | — |
| `logs` | `GET` | `/api/v1/settings/logs/posting-errors` | `ADMIN` | `export_posting_error_logs` | — |
| `pdf_templates` | `DELETE` | `/api/v1/admin/pdf-template-versions/{version_id}` | `ADMIN` | `delete_pdf_template_version` | — |
| `pdf_templates` | `PATCH` | `/api/v1/admin/pdf-template-versions/{version_id}` | `ADMIN` | `patch_pdf_template_version` | — |
| `pdf_templates` | `POST` | `/api/v1/admin/pdf-template-versions/{version_id}/preview` | `ADMIN` | `preview_pdf_template_version` | — |
| `pdf_templates` | `POST` | `/api/v1/admin/pdf-template-versions/{version_id}/publish` | `ADMIN` | `publish_pdf_template_version` | — |
| `pdf_templates` | `GET` | `/api/v1/admin/pdf-templates` | `ADMIN` | `list_pdf_templates` | — |
| `pdf_templates` | `POST` | `/api/v1/admin/pdf-templates` | `ADMIN` | `create_pdf_template` | — |
| `pdf_templates` | `DELETE` | `/api/v1/admin/pdf-templates/{template_id}` | `ADMIN` | `delete_pdf_template` | — |
| `pdf_templates` | `GET` | `/api/v1/admin/pdf-templates/{template_id}` | `ADMIN` | `get_pdf_template` | — |
| `pdf_templates` | `POST` | `/api/v1/admin/pdf-templates/{template_id}/versions` | `ADMIN` | `create_pdf_template_version` | — |
| `pdf_templates` | `GET` | `/api/v1/print-artifacts/{artifact_id}/download` | `ADMIN, DEPT_USER, OPERATOR` | `download_print_artifact` | — |
| `pdf_templates` | `GET` | `/api/v1/requests/{request_id}/print/act` | `ADMIN, DEPT_USER, OPERATOR` | `print_request_issue_act` | — |
| `pdf_templates` | `POST` | `/api/v1/requests/{request_id}/print/pdf` | `ADMIN, DEPT_USER, OPERATOR` | `print_request_pdf` | — |
| `requests` | `GET` | `/api/v1/posting-sessions/{session_id}` | `ADMIN, DEPT_USER, OPERATOR` | `get_posting_session` | DEPT_USER: тільки власний підрозділ; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `GET` | `/api/v1/requests` | `ADMIN, DEPT_USER, OPERATOR` | `list_requests` | Є окрема логіка/скоуп для DEPT_USER; Є окрема логіка/скоуп для OPERATOR |
| `requests` | `POST` | `/api/v1/requests` | `DEPT_USER` | `create_request` | — |
| `requests` | `POST` | `/api/v1/requests/admin` | `ADMIN` | `create_request_as_admin` | — |
| `requests` | `POST` | `/api/v1/requests/admin/month-end-confirm` | `ADMIN` | `month_end_confirm_requests` | — |
| `requests` | `DELETE` | `/api/v1/requests/{req_id}` | `ADMIN, DEPT_USER` | `delete_draft_request` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `GET` | `/api/v1/requests/{req_id}` | `ADMIN, DEPT_USER, OPERATOR` | `get_request_detail` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; OPERATOR: лише заявки APPROVED/ISSUED_BY_OPERATOR; Видача оператором лише APPROVED/ISSUED_BY_OPERATOR; Є окрема логіка/скоуп для DEPT_USER; Є окрема логіка/скоуп для OPERATOR |
| `requests` | `PUT` | `/api/v1/requests/{req_id}` | `DEPT_USER` | `update_request` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток |
| `requests` | `POST` | `/api/v1/requests/{req_id}/approve` | `ADMIN` | `approve_request` | — |
| `requests` | `GET` | `/api/v1/requests/{req_id}/audit` | `ADMIN, DEPT_USER, OPERATOR` | `get_request_audit` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `POST` | `/api/v1/requests/{req_id}/confirm` | `DEPT_USER` | `confirm_request` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу |
| `requests` | `POST` | `/api/v1/requests/{req_id}/issue` | `OPERATOR` | `issue_request` | — |
| `requests` | `POST` | `/api/v1/requests/{req_id}/items` | `DEPT_USER` | `add_item` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток |
| `requests` | `DELETE` | `/api/v1/requests/{req_id}/items/{item_id}` | `DEPT_USER` | `delete_item` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток |
| `requests` | `POST` | `/api/v1/requests/{req_id}/planned-activities` | `ADMIN, DEPT_USER` | `set_request_planned_activities` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `GET` | `/api/v1/requests/{req_id}/posting-sessions` | `ADMIN, DEPT_USER, OPERATOR` | `get_request_posting_sessions` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `GET` | `/api/v1/requests/{req_id}/print` | `ADMIN, DEPT_USER, OPERATOR` | `print_request` | Перевірка належності заявки підрозділу; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `POST` | `/api/v1/requests/{req_id}/reject` | `ADMIN` | `reject_request` | — |
| `requests` | `POST` | `/api/v1/requests/{req_id}/reverse` | `ADMIN` | `reverse_request` | — |
| `requests` | `GET` | `/api/v1/requests/{req_id}/snapshots` | `ADMIN, DEPT_USER, OPERATOR` | `get_request_snapshots` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Є окрема логіка/скоуп для DEPT_USER |
| `requests` | `POST` | `/api/v1/requests/{req_id}/submit` | `DEPT_USER` | `submit_request` | DEPT_USER: тільки власний підрозділ; Перевірка належності заявки підрозділу; Редагування лише чернеток |
| `routes` | `GET` | `/api/v1/route-change-requests` | `ADMIN, DEPT_USER` | `list_route_change_requests` | Є окрема логіка/скоуп для DEPT_USER |
| `routes` | `POST` | `/api/v1/route-change-requests/{req_id}/approve` | `ADMIN` | `approve_route_change_request` | — |
| `routes` | `POST` | `/api/v1/route-change-requests/{req_id}/reject` | `ADMIN` | `reject_route_change_request` | — |
| `routes` | `GET` | `/api/v1/routes` | `ADMIN, DEPT_USER` | `list_routes` | Є окрема логіка/скоуп для DEPT_USER |
| `routes` | `POST` | `/api/v1/routes` | `ADMIN, DEPT_USER` | `create_route` | Є окрема логіка/скоуп для DEPT_USER |
| `routes` | `POST` | `/api/v1/routes/{rid}/approve` | `ADMIN` | `approve_route` | — |
| `routes` | `POST` | `/api/v1/routes/{rid}/change-requests` | `DEPT_USER` | `create_route_change_request` | — |
| `routes` | `POST` | `/api/v1/routes/{rid}/reject` | `ADMIN` | `reject_route` | — |
| `settings` | `GET` | `/api/v1/settings/density` | `ADMIN` | `get_density_settings` | — |
| `settings` | `POST` | `/api/v1/settings/density` | `ADMIN` | `set_density_settings` | — |
| `settings` | `GET` | `/api/v1/settings/density/history` | `ADMIN` | `get_density_history` | — |
| `settings` | `GET` | `/api/v1/settings/features` | `ADMIN` | `get_feature_settings` | — |
| `settings` | `POST` | `/api/v1/settings/features` | `ADMIN` | `set_feature_settings` | — |
| `settings` | `GET` | `/api/v1/settings/planned-activities` | `ADMIN, OPERATOR, DEPT_USER` | `list_planned_activities` | — |
| `settings` | `POST` | `/api/v1/settings/planned-activities` | `ADMIN` | `create_planned_activity` | — |
| `settings` | `DELETE` | `/api/v1/settings/planned-activities/{activity_id}` | `ADMIN` | `delete_planned_activity` | — |
| `settings` | `PATCH` | `/api/v1/settings/planned-activities/{activity_id}` | `ADMIN` | `update_planned_activity` | — |
| `settings` | `GET` | `/api/v1/settings/pwa` | `ADMIN` | `get_pwa_settings` | — |
| `settings` | `POST` | `/api/v1/settings/pwa` | `ADMIN` | `set_pwa_settings` | — |
| `settings` | `DELETE` | `/api/v1/settings/pwa/icon` | `ADMIN` | `delete_pwa_icon` | — |
| `settings` | `POST` | `/api/v1/settings/pwa/icon` | `ADMIN` | `upload_pwa_icon` | — |
| `settings` | `GET` | `/api/v1/settings/pwa/icon/{size}.png` | `PUBLIC` | `get_pwa_icon_binary` | — |
| `settings` | `GET` | `/api/v1/settings/pwa/icons` | `ADMIN` | `get_pwa_icons` | — |
| `settings` | `GET` | `/api/v1/settings/pwa/manifest.webmanifest` | `PUBLIC` | `get_dynamic_manifest` | — |
| `settings` | `GET` | `/api/v1/settings/support` | `ADMIN, OPERATOR, DEPT_USER` | `get_support_settings` | — |
| `settings` | `POST` | `/api/v1/settings/support` | `ADMIN` | `set_support_settings` | — |
| `settings` | `GET` | `/api/v1/settings/support/public` | `PUBLIC` | `get_support_settings_public` | — |
| `stock` | `GET` | `/api/v1/stock/adjustments` | `ADMIN` | `list_adjustments` | — |
| `stock` | `POST` | `/api/v1/stock/adjustments` | `ADMIN` | `create_adjustment` | — |
| `stock` | `GET` | `/api/v1/stock/adjustments/{adjustment_id}` | `ADMIN` | `get_adjustment_detail` | — |
| `stock` | `GET` | `/api/v1/stock/balance` | `ADMIN, OPERATOR` | `get_balance` | — |
| `stock` | `GET` | `/api/v1/stock/ledger` | `ADMIN` | `list_ledger` | — |
| `stock` | `GET` | `/api/v1/stock/receipts` | `ADMIN` | `list_receipts` | — |
| `stock` | `POST` | `/api/v1/stock/receipts` | `ADMIN` | `create_receipt` | — |
| `updates` | `POST` | `/api/v1/system/updates/apply` | `ADMIN` | `apply_system_update` | — |
| `updates` | `GET` | `/api/v1/system/updates/check` | `ADMIN` | `check_system_update` | — |
| `updates` | `GET` | `/api/v1/system/updates/config` | `ADMIN` | `get_system_update_config` | — |
| `updates` | `POST` | `/api/v1/system/updates/config` | `ADMIN` | `set_system_update_config` | — |
| `updates` | `GET` | `/api/v1/system/updates/logs` | `ADMIN` | `list_system_update_logs` | — |
| `updates` | `GET` | `/api/v1/system/updates/manifest` | `ADMIN` | `get_system_update_manifest_compat` | — |
| `updates` | `GET` | `/api/v1/system/updates/meta` | `ADMIN` | `get_system_update_meta` | — |
| `updates` | `POST` | `/api/v1/system/updates/rollback` | `ADMIN` | `rollback_system_update` | — |
| `updates` | `GET` | `/api/v1/system/updates/status/{job_id}` | `ADMIN` | `get_system_update_status` | — |
| `updates` | `POST` | `/api/v1/system/updates/{update_log_id}/rollback` | `ADMIN` | `rollback_system_update_by_log_id` | — |
| `users` | `GET` | `/api/v1/users` | `ADMIN` | `list_users` | — |
| `users` | `POST` | `/api/v1/users` | `ADMIN` | `create_user` | — |
| `users` | `DELETE` | `/api/v1/users/{user_id}` | `ADMIN` | `delete_user` | — |
| `users` | `GET` | `/api/v1/users/{user_id}` | `ADMIN` | `get_user` | — |
| `users` | `PATCH` | `/api/v1/users/{user_id}` | `ADMIN` | `update_user` | — |
| `vehicle_change_requests` | `GET` | `/api/v1/vehicle-change-requests` | `ADMIN, DEPT_USER` | `list_vehicle_change_requests` | Є окрема логіка/скоуп для DEPT_USER |
| `vehicle_change_requests` | `POST` | `/api/v1/vehicle-change-requests/{req_id}/approve` | `ADMIN` | `approve_vehicle_change_request` | — |
| `vehicle_change_requests` | `POST` | `/api/v1/vehicle-change-requests/{req_id}/reject` | `ADMIN` | `reject_vehicle_change_request` | — |
| `vehicle_change_requests` | `POST` | `/api/v1/vehicles/{vid}/change-requests` | `DEPT_USER` | `create_vehicle_change_request` | — |
| `vehicles` | `GET` | `/api/v1/vehicles` | `ADMIN, DEPT_USER, OPERATOR` | `list_vehicles` | Є окрема логіка/скоуп для OPERATOR |
| `vehicles` | `POST` | `/api/v1/vehicles` | `ADMIN, DEPT_USER` | `create_vehicle` | Є окрема логіка/скоуп для DEPT_USER |
| `vehicles` | `DELETE` | `/api/v1/vehicles/{vid}` | `ADMIN` | `delete_vehicle` | — |
| `vehicles` | `PATCH` | `/api/v1/vehicles/{vid}` | `ADMIN` | `update_vehicle` | — |
| `vehicles` | `POST` | `/api/v1/vehicles/{vid}/approve` | `ADMIN` | `approve_vehicle` | — |

## 5. Пояснення Access

- `PUBLIC`: endpoint без role-checker (може мати інші перевірки).
- `AUTHENTICATED`: будь-який активний користувач з валідним токеном.
- `ADMIN`, `OPERATOR`, `DEPT_USER`: строго рольовий доступ.
- `ADMIN, DEPT_USER` (та інші комбінації): доступний набір ролей, додаткові обмеження див. у колонці перевірок.

## 6. Рекомендації експлуатації

- Ревізію цього документа робити після кожного релізу зі зміною endpoint-ів або role logic.
- Для audit trail зберігати версію цього PDF разом з релізом.
- Для критичних дій (`approve/issue/confirm/restore/update`) залишати додатковий операційний контроль через журнал дій.
