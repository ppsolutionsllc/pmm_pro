import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const StockAdjustments: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [reason, setReason] = useState('');
  const [fuelType, setFuelType] = useState('АБ');
  const [deltaLiters, setDeltaLiters] = useState('');
  const [deltaKg, setDeltaKg] = useState('');
  const [requestId, setRequestId] = useState('');
  const [comment, setComment] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data: any = await api.getStockAdjustments();
      setRows(data || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити коригування', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => {
    setReason('');
    setFuelType('АБ');
    setDeltaLiters('');
    setDeltaKg('');
    setRequestId('');
    setComment('');
  };

  const onCreate = async () => {
    if (!reason.trim()) {
      toast('Вкажіть причину коригування', 'warning');
      return;
    }
    const liters = Number(deltaLiters || 0);
    const kg = Number(deltaKg || 0);
    if (!Number.isFinite(liters) || !Number.isFinite(kg) || (Math.abs(liters) < 1e-9 && Math.abs(kg) < 1e-9)) {
      toast('Вкажіть delta літрів або кг', 'warning');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        reason: reason.trim(),
        lines: [
          {
            fuel_type: fuelType,
            delta_liters: liters,
            delta_kg: kg,
            request_id: requestId ? Number(requestId) : null,
            comment: comment.trim() || null,
          },
        ],
      };
      const created: any = await api.createStockAdjustment(payload);
      toast('Коригування створено', 'success');
      setModalOpen(false);
      resetForm();
      await load();
      if (created?.id) {
        navigate(`/admin/stock/adjustments/${created.id}`);
      }
    } catch (e: any) {
      toast(e.message || 'Не вдалося створити коригування', 'error');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'adjustment_doc_no', title: 'Акт' },
    { key: 'reason', title: 'Причина' },
    {
      key: 'created_at',
      title: 'Дата',
      render: (r: any) => (r.created_at ? new Date(r.created_at).toLocaleString('uk-UA') : '—'),
    },
    { key: 'created_by', title: 'Ким створено' },
    {
      key: 'actions',
      title: 'Дії',
      render: (r: any) => (
        <button className="btn-secondary !py-1" onClick={() => navigate(`/admin/stock/adjustments/${r.id}`)}>
          Деталі
        </button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Коригування"
        subtitle="Акти коригування складу"
        actions={
          <button className="btn-primary" onClick={() => setModalOpen(true)}>
            <Plus size={16} /> Нове коригування
          </button>
        }
      />

      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={rows} emptyText="Коригувань немає" />}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Створити акт коригування"
        size="md"
        footer={
          <>
            <button className="btn-secondary" onClick={() => setModalOpen(false)}>Скасувати</button>
            <button className="btn-primary" onClick={onCreate} disabled={saving}>
              {saving ? 'Створення...' : 'Створити'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Причина</label>
            <textarea className="input-field" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Тип пального</label>
              <select className="input-field" value={fuelType} onChange={(e) => setFuelType(e.target.value)}>
                <option value="АБ">АБ</option>
                <option value="ДП">ДП</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Request ID (опц.)</label>
              <input className="input-field" type="number" value={requestId} onChange={(e) => setRequestId(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Δ Літри</label>
              <input className="input-field" type="number" step="0.000001" value={deltaLiters} onChange={(e) => setDeltaLiters(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Δ Кг</label>
              <input className="input-field" type="number" step="0.01" value={deltaKg} onChange={(e) => setDeltaKg(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Коментар рядка</label>
            <input className="input-field" value={comment} onChange={(e) => setComment(e.target.value)} />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default StockAdjustments;
