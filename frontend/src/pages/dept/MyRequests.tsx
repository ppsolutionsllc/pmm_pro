import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';
import { api } from '../../api';
import { Plus, FileText, Trash2 } from 'lucide-react';
import { useToast } from '../../components/Toast';

const statuses = [
  { value: '', label: 'Всі' },
  { value: 'DRAFT', label: 'Чернетка' },
  { value: 'SUBMITTED', label: 'Подано' },
  { value: 'APPROVED', label: 'Затверджено' },
  { value: 'ISSUED_BY_OPERATOR', label: 'Видано' },
  { value: 'POSTED', label: 'Проведено' },
];

const MyRequests: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [lockBannerHidden, setLockBannerHidden] = useState(false);

  const load = () => {
    setLoading(true);
    const params: any = {};
    if (statusFilter) params.status = statusFilter;
    api.getRequests(params).then(setRequests).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, [statusFilter]);

  useEffect(() => {
    try {
      setLockBannerHidden(localStorage.getItem('dept_lock_banner_hidden') === '1');
    } catch (e) {
      setLockBannerHidden(false);
    }
  }, []);

  const hasActiveRequest = (requests || []).some(
    (r: any) => r.status === 'SUBMITTED' || r.status === 'APPROVED' || r.status === 'ISSUED_BY_OPERATOR'
  );

  useEffect(() => {
    if (!hasActiveRequest && lockBannerHidden) {
      setLockBannerHidden(false);
      try {
        localStorage.removeItem('dept_lock_banner_hidden');
      } catch (e) {}
    }
  }, [hasActiveRequest, lockBannerHidden]);

  const deleteDraft = async (requestId: number, requestNumber?: string) => {
    const accepted = window.confirm(`Видалити чернетку ${requestNumber || `#${requestId}`}?`);
    if (!accepted) return;
    try {
      await api.deleteDraftRequest(requestId);
      toast('Чернетку видалено', 'success');
      load();
    } catch (e: any) {
      toast(e?.message || 'Не вдалося видалити чернетку', 'error');
    }
  };

  if (loading) return <LoadingSkeleton type="cards" />;

  return (
    <div>
      <PageHeader
        title="Мої заявки"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary">Оновити</button>
            <button
              onClick={() => navigate('/dept/create')}
              className="btn-primary"
            >
              <Plus size={16} /> Створити заявку
            </button>
          </div>
        }
      />

      {hasActiveRequest && !lockBannerHidden && (
        <div className="mb-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-danger">Є активна заявка підрозділу</div>
              <div className="text-sm text-gray-200">
                Чернетки можна створювати без обмежень, але подати нову заявку не вийде, поки є активна заявка (подана, затверджена або видана оператором).
              </div>
            </div>
            <button
              className="btn-ghost text-danger hover:text-danger/80"
              onClick={() => {
                setLockBannerHidden(true);
                try {
                  localStorage.setItem('dept_lock_banner_hidden', '1');
                } catch (e) {}
              }}
              title="Закрити"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        {statuses.map(s => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${statusFilter === s.value ? 'bg-accent text-mil-950' : 'bg-mil-700 text-gray-400 hover:bg-mil-600'}`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {requests.length === 0 ? (
        <EmptyState
          title="Заявок немає"
          message="Створіть першу заявку на отримання ПММ"
          icon={<FileText size={48} />}
          action={<button onClick={() => navigate('/dept/create')} className="btn-primary"><Plus size={16} /> Створити</button>}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {requests.map((r: any) => (
            <div
              key={r.id}
              onClick={() => navigate(`/dept/requests/${r.id}`)}
              className="card hover:border-accent/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-gray-200">{r.request_number}</span>
                <div className="flex items-center gap-2">
                  {r.status === 'DRAFT' && (
                    <button
                      type="button"
                      className="btn-danger text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteDraft(r.id, r.request_number);
                      }}
                      title="Видалити чернетку"
                    >
                      <Trash2 size={14} />
                      Видалити
                    </button>
                  )}
                  <StatusBadge status={r.status} isRejected={!!r.is_rejected} />
                  {r.has_debt && <span className="text-xs px-2 py-0.5 rounded-full bg-danger/20 text-danger">Заборгованість</span>}
                </div>
              </div>
              <div className="space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Маршрут</span>
                  <span className="text-gray-300 truncate ml-2">{r.route_text || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Плече підвезення</span>
                  <span className="text-gray-300">{r.distance_km_per_trip ? `${r.distance_km_per_trip} км` : '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Створено</span>
                  <span className="text-gray-300">{r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyRequests;
