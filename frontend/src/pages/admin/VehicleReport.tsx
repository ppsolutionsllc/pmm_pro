import React, { useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { api } from '../../api';
import { useToast } from '../../components/Toast';

const VehicleReport: React.FC = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [vehicleId, setVehicleId] = useState('');
  const [route, setRoute] = useState('');
  const [lastJobId, setLastJobId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const rep: any = await api.getVehicleConsumptionReport({
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        vehicle_id: vehicleId ? Number(vehicleId) : undefined,
        route_contains: route || undefined,
      });
      setRows(rep.rows || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити звіт', 'error');
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format: 'XLSX' | 'PDF') => {
    try {
      const created: any = await api.createVehicleReportExportJob(format, {
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        vehicle_id: vehicleId ? Number(vehicleId) : undefined,
        route_contains: route || undefined,
      });
      setLastJobId(created.job_id);
      for (let i = 0; i < 60; i += 1) {
        const job: any = await api.getJob(created.job_id);
        if (job.status === 'SUCCESS') {
          const blob = await api.downloadJobArtifact(created.job_id);
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `vehicle_report_${created.job_id}.${format === 'PDF' ? 'pdf' : 'xlsx'}`;
          a.click();
          URL.revokeObjectURL(url);
          return;
        }
        if (job.status === 'FAILED') {
          throw new Error(job.error_message || 'Помилка експорту');
        }
        await new Promise(r => setTimeout(r, 1200));
      }
      throw new Error('Таймаут очікування export job');
    } catch (e: any) {
      toast(e.message || 'Не вдалося експортувати звіт', 'error');
    }
  };

  const columns = [
    { key: 'period', title: 'Період' },
    { key: 'vehicle_brand', title: 'Транспорт' },
    { key: 'vehicle_identifier', title: 'Номер' },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'route', title: 'Маршрут' },
    { key: 'total_km', title: 'Км' },
    { key: 'requested_liters', title: 'Літри' },
    { key: 'requested_kg', title: 'Кг' },
    { key: 'requests_count', title: 'К-ть заявок' },
  ];

  return (
    <div>
      <PageHeader title="Звіт по транспорту" subtitle="Витрата ПММ по ТЗ/періоду/маршруту" />
      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input" />
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input" />
          <input placeholder="Vehicle ID" value={vehicleId} onChange={e => setVehicleId(e.target.value)} className="input" />
          <input placeholder="Маршрут містить..." value={route} onChange={e => setRoute(e.target.value)} className="input" />
        </div>
        <div className="mt-3 flex gap-2">
          <button onClick={load} className="btn-primary" disabled={loading}>
            {loading ? 'Завантаження...' : 'Показати'}
          </button>
          <button onClick={() => exportReport('XLSX')} className="btn-secondary">Експорт XLSX</button>
          <button onClick={() => exportReport('PDF')} className="btn-secondary">Експорт PDF</button>
          {lastJobId && <span className="text-xs text-gray-500 self-center">Job: {lastJobId}</span>}
        </div>
      </div>
      <DataTable columns={columns} data={rows} emptyText="Немає даних" />
    </div>
  );
};

export default VehicleReport;
