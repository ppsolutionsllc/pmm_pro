import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const PdfTemplates: React.FC = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<any[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('Заявка ПММ (Новий шаблон)');
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list: any[] = await api.listPdfTemplates();
      setRows(Array.isArray(list) ? list : []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити шаблони', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createTemplate = async () => {
    if (!name.trim()) {
      toast('Вкажіть назву шаблону', 'warning');
      return;
    }
    setSaving(true);
    try {
      const resp: any = await api.createPdfTemplate({ name: name.trim(), scope: 'REQUEST_FUEL', is_active: true });
      const id = resp?.template?.id;
      toast('Шаблон створено', 'success');
      setCreateOpen(false);
      if (id) navigate(`/admin/settings/pdf-templates/${id}`);
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося створити шаблон', 'error');
    } finally {
      setSaving(false);
    }
  };

  const deleteTemplate = async (row: any) => {
    const accepted = window.confirm(`Видалити шаблон "${row?.name || 'Без назви'}"?`);
    if (!accepted) return;
    setDeletingId(row.id);
    try {
      await api.deletePdfTemplate(row.id);
      toast('Шаблон видалено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося видалити шаблон', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    { key: 'name', title: 'Назва' },
    { key: 'is_active', title: 'Активний', render: (r: any) => (r.is_active ? 'Так' : 'Ні') },
    { key: 'scope', title: 'Область застосування' },
    { key: 'last_published_version', title: 'Опублікована версія', render: (r: any) => (r.last_published_version ? `v${r.last_published_version}` : '—') },
    {
      key: 'actions',
      title: 'Дії',
      render: (r: any) => (
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-secondary"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/admin/settings/pdf-templates/${r.id}`);
            }}
          >
            Відкрити
          </button>
          <button
            type="button"
            className="btn-danger"
            disabled={deletingId === r.id}
            onClick={(e) => {
              e.stopPropagation();
              deleteTemplate(r);
            }}
          >
            {deletingId === r.id ? 'Видалення...' : 'Видалити'}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="PDF шаблони"
        subtitle="Система → Шаблони → PDF шаблони"
        actions={<button className="btn-primary" onClick={() => setCreateOpen(true)}>Створити</button>}
      />

      {loading ? <LoadingSkeleton rows={6} /> : <DataTable columns={columns as any} data={rows} emptyText="Шаблони відсутні" />}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Створити PDF шаблон">
        <div className="space-y-3">
          <div>
            <label className="label">Назва</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setCreateOpen(false)} disabled={saving}>Скасувати</button>
            <button className="btn-primary" onClick={createTemplate} disabled={saving}>{saving ? 'Збереження...' : 'Створити'}</button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default PdfTemplates;
