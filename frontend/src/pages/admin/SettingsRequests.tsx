import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus, Pencil, Trash2 } from 'lucide-react';

const SettingsRequests: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<any[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', is_active: true });

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', is_active: true });

  const load = () => {
    setLoading(true);
    api.listPlannedActivities({}).then(setRows).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    setCreating(true);
    try {
      await api.createPlannedActivity({ name: createForm.name, is_active: !!createForm.is_active });
      toast('Захід додано', 'success');
      setCreateOpen(false);
      setCreateForm({ name: '', is_active: true });
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setCreating(false); }
  };

  const openEdit = (r: any) => {
    setEditing(r);
    setEditForm({ name: r.name || '', is_active: !!r.is_active });
    setEditOpen(true);
  };

  const saveEdit = async () => {
    if (!editing) return;
    setEditSaving(true);
    try {
      await api.updatePlannedActivity(editing.id, { name: editForm.name, is_active: !!editForm.is_active });
      toast('Збережено', 'success');
      setEditOpen(false);
      setEditing(null);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setEditSaving(false); }
  };

  const del = async (r: any) => {
    if (!confirm('Видалити захід?')) return;
    try {
      await api.deletePlannedActivity(r.id);
      toast('Видалено', 'success');
      load();
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'name', title: 'Назва', render: (r: any) => <span className="font-medium text-gray-200">{r.name}</span> },
    { key: 'is_active', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'}`}>
        {r.is_active ? 'Активний' : 'Неактивний'}
      </span>
    ) },
    { key: 'actions', title: '', render: (r: any) => (
      <div className="flex justify-end gap-2">
        <button className="btn-ghost text-xs" onClick={(e) => { e.stopPropagation(); openEdit(r); }}>
          <span className="inline-flex items-center gap-1"><Pencil size={14} /> Редагувати</span>
        </button>
        <button className="btn-ghost text-xs text-danger" onClick={(e) => { e.stopPropagation(); del(r); }}>
          <span className="inline-flex items-center gap-1"><Trash2 size={14} /> Видалити</span>
        </button>
      </div>
    ) },
  ];

  return (
    <div>
      <PageHeader
        title="Заявки"
        subtitle="Налаштування запланованих заходів"
        actions={<button onClick={() => setCreateOpen(true)} className="btn-primary"><Plus size={16} /> Додати захід</button>}
      />

      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={rows} emptyText="Заходів немає" />}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новий захід"
        size="sm"
        footer={
          <>
            <button onClick={() => setCreateOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={create} className="btn-primary" disabled={creating || !createForm.name}>
              {creating ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва *</label>
            <input className="input-field" value={createForm.name} onChange={e => setCreateForm({ ...createForm, name: e.target.value })} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="pa" checked={createForm.is_active} onChange={e => setCreateForm({ ...createForm, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="pa" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>

      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Редагування заходу"
        size="sm"
        footer={
          <>
            <button onClick={() => setEditOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={saveEdit} className="btn-primary" disabled={editSaving || !editForm.name}>
              {editSaving ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва *</label>
            <input className="input-field" value={editForm.name} onChange={e => setEditForm({ ...editForm, name: e.target.value })} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="pa2" checked={editForm.is_active} onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="pa2" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SettingsRequests;
