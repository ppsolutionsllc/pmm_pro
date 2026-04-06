import React, { useEffect, useMemo, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react';

type Department = {
  id: number;
  name: string;
};

type RouteRow = {
  id: number;
  department_id: number;
  name: string;
  points: string[];
  distance_km: number;
  is_approved: boolean;
};

type ChangeRequestRow = {
  id: number;
  route_id: number;
  department_id: number;
  status: string;
  name?: string | null;
  points?: string[] | null;
  distance_km?: number | null;
  created_at?: string | null;
};

const API_BASE = '/api/v1';

const getToken = (): string =>
  sessionStorage.getItem('token')
  || localStorage.getItem('token')
  || '';

const apiRequest = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const headers = new Headers(init?.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = 'Помилка запиту';
    try {
      const data = await response.json();
      message = data?.detail || data?.message || message;
    } catch {
      try {
        message = await response.text();
      } catch {}
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
};

const parsePoints = (value: string): string[] =>
  value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);

const formatPoints = (points: string[] | null | undefined): string =>
  (points || []).join(' -> ');

const RoutesAdminPage: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [routes, setRoutes] = useState<RouteRow[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [changeRequests, setChangeRequests] = useState<ChangeRequestRow[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRouteId, setEditingRouteId] = useState<number | null>(null);
  const [form, setForm] = useState({
    department_id: '',
    name: '',
    points_text: '',
    distance_km: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      const [routesData, departmentsData, changeRequestsData] = await Promise.all([
        apiRequest<RouteRow[]>('/routes'),
        apiRequest<Department[]>('/departments'),
        apiRequest<ChangeRequestRow[]>('/route-change-requests?status=PENDING').catch(() => []),
      ]);
      setRoutes(routesData || []);
      setDepartments(departmentsData || []);
      setChangeRequests(changeRequestsData || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити маршрути', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => {
    setEditingRouteId(null);
    setForm({
      department_id: '',
      name: '',
      points_text: '',
      distance_km: '',
    });
  };

  const openCreate = () => {
    resetForm();
    setModalOpen(true);
  };

  const openEdit = (row: RouteRow) => {
    setEditingRouteId(row.id);
    setForm({
      department_id: String(row.department_id),
      name: row.name || '',
      points_text: (row.points || []).join('\n'),
      distance_km: String(row.distance_km ?? ''),
    });
    setModalOpen(true);
  };

  const saveRoute = async () => {
    const departmentId = Number(form.department_id || 0);
    const distanceKm = Number(form.distance_km || 0);
    const points = parsePoints(form.points_text);
    if (!departmentId) {
      toast('Оберіть підрозділ', 'warning');
      return;
    }
    if (!form.name.trim()) {
      toast('Вкажіть назву маршруту', 'warning');
      return;
    }
    if (!points.length) {
      toast('Додайте хоча б одну точку маршруту', 'warning');
      return;
    }
    if (!Number.isFinite(distanceKm) || distanceKm <= 0) {
      toast('Вкажіть коректну відстань', 'warning');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        department_id: departmentId,
        name: form.name.trim(),
        points,
        distance_km: distanceKm,
      };
      if (editingRouteId) {
        await apiRequest<RouteRow>(`/routes/${editingRouteId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
        toast('Маршрут оновлено', 'success');
      } else {
        await apiRequest<RouteRow>('/routes', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        toast('Маршрут створено', 'success');
      }
      setModalOpen(false);
      resetForm();
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося зберегти маршрут', 'error');
    } finally {
      setSaving(false);
    }
  };

  const setApproval = async (routeId: number, approve: boolean) => {
    try {
      await apiRequest<RouteRow>(`/routes/${routeId}/${approve ? 'approve' : 'reject'}`, {
        method: 'POST',
      });
      toast(approve ? 'Маршрут погоджено' : 'Маршрут відхилено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося змінити статус маршруту', 'error');
    }
  };

  const decideChangeRequest = async (requestId: number, approve: boolean) => {
    try {
      await apiRequest<ChangeRequestRow>(`/route-change-requests/${requestId}/${approve ? 'approve' : 'reject'}`, {
        method: 'POST',
      });
      toast(approve ? 'Запит на зміну погоджено' : 'Запит на зміну відхилено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося обробити запит на зміну', 'error');
    }
  };

  const deleteRoute = async (row: RouteRow) => {
    const confirmed = window.confirm(`Видалити маршрут "${row.name}"?`);
    if (!confirmed) return;

    try {
      await apiRequest<{ ok: boolean }>(`/routes/${row.id}`, {
        method: 'DELETE',
      });
      toast('Маршрут видалено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося видалити маршрут', 'error');
    }
  };

  const departmentMap = useMemo(
    () => Object.fromEntries(departments.map((d) => [d.id, d.name])),
    [departments],
  );

  const routeColumns = [
    { key: 'id', title: 'ID' },
    {
      key: 'department_id',
      title: 'Підрозділ',
      render: (row: RouteRow) => departmentMap[row.department_id] || `#${row.department_id}`,
    },
    { key: 'name', title: 'Назва' },
    {
      key: 'points',
      title: 'Точки',
      render: (row: RouteRow) => formatPoints(row.points),
    },
    {
      key: 'distance_km',
      title: 'Відстань, км',
      render: (row: RouteRow) => row.distance_km,
    },
    {
      key: 'is_approved',
      title: 'Статус',
      render: (row: RouteRow) => (
        <span className={row.is_approved ? 'text-accent' : 'text-warn'}>
          {row.is_approved ? 'Погоджено' : 'Очікує / відхилено'}
        </span>
      ),
    },
    {
      key: 'actions',
      title: 'Дії',
      render: (row: RouteRow) => (
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-secondary !py-1 !px-3"
            onClick={(e) => {
              e.stopPropagation();
              openEdit(row);
            }}
          >
            <Pencil size={14} /> Редагувати
          </button>
          {!row.is_approved && (
            <button
              type="button"
              className="btn-primary !py-1 !px-3"
              onClick={(e) => {
                e.stopPropagation();
                setApproval(row.id, true);
              }}
            >
              <Check size={14} /> Погодити
            </button>
          )}
          {row.is_approved && (
            <button
              type="button"
              className="btn-danger !py-1 !px-3"
              onClick={(e) => {
                e.stopPropagation();
                setApproval(row.id, false);
              }}
            >
              <X size={14} /> Відхилити
            </button>
          )}
          <button
            type="button"
            className="btn-danger !py-1 !px-3"
            onClick={(e) => {
              e.stopPropagation();
              deleteRoute(row);
            }}
          >
            <Trash2 size={14} /> Видалити
          </button>
        </div>
      ),
    },
  ];

  const changeRequestColumns = [
    { key: 'id', title: 'ID' },
    { key: 'route_id', title: 'Маршрут' },
    {
      key: 'department_id',
      title: 'Підрозділ',
      render: (row: ChangeRequestRow) => departmentMap[row.department_id] || `#${row.department_id}`,
    },
    { key: 'name', title: 'Нова назва', render: (row: ChangeRequestRow) => row.name || '—' },
    {
      key: 'points',
      title: 'Нові точки',
      render: (row: ChangeRequestRow) => formatPoints(row.points || []),
    },
    {
      key: 'distance_km',
      title: 'Нова відстань, км',
      render: (row: ChangeRequestRow) => row.distance_km ?? '—',
    },
    {
      key: 'actions',
      title: 'Дії',
      render: (row: ChangeRequestRow) => (
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-primary !py-1 !px-3"
            onClick={() => decideChangeRequest(row.id, true)}
          >
            <Check size={14} /> Погодити
          </button>
          <button
            type="button"
            className="btn-danger !py-1 !px-3"
            onClick={() => decideChangeRequest(row.id, false)}
          >
            <X size={14} /> Відхилити
          </button>
        </div>
      ),
    },
  ];

  if (loading) return <LoadingSkeleton rows={6} />;

  return (
    <div>
      <PageHeader
        title="Маршрути"
        subtitle="Довідник маршрутів і запити на зміни"
        actions={
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={load}>Оновити</button>
            <button className="btn-primary" onClick={openCreate}>
              <Plus size={16} /> Новий маршрут
            </button>
          </div>
        }
      />

      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Маршрути</h3>
          <DataTable columns={routeColumns} data={routes} emptyText="Маршрутів немає" />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Запити на зміни</h3>
          <DataTable columns={changeRequestColumns} data={changeRequests} emptyText="Запитів на зміни немає" />
        </div>
      </div>

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          resetForm();
        }}
        title={editingRouteId ? 'Редагувати маршрут' : 'Створити маршрут'}
        size="lg"
        footer={(
          <>
            <button
              className="btn-secondary"
              onClick={() => {
                setModalOpen(false);
                resetForm();
              }}
            >
              Скасувати
            </button>
            <button className="btn-primary" onClick={saveRoute} disabled={saving}>
              {saving ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        )}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Підрозділ</label>
            <select
              className="input-field"
              value={form.department_id}
              onChange={(e) => setForm((prev) => ({ ...prev, department_id: e.target.value }))}
            >
              <option value="">Оберіть підрозділ</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва маршруту</label>
            <input
              className="input-field"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Точки маршруту</label>
            <textarea
              className="input-field min-h-32"
              value={form.points_text}
              onChange={(e) => setForm((prev) => ({ ...prev, points_text: e.target.value }))}
              placeholder={'Кожну точку вкажіть з нового рядка'}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Відстань, км</label>
            <input
              type="number"
              step="0.1"
              className="input-field"
              value={form.distance_km}
              onChange={(e) => setForm((prev) => ({ ...prev, distance_km: e.target.value }))}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default RoutesAdminPage;
