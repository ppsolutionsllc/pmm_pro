import React, { useEffect, useMemo, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { useAuth } from '../../auth';
import { Plus, Pencil } from 'lucide-react';

const DeptRoutes: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [routes, setRoutes] = useState<any[]>([]);
  const [pendingChanges, setPendingChanges] = useState<any[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', pointsText: '', distance_km: '' });

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [editForm, setEditForm] = useState({ name: '', pointsText: '', distance_km: '' });
  const [editSaving, setEditSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.listRoutes({}),
      api.listRouteChangeRequests({ status: 'PENDING' }),
    ]).then(([r, ch]) => {
      setRoutes(r || []);
      setPendingChanges(ch || []);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const parsePoints = (txt: string) => txt
    .split(/\r?\n|\s*—\s*|\s*-\s*/g)
    .map(s => s.trim())
    .filter(Boolean);

  const create = async () => {
    if (!user?.department_id) return;
    setCreating(true);
    try {
      await api.createRoute({
        department_id: user.department_id,
        name: form.name,
        points: parsePoints(form.pointsText),
        distance_km: parseFloat(form.distance_km),
      });
      toast('Маршрут додано. Очікує підтвердження адміністратора', 'success');
      setCreateOpen(false);
      setForm({ name: '', pointsText: '', distance_km: '' });
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setCreating(false); }
  };

  const pendingByRouteId = useMemo(() => {
    const map = new Map<number, any>();
    for (const r of (pendingChanges || [])) {
      if (!map.has(r.route_id)) map.set(r.route_id, r);
    }
    return map;
  }, [pendingChanges]);

  const openEdit = (r: any) => {
    setEditing(r);
    setEditForm({
      name: r.name || '',
      pointsText: (r.points || []).join('\n'),
      distance_km: String(r.distance_km ?? ''),
    });
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editing) return;
    setEditSaving(true);
    try {
      await api.createRouteChangeRequest(editing.id, {
        name: editForm.name,
        points: parsePoints(editForm.pointsText),
        distance_km: editForm.distance_km ? parseFloat(editForm.distance_km) : null,
      });
      toast('Зміни відправлено на підтвердження адміністратора', 'success');
      setEditOpen(false);
      setEditing(null);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setEditSaving(false); }
  };

  const columns = [
    { key: 'name', title: 'Назва', render: (r: any) => <span className="font-medium text-gray-200">{r.name}</span> },
    { key: 'points', title: 'Точки', render: (r: any) => (r.points || []).join(' — ') || '—' },
    { key: 'distance_km', title: 'Плече підвезення', render: (r: any) => r.distance_km ?? '—' },
    { key: 'is_approved', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_approved ? 'bg-accent/20 text-accent' : 'bg-warn/20 text-warn'}`}>
        {r.is_approved ? 'Підтверджено' : 'Очікує'}
      </span>
    ) },
    { key: 'actions', title: '', render: (r: any) => (
      <button
        className="btn-ghost text-xs"
        onClick={(e) => { e.stopPropagation(); openEdit(r); }}
        disabled={!r.is_approved || pendingByRouteId.has(r.id)}
        title={!r.is_approved ? 'Маршрут не підтверджено' : pendingByRouteId.has(r.id) ? 'Є зміни на підтвердженні' : 'Редагувати'}
      >
        <span className="inline-flex items-center gap-1"><Pencil size={14} /> Редагувати</span>
      </button>
    ) },
  ];

  if (loading) return <LoadingSkeleton />;

  return (
    <div>
      <PageHeader
        title="Маршрути"
        subtitle="Ваші маршрути (для використання потрібне підтвердження адміністратора)"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button onClick={() => setCreateOpen(true)} className="btn-primary"><Plus size={16} /> Додати</button>
          </div>
        }
      />

      <DataTable columns={columns} data={routes} emptyText="Маршрутів немає" />

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новий маршрут (потрібне підтвердження)"
        size="sm"
        footer={
          <>
            <button onClick={() => setCreateOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={create} className="btn-primary" disabled={creating || !form.name}>
              {creating ? 'Додавання...' : 'Додати'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
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
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Редагування маршруту (потрібне підтвердження)"
        size="sm"
        footer={
          <>
            <button onClick={() => setEditOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={submitEdit} className="btn-primary" disabled={editSaving || !editForm.name}>
              {editSaving ? 'Надсилання...' : 'Надіслати на підтвердження'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва *</label>
            <input className="input-field" value={editForm.name} onChange={e => setEditForm({ ...editForm, name: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Плече підвезення *</label>
            <input className="input-field" type="number" step="0.1" value={editForm.distance_km} onChange={e => setEditForm({ ...editForm, distance_km: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Точки маршруту</label>
            <textarea
              className="input-field min-h-[110px]"
              value={editForm.pointsText}
              onChange={e => setEditForm({ ...editForm, pointsText: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DeptRoutes;
