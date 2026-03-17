import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { incidentSeverityLabel, incidentStatusLabel, incidentTypeLabel } from '../../utils/humanLabels';

const STATUS_OPTIONS = ['', 'NEW', 'IN_PROGRESS', 'RESOLVED'];
const SEVERITY_OPTIONS = ['', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const TYPE_OPTIONS = ['', 'POSTING_FAILED', 'ADJUSTMENT_FAILED', 'EXPORT_FAILED', 'BACKUP_FAILED', 'RECONCILE_FAILED', 'SYSTEM_UPDATE_FAILED', 'SECURITY_ALERT'];

const severityClass: Record<string, string> = {
  LOW: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  MEDIUM: 'bg-warn/20 text-warn border-warn/30',
  HIGH: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  CRITICAL: 'bg-danger/20 text-danger border-danger/40',
};

const statusClass: Record<string, string> = {
  NEW: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  IN_PROGRESS: 'bg-warn/15 text-warn border-warn/30',
  RESOLVED: 'bg-accent/15 text-accent border-accent/30',
};

const Incidents: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [unresolvedCount, setUnresolvedCount] = useState(0);

  const [status, setStatus] = useState('');
  const [severity, setSeverity] = useState('');
  const [type, setType] = useState('');
  const [q, setQ] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closeComment, setCloseComment] = useState('');
  const [selected, setSelected] = useState<any>(null);
  const [acting, setActing] = useState(false);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  const notifyBadgeRefresh = () => {
    window.dispatchEvent(new CustomEvent('admin-incidents-updated'));
  };

  const load = async () => {
    setLoading(true);
    try {
      const resp: any = await api.getAdminIncidents({
        status: status || undefined,
        severity: severity || undefined,
        type: type || undefined,
        q: q || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        page,
        page_size: pageSize,
      });
      setItems(resp?.items || []);
      setTotal(Number(resp?.total || 0));
      setUnresolvedCount(Number(resp?.unresolved_count || 0));
      notifyBadgeRefresh();
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити інциденти', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, pageSize]);

  const applyFilters = () => {
    setPage(1);
    load();
  };

  const setInProgress = async (row: any) => {
    setActing(true);
    try {
      await api.patchAdminIncident(row.id, { status: 'IN_PROGRESS' });
      toast('Інцидент взято в роботу.', 'success');
      await load();
    } catch (e: any) {
      toast('Не вдалося змінити статус. Спробуйте ще раз.', 'error');
    } finally {
      setActing(false);
    }
  };

  const openResolveModal = (row: any) => {
    setSelected(row);
    setCloseComment('');
    setCloseModalOpen(true);
  };

  const resolveSelected = async () => {
    if (!selected) return;
    if (!closeComment.trim()) {
      toast('Коментар вирішення обовʼязковий', 'warning');
      return;
    }
    setActing(true);
    try {
      await api.patchAdminIncident(selected.id, {
        status: 'RESOLVED',
        resolution_comment: closeComment.trim(),
      });
      toast('Інцидент закрито.', 'success');
      setCloseModalOpen(false);
      setSelected(null);
      setCloseComment('');
      await load();
    } catch (e: any) {
      toast('Не вдалося змінити статус. Спробуйте ще раз.', 'error');
    } finally {
      setActing(false);
    }
  };

  const retryRow = async (row: any) => {
    if (!window.confirm('Повторити операцію?')) return;
    setActing(true);
    try {
      await api.retryAdminIncident(row.id);
      toast('Повторну спробу запущено.', 'success');
      await load();
    } catch (e: any) {
      const msg = (e?.message || '').toLowerCase();
      if (msg.includes('retry not available')) {
        toast('Повтор недоступний для цього типу інциденту.', 'error');
      } else {
        toast(e.message || 'Не вдалося змінити статус. Спробуйте ще раз.', 'error');
      }
    } finally {
      setActing(false);
    }
  };

  const canRetry = (row: any) => ['POSTING_FAILED', 'EXPORT_FAILED', 'RECONCILE_FAILED'].includes(String(row.type || ''));

  const columns = [
    {
      key: 'created_at',
      title: 'Дата/час',
      render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleString('uk-UA') : '—',
    },
    {
      key: 'severity',
      title: 'Рівень',
      render: (r: any) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs ${severityClass[r.severity] || 'bg-mil-800 text-gray-300 border-mil-700'}`}>
          {incidentSeverityLabel(r.severity)}
        </span>
      ),
    },
    { key: 'type', title: 'Тип', render: (r: any) => incidentTypeLabel(r.type) },
    {
      key: 'status',
      title: 'Статус',
      render: (r: any) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs ${statusClass[r.status] || 'bg-mil-800 text-gray-300 border-mil-700'}`}>
          {incidentStatusLabel(r.status)}
        </span>
      ),
    },
    {
      key: 'request_id',
      title: 'Заявка',
      render: (r: any) => r.request_id ? (
        <Link
          to={`/admin/requests/${r.request_id}`}
          className="text-accent hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          #{r.request_id}
        </Link>
      ) : '—',
    },
    {
      key: 'message',
      title: 'Опис',
      render: (r: any) => <span className="line-clamp-2 max-w-[420px]">{r.message}</span>,
    },
    {
      key: 'actions',
      title: 'Дії',
      render: (r: any) => (
        <div className="flex flex-wrap gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button className="btn-secondary !py-1 !px-2 text-xs" onClick={() => navigate(`/admin/incidents/${r.id}`)}>Відкрити</button>
          {r.status === 'NEW' && (
            <button className="btn-secondary !py-1 !px-2 text-xs" disabled={acting} onClick={() => setInProgress(r)}>
              Взяти в роботу
            </button>
          )}
          {r.status !== 'RESOLVED' && (
            <button className="btn-secondary !py-1 !px-2 text-xs" disabled={acting} onClick={() => openResolveModal(r)}>
              Закрити
            </button>
          )}
          <button className="btn-secondary !py-1 !px-2 text-xs" disabled={acting || !canRetry(r)} onClick={() => retryRow(r)}>
            Повторити
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Інциденти"
        subtitle="Критичні збої проведення, експорту, reconcile та системних операцій"
        actions={
          <div className="flex gap-2 items-center">
            <span className="text-xs px-2 py-1 rounded-full bg-danger/20 text-danger border border-danger/40">
              Невирішені: {unresolvedCount}
            </span>
            <button className="btn-secondary" onClick={load}>Оновити</button>
          </div>
        }
      />

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-3">
          <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTIONS.map(v => <option key={v} value={v}>{v ? incidentStatusLabel(v) : 'Статус: усі'}</option>)}
          </select>
          <select className="input-field" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITY_OPTIONS.map(v => <option key={v} value={v}>{v ? incidentSeverityLabel(v) : 'Рівень: усі'}</option>)}
          </select>
          <select className="input-field" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPE_OPTIONS.map(v => <option key={v} value={v}>{v ? incidentTypeLabel(v) : 'Тип: усі'}</option>)}
          </select>
          <input className="input-field" placeholder="Пошук в описі інциденту" value={q} onChange={(e) => setQ(e.target.value)} />
          <input className="input-field" type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <input className="input-field" type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={applyFilters}>Застосувати</button>
          <button
            className="btn-secondary"
            onClick={() => {
              setStatus('');
              setSeverity('');
              setType('');
              setQ('');
              setDateFrom('');
              setDateTo('');
              setPage(1);
              setTimeout(() => load(), 0);
            }}
          >
            Скинути
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400">Завантаження...</div>
      ) : (
        <DataTable columns={columns as any} data={items} emptyText="Немає інцидентів за вибраними фільтрами" />
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-gray-400">Всього: {total}</div>
        <div className="flex items-center gap-2">
          <select className="input-field w-auto" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
            {[10, 20, 50, 100].map(s => <option key={s} value={s}>{s}/стор.</option>)}
          </select>
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>←</button>
          <span className="text-sm text-gray-300">Сторінка {page} / {totalPages}</span>
          <button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>→</button>
        </div>
      </div>

      <Modal
        open={closeModalOpen}
        onClose={() => setCloseModalOpen(false)}
        title="Закрити інцидент"
        size="sm"
        footer={(
          <>
            <button className="btn-secondary" onClick={() => setCloseModalOpen(false)}>Скасувати</button>
            <button className="btn-primary" disabled={acting} onClick={resolveSelected}>Підтвердити</button>
          </>
        )}
      >
        <div className="space-y-2">
          <div className="text-sm text-gray-300">Коментар вирішення</div>
          <textarea
            className="input-field min-h-[120px]"
            value={closeComment}
            onChange={(e) => setCloseComment(e.target.value)}
            placeholder="Опишіть, як вирішено інцидент..."
          />
        </div>
      </Modal>
    </div>
  );
};

export default Incidents;
