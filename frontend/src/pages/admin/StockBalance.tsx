import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { api } from '../../api';
import { Fuel, Droplets } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { formatQuantity, roundUpQuantity } from '../../utils/quantities';

const StockBalance: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState<any[]>([]);

  useEffect(() => {
    api.getBalance()
      .then(setBalance)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton type="cards" />;

  const ab = balance.find((b: any) => b.fuel_type === 'АБ');
  const dp = balance.find((b: any) => b.fuel_type === 'ДП');

  const balanceData = [
    { fuel: 'АБ', liters: roundUpQuantity(ab?.balance_liters), kg: roundUpQuantity(ab?.balance_kg) },
    { fuel: 'ДП', liters: roundUpQuantity(dp?.balance_liters), kg: roundUpQuantity(dp?.balance_kg) },
  ];

  return (
    <div>
      <PageHeader title="Баланс складу" subtitle="Поточні залишки палива" />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl">
        <div className="card border-l-4 border-l-blue-400">
          <div className="flex items-center gap-3 mb-4">
            <Fuel size={24} className="text-blue-400" />
            <h3 className="text-lg font-bold text-gray-200">АБ (Бензин)</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase">Літри</p>
              <p className="text-2xl font-bold text-blue-400">{formatQuantity(ab?.balance_liters)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Кілограми</p>
              <p className="text-2xl font-bold text-blue-400">{formatQuantity(ab?.balance_kg)}</p>
            </div>
          </div>
        </div>

        <div className="card border-l-4 border-l-amber-400">
          <div className="flex items-center gap-3 mb-4">
            <Droplets size={24} className="text-amber-400" />
            <h3 className="text-lg font-bold text-gray-200">ДП (Дизель)</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase">Літри</p>
              <p className="text-2xl font-bold text-amber-400">{formatQuantity(dp?.balance_liters)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Кілограми</p>
              <p className="text-2xl font-bold text-amber-400">{formatQuantity(dp?.balance_kg)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 mt-6">
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Баланс по типу палива
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={balanceData}>
              <XAxis dataKey="fuel" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="liters" stroke="#82ca9d" />
              <Line type="monotone" dataKey="kg" stroke="#8884d8" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default StockBalance;
