import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus } from 'lucide-react';

const StockReceipts: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [receipts, setReceipts] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ fuel_type: 'АБ', input_unit: 'L', input_amount: '' });
  const [density, setDensity] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([api.getReceipts(), api.getDensity().catch(() => null)])
      .then(([r, d]) => { setReceipts(r); setDensity(d); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const computed = () => {
    if (!density || !form.input_amount) return { liters: 0, kg: 0 };
    const amount = parseFloat(form.input_amount) || 0;
    const factor = form.fuel_type === 'АБ' ? density.density_factor_ab : density.density_factor_dp;
    if (form.input_unit === 'L') return { liters: amount, kg: +(amount * factor).toFixed(2) };
    return { liters: +(amount / factor).toFixed(2), kg: amount };
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.createReceipt({ fuel_type: form.fuel_type, input_unit: form.input_unit, input_amount: parseFloat(form.input_amount) });
      toast('Прихід додано', 'success');
      setModalOpen(false);
      setForm({ fuel_type: 'АБ', input_unit: 'L', input_amount: '' });
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const columns = [
    { key: 'id', title: 'ID' },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'input_unit', title: 'Одиниця' },
    { key: 'input_amount', title: 'Кількість', render: (r: any) => r.input_amount?.toFixed(2) },
    { key: 'computed_liters', title: 'Літри', render: (r: any) => r.computed_liters?.toFixed(2) },
    { key: 'computed_kg', title: 'Кг', render: (r: any) => r.computed_kg?.toFixed(2) },
    { key: 'created_at', title: 'Дата', render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—' },
  ];

  const c = computed();

  return (
    <div>
      <PageHeader
        title="Прихід ПММ"
        subtitle="Записи про надходження палива"
        actions={<button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16} /> Додати прихід</button>}
      />

      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={receipts} emptyText="Приходів немає" />}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Новий прихід"
        size="sm"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={handleSave} className="btn-primary" disabled={saving || !form.input_amount}>
              {saving ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Тип палива</label>
            <select className="input-field" value={form.fuel_type} onChange={e => setForm({ ...form, fuel_type: e.target.value })}>
              <option value="АБ">АБ (Бензин)</option>
              <option value="ДП">ДП (Дизель)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Одиниця вимірювання</label>
            <select className="input-field" value={form.input_unit} onChange={e => setForm({ ...form, input_unit: e.target.value })}>
              <option value="L">Літри (L)</option>
              <option value="KG">Кілограми (KG)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Кількість</label>
            <input
              className="input-field"
              type="number"
              step="0.01"
              value={form.input_amount}
              onChange={e => setForm({ ...form, input_amount: e.target.value })}
              placeholder="0.00"
            />
          </div>
          {density && form.input_amount && (
            <div className="bg-mil-800 rounded-lg p-3 text-sm">
              <p className="text-gray-400">Розрахунок:</p>
              <p className="text-gray-200">Літри: <strong>{c.liters}</strong></p>
              <p className="text-gray-200">Кілограми: <strong>{c.kg}</strong></p>
            </div>
          )}
          {!density && <p className="text-warn text-sm">⚠ Коефіцієнти густини не налаштовані</p>}
        </div>
      </Modal>
    </div>
  );
};

export default StockReceipts;
