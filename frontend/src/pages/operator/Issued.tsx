import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';
import { api } from '../../api';
import { Clock } from 'lucide-react';

const Issued: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);

  const load = () => {
    setLoading(true);
    Promise.all([api.getRequests({ status: 'ISSUED_BY_OPERATOR' }), api.getDepartments()])
      .then(([r, d]) => { setRequests(r); setDepartments(d); })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const t = setInterval(load, 300000);
    return () => clearInterval(t);
  }, []);

  const deptName = (id: number) => departments.find((d: any) => d.id === id)?.name || `Підрозділ #${id}`;

  if (loading) return <LoadingSkeleton type="cards" />;

  return (
    <div>
      <PageHeader
        title="Видано оператором"
        subtitle="Заявки, що очікують підтвердження підрозділу"
        actions={<button onClick={load} className="btn-secondary">Оновити</button>}
      />

      {requests.length === 0 ? (
        <EmptyState title="Немає заявок" message="Всі видані заявки вже підтверджені" icon={<Clock size={48} />} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {requests.map((r: any) => (
            <div key={r.id} className="card">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-gray-200">{r.request_number}</span>
                <StatusBadge status={r.status} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Підрозділ</span>
                  <span className="text-gray-300">{deptName(r.department_id)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Маршрут</span>
                  <span className="text-gray-300 truncate ml-2">{r.route_text || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Видано</span>
                  <span className="text-gray-300">{r.operator_issued_at ? new Date(r.operator_issued_at).toLocaleDateString('uk-UA') : '—'}</span>
                </div>
              </div>
              <div className="mt-4 bg-warn/10 text-warn text-xs rounded-lg px-3 py-2 text-center">
                Очікує підтвердження підрозділу
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Issued;
