import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { Printer } from 'lucide-react';
import { api } from '../../api';
import { ledgerRefTypeLabel } from '../../utils/humanLabels';

const StockLedger: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<any[]>([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const load = (period?: { from?: string; to?: string }) => {
    const effectiveFrom = period?.from ?? dateFrom;
    const effectiveTo = period?.to ?? dateTo;
    setLoading(true);
    api.getLedger({
      date_from: effectiveFrom || undefined,
      date_to: effectiveTo || undefined,
    }).then(setLedger).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const formatNum = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '0.00';
    const n = Number(value);
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}`;
  };

  const esc = (value: any) =>
    String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

  const handlePrint = () => {
    if (!ledger.length) {
      toast('Немає записів для друку', 'warning');
      return;
    }

    const rowsHtml = ledger
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
        <title>Журнал руху палива</title>
        <style>
          @page { size: A4 landscape; margin: 12mm; }
          body { font-family: Arial, sans-serif; margin: 0; color: #111827; }
          h1 { margin: 0 0 8px; font-size: 20px; }
          .meta { margin: 0 0 14px; color: #4b5563; font-size: 12px; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; }
          th, td { border: 1px solid #374151; padding: 6px 8px; text-align: left; }
          th { background: #f3f4f6; font-weight: 700; }
          .pos { color: #047857; font-weight: 700; }
          .neg { color: #b91c1c; font-weight: 700; }
        </style>
      </head>
      <body>
        <h1>Журнал руху палива</h1>
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

    const popup = window.open('', '_blank', 'noopener,noreferrer');
    if (!popup) {
      toast('Дозвольте відкриття нового вікна для друку', 'warning');
      return;
    }
    popup.document.open();
    popup.document.write(html);
    popup.document.close();
    popup.focus();
    popup.print();
  };

  const openRelatedDocument = (row: any) => {
    const url = String(row?.ref_doc_url || '').trim();
    if (!url) {
      toast('Повʼязаний документ не знайдено', 'warning');
      return;
    }
    navigate(url);
  };

  const columns = [
    { key: 'id', title: '№' },
    { key: 'fuel_type', title: 'Паливо' },
    { key: 'delta_liters', title: 'Δ Літри', render: (r: any) => <span className={r.delta_liters >= 0 ? 'text-accent' : 'text-danger'}>{r.delta_liters >= 0 ? '+' : ''}{r.delta_liters?.toFixed(2)}</span> },
    { key: 'delta_kg', title: 'Δ Кг', render: (r: any) => <span className={r.delta_kg >= 0 ? 'text-accent' : 'text-danger'}>{r.delta_kg >= 0 ? '+' : ''}{r.delta_kg?.toFixed(2)}</span> },
    { key: 'ref_type', title: 'Операція', render: (r: any) => ledgerRefTypeLabel(r.ref_type) },
    {
      key: 'ref_id',
      title: 'Повʼязаний документ',
      render: (r: any) => (
        r.ref_doc_url ? (
          <button
            type="button"
            className="text-accent hover:underline"
            onClick={() => openRelatedDocument(r)}
          >
            {r.ref_doc_label || `Документ №${r.ref_id}`}
          </button>
        ) : (r.ref_doc_label || '—')
      ),
    },
    { key: 'created_at', title: 'Дата', render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleDateString('uk-UA') : '—' },
  ];

  return (
    <div>
      <PageHeader
        title="Журнал руху палива"
        subtitle="Журнал руху палива"
        actions={
          <div className="flex gap-2">
            <button onClick={() => load()} className="btn-secondary" disabled={loading}>Оновити</button>
            <button onClick={handlePrint} className="btn-secondary" disabled={loading || !ledger.length}>
              <Printer size={16} /> Друк
            </button>
          </div>
        }
      />

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
            onClick={() => {
              if (dateFrom && dateTo && dateTo < dateFrom) {
                toast('Дата "по" повинна бути не раніше дати "з"', 'warning');
                return;
              }
              load();
            }}
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

      {loading ? <LoadingSkeleton /> : <DataTable columns={columns} data={ledger} emptyText="Записів немає" />}
    </div>
  );
};

export default StockLedger;
