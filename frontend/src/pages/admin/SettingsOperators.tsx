import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus } from 'lucide-react';

const SettingsOperators: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [operators, setOperators] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ login: '', password: '', full_name: '', phone: '', rank: '', position: '', is_active: true });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    api.getUsers({ role: 'OPERATOR' }).then(setOperators).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.createUser({
        login: form.login,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone,
        rank: form.rank || null,
        position: form.position || null,
        is_active: form.is_active,
        role: 'OPERATOR',
      });
      toast('Оператора створено', 'success');
      setModalOpen(false);
      setForm({ login: '', password: '', full_name: '', phone: '', rank: '', position: '', is_active: true });
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'login', title: 'Логін', render: (r: any) => <span className="font-medium text-gray-200">{r.login}</span> },
    { key: 'full_name', title: "Повне ім'я" },
    { key: 'phone', title: 'Телефон' },
    { key: 'is_active', title: 'Статус', render: (r: any) => (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? 'bg-accent/20 text-accent' : 'bg-gray-600/30 text-gray-400'}`}>
        {r.is_active ? 'Активний' : 'Неактивний'}
      </span>
    )},
  ];

  return (
    <div>
      <PageHeader
        title="Оператори ПММ"
        subtitle="Управління операторами видачі палива"
        actions={<button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16} /> Додати оператора</button>}
      />
      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={operators} emptyText="Операторів немає" />}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Новий оператор"
        size="sm"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleSave} className="btn-primary" disabled={saving || !form.login || !form.password}>
              {saving ? 'Збереження...' : 'Створити'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Логін *</label>
            <input className="input-field" value={form.login} onChange={e => setForm({ ...form, login: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Пароль *</label>
            <input className="input-field" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Повне ім'я</label>
            <input className="input-field" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Телефон</label>
            <input className="input-field" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Звання</label>
            <input className="input-field" value={form.rank} onChange={e => setForm({ ...form, rank: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Посада</label>
            <input className="input-field" value={form.position} onChange={e => setForm({ ...form, position: e.target.value })} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="oa" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="oa" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default SettingsOperators;
