import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import ConfirmModal from '../../components/ConfirmModal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus, Trash2, Power } from 'lucide-react';

const Vehicles: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [deptFilter, setDeptFilter] = useState('');
  const [form, setForm] = useState({ department_id: '', brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '', is_active: true });
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toDelete, setToDelete] = useState<any>(null);
  const [pendingChanges, setPendingChanges] = useState<any[]>([]);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffReq, setDiffReq] = useState<any>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.getVehicles(), api.getDepartments(), api.listVehicleChangeRequests({ status: 'PENDING' })])
      .then(([v, d, ch]) => { setVehicles(v); setDepartments(d); setPendingChanges(ch || []); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ department_id: '', brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '', is_active: true });
    setModalOpen(true);
  };

  const openEdit = (v: any) => {
    setEditing(v);
    setForm({
      department_id: String(v.department_id),
      brand: v.brand,
      identifier: v.identifier || '',
      fuel_type: v.fuel_type,
      consumption_l_per_100km: String(v.consumption_l_per_100km),
      is_active: v.is_active,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const data = {
      department_id: Number(form.department_id),
      brand: form.brand,
      identifier: form.identifier || null,
      fuel_type: form.fuel_type,
      consumption_l_per_100km: parseFloat(form.consumption_l_per_100km),
      is_active: form.is_active,
    };
    try {
      if (editing) {
        await api.updateVehicle(editing.id, data);
        toast('Транспорт оновлено', 'success');
      } else {
        await api.createVehicle(data);
        toast('Транспорт створено', 'success');
      }
      setModalOpen(false);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const deptName = (id: number) => departments.find((d: any) => d.id === id)?.name || `#${id}`;
  const filtered = deptFilter ? vehicles.filter((v: any) => v.department_id === Number(deptFilter)) : vehicles;

  const approve = async (v: any) => {
    try {
      await api.approveVehicle(v.id);
      toast('Транспорт підтверджено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const approveChange = async (r: any) => {
    try {
      await api.approveVehicleChangeRequest(r.id);
      toast('Зміни застосовано', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const rejectChange = async (r: any) => {
    try {
      await api.rejectVehicleChangeRequest(r.id);
      toast('Зміни відхилено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const openDiff = (r: any) => {
    setDiffReq(r);
    setDiffOpen(true);
  };

  const diffVehicle = diffReq ? vehicles.find((v: any) => v.id === diffReq.vehicle_id) : null;
  const diffRows = (() => {
    if (!diffReq || !diffVehicle) return [] as Array<{ field: string; oldVal: any; newVal: any }>;
    const rows: Array<{ field: string; oldVal: any; newVal: any }> = [];
    const add = (field: string, oldVal: any, newVal: any) => {
      const o = oldVal ?? null;
      const n = newVal ?? null;
      if (n === null) return; // change request didn't propose a value
      if (String(o ?? '') === String(n ?? '')) return;
      rows.push({ field, oldVal: o, newVal: n });
    };
    add('Марка', diffVehicle.brand, diffReq.brand);
    add('Номер/ID', diffVehicle.identifier, diffReq.identifier);
    add('Паливо', diffVehicle.fuel_type, diffReq.fuel_type);
    add('Витрата (л/100км)', diffVehicle.consumption_l_per_100km, diffReq.consumption_l_per_100km);
    return rows;
  })();

  const toggleActive = async (v: any) => {
    try {
      await api.updateVehicle(v.id, { is_active: !v.is_active });
      toast(v.is_active ? 'Транспорт вимкнено' : 'Транспорт увімкнено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const askDelete = (v: any) => {
    setToDelete(v);
    setDeleteOpen(true);
  };

  const doDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await api.deleteVehicle(toDelete.id);
      toast('Транспорт видалено', 'success');
      setDeleteOpen(false);
      setToDelete(null);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setDeleting(false); }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'brand', title: 'Марка', render: (r: any) => <span className="font-medium text-gray-200">{r.brand}</span> },
    { key: 'identifier', title: 'Номер/ID', render: (r: any) => r.identifier || <span className="text-gray-500">—</span> },
    { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'consumption_l_per_100km', title: 'л/100км', render: (r: any) => r.consumption_l_per_100km?.toFixed(2) },
    { key: 'consumption_l_per_km', title: 'л/км', render: (r: any) => r.consumption_l_per_km?.toFixed(3) },
    { key: 'is_approved', title: 'Підтв.', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_approved ? 'bg-accent/20 text-accent' : 'bg-warn/20 text-warn'}`}>
        {r.is_approved ? 'Так' : 'Очікує'}
      </span>
    )},
    { key: 'is_active', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'}`}>
        {r.is_active ? 'Активний' : 'Неактивний'}
      </span>
    )},
    { key: 'actions', title: '', render: (r: any) => (
      <div className="flex items-center gap-2 justify-end">
        <button
          onClick={(e) => { e.stopPropagation(); toggleActive(r); }}
          className="btn-ghost text-xs"
          title={r.is_active ? 'Вимкнути' : 'Увімкнути'}
        >
          <Power size={14} />
        </button>
        {!r.is_approved && (
          <button onClick={(e) => { e.stopPropagation(); approve(r); }} className="btn-primary text-xs">Підтвердити</button>
        )}
        <button onClick={(e) => { e.stopPropagation(); openEdit(r); }} className="btn-ghost text-xs">Редагувати</button>
        <button onClick={(e) => { e.stopPropagation(); askDelete(r); }} className="btn-danger text-xs" title="Видалити">
          <Trash2 size={14} />
        </button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader
        title="Транспорт"
        subtitle="Управління транспортом підрозділів"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button onClick={openCreate} className="btn-primary"><Plus size={16} /> Додати</button>
          </div>
        }
      />

      {pendingChanges.length > 0 && (
        <div className="card mb-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Зміни на підтвердження ({pendingChanges.length})</h3>
          <DataTable
            columns={[
              { key: 'id', title: 'ID' },
              { key: 'vehicle_id', title: 'Транспорт ID' },
              { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
              { key: 'brand', title: 'Марка' },
              { key: 'identifier', title: 'Номер/ID', render: (r: any) => r.identifier || '—' },
              { key: 'fuel_type', title: 'Паливо' },
              { key: 'consumption_l_per_100km', title: 'л/100км' },
              { key: 'actions', title: '', render: (r: any) => (
                <div className="flex gap-2 justify-end">
                  <button onClick={() => openDiff(r)} className="btn-ghost text-xs">Деталі</button>
                  <button onClick={() => approveChange(r)} className="btn-primary text-xs">Підтвердити</button>
                  <button onClick={() => rejectChange(r)} className="btn-secondary text-xs">Відхилити</button>
                </div>
              ) },
            ]}
            data={pendingChanges}
            emptyText="Немає змін"
          />
        </div>
      )}

      <Modal
        open={diffOpen}
        onClose={() => { setDiffOpen(false); setDiffReq(null); }}
        title="Зміни по транспорту"
        size="sm"
        footer={<button onClick={() => { setDiffOpen(false); setDiffReq(null); }} className="btn-primary">Закрити</button>}
      >
        {!diffReq || !diffVehicle ? (
          <div className="text-sm text-gray-500">Немає даних для порівняння</div>
        ) : diffRows.length === 0 ? (
          <div className="text-sm text-gray-500">Заявка не містить змін</div>
        ) : (
          <div className="space-y-3">
            <div className="text-xs text-gray-500">Транспорт ID: <span className="text-gray-300">{diffReq.vehicle_id}</span></div>
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

      <div className="mb-4">
        <select className="input-field w-auto" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
          <option value="">Всі підрозділи</option>
          {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>

      {loading ? <LoadingSkeleton /> : (
        <DataTable
          columns={columns}
          data={filtered}
          emptyText="Транспорту немає"
        />
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Редагувати транспорт' : 'Новий транспорт'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleSave} className="btn-primary" disabled={saving || !form.brand || !form.department_id || !form.consumption_l_per_100km}>
              {saving ? 'Збереження...' : 'Зберегти'}
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
          <div className="flex items-center gap-2">
            <input type="checkbox" id="va" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="va" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>

      <ConfirmModal
        open={deleteOpen}
        onClose={() => { if (!deleting) setDeleteOpen(false); }}
        onConfirm={doDelete}
        title="Видалити транспорт"
        message={toDelete ? `Видалити транспорт: ${toDelete.brand}?` : 'Видалити транспорт?'}
        confirmText="Видалити"
        confirmClass="btn-danger"
        loading={deleting}
      />
    </div>
  );
};

export default Vehicles;
