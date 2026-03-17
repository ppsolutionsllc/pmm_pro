import React, { useEffect, useMemo, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus, Search, ArrowUpDown } from 'lucide-react';

const AdminRoutes: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [routes, setRoutes] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [pendingChanges, setPendingChanges] = useState<any[]>([]);

  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [sortKey, setSortKey] = useState<'created_at' | 'name' | 'distance_km' | 'department'>('created_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const [diffOpen, setDiffOpen] = useState(false);
  const [diffMode, setDiffMode] = useState<'new' | 'change'>('change');
  const [diffTarget, setDiffTarget] = useState<any>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ department_id: '', name: '', pointsText: '', distance_km: '' });

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getDepartments(),
      api.listRoutes({}),
      api.listRouteChangeRequests({ status: 'PENDING' }),
    ]).then(([d, r, ch]) => {
      setDepartments(d || []);
      setRoutes(r || []);
      setPendingChanges(ch || []);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const deptName = (id: number) => departments.find((d: any) => d.id === id)?.name || `#${id}`;

  const pendingNewRoutes = useMemo(() => (routes || []).filter((r: any) => !r.is_approved), [routes]);
  const approvedRoutes = useMemo(() => (routes || []).filter((r: any) => r.is_approved), [routes]);

  const filteredSortedApprovedRoutes = useMemo(() => {
    const q = search.trim().toLowerCase();
    const arr = (approvedRoutes || []).filter((r: any) => {
      if (deptFilter && String(r.department_id) !== String(deptFilter)) return false;
      if (!q) return true;
      const hay = `${r.name || ''} ${(r.points || []).join(' ')}`.toLowerCase();
      return hay.includes(q);
    });
    const dir = sortDir === 'asc' ? 1 : -1;
    arr.sort((a: any, b: any) => {
      if (sortKey === 'department') return deptName(a.department_id).localeCompare(deptName(b.department_id)) * dir;
      if (sortKey === 'name') return String(a.name || '').localeCompare(String(b.name || '')) * dir;
      if (sortKey === 'distance_km') return ((a.distance_km ?? 0) - (b.distance_km ?? 0)) * dir;
      const at = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
      return (at - bt) * dir;
    });
    return arr;
  }, [approvedRoutes, deptFilter, search, sortKey, sortDir, departments]);

  const parsePoints = (txt: string) => txt
    .split(/\r?\n|\s*—\s*|\s*-\s*/g)
    .map(s => s.trim())
    .filter(Boolean);

  const create = async () => {
    setCreating(true);
    try {
      await api.createRoute({
        department_id: Number(form.department_id),
        name: form.name,
        points: parsePoints(form.pointsText),
        distance_km: parseFloat(form.distance_km),
      });
      toast('Маршрут створено', 'success');
      setCreateOpen(false);
      setForm({ department_id: '', name: '', pointsText: '', distance_km: '' });
      load();
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setCreating(false);
    }
  };

  const approveNew = async (r: any) => {
    try {
      await api.approveRoute(r.id);
      toast('Маршрут підтверджено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const rejectNew = async (r: any) => {
    try {
      await api.rejectRoute(r.id);
      toast('Маршрут відхилено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const approveChange = async (c: any) => {
    try {
      await api.approveRouteChangeRequest(c.id);
      toast('Зміни застосовано', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const rejectChange = async (c: any) => {
    try {
      await api.rejectRouteChangeRequest(c.id);
      toast('Зміни відхилено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const openDiffNew = (r: any) => {
    setDiffMode('new');
    setDiffTarget(r);
    setDiffOpen(true);
  };

  const openDiffChange = (c: any) => {
    setDiffMode('change');
    setDiffTarget(c);
    setDiffOpen(true);
  };

  const diffRoute = useMemo(() => {
    if (!diffTarget) return null;
    if (diffMode === 'new') return null;
    return routes.find((r: any) => r.id === diffTarget.route_id) || null;
  }, [diffTarget, diffMode, routes]);

  const diffRows = useMemo(() => {
    if (!diffTarget) return [] as Array<{ field: string; oldVal: any; newVal: any }>;

    const rows: Array<{ field: string; oldVal: any; newVal: any }> = [];
    const add = (field: string, oldVal: any, newVal: any) => {
      const o = oldVal ?? null;
      const n = newVal ?? null;
      if (n === null) return;
      if (String(o ?? '') === String(n ?? '')) return;
      rows.push({ field, oldVal: o, newVal: n });
    };

    if (diffMode === 'new') {
      add('Назва', null, diffTarget.name);
      add('Точки', null, (diffTarget.points || []).join(' — '));
      add('Плече підвезення', null, diffTarget.distance_km);
      return rows;
    }

    if (!diffRoute) return rows;
    add('Назва', diffRoute.name, diffTarget.name);
    add('Точки', (diffRoute.points || []).join(' — '), diffTarget.points ? (diffTarget.points || []).join(' — ') : null);
    add('Плече підвезення', diffRoute.distance_km, diffTarget.distance_km);
    return rows;
  }, [diffTarget, diffMode, diffRoute]);

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
    { key: 'name', title: 'Назва' },
    { key: 'points', title: 'Точки', render: (r: any) => (r.points || []).join(' — ') || '—' },
    { key: 'distance_km', title: 'Плече підвезення', render: (r: any) => r.distance_km ?? '—' },
    { key: 'is_approved', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_approved ? 'bg-accent/20 text-accent' : 'bg-warn/20 text-warn'}`}>
        {r.is_approved ? 'Підтверджено' : 'Очікує'}
      </span>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Маршрути"
        subtitle="Довідник маршрутів"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button onClick={() => setCreateOpen(true)} className="btn-primary"><Plus size={16} /> Додати</button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[220px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input-field pl-9"
            placeholder="Пошук по назві або точках..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="input-field w-auto" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
          <option value="">Всі підрозділи</option>
          {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select className="input-field w-auto" value={sortKey} onChange={e => setSortKey(e.target.value as any)}>
          <option value="created_at">Сортування: дата</option>
          <option value="department">Сортування: підрозділ</option>
          <option value="name">Сортування: назва</option>
          <option value="distance_km">Сортування: плече підвезення</option>
        </select>
        <button onClick={() => setSortDir(sortDir === 'asc' ? 'desc' : 'asc')} className="btn-secondary">
          <ArrowUpDown size={16} /> {sortDir === 'asc' ? '↑' : '↓'}
        </button>
      </div>

      {pendingNewRoutes.length > 0 && (
        <div className="card mb-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Нові маршрути на підтвердження ({pendingNewRoutes.length})</h3>
          <DataTable
            columns={[
              { key: 'id', title: 'ID' },
              { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
              { key: 'name', title: 'Назва' },
              { key: 'points', title: 'Точки', render: (r: any) => (r.points || []).join(' — ') || '—' },
              { key: 'distance_km', title: 'Плече підвезення', render: (r: any) => r.distance_km ?? '—' },
              { key: 'actions', title: '', render: (r: any) => (
                <div className="flex gap-2 justify-end">
                  <button onClick={() => openDiffNew(r)} className="btn-ghost text-xs">Деталі</button>
                  <button onClick={() => approveNew(r)} className="btn-primary text-xs">Підтвердити</button>
                  <button onClick={() => rejectNew(r)} className="btn-secondary text-xs">Відхилити</button>
                </div>
              ) },
            ]}
            data={pendingNewRoutes}
            emptyText="Немає"
          />
        </div>
      )}

      {pendingChanges.length > 0 && (
        <div className="card mb-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Зміни маршрутів на підтвердження ({pendingChanges.length})</h3>
          <DataTable
            columns={[
              { key: 'id', title: 'ID' },
              { key: 'route_id', title: 'Маршрут ID' },
              { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
              { key: 'name', title: 'Назва', render: (r: any) => r.name || '—' },
              { key: 'points', title: 'Точки', render: (r: any) => (r.points || []).join(' — ') || '—' },
              { key: 'distance_km', title: 'Плече підвезення', render: (r: any) => r.distance_km ?? '—' },
              { key: 'actions', title: '', render: (r: any) => (
                <div className="flex gap-2 justify-end">
                  <button onClick={() => openDiffChange(r)} className="btn-ghost text-xs">Деталі</button>
                  <button onClick={() => approveChange(r)} className="btn-primary text-xs">Підтвердити</button>
                  <button onClick={() => rejectChange(r)} className="btn-secondary text-xs">Відхилити</button>
                </div>
              ) },
            ]}
            data={pendingChanges}
            emptyText="Немає"
          />
        </div>
      )}

      {loading ? <LoadingSkeleton /> : (
        <DataTable columns={columns} data={filteredSortedApprovedRoutes} emptyText="Маршрутів немає" />
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новий маршрут"
        size="sm"
        footer={
          <>
            <button onClick={() => setCreateOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={create} className="btn-primary" disabled={creating || !form.department_id || !form.name}>
              {creating ? 'Створення...' : 'Створити'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Підрозділ *</label>
            <select className="input-field" value={form.department_id} onChange={e => setForm({ ...form, department_id: e.target.value })}>
              <option value="">Оберіть...</option>
              {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва *</label>
            <input className="input-field" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Плече підвезення *</label>
            <input className="input-field" type="number" step="0.1" value={form.distance_km} onChange={e => setForm({ ...form, distance_km: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Точки маршруту</label>
            <textarea
              className="input-field min-h-[110px]"
              value={form.pointsText}
              onChange={e => setForm({ ...form, pointsText: e.target.value })}
              placeholder="Кожна точка з нового рядка або через тире"
            />
          </div>
        </div>
      </Modal>

      <Modal
        open={diffOpen}
        onClose={() => { setDiffOpen(false); setDiffTarget(null); }}
        title="Зміни маршруту"
        size="sm"
        footer={<button onClick={() => { setDiffOpen(false); setDiffTarget(null); }} className="btn-primary">Закрити</button>}
      >
        {!diffTarget ? (
          <div className="text-sm text-gray-500">Немає даних для порівняння</div>
        ) : diffMode === 'change' && !diffRoute ? (
          <div className="text-sm text-gray-500">Не знайдено поточний маршрут для порівняння</div>
        ) : diffRows.length === 0 ? (
          <div className="text-sm text-gray-500">Заявка не містить змін</div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
              <div>Поле</div>
              <div>Було</div>
              <div>Стало</div>
            </div>
            <div className="space-y-2">
              {diffRows.map((row) => (
                <div key={row.field} className="grid grid-cols-3 gap-2 items-start">
                  <div className="text-sm text-gray-300">{row.field}</div>
                  <div className="text-sm text-gray-500 break-words">{row.oldVal === null || row.oldVal === '' ? '—' : String(row.oldVal)}</div>
                  <div className="text-sm text-accent break-words">{row.newVal === null || row.newVal === '' ? '—' : String(row.newVal)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AdminRoutes;
