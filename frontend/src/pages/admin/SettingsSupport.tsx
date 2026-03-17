import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const SettingsSupport: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ enabled: false, label: '', url: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getSupport()
      .then(d => setForm({ enabled: !!d.enabled, label: d.label || '', url: d.url || '' }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.setSupport(form);
      toast('Налаштування підтримки збережено', 'success');
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingSkeleton type="form" rows={3} />;

  return (
    <div>
      <PageHeader title="Підтримка (Signal)" subtitle="Налаштування кнопки підтримки для користувачів" />
      <div className="card max-w-lg space-y-4">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="se"
            checked={form.enabled}
            onChange={e => setForm({ ...form, enabled: e.target.checked })}
            className="rounded"
          />
          <label htmlFor="se" className="text-sm text-gray-300">Увімкнути підтримку</label>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Назва кнопки</label>
          <input className="input-field" value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} placeholder="Наприклад: Написати в Signal" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">URL посилання</label>
          <input className="input-field" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} placeholder="https://signal.me/..." />
        </div>
        <button onClick={save} className="btn-primary" disabled={saving}>
          {saving ? 'Збереження...' : 'Зберегти'}
        </button>
      </div>
    </div>
  );
};

export default SettingsSupport;
