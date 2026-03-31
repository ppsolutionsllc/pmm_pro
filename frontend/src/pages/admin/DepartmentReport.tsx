import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { api } from '../../api';
import { useToast } from '../../components/Toast';
import { Printer } from 'lucide-react';
import { formatQuantity } from '../../utils/quantities';

const REQUEST_STATUSES = [
  { value: '', label: 'Усі статуси' },
  { value: 'DRAFT', label: 'Чернетка' },
  { value: 'SUBMITTED', label: 'Подано' },
  { value: 'APPROVED', label: 'Затверджено' },
  { value: 'ISSUED_BY_OPERATOR', label: 'Видано оператором' },
  { value: 'POSTED', label: 'Проведено' },
  { value: 'REJECTED', label: 'Відхилено' },
  { value: 'CANCELED', label: 'Скасовано' },
];

const DepartmentReport: React.FC = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [status, setStatus] = useState('');

  const load = async () => {
    if (dateFrom && dateTo && dateTo < dateFrom) {
      toast('Дата "по" повинна бути не раніше дати "з"', 'warning');
      return;
    }
    setLoading(true);
    try {
      const rep: any = await api.getDepartmentsReport({
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        department_id: departmentId ? Number(departmentId) : undefined,
        status: status || undefined,
      });
      setRows(rep.rows || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити звіт', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.getDepartments()
      .then((list: any[]) => setDepartments(list || []))
      .catch(() => setDepartments([]));
  }, []);

  useEffect(() => {
    load();
  }, []);

  const esc = (value: any) =>
    String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

  const printReport = () => {
    if (!rows.length) {
      toast('Немає даних для друку', 'warning');
      return;
    }
    const periodLabel = dateFrom || dateTo
      ? `${dateFrom || '...'} - ${dateTo || '...'}`
      : 'Увесь період';
    const statusLabel = REQUEST_STATUSES.find((s) => s.value === status)?.label || 'Усі статуси';
    const deptLabel = departmentId
      ? (departments.find((d: any) => Number(d.id) === Number(departmentId))?.name || `#${departmentId}`)
      : 'Усі';

    const bodyRows = rows.map((r: any) => `
      <tr>
        <td>${esc(r.department_name || `#${r.department_id}`)}</td>
        <td>${esc(r.requests_count ?? 0)}</td>
        <td>${esc(r.posted_count ?? 0)}</td>
        <td>${esc(r.debt_requests_count ?? 0)}</td>
        <td>${esc(formatQuantity(r.requested_ab_liters))}</td>
        <td>${esc(formatQuantity(r.requested_dp_liters))}</td>
        <td>${esc(formatQuantity(r.issued_ab_liters))}</td>
        <td>${esc(formatQuantity(r.issued_dp_liters))}</td>
        <td>${esc(formatQuantity(r.debt_ab_liters))}</td>
        <td>${esc(formatQuantity(r.debt_dp_liters))}</td>
      </tr>
    `).join('');

    const html = `
      <!doctype html>
      <html lang="uk">
      <head>
        <meta charset="utf-8" />
        <title>Звіт по підрозділах</title>
        <style>
          @page { size: A4 landscape; margin: 12mm; }
          body { font-family: "Times New Roman", serif; margin: 0; color: #111827; }
          h1 { margin: 0 0 8px; font-size: 20px; }
          .meta { margin: 0 0 14px; color: #4b5563; font-size: 12px; line-height: 1.3; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }
          th, td { border: 1px solid #374151; padding: 6px 8px; text-align: left; white-space: normal; word-break: break-word; overflow-wrap: anywhere; }
          th { background: #f3f4f6; font-weight: 700; }
          .right { text-align: right; }
        </style>
      </head>
      <body>
        <h1>Звіт по підрозділах</h1>
        <p class="meta">
          Період: ${esc(periodLabel)}<br/>
          Підрозділ: ${esc(deptLabel)}<br/>
          Статус: ${esc(statusLabel)}<br/>
          Сформовано: ${esc(new Date().toLocaleString('uk-UA'))}
        </p>
        <table>
          <thead>
            <tr>
              <th>Підрозділ</th>
              <th>Заявок</th>
              <th>Проведено</th>
              <th>З боргом</th>
              <th>Запитано АБ (л)</th>
              <th>Запитано ДП (л)</th>
              <th>Видано АБ (л)</th>
              <th>Видано ДП (л)</th>
              <th>Борг АБ (л)</th>
              <th>Борг ДП (л)</th>
            </tr>
          </thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </body>
      </html>
    `;

    const popup = window.open('', '_blank');
    if (!popup) {
      toast('Дозвольте відкриття нового вікна для друку', 'warning');
      return;
    }
    popup.document.open();
    popup.document.write(html);
    popup.document.close();
    setTimeout(() => {
      if (!popup.closed) {
        popup.focus();
        popup.print();
      }
    }, 80);
  };

  const columns = [
    { key: 'department_name', title: 'Підрозділ' },
    { key: 'requests_count', title: 'Заявок' },
    { key: 'posted_count', title: 'Проведено' },
    { key: 'debt_requests_count', title: 'З боргом' },
    { key: 'requested_ab_liters', title: 'Запитано АБ (л)', render: (r: any) => formatQuantity(r.requested_ab_liters) },
    { key: 'requested_dp_liters', title: 'Запитано ДП (л)', render: (r: any) => formatQuantity(r.requested_dp_liters) },
    { key: 'issued_ab_liters', title: 'Видано АБ (л)', render: (r: any) => formatQuantity(r.issued_ab_liters) },
    { key: 'issued_dp_liters', title: 'Видано ДП (л)', render: (r: any) => formatQuantity(r.issued_dp_liters) },
    { key: 'debt_ab_liters', title: 'Борг АБ (л)', render: (r: any) => formatQuantity(r.debt_ab_liters) },
    { key: 'debt_dp_liters', title: 'Борг ДП (л)', render: (r: any) => formatQuantity(r.debt_dp_liters) },
  ];

  return (
    <div>
      <PageHeader
        title="Звіт по підрозділах"
        subtitle="Зведення заявок та видачі ПММ по підрозділах"
        actions={
          <div className="flex gap-2">
            <button onClick={load} className="btn-secondary" disabled={loading}>
              {loading ? 'Завантаження...' : 'Оновити'}
            </button>
            <button onClick={printReport} className="btn-secondary" disabled={!rows.length}>
              <Printer size={16} /> Друк
            </button>
          </div>
        }
      />

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input-field" />
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input-field" />
          <select className="input-field" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
            <option value="">Усі підрозділи</option>
            {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value)}>
            {REQUEST_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <DataTable columns={columns} data={rows} emptyText="Немає даних" />
    </div>
  );
};

export default DepartmentReport;
