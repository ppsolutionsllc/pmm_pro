import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { api } from '../../api';
import { CheckSquare, Clock, CheckCircle, Fuel, CalendarRange } from 'lucide-react';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);
  const [balance, setBalance] = useState<any[]>([]);
  const [ledger, setLedger] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([api.getRequests(), api.getBalance().catch(() => []), api.getLedger().catch(() => [])])
      .then(([reqs, bal, led]) => { setRequests(reqs); setBalance(bal); setLedger(led); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton type="cards" />;

  const approved = requests.filter(r => r.status === 'APPROVED');
  const issued = requests.filter(r => r.status === 'ISSUED_BY_OPERATOR');
  const posted = requests.filter(r => r.status === 'POSTED');
  const balAB = balance.find((b: any) => b.fuel_type === 'АБ');
  const balDP = balance.find((b: any) => b.fuel_type === 'ДП');
  const now = new Date();
  const prevMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth(), 1);
  const prevMonthLabel = prevMonthStart.toLocaleString('uk-UA', { month: 'long', year: 'numeric' });

  const prevMonthUsage = ledger.reduce((acc: { ab: number; dp: number; total: number }, row: any) => {
    const ts = row?.created_at ? new Date(row.created_at) : null;
    if (!ts || Number.isNaN(ts.getTime())) return acc;
    if (ts < prevMonthStart || ts >= prevMonthEnd) return acc;
    if (typeof row?.delta_liters !== 'number' || row.delta_liters >= 0) return acc;
    const used = Math.abs(row.delta_liters);
    if (row.fuel_type === 'АБ') acc.ab += used;
    else if (row.fuel_type === 'ДП') acc.dp += used;
    acc.total += used;
    return acc;
  }, { ab: 0, dp: 0, total: 0 });

  return (
    <div>
      <PageHeader title="Дашборд" subtitle="Огляд системи обліку ПММ" />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <StatCard
          title="Готово до видачі"
          value={approved.length}
          color="green"
          icon={<CheckSquare size={28} />}
          onClick={() => navigate('/admin/requests?status=APPROVED')}
        />
        <StatCard
          title="Видано оператором"
          value={issued.length}
          color="orange"
          icon={<Clock size={28} />}
          onClick={() => navigate('/admin/requests?status=ISSUED_BY_OPERATOR')}
        />
        <StatCard
          title="Проведено"
          value={posted.length}
          color="blue"
          icon={<CheckCircle size={28} />}
        />
        <StatCard
          title="Баланс АБ / ДП"
          value={`${balAB?.balance_liters?.toFixed(1) || 0} / ${balDP?.balance_liters?.toFixed(1) || 0} л`}
          subtitle={`${balAB?.balance_kg?.toFixed(1) || 0} / ${balDP?.balance_kg?.toFixed(1) || 0} кг`}
          color="gray"
          icon={<Fuel size={28} />}
          onClick={() => navigate('/admin/stock/balance')}
        />
        <StatCard
          title="АБ (минулого місяця)"
          value={`${prevMonthUsage.ab.toFixed(1)} л`}
          subtitle={prevMonthLabel}
          color="orange"
          icon={<CalendarRange size={28} />}
          onClick={() => navigate('/admin/stock/ledger')}
        />
        <StatCard
          title="ДП (минулого місяця)"
          value={`${prevMonthUsage.dp.toFixed(1)} л`}
          subtitle={prevMonthLabel}
          color="orange"
          icon={<CalendarRange size={28} />}
          onClick={() => navigate('/admin/stock/ledger')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ready to issue */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            🟩 Готово до видачі (топ 10)
          </h3>
          {approved.length === 0 ? (
            <p className="text-gray-600 text-sm py-4">Немає заявок</p>
          ) : (
            <div className="space-y-2">
              {approved.slice(0, 10).map((r: any) => (
                <div
                  key={r.id}
                  onClick={() => navigate(`/admin/requests/${r.id}`)}
                  className="flex items-center justify-between p-3 rounded-lg bg-mil-800/50 hover:bg-mil-700/50 cursor-pointer transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-gray-200">{r.request_number}</span>
                    <span className="text-xs text-gray-500 ml-2">Підрозділ #{r.department_id}</span>
                  </div>
                  <StatusBadge status={r.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Waiting confirmation */}
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            🟧 Чекають підтвердження (топ 10)
          </h3>
          {issued.length === 0 ? (
            <p className="text-gray-600 text-sm py-4">Немає заявок</p>
          ) : (
            <div className="space-y-2">
              {issued.slice(0, 10).map((r: any) => (
                <div
                  key={r.id}
                  onClick={() => navigate(`/admin/requests/${r.id}`)}
                  className="flex items-center justify-between p-3 rounded-lg bg-mil-800/50 hover:bg-mil-700/50 cursor-pointer transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-gray-200">{r.request_number}</span>
                    <span className="text-xs text-gray-500 ml-2">Підрозділ #{r.department_id}</span>
                  </div>
                  <StatusBadge status={r.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
