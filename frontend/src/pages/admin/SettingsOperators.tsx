import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Pencil, Plus, Trash2 } from 'lucide-react';

type OperatorForm = {
  login: string;
  password: string;
  full_name: string;
  phone: string;
  rank: string;
  position: string;
  is_active: boolean;
};

const emptyForm = (): OperatorForm => ({
  login: '',
  password: '',
  full_name: '',
  phone: '',
  rank: '',
  position: '',
  is_active: true,
});

const SettingsOperators: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [operators, setOperators] = useState<any[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<OperatorForm>(emptyForm());
  const [creating, setCreating] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [editForm, setEditForm] = useState<OperatorForm>(emptyForm());
  const [savingEdit, setSavingEdit] = useState(false);

  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    api
      .getUsers({ role: 'OPERATOR' })
      .then(setOperators)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await api.createUser({
        login: createForm.login.trim(),
        password: createForm.password,
        full_name: createForm.full_name || null,
        phone: createForm.phone || null,
        rank: createForm.rank || null,
        position: createForm.position || null,
        is_active: createForm.is_active,
        role: 'OPERATOR',
      });
      toast('Оператора створено', 'success');
      setCreateOpen(false);
      setCreateForm(emptyForm());
      load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося створити оператора', 'error');
    } finally {
      setCreating(false);
    }
  };

  const openEdit = (row: any) => {
    setEditing(row);
    setEditForm({
      login: row.login || '',
      password: '',
      full_name: row.full_name || '',
      phone: row.phone || '',
      rank: row.rank || '',
      position: row.position || '',
      is_active: Boolean(row.is_active),
    });
    setEditOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editing) return;
    setSavingEdit(true);
    try {
      const payload: any = {
        login: editForm.login.trim(),
        full_name: editForm.full_name || null,
        phone: editForm.phone || null,
        rank: editForm.rank || null,
        position: editForm.position || null,
        is_active: editForm.is_active,
      };
      if (editForm.password.trim()) payload.password = editForm.password;
      await api.updateUser(editing.id, payload);
      toast('Оператора оновлено', 'success');
      setEditOpen(false);
      setEditing(null);
      setEditForm(emptyForm());
      load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося оновити оператора', 'error');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (row: any) => {
    if (!window.confirm(`Видалити оператора "${row.login}"?`)) return;
    setDeletingId(row.id);
    try {
      await api.deleteUser(row.id);
      toast('Оператора видалено', 'success');
      load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося видалити оператора', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'login', title: 'Логін', render: (r: any) => <span className="font-medium text-gray-200">{r.login}</span> },
    { key: 'full_name', title: "Повне ім'я", render: (r: any) => r.full_name || '—' },
    { key: 'phone', title: 'Телефон', render: (r: any) => r.phone || '—' },
    {
      key: 'is_active',
      title: 'Статус',
      render: (r: any) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
            r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'
          }`}
        >
          {r.is_active ? 'Активний' : 'Неактивний'}
        </span>
      ),
    },
    {
      key: 'actions',
      title: '',
      render: (r: any) => (
        <div className="flex justify-end gap-2">
          <button className="btn-ghost text-xs" onClick={(e) => { e.stopPropagation(); openEdit(r); }}>
            <span className="inline-flex items-center gap-1"><Pencil size={14} /> Редагувати</span>
          </button>
          <button
            className="btn-ghost text-xs text-danger"
            onClick={(e) => { e.stopPropagation(); handleDelete(r); }}
            disabled={deletingId === r.id}
          >
            <span className="inline-flex items-center gap-1"><Trash2 size={14} /> {deletingId === r.id ? 'Видалення...' : 'Видалити'}</span>
          </button>
        </div>
      ),
    },
  ];

  const renderForm = (
    form: OperatorForm,
    setForm: React.Dispatch<React.SetStateAction<OperatorForm>>,
    withPasswordRequired: boolean,
  ) => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">Логін *</label>
        <input className="input-field" value={form.login} onChange={(e) => setForm((prev) => ({ ...prev, login: e.target.value }))} />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">
          Пароль {withPasswordRequired ? '*' : '(залиште порожнім, щоб не змінювати)'}
        </label>
        <input
          className="input-field"
          type="password"
          value={form.password}
          onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">Повне ім'я</label>
        <input className="input-field" value={form.full_name} onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))} />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">Телефон</label>
        <input className="input-field" value={form.phone} onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))} />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">Звання</label>
        <input className="input-field" value={form.rank} onChange={(e) => setForm((prev) => ({ ...prev, rank: e.target.value }))} />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-1">Посада</label>
        <input className="input-field" value={form.position} onChange={(e) => setForm((prev) => ({ ...prev, position: e.target.value }))} />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={withPasswordRequired ? 'operator_create_active' : 'operator_edit_active'}
          checked={form.is_active}
          onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
          className="rounded"
        />
        <label htmlFor={withPasswordRequired ? 'operator_create_active' : 'operator_edit_active'} className="text-sm text-gray-300">Активний</label>
      </div>
    </div>
  );

  return (
    <div>
      <PageHeader
        title="Оператори ПММ"
        subtitle="Управління операторами видачі палива"
        actions={<button onClick={() => setCreateOpen(true)} className="btn-primary"><Plus size={16} /> Додати оператора</button>}
      />
      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={operators} emptyText="Операторів немає" />}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новий оператор"
        size="sm"
        footer={
          <>
            <button onClick={() => setCreateOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleCreate} className="btn-primary" disabled={creating || !createForm.login.trim() || !createForm.password}>
              {creating ? 'Збереження...' : 'Створити'}
            </button>
          </>
        }
      >
        {renderForm(createForm, setCreateForm, true)}
      </Modal>

      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title={editing ? `Редагування оператора: ${editing.login}` : 'Редагування оператора'}
        size="sm"
        footer={
          <>
            <button onClick={() => setEditOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleSaveEdit} className="btn-primary" disabled={savingEdit || !editForm.login.trim()}>
              {savingEdit ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        {renderForm(editForm, setEditForm, false)}
      </Modal>
    </div>
  );
};

export default SettingsOperators;
