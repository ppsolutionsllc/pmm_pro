import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { api } from '../../api';
import { Search } from 'lucide-react';

const statuses = [
  { value: '', label: 'Всі' },
  { value: 'DRAFT', label: 'Чернетка' },
  { value: 'SUBMITTED', label: 'Подано' },
  { value: 'APPROVED', label: 'Затверджено' },
  { value: 'ISSUED_BY_OPERATOR', label: 'Видано' },
  { value: 'POSTED', label: 'Проведено' },
];

const RequestsList: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [deptFilter, setDeptFilter] = useState('');
  const [search, setSearch] = useState('');

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({ department_id: '', route_text: '', distance_km_per_trip: '', persons_involved_count: '0', training_days_count: '0', justification_text: '' });

  const load = () => {
    setLoading(true);
    const params: any = {};
    if (statusFilter) params.status = statusFilter;
    if (deptFilter) params.department_id = Number(deptFilter);
    if (search) params.search = search;
    Promise.all([api.getRequests(params), api.getDepartments()])
      .then(([r, d]) => { setRequests(r); setDepartments(d); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter, deptFilter]);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, [statusFilter, deptFilter, search]);

  const deptName = (id: number) => departments.find((d: any) => d.id === id)?.name || `#${id}`;

  const columns = [
    { key: 'request_number', title: '№ Заявки', render: (r: any) => <span className="font-medium text-gray-200">{r.request_number}</span> },
    { key: 'department_id', title: 'Підрозділ', render: (r: any) => deptName(r.department_id) },
    { key: 'route_warn', title: 'Маршрут', render: (r: any) => (
      r.route_is_manual ? <span className="text-xs text-warn">Ручний</span> : <span className="text-xs text-gray-500">—</span>
    ) },
    { key: 'status', title: 'Статус', render: (r: any) => <StatusBadge status={r.status} isRejected={!!r.is_rejected} /> },
    { key: 'created_at', title: 'Створено', render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—' },
  ];

  return (
    <div>
      <PageHeader
        title="Заявки"
        subtitle="Перелік усіх заявок"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button onClick={() => navigate('/admin/settings/requests')} className="btn-secondary">Налаштування заявок</button>
            <button onClick={() => setCreateOpen(true)} className="btn-primary">Створити заявку</button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <select className="input-field w-auto" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          {statuses.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select className="input-field w-auto" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
          <option value="">Всі підрозділи</option>
          {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input-field pl-9"
            placeholder="Пошук по номеру..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
          />
        </div>
        <button onClick={load} className="btn-secondary">Знайти</button>
      </div>

      {loading ? <LoadingSkeleton /> : (
        <DataTable
          columns={columns}
          data={requests}
          onRowClick={(r: any) => navigate(`/admin/requests/${r.id}`)}
          emptyText="Заявок немає"
        />
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Нова заявка (від імені підрозділу)"
        size="sm"
        footer={
          <>
            <button onClick={() => setCreateOpen(false)} className="btn-secondary">Скасувати</button>
            <button
              onClick={async () => {
                setCreating(true);
                try {
                  const r = await api.createRequestAsAdmin({
                    department_id: Number(createForm.department_id),
                    route_text: createForm.route_text || null,
                    distance_km_per_trip: createForm.distance_km_per_trip ? parseFloat(createForm.distance_km_per_trip) : null,
                    persons_involved_count: parseInt(createForm.persons_involved_count),
                    training_days_count: parseInt(createForm.training_days_count),
                    justification_text: createForm.justification_text || null,
                  });
                  setCreateOpen(false);
                  setCreateForm({ department_id: '', route_text: '', distance_km_per_trip: '', persons_involved_count: '0', training_days_count: '0', justification_text: '' });
                  load();
                  navigate(`/admin/requests/${r.id}`);
                } catch (e: any) {
                  alert(e.message || 'Помилка');
                } finally {
                  setCreating(false);
                }
              }}
              className="btn-primary"
              disabled={creating || !createForm.department_id}
            >
              {creating ? 'Створення...' : 'Створити'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Підрозділ *</label>
            <select className="input-field" value={createForm.department_id} onChange={e => setCreateForm({ ...createForm, department_id: e.target.value })}>
              <option value="">Оберіть...</option>
              {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Маршрут</label>
            <input className="input-field" value={createForm.route_text} onChange={e => setCreateForm({ ...createForm, route_text: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Плече підвезення</label>
            <input className="input-field" type="number" value={createForm.distance_km_per_trip} onChange={e => setCreateForm({ ...createForm, distance_km_per_trip: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Кількість о/с, що залучались до навчань (занять) *</label>
            <input className="input-field" type="number" step="1" value={createForm.persons_involved_count} onChange={e => setCreateForm({ ...createForm, persons_involved_count: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Кількість навчальних (робочих) днів *</label>
            <input className="input-field" type="number" step="1" value={createForm.training_days_count} onChange={e => setCreateForm({ ...createForm, training_days_count: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Коментарі</label>
            <textarea className="input-field min-h-[90px]" value={createForm.justification_text} onChange={e => setCreateForm({ ...createForm, justification_text: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default RequestsList;
