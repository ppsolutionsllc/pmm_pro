import React, { useEffect, useMemo, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { useAuth } from '../../auth';
import { Pencil, Plus } from 'lucide-react';

const DeptVehicles: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [pendingChanges, setPendingChanges] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '' });
  const [saving, setSaving] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [editForm, setEditForm] = useState({ brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '' });
  const [editSaving, setEditSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getVehicles(),
      api.listVehicleChangeRequests({ status: 'PENDING' }),
    ]).then(([v, ch]) => {
      setVehicles(v);
      setPendingChanges(ch || []);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const deptVehicles = useMemo(() => vehicles.filter((v: any) => v.department_id === user?.department_id), [vehicles, user?.department_id]);

  const pendingByVehicleId = useMemo(() => {
    const map = new Map<number, any>();
    for (const r of (pendingChanges || [])) {
      if (!map.has(r.vehicle_id)) map.set(r.vehicle_id, r);
    }
    return map;
  }, [pendingChanges]);

  const openEdit = (v: any) => {
    setEditing(v);
    setEditForm({
      brand: v.brand || '',
      identifier: v.identifier || '',
      fuel_type: v.fuel_type || 'АБ',
      consumption_l_per_100km: String(v.consumption_l_per_100km ?? ''),
    });
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editing) return;
    setEditSaving(true);
    try {
      await api.createVehicleChangeRequest(editing.id, {
        brand: editForm.brand,
        identifier: editForm.identifier || null,
        fuel_type: editForm.fuel_type,
        consumption_l_per_100km: parseFloat(editForm.consumption_l_per_100km),
      });
      toast('Зміни відправлено на підтвердження адміністратора', 'success');
      setEditOpen(false);
      setEditing(null);
      load();
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setEditSaving(false);
    }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.createVehicle({
        department_id: user?.department_id,
        brand: form.brand,
        identifier: form.identifier || null,
        fuel_type: form.fuel_type,
        consumption_l_per_100km: parseFloat(form.consumption_l_per_100km),
        is_active: true,
      });
      toast('Транспорт додано. Очікує підтвердження адміністратора', 'success');
      setModalOpen(false);
      setForm({ brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '' });
      load();
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'brand', title: 'Марка', render: (r: any) => <span className="font-medium text-gray-200">{r.brand}</span> },
    { key: 'identifier', title: 'Номер/ID', render: (r: any) => r.identifier || <span className="text-gray-500">—</span> },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'consumption_l_per_100km', title: 'л/100км', render: (r: any) => r.consumption_l_per_100km?.toFixed?.(2) ?? r.consumption_l_per_100km },
    { key: 'consumption_l_per_km', title: 'л/км', render: (r: any) => r.consumption_l_per_km?.toFixed?.(3) ?? r.consumption_l_per_km },
    { key: 'is_approved', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_approved ? 'bg-accent/20 text-accent' : 'bg-warn/20 text-warn'}`}>
        {r.is_approved ? 'Підтверджено' : 'Очікує'}
      </span>
    ) },
    { key: 'change', title: 'Зміни', render: (r: any) => (
      pendingByVehicleId.has(r.id) ? (
        <span className="text-xs text-warn">На підтвердженні</span>
      ) : (
        <span className="text-xs text-gray-500">—</span>
      )
    ) },
    { key: 'is_active', title: 'Активний', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'}`}>
        {r.is_active ? 'Так' : 'Ні'}
      </span>
    ) },
    { key: 'actions', title: '', render: (r: any) => (
      <button
        className="btn-ghost text-xs"
        onClick={(e) => { e.stopPropagation(); openEdit(r); }}
        disabled={pendingByVehicleId.has(r.id)}
        title={pendingByVehicleId.has(r.id) ? 'Є зміни на підтвердженні' : 'Редагувати'}
      >
        <span className="inline-flex items-center gap-1"><Pencil size={14} /> Редагувати</span>
      </button>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Транспорт"
        subtitle="Ваш транспорт (включно з тим, що очікує підтвердження)"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16} /> Додати</button>
          </div>
        }
      />

      {loading ? (
        <LoadingSkeleton />
      ) : (
        <DataTable columns={columns} data={deptVehicles} emptyText="Транспорту немає" />
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Новий транспорт (потрібне підтвердження)"
        size="sm"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleCreate} className="btn-primary" disabled={saving || !form.brand || !form.consumption_l_per_100km}>
              {saving ? 'Збереження...' : 'Додати'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Марка *</label>
            <input className="input-field" value={form.brand} onChange={e => setForm({ ...form, brand: e.target.value })} placeholder="Напр.: Toyota Hilux" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Номер / ідентифікатор</label>
            <input className="input-field" value={form.identifier} onChange={e => setForm({ ...form, identifier: e.target.value })} placeholder="Напр.: АА1234ВК або Борт-12" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Тип палива *</label>
            <select className="input-field" value={form.fuel_type} onChange={e => setForm({ ...form, fuel_type: e.target.value })}>
              <option value="АБ">АБ (Бензин)</option>
              <option value="ДП">ДП (Дизель)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Витрата (л/100км) *</label>
            <input className="input-field" type="number" step="0.01" value={form.consumption_l_per_100km} onChange={e => setForm({ ...form, consumption_l_per_100km: e.target.value })} />
            {!!form.consumption_l_per_100km && (
              <p className="text-xs text-gray-500 mt-1">На 1 км: {(parseFloat(form.consumption_l_per_100km) / 100).toFixed(3)} л/км</p>
            )}
          </div>
        </div>
      </Modal>

      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Редагування транспорту (потрібне підтвердження)"
        size="sm"
        footer={
          <>
            <button onClick={() => setEditOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={submitEdit} className="btn-primary" disabled={editSaving || !editForm.brand || !editForm.consumption_l_per_100km}>
              {editSaving ? 'Надсилання...' : 'Надіслати на підтвердження'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Марка *</label>
            <input className="input-field" value={editForm.brand} onChange={e => setEditForm({ ...editForm, brand: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Номер / ідентифікатор</label>
            <input className="input-field" value={editForm.identifier} onChange={e => setEditForm({ ...editForm, identifier: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Тип палива *</label>
            <select className="input-field" value={editForm.fuel_type} onChange={e => setEditForm({ ...editForm, fuel_type: e.target.value })}>
              <option value="АБ">АБ (Бензин)</option>
              <option value="ДП">ДП (Дизель)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Витрата (л/100км) *</label>
            <input className="input-field" type="number" step="0.01" value={editForm.consumption_l_per_100km} onChange={e => setEditForm({ ...editForm, consumption_l_per_100km: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DeptVehicles;
