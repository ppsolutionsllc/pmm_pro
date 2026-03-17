const REQUEST_STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Чернетка',
  SUBMITTED: 'Подано',
  APPROVED: 'Затверджено',
  ISSUED: 'Видано',
  ISSUED_BY_OPERATOR: 'Видано оператором',
  POSTED: 'Проведено',
  POSTED_WITH_DEBT: 'Проведено із заборгованістю',
  REJECTED: 'Відхилено',
  CANCELED: 'Скасовано',
};

const INCIDENT_STATUS_LABELS: Record<string, string> = {
  NEW: 'Новий',
  IN_PROGRESS: 'У роботі',
  RESOLVED: 'Закрито',
};

const INCIDENT_SEVERITY_LABELS: Record<string, string> = {
  LOW: 'Низький',
  MEDIUM: 'Середній',
  HIGH: 'Високий',
  CRITICAL: 'Критичний',
};

const INCIDENT_TYPE_LABELS: Record<string, string> = {
  POSTING_FAILED: 'Помилка проведення',
  ADJUSTMENT_FAILED: 'Помилка коригування',
  EXPORT_FAILED: 'Помилка експорту',
  BACKUP_FAILED: 'Помилка резервного копіювання',
  RECONCILE_FAILED: 'Помилка звірки складу',
  SYSTEM_UPDATE_FAILED: 'Помилка оновлення системи',
  SECURITY_ALERT: 'Попередження безпеки',
};

const JOB_STATUS_LABELS: Record<string, string> = {
  QUEUED: 'У черзі',
  RUNNING: 'Виконується',
  IN_PROGRESS: 'Виконується',
  SUCCESS: 'Успішно',
  FAILED: 'Помилка',
  STARTED: 'Розпочато',
  ROLLED_BACK: 'Відкочено',
};

const JOB_TYPE_LABELS: Record<string, string> = {
  PDF_EXPORT: 'Експорт PDF',
  XLSX_EXPORT: 'Експорт Excel',
  MONTH_END_BATCH: 'Пакетне підтвердження місяця',
  RECONCILE: 'Звірка складу',
  SYSTEM_UPDATE: 'Оновлення системи',
  SYSTEM_ROLLBACK: 'Відкат оновлення',
  BACKUP_CREATE: 'Створення резервної копії',
  BACKUP_VERIFY: 'Перевірка резервної копії',
};

const UPDATE_OPERATION_LABELS: Record<string, string> = {
  UPDATE: 'Оновлення',
  ROLLBACK: 'Відкат',
};

const OPERATION_LABELS: Record<string, string> = {
  CONFIRM: 'Підтвердження отримання',
  MONTH_END_CONFIRM: 'Підтвердження адміном (кінець місяця)',
  ADJUSTMENT: 'Коригування',
  EXPORT: 'Експорт',
  RECONCILE: 'Звірка складу',
  UPDATE: 'Оновлення',
  SYSTEM_UPDATE: 'Оновлення системи',
  SYSTEM_ROLLBACK: 'Відкат оновлення',
  LOCK: 'Блокування оновлення',
  PRECHECK: 'Перевірка перед запуском',
  BACKUP: 'Створення резервної копії',
  FETCH_CODE: 'Отримання коду',
  BUILD: 'Збірка',
  MIGRATE: 'Оновлення структури БД',
  DEPLOY: 'Розгортання',
  HEALTHCHECK: 'Перевірка працездатності',
  FINALIZE: 'Завершення',
  ROLLBACK: 'Відкат',
};

const LEDGER_REF_TYPE_LABELS: Record<string, string> = {
  receipt: 'Прихід',
  issue: 'Видача',
  adjustment: 'Коригування',
};

const PDF_ALIGN_LABELS: Record<string, string> = {
  left: 'Ліворуч',
  center: 'По центру',
  right: 'Праворуч',
};

const PDF_FORMAT_LABELS: Record<string, string> = {
  text: 'Текст',
  number_0: 'Число (без десяткових)',
  number_2: 'Число (2 знаки)',
  date: 'Дата',
  datetime: 'Дата і час',
};

const prettifyCode = (value: string): string =>
  value
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());

const mapLabel = (map: Record<string, string>, value?: string | null): string => {
  if (!value) return '—';
  return map[value] || prettifyCode(value);
};

export const requestStatusLabel = (value?: string | null): string => mapLabel(REQUEST_STATUS_LABELS, value);
export const incidentStatusLabel = (value?: string | null): string => mapLabel(INCIDENT_STATUS_LABELS, value);
export const incidentSeverityLabel = (value?: string | null): string => mapLabel(INCIDENT_SEVERITY_LABELS, value);
export const incidentTypeLabel = (value?: string | null): string => mapLabel(INCIDENT_TYPE_LABELS, value);
export const jobStatusLabel = (value?: string | null): string => mapLabel(JOB_STATUS_LABELS, value);
export const jobTypeLabel = (value?: string | null): string => mapLabel(JOB_TYPE_LABELS, value);
export const updateOperationLabel = (value?: string | null): string => mapLabel(UPDATE_OPERATION_LABELS, value);
export const operationLabel = (value?: string | null): string => mapLabel(OPERATION_LABELS, value);
export const ledgerRefTypeLabel = (value?: string | null): string => mapLabel(LEDGER_REF_TYPE_LABELS, value);
export const pdfAlignLabel = (value?: string | null): string => mapLabel(PDF_ALIGN_LABELS, value);
export const pdfFormatLabel = (value?: string | null): string => mapLabel(PDF_FORMAT_LABELS, value);
export const userActorLabel = (value?: number | string | null): string => (value ? `Користувач #${value}` : 'Система');
