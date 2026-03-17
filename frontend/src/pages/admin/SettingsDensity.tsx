import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const SettingsDensity: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ density_factor_ab: '', density_factor_dp: '' });

  useEffect(() => {
    api.getDensity()
      .then((d: any) => setForm({
        density_factor_ab: String(d.density_factor_ab ?? ''),
        density_factor_dp: String(d.density_factor_dp ?? ''),
      }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.setDensity({
        density_factor_ab: parseFloat(form.density_factor_ab),
        density_factor_dp: parseFloat(form.density_factor_dp),
      });
      toast('Густину збережено', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSkeleton type="form" rows={2} />;

  return (
    <div>
      <PageHeader title="Густина" subtitle="Коефіцієнти перерахунку літрів у кг" />
      <div className="card max-w-lg space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">АБ (кг/л)</label>
          <input
            className="input-field"
            type="number"
            step="0.0001"
            value={form.density_factor_ab}
            onChange={e => setForm({ ...form, density_factor_ab: e.target.value })}
            placeholder="0.0000"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">ДП (кг/л)</label>
          <input
            className="input-field"
            type="number"
            step="0.0001"
            value={form.density_factor_dp}
            onChange={e => setForm({ ...form, density_factor_dp: e.target.value })}
            placeholder="0.0000"
          />
        </div>
        <button onClick={save} className="btn-primary" disabled={saving || !form.density_factor_ab || !form.density_factor_dp}>
          {saving ? 'Збереження...' : 'Зберегти'}
        </button>
      </div>
    </div>
  );
};

export default SettingsDensity;
