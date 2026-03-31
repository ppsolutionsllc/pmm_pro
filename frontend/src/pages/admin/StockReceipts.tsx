import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { Plus, Printer } from 'lucide-react';
import { ledgerRefTypeLabel } from '../../utils/humanLabels';
import { formatQuantity, formatSignedQuantity, roundUpQuantity } from '../../utils/quantities';

const StockReceipts: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [receipts, setReceipts] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ fuel_type: 'АБ', input_unit: 'L', input_amount: '' });
  const [density, setDensity] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [printing, setPrinting] = useState(false);
  const linkedReceiptId = Number(searchParams.get('receipt_id') || 0) || null;

  const load = (period?: { from?: string; to?: string }) => {
    const effectiveFrom = period?.from ?? dateFrom;
    const effectiveTo = period?.to ?? dateTo;
    setLoading(true);
    const params = {
      date_from: effectiveFrom || undefined,
      date_to: effectiveTo || undefined,
    };
    Promise.all([api.getReceipts(params), api.getDensity().catch(() => null)])
      .then(([r, d]) => { setReceipts(r); setDensity(d); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const computed = () => {
    if (!density || !form.input_amount) return { liters: 0, kg: 0 };
    const amount = parseFloat(form.input_amount) || 0;
    const factor = form.fuel_type === 'АБ' ? density.density_factor_ab : density.density_factor_dp;
    if (form.input_unit === 'L') return { liters: roundUpQuantity(amount), kg: roundUpQuantity(amount * factor) };
    return { liters: roundUpQuantity(amount / factor), kg: roundUpQuantity(amount) };
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

  const formatNum = (value: number | null | undefined) => {
    return formatSignedQuantity(value);
  };

  const esc = (value: any) =>
    String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

  const handlePrintMovement = async () => {
    if (dateFrom && dateTo && dateTo < dateFrom) {
      toast('Дата "по" повинна бути не раніше дати "з"', 'warning');
      return;
    }

    const popup = window.open('', '_blank');
    if (!popup) {
      toast('Дозвольте відкриття нового вікна для друку', 'warning');
      return;
    }
    popup.document.open();
    popup.document.write('<!doctype html><html lang="uk"><head><meta charset="utf-8" /><title>Формування друку</title></head><body style="font-family: Times New Roman, serif; padding: 20px;">Формування звіту...</body></html>');
    popup.document.close();

    setPrinting(true);
    try {
      const rows: any[] = await api.getLedger({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      if (!rows.length) {
        if (!popup.closed) popup.close();
        toast('Немає руху палива за обраний період', 'warning');
        return;
      }

      const rowsHtml = rows
        .map((row) => {
          const createdAt = row.created_at ? new Date(row.created_at).toLocaleString('uk-UA') : '—';
          return `
            <tr>
              <td>${esc(row.id)}</td>
              <td>${esc(row.fuel_type || '—')}</td>
              <td class="${Number(row.delta_liters || 0) < 0 ? 'neg' : 'pos'}">${esc(formatNum(row.delta_liters))}</td>
              <td class="${Number(row.delta_kg || 0) < 0 ? 'neg' : 'pos'}">${esc(formatNum(row.delta_kg))}</td>
              <td>${esc(ledgerRefTypeLabel(row.ref_type))}</td>
              <td>${esc(row.ref_id ?? '—')}</td>
              <td>${esc(createdAt)}</td>
            </tr>
          `;
        })
        .join('');

      const periodLabel = dateFrom || dateTo
        ? `${dateFrom || '...'} - ${dateTo || '...'}`
        : 'Увесь період';

      const html = `
        <!doctype html>
        <html lang="uk">
        <head>
          <meta charset="utf-8" />
          <title>Рух ПММ за період</title>
          <style>
            @page { size: A4 landscape; margin: 12mm; }
            body { font-family: "Times New Roman", serif; margin: 0; color: #111827; }
            h1 { margin: 0 0 8px; font-size: 20px; }
            .meta { margin: 0 0 14px; color: #4b5563; font-size: 12px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th, td { border: 1px solid #374151; padding: 6px 8px; text-align: left; white-space: normal; word-break: break-word; overflow-wrap: anywhere; }
            th { background: #f3f4f6; font-weight: 700; }
            .pos { color: #047857; font-weight: 700; }
            .neg { color: #b91c1c; font-weight: 700; }
          </style>
        </head>
        <body>
          <h1>Рух ПММ за період</h1>
          <p class="meta">Період: ${esc(periodLabel)}<br/>Сформовано: ${esc(new Date().toLocaleString('uk-UA'))}</p>
          <table>
            <thead>
              <tr>
                <th>№</th>
                <th>Паливо</th>
                <th>Δ Літри</th>
                <th>Δ Кг</th>
                <th>Операція</th>
                <th>Повʼязаний документ</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </body>
        </html>
      `;

      popup.document.open();
      popup.document.write(html);
      popup.document.close();
      setTimeout(() => {
        if (!popup.closed) {
          popup.focus();
          popup.print();
        }
      }, 80);
    } catch (e: any) {
      if (!popup.closed) {
        popup.document.open();
        popup.document.write('<!doctype html><html lang="uk"><head><meta charset="utf-8" /><title>Помилка</title></head><body style="font-family: Times New Roman, serif; padding: 20px;">Не вдалося сформувати друк.</body></html>');
        popup.document.close();
      }
      toast(e.message || 'Не вдалося сформувати друк руху', 'error');
    } finally {
      setPrinting(false);
    }
  };

  const columns = [
    {
      key: 'id',
      title: 'ID',
      render: (r: any) => {
        const isLinked = linkedReceiptId !== null && Number(r.id) === linkedReceiptId;
        return isLinked
          ? <span className="font-semibold text-accent">#{r.id} (з журналу)</span>
          : `#${r.id}`;
      },
    },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'input_unit', title: 'Одиниця' },
    { key: 'input_amount', title: 'Кількість', render: (r: any) => formatQuantity(r.input_amount) },
    { key: 'computed_liters', title: 'Літри', render: (r: any) => formatQuantity(r.computed_liters) },
    { key: 'computed_kg', title: 'Кг', render: (r: any) => formatQuantity(r.computed_kg) },
    { key: 'created_at', title: 'Дата', render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—' },
  ];

  const c = computed();

  return (
    <div>
      <PageHeader
        title="Прихід ПММ"
        subtitle="Записи про надходження палива"
        actions={
          <div className="flex gap-2">
            <button onClick={handlePrintMovement} className="btn-secondary" disabled={printing}>
              <Printer size={16} /> {printing ? 'Формування...' : 'Друк руху'}
            </button>
            <button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16} /> Додати прихід</button>
          </div>
        }
      />

      {linkedReceiptId && (
        <div className="mb-4 rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 text-sm text-gray-200">
          Відкрито повʼязаний документ: прихід №{linkedReceiptId}.
        </div>
      )}

      <div className="card mb-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Період</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">З дати</label>
            <input
              type="date"
              className="input-field"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">По дату</label>
            <input
              type="date"
              className="input-field"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <button
            className="btn-secondary"
            onClick={() => load()}
            disabled={loading}
          >
            Застосувати
          </button>
          <button
            className="btn-ghost"
            onClick={() => {
              setDateFrom('');
              setDateTo('');
              load({ from: '', to: '' });
            }}
            disabled={loading}
          >
            Скинути
          </button>
        </div>
      </div>

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
