import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import ConfirmModal from '../../components/ConfirmModal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Package, CheckCircle } from 'lucide-react';

const ReadyToIssue: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [acting, setActing] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([api.getRequests({ status: 'APPROVED' }), api.getDepartments()])
      .then(([r, d]) => { setRequests(r); setDepartments(d); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const deptName = (id: number) => departments.find((d: any) => d.id === id)?.name || `Підрозділ #${id}`;

  const handleIssue = async () => {
    if (!selected) return;
    setActing(true);
    try {
      await api.issueRequest(selected.id);
      toast('Заявку видано', 'success');
      setConfirmOpen(false);
      setSelected(null);
      load();
    } catch (e: any) { toast(e.message || 'Не вдалося видати заявку', 'error'); }
    finally { setActing(false); }
  };

  if (loading) return <LoadingSkeleton type="cards" />;

  return (
    <div>
      <PageHeader
        title="Готово до видачі"
        subtitle="Затверджені заявки, які готові до видачі палива"
        actions={<button onClick={load} className="btn-secondary">Оновити</button>}
      />

      {requests.length === 0 ? (
        <EmptyState title="Немає заявок" message="Всі затверджені заявки вже видані" icon={<Package size={48} />} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {requests.map((r: any) => (
            <div key={r.id} className="card hover:border-accent/50 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-gray-200">{r.request_number}</span>
                <StatusBadge status={r.status} />
              </div>
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Підрозділ</span>
                  <span className="text-gray-300">{deptName(r.department_id)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Маршрут</span>
                  <span className="text-gray-300 truncate ml-2">{r.route_text || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Створено</span>
                  <span className="text-gray-300">{r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—'}</span>
                </div>
              </div>
              <button
                onClick={() => { setSelected(r); setConfirmOpen(true); }}
                className="btn-primary w-full justify-center"
              >
                <CheckCircle size={16} /> Видано
              </button>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleIssue}
        title="Підтвердити видачу"
        message={`Ви підтверджуєте видачу палива за заявкою ${selected?.request_number}?`}
        confirmText="Видано"
        loading={acting}
      />
    </div>
  );
};

export default ReadyToIssue;
