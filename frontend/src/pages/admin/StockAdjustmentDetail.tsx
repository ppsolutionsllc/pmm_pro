import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import DataTable from '../../components/DataTable';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const StockAdjustmentDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [row, setRow] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (!id) return;
        const data: any = await api.getStockAdjustment(Number(id));
        setRow(data);
      } catch (e: any) {
        toast(e.message || 'Не вдалося завантажити коригування', 'error');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const columns = [
    { key: 'id', title: '№ рядка' },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'delta_liters', title: 'Δ Літри', render: (r: any) => Number(r.delta_liters || 0).toFixed(6) },
    { key: 'delta_kg', title: 'Δ Кг', render: (r: any) => Number(r.delta_kg || 0).toFixed(2) },
    { key: 'request_id', title: 'Заявка', render: (r: any) => r.request_id || '—' },
    { key: 'comment', title: 'Коментар', render: (r: any) => r.comment || '—' },
  ];

  return (
    <div>
      <PageHeader
        title={row?.adjustment_doc_no ? `Коригування ${row.adjustment_doc_no}` : 'Деталі коригування'}
        subtitle="Акт коригування складу"
        actions={<button className="btn-secondary" onClick={() => navigate('/admin/stock/adjustments')}>Назад</button>}
      />

      {loading ? (
        <LoadingSkeleton rows={6} />
      ) : !row ? (
        <div className="card text-gray-400">Коригування не знайдено</div>
      ) : (
        <div className="space-y-4">
          <div className="card grid grid-cols-1 md:grid-cols-2 gap-3">
            <div><span className="text-gray-400">Номер:</span> {row.id}</div>
            <div><span className="text-gray-400">Дата:</span> {row.created_at ? new Date(row.created_at).toLocaleString('uk-UA') : '—'}</div>
            <div><span className="text-gray-400">Створив:</span> {row.created_by || 'Система'}</div>
            <div><span className="text-gray-400">Документ:</span> {row.adjustment_doc_no}</div>
            <div className="md:col-span-2"><span className="text-gray-400">Причина:</span> {row.reason}</div>
          </div>
          <DataTable columns={columns} data={row.lines || []} emptyText="Рядків немає" />
        </div>
      )}
    </div>
  );
};

export default StockAdjustmentDetail;
