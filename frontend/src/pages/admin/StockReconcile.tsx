import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { api } from '../../api';
import { useToast } from '../../components/Toast';
import { formatQuantity, formatSignedQuantity } from '../../utils/quantities';

const StockReconcile: React.FC = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  const loadNow = async () => {
    setLoading(true);
    try {
      const data: any[] = await api.getStockReconcile();
      setRows(data || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося отримати звірку', 'error');
    } finally {
      setLoading(false);
    }
  };

  const pollJob = async (id: string) => {
    for (let i = 0; i < 60; i += 1) {
      const job: any = await api.getJob(id);
      if (job.status === 'SUCCESS') {
        setRunning(false);
        setRows(job.result_json?.rows || []);
        return;
      }
      if (job.status === 'FAILED') {
        setRunning(false);
        toast(job.error_message || 'Помилка виконання звірки', 'error');
        return;
      }
      await new Promise(r => setTimeout(r, 1500));
    }
    setRunning(false);
  };

  const runReconcile = async () => {
    try {
      setRunning(true);
      const created: any = await api.createReconcileJob();
      setJobId(created.job_id);
      await pollJob(created.job_id);
    } catch (e: any) {
      setRunning(false);
      toast(e.message || 'Не вдалося запустити звірку', 'error');
    }
  };

  useEffect(() => {
    loadNow();
  }, []);

  const columns = [
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'receipts_liters', title: 'Прихід (л)', render: (r: any) => formatQuantity(r.receipts_liters) },
    { key: 'issues_liters', title: 'Видача (л)', render: (r: any) => formatQuantity(r.issues_liters) },
    { key: 'adjustments_liters', title: 'Коригування (л)', render: (r: any) => formatSignedQuantity(r.adjustments_liters) },
    { key: 'expected_balance_liters', title: 'Очікувано (л)', render: (r: any) => formatSignedQuantity(r.expected_balance_liters) },
    { key: 'actual_balance_liters', title: 'Факт (л)', render: (r: any) => formatSignedQuantity(r.actual_balance_liters) },
    {
      key: 'difference_liters',
      title: 'Різниця (л)',
      render: (r: any) => (
        <span className={Math.abs(Number(r.difference_liters || 0)) < 0.000001 ? 'text-accent' : 'text-danger'}>
          {formatSignedQuantity(r.difference_liters)}
        </span>
      ),
    },
    {
      key: 'is_consistent',
      title: 'Статус',
      render: (r: any) => (
        <span className={r.is_consistent ? 'text-accent' : 'text-danger'}>
          {r.is_consistent ? 'OK' : 'Розбіжність'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="Перевірка складу" subtitle="One-click звірка: receipts - issues ± adjustments = balance" />
      <div className="mb-4 flex gap-2">
        <button onClick={runReconcile} className="btn-primary" disabled={running}>
          {running ? 'Виконується...' : 'Запустити звірку'}
        </button>
        {jobId && (
          <button
            className="btn-secondary"
            onClick={async () => {
              try {
                const blob = await api.downloadJobArtifact(jobId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `reconcile_${jobId}.xlsx`;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e: any) {
                toast(e.message || 'Артефакт недоступний', 'error');
              }
            }}
          >
            Завантажити звіт
          </button>
        )}
      </div>
      {loading ? <div className="text-gray-400">Завантаження...</div> : <DataTable columns={columns} data={rows} emptyText="Немає даних" />}
    </div>
  );
};

export default StockReconcile;
