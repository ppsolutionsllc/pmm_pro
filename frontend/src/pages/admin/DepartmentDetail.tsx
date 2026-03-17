import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { ArrowLeft, Plus, UserPlus } from 'lucide-react';

const DepartmentDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [dept, setDept] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [signatures, setSignatures] = useState<any>({
    approval_title: 'З розрахунком згоден:',
    approval_position: '',
    approval_name: '',
    agreed_title: 'ПОГОДЖЕНО:',
    agreed_position: '',
    agreed_name: '',
  });
  const [signaturesSaving, setSignaturesSaving] = useState(false);
  const [tab, setTab] = useState<'info' | 'users'>('info');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ login: '', password: '', full_name: '', phone: '', rank: '', position: '', is_active: true });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getDepartment(Number(id)),
      api.getUsers({ department_id: Number(id), role: 'DEPT_USER' }),
      api.getDepartmentPrintSignatures(Number(id)),
    ]).then(([d, u, s]) => {
      setDept(d);
      setUsers(u);
      setSignatures({
        approval_title: s?.approval_title || 'З розрахунком згоден:',
        approval_position: s?.approval_position || '',
        approval_name: s?.approval_name || '',
        agreed_title: s?.agreed_title || 'ПОГОДЖЕНО:',
        agreed_position: s?.agreed_position || '',
        agreed_name: s?.agreed_name || '',
      });
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleAddUser = async () => {
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
        role: 'DEPT_USER',
        department_id: Number(id),
      });
      toast('Користувача створено', 'success');
      setModalOpen(false);
      setForm({ login: '', password: '', full_name: '', phone: '', rank: '', position: '', is_active: true });
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingSkeleton type="form" rows={4} />;
  if (!dept) return <div className="text-gray-500">Підрозділ не знайдено</div>;

  const userCols = [
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

  const saveSignatures = async () => {
    setSignaturesSaving(true);
    try {
      await api.updateDepartmentPrintSignatures(Number(id), signatures);
      toast('Підписантів підрозділу збережено', 'success');
    } catch (e: any) {
      toast(e.message || 'Не вдалося зберегти підписантів', 'error');
    } finally {
      setSignaturesSaving(false);
    }
  };

  return (
    <div>
      <PageHeader
        title={dept.name}
        subtitle={`Підрозділ #${dept.id}`}
        actions={<button onClick={() => navigate(-1)} className="btn-ghost"><ArrowLeft size={16} /> Назад</button>}
      />

      <div className="flex gap-2 mb-6 border-b border-mil-700">
        <button onClick={() => setTab('info')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'info' ? 'border-accent text-accent' : 'border-transparent text-gray-400 hover:text-gray-200'}`}>Дані</button>
        <button onClick={() => setTab('users')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'users' ? 'border-accent text-accent' : 'border-transparent text-gray-400 hover:text-gray-200'}`}>Користувачі ({users.length})</button>
      </div>

      {tab === 'info' && (
        <div className="space-y-5">
          <div className="card max-w-lg">
            <div className="space-y-3">
              <div><p className="text-xs text-gray-500">Назва</p><p className="text-sm text-gray-200">{dept.name}</p></div>
              <div><p className="text-xs text-gray-500">Статус</p><p className="text-sm text-gray-200">{dept.is_deleted ? 'Видалений' : dept.is_active ? 'Активний' : 'Неактивний'}</p></div>
              {dept.is_deleted && (
                <>
                  <div><p className="text-xs text-gray-500">Дата видалення</p><p className="text-sm text-red-300">{dept.deleted_at ? new Date(dept.deleted_at).toLocaleString() : '—'}</p></div>
                  <div><p className="text-xs text-gray-500">Причина</p><p className="text-sm text-red-300">{dept.deletion_reason || '—'}</p></div>
                </>
              )}
            </div>
          </div>

          <div className="card max-w-3xl">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">Підписанти для друку заявки</h3>
            <div className="space-y-3">
              <div>
                <label className="label">З розрахунком згоден (заголовок)</label>
                <input
                  className="input-field"
                  value={signatures.approval_title}
                  onChange={(e) => setSignatures({ ...signatures, approval_title: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="label">З розрахунком згоден — посада</label>
                  <input
                    className="input-field"
                    value={signatures.approval_position}
                    onChange={(e) => setSignatures({ ...signatures, approval_position: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">З розрахунком згоден — ПІБ</label>
                  <input
                    className="input-field"
                    value={signatures.approval_name}
                    onChange={(e) => setSignatures({ ...signatures, approval_name: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="label">ПОГОДЖЕНО (заголовок)</label>
                <input
                  className="input-field"
                  value={signatures.agreed_title}
                  onChange={(e) => setSignatures({ ...signatures, agreed_title: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="label">ПОГОДЖЕНО — посада</label>
                  <input
                    className="input-field"
                    value={signatures.agreed_position}
                    onChange={(e) => setSignatures({ ...signatures, agreed_position: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">ПОГОДЖЕНО — ПІБ</label>
                  <input
                    className="input-field"
                    value={signatures.agreed_name}
                    onChange={(e) => setSignatures({ ...signatures, agreed_name: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <button className="btn-primary" onClick={saveSignatures} disabled={signaturesSaving}>
                  {signaturesSaving ? 'Збереження...' : 'Зберегти підписантів'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'users' && (
        <div>
          <div className="flex justify-end mb-3">
            <button onClick={() => setModalOpen(true)} className="btn-primary" disabled={Boolean(dept.is_deleted)}>
              <UserPlus size={16} /> Додати користувача
            </button>
          </div>
          <DataTable columns={userCols} data={users} emptyText="Користувачів немає" />
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Новий користувач підрозділу"
        size="sm"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleAddUser} className="btn-primary" disabled={saving || !form.login || !form.password}>
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
            <input type="checkbox" id="ua" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            <label htmlFor="ua" className="text-sm text-gray-300">Активний</label>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DepartmentDetail;
