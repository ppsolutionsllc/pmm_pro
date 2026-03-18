const API_ROOT = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
const BASE = API_ROOT ? `${API_ROOT}/api/v1` : '/api/v1';

function getToken(): string | null {
  return sessionStorage.getItem('token');
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function request<T = any>(url: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...authHeaders(),
    ...(opts.headers as Record<string, string> || {}),
  };
  if (opts.body && typeof opts.body === 'string') {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  const res = await fetch(`${BASE}${url}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null as T;
  return res.json();
}

type QueryValue = string | number | boolean | null | undefined;

function withQuery(path: string, params?: Record<string, QueryValue>): string {
  if (!params) return path;
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || `${value}`.length === 0) return;
    sp.set(key, String(value));
  });
  const query = sp.toString();
  return query ? `${path}?${query}` : path;
}

async function requestBlob(url: string, opts: RequestInit = {}): Promise<Blob> {
  const res = await fetch(`${BASE}${url}`, { ...opts, headers: { ...authHeaders(), ...(opts.headers as Record<string, string> || {}) } });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.blob();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    fetch(`${BASE}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    }).then(async r => {
      if (!r.ok) throw new Error('Невірний логін або пароль');
      return r.json();
    }),
  me: () => request('/me'),

  // Departments
  getDepartments: (params?: { include_deleted?: boolean }) => request(withQuery('/departments', params)),
  getDepartment: (id: number) => request(`/departments/${id}`),
  createDepartment: (data: any) => request('/departments', { method: 'POST', body: JSON.stringify(data) }),
  updateDepartment: (id: number, data: any) => request(`/departments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteDepartment: (id: number, reason: string) =>
    request(`/departments/${id}`, { method: 'DELETE', body: JSON.stringify({ reason }) }),
  getMyDepartmentPrintSignatures: () => request('/departments/me/print-signatures'),
  updateMyDepartmentPrintSignatures: (data: any) =>
    request('/departments/me/print-signatures', { method: 'PUT', body: JSON.stringify(data) }),
  getDepartmentPrintSignatures: (id: number) => request(`/departments/${id}/print-signatures`),
  updateDepartmentPrintSignatures: (id: number, data: any) =>
    request(`/departments/${id}/print-signatures`, { method: 'PUT', body: JSON.stringify(data) }),

  // Users
  getUsers: (params?: { role?: string; department_id?: number }) => request(withQuery('/users', params)),
  createUser: (data: any) => request('/users', { method: 'POST', body: JSON.stringify(data) }),

  // Vehicles
  getVehicles: () => request('/vehicles'),
  createVehicle: (data: any) => request('/vehicles', { method: 'POST', body: JSON.stringify(data) }),
  updateVehicle: (id: number, data: any) => request(`/vehicles/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  approveVehicle: (id: number) => request(`/vehicles/${id}/approve`, { method: 'POST' }),
  deleteVehicle: (id: number) => request(`/vehicles/${id}`, { method: 'DELETE' }),

  // Vehicle change requests
  createVehicleChangeRequest: (vehicleId: number, data: any) => request(`/vehicles/${vehicleId}/change-requests`, { method: 'POST', body: JSON.stringify(data) }),
  listVehicleChangeRequests: (params?: { status?: string; department_id?: number }) =>
    request(withQuery('/vehicle-change-requests', params)),
  approveVehicleChangeRequest: (id: number) => request(`/vehicle-change-requests/${id}/approve`, { method: 'POST' }),
  rejectVehicleChangeRequest: (id: number) => request(`/vehicle-change-requests/${id}/reject`, { method: 'POST' }),

  // Routes
  listRoutes: (params?: { department_id?: number; only_approved?: boolean }) => request(withQuery('/routes', params)),
  createRoute: (data: any) => request('/routes', { method: 'POST', body: JSON.stringify(data) }),
  approveRoute: (id: number) => request(`/routes/${id}/approve`, { method: 'POST' }),
  rejectRoute: (id: number) => request(`/routes/${id}/reject`, { method: 'POST' }),

  // Route change requests
  createRouteChangeRequest: (routeId: number, data: any) => request(`/routes/${routeId}/change-requests`, { method: 'POST', body: JSON.stringify(data) }),
  listRouteChangeRequests: (params?: { status?: string; department_id?: number }) =>
    request(withQuery('/route-change-requests', params)),
  approveRouteChangeRequest: (id: number) => request(`/route-change-requests/${id}/approve`, { method: 'POST' }),
  rejectRouteChangeRequest: (id: number) => request(`/route-change-requests/${id}/reject`, { method: 'POST' }),

  // Settings
  getDensity: () => request('/settings/density'),
  setDensity: (data: any) => request('/settings/density', { method: 'POST', body: JSON.stringify(data) }),
  getSupportPublic: () => request('/settings/support/public'),
  getSupport: () => request('/settings/support'),
  setSupport: (data: any) => request('/settings/support', { method: 'POST', body: JSON.stringify(data) }),
  getPwa: () => request('/settings/pwa'),
  setPwa: (data: any) => request('/settings/pwa', { method: 'POST', body: JSON.stringify(data) }),
  getPwaIcons: () => request('/settings/pwa/icons'),
  uploadPwaIcon: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/settings/pwa/icon', { method: 'POST', body: fd });
  },
  deletePwaIcon: () => request('/settings/pwa/icon', { method: 'DELETE' }),

  listPlannedActivities: (params?: { only_active?: boolean }) => request(withQuery('/settings/planned-activities', params)),
  createPlannedActivity: (data: any) => request('/settings/planned-activities', { method: 'POST', body: JSON.stringify(data) }),
  updatePlannedActivity: (id: number, data: any) => request(`/settings/planned-activities/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePlannedActivity: (id: number) => request(`/settings/planned-activities/${id}`, { method: 'DELETE' }),

  // Stock
  createReceipt: (data: any) => request('/stock/receipts', { method: 'POST', body: JSON.stringify(data) }),
  getReceipts: () => request('/stock/receipts'),
  getBalance: () => request('/stock/balance'),
  getLedger: () => request('/stock/ledger'),
  createStockAdjustment: (data: any, idempotencyKey?: string) =>
    request('/stock/adjustments', {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: JSON.stringify(idempotencyKey ? { ...data, idempotency_key: idempotencyKey } : data),
    }),
  getStockAdjustments: () => request('/stock/adjustments'),
  getStockAdjustment: (id: number) => request(`/stock/adjustments/${id}`),
  getStockReconcile: () => request('/stock/reconcile'),
  createReconcileJob: (filters?: any) => request('/jobs/reconcile', { method: 'POST', body: JSON.stringify({ filters: filters || {} }) }),

  // Requests
  getRequests: (params?: { status?: string; department_id?: number; search?: string }) => request(withQuery('/requests', params)),
  getRequest: (id: number) => request(`/requests/${id}`),
  createRequest: (data: any) => request('/requests', { method: 'POST', body: JSON.stringify(data) }),
  createRequestAsAdmin: (data: any) => request('/requests/admin', { method: 'POST', body: JSON.stringify(data) }),
  deleteDraftRequest: (id: number) => request(`/requests/${id}`, { method: 'DELETE' }),
  addRequestItem: (reqId: number, data: any) => request(`/requests/${reqId}/items`, { method: 'POST', body: JSON.stringify(data) }),
  deleteRequestItem: (reqId: number, itemId: number) => request(`/requests/${reqId}/items/${itemId}`, { method: 'DELETE' }),
  submitRequest: (id: number) => request(`/requests/${id}/submit`, { method: 'POST' }),
  rejectRequest: (id: number, comment: string) => request(`/requests/${id}/reject`, { method: 'POST', body: JSON.stringify({ comment }) }),
  approveRequest: (id: number) => request(`/requests/${id}/approve`, { method: 'POST' }),
  issueRequest: (id: number) => request(`/requests/${id}/issue`, { method: 'POST' }),
  confirmRequest: (id: number, idempotencyKey?: string) =>
    request(`/requests/${id}/confirm`, {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: JSON.stringify(idempotencyKey ? { idempotency_key: idempotencyKey } : {}),
    }),
  printRequestPdf: (id: number, data?: { template_id?: string; force_regenerate?: boolean }) =>
    request(`/requests/${id}/print/pdf`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    }),
  downloadPrintArtifact: (artifactId: string) => requestBlob(`/print-artifacts/${artifactId}/download`),
  listPdfTemplates: () => request('/admin/pdf-templates'),
  createPdfTemplate: (data: { name: string; scope?: string; is_active?: boolean }) =>
    request('/admin/pdf-templates', { method: 'POST', body: JSON.stringify(data) }),
  getPdfTemplate: (id: string) => request(`/admin/pdf-templates/${id}`),
  deletePdfTemplate: (id: string) => request(`/admin/pdf-templates/${id}`, { method: 'DELETE' }),
  updatePdfTemplateVersion: (
    versionId: string,
    data: {
      name?: string;
      layout_json?: any;
      table_columns_json?: any[];
      mapping_json?: any;
      rules_json?: any;
      service_block_json?: any;
    },
  ) =>
    request(`/admin/pdf-template-versions/${versionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  previewPdfTemplateVersion: (
    versionId: string,
    payload: {
      request_id: number;
      name?: string;
      layout_json?: any;
      table_columns_json?: any[];
      mapping_json?: any;
      rules_json?: any;
      service_block_json?: any;
    },
  ) => requestBlob(`/admin/pdf-template-versions/${versionId}/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }),

  // system logs for admin panel
  getSystemLogs: () => request('/settings/logs'),
  clearSystemLogs: () => request('/settings/logs/clear', { method: 'POST' }),
  getAdminAlerts: () => request('/settings/alerts'),
  resolveAdminAlert: (id: number, comment?: string) =>
    request(`/settings/alerts/${id}/resolve`, { method: 'POST', body: JSON.stringify({ comment: comment || '' }) }),
  getAdminIncidents: (params?: {
    status?: string;
    severity?: string;
    type?: string;
    q?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) => request(withQuery('/admin/incidents', params)),
  getAdminIncident: (id: string) => request(`/admin/incidents/${id}`),
  patchAdminIncident: (id: string, data: { status?: string; resolution_comment?: string; message?: string }) =>
    request(`/admin/incidents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  retryAdminIncident: (id: string) => request(`/admin/incidents/${id}/retry`, { method: 'POST' }),
  getAdminIncidentsUnresolvedCount: () => request('/admin/incidents/unresolved_count'),
  exportSystemLogs: () => requestBlob('/settings/logs/export'),

  // backup / restore
  createDbBackup: () => request('/settings/backups/create', { method: 'POST' }),
  listDbBackups: () => request('/settings/backups'),
  uploadDbBackup: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/settings/backups/upload', { method: 'POST', body: fd });
  },
  uploadAndRestoreDbBackup: (file: File, confirm = 'RESTORE') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('confirm', confirm);
    return request('/settings/backups/upload-and-restore', { method: 'POST', body: fd });
  },
  getDbBackupConfig: () => request('/settings/backups/config'),
  setDbBackupConfig: (data: { schedule_enabled: boolean; schedule_interval_hours: number; rotation_keep: number }) =>
    request('/settings/backups/config', { method: 'POST', body: JSON.stringify(data) }),
  verifyDbBackup: (filename: string) => request(`/settings/backups/${encodeURIComponent(filename)}/verify`, { method: 'POST' }),
  restoreDbBackup: (filename: string, confirm = 'RESTORE') =>
    request(`/settings/backups/${encodeURIComponent(filename)}/restore`, {
      method: 'POST',
      body: JSON.stringify({ confirm }),
    }),
  deleteDbBackup: (filename: string) => request(`/settings/backups/${encodeURIComponent(filename)}`, { method: 'DELETE' }),
  downloadDbBackup: (filename: string) => requestBlob(`/settings/backups/${encodeURIComponent(filename)}/download`),

  // reports / export jobs
  getVehicleConsumptionReport: (filters?: any) => request(withQuery('/reports/vehicle-consumption', filters)),
  createVehicleReportExportJob: (format = 'XLSX', filters?: any) =>
    request('/jobs/exports/vehicle-report', { method: 'POST', body: JSON.stringify({ format, filters: filters || {} }) }),
  getJob: (jobId: string) => request(`/jobs/${jobId}`),
  downloadJobArtifact: (jobId: string) => requestBlob(`/jobs/${jobId}/download`),

  // system updates
  getSystemUpdateConfig: () => request('/system/updates/config'),
  setSystemUpdateConfig: (data: { default_with_backup?: boolean | null }) =>
    request('/system/updates/config', { method: 'POST', body: JSON.stringify(data) }),
  getSystemUpdateMeta: () => request('/system/updates/meta'),
  getSystemUpdateCheck: () => request('/system/updates/check'),
  getSystemUpdateLogs: (limit = 50) => request(withQuery('/system/updates/logs', { limit })),
  applySystemUpdate: (target_version?: string, backup = true) =>
    request('/system/updates/apply', { method: 'POST', body: JSON.stringify({ target_version, backup }) }),
  rollbackSystemUpdateByLogId: (update_log_id: number) =>
    request(`/system/updates/${update_log_id}/rollback`, { method: 'POST' }),
  getSystemUpdateStatus: (jobId: string) => request(`/system/updates/status/${jobId}`),

  setRequestPlannedActivities: (id: number, planned_activity_ids: number[]) =>
    request(`/requests/${id}/planned-activities`, { method: 'POST', body: JSON.stringify({ planned_activity_ids }) }),
};
