import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus, Trash2 } from 'lucide-react';

const Departments: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ name: '', is_active: true });
  const [saving, setSaving] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingRow, setDeletingRow] = useState<any>(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);

  const load = () => {
    setLoading(true);
    api.getDepartments({ include_deleted: true }).then(setDepartments).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); setForm({ name: '', is_active: true }); setModalOpen(true); };
  const openEdit = (d: any) => { setEditing(d); setForm({ name: d.name, is_active: d.is_active }); setModalOpen(true); };
  const openDelete = (d: any) => {
    setDeletingRow(d);
    setDeleteReason('');
    setDeleteModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        await api.updateDepartment(editing.id, form);
        toast('Підрозділ оновлено', 'success');
      } else {
        await api.createDepartment(form);
        toast('Підрозділ створено', 'success');
      }
      setModalOpen(false);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!deletingRow) return;
    setDeleting(true);
    try {
      await api.deleteDepartment(Number(deletingRow.id), deleteReason);
      toast('Підрозділ позначено як видалений', 'success');
      setDeleteModalOpen(false);
      setDeletingRow(null);
      setDeleteReason('');
      load();
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setDeleting(false);
    }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    {
      key: 'name',
      title: 'Назва',
      render: (r: any) => (
        <div className="space-y-1">
          <div className="font-medium text-gray-200">{r.name}</div>
          {r.is_deleted && (
            <div className="text-xs text-red-400">
              Видалено: {r.deleted_at ? new Date(r.deleted_at).toLocaleString() : '—'}
              {r.deletion_reason ? ` • ${r.deletion_reason}` : ''}
            </div>
          )}
        </div>
      ),
    },
    { key: 'is_active', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_deleted ? 'bg-red-500/20 text-red-300' : r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'}`}>
        {r.is_deleted ? 'Видалений' : r.is_active ? 'Активний' : 'Неактивний'}
      </span>
    )},
    { key: 'actions', title: '', render: (r: any) => (
      <div className="flex items-center gap-2">
        <button
          onClick={(e) => { e.stopPropagation(); openEdit(r); }}
          className="btn-ghost text-xs"
          disabled={Boolean(r.is_deleted)}
        >
          Редагувати
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); openDelete(r); }}
          className="btn-ghost text-xs text-red-400"
          disabled={Boolean(r.is_deleted)}
        >
          <Trash2 size={14} /> Видалити
        </button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader
        title="Підрозділи"
        subtitle="Управління підрозділами"
        actions={<button onClick={openCreate} className="btn-primary"><Plus size={16} /> Додати</button>}
      />

      {loading ? <LoadingSkeleton /> : (
        <DataTable
          columns={columns}
          data={departments}
          onRowClick={(r: any) => navigate(`/admin/departments/${r.id}`)}
          emptyText="Підрозділів немає"
        />
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Редагувати підрозділ' : 'Новий підрозділ'}
        size="sm"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleSave} className="btn-primary" disabled={saving || !form.name}>
              {saving ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Назва</label>
            <input className="input-field" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Назва підрозділу" />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="is_active" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>

      <Modal
        open={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Видалити підрозділ"
        size="sm"
        footer={
          <>
            <button onClick={() => setDeleteModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button
              onClick={handleDelete}
              className="btn-danger"
              disabled={deleting || !deleteReason.trim()}
            >
              {deleting ? 'Видалення...' : 'Підтвердити видалення'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-300">
            Підрозділ буде позначений як видалений. Дані не видаляються з історії.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Причина видалення *</label>
            <textarea
              className="input-field min-h-[90px]"
              value={deleteReason}
              onChange={e => setDeleteReason(e.target.value)}
              placeholder="Вкажіть причину"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Departments;
