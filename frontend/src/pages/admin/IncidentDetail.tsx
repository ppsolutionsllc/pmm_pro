import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import {
  incidentSeverityLabel,
  incidentStatusLabel,
  incidentTypeLabel,
  jobStatusLabel,
  jobTypeLabel,
  operationLabel,
  requestStatusLabel,
  userActorLabel,
} from '../../utils/humanLabels';

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

const IncidentDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [incident, setIncident] = useState<any>(null);
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closeComment, setCloseComment] = useState('');
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [acting, setActing] = useState(false);

  const canRetry = useMemo(
    () => ['POSTING_FAILED', 'EXPORT_FAILED', 'RECONCILE_FAILED'].includes(String(incident?.type || '')),
    [incident?.type],
  );

  const notifyBadgeRefresh = () => {
    window.dispatchEvent(new CustomEvent('admin-incidents-updated'));
  };

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const row: any = await api.getAdminIncident(id);
      setIncident(row);
      notifyBadgeRefresh();
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити інцидент', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const setInProgress = async () => {
    if (!incident) return;
    setActing(true);
    try {
      await api.patchAdminIncident(incident.id, { status: 'IN_PROGRESS' });
      toast('Інцидент взято в роботу.', 'success');
      await load();
    } catch {
      toast('Не вдалося змінити статус. Спробуйте ще раз.', 'error');
    } finally {
      setActing(false);
    }
  };

  const resolveIncident = async () => {
    if (!incident) return;
    if (!closeComment.trim()) {
      toast('Коментар вирішення обовʼязковий', 'warning');
      return;
    }
    setActing(true);
    try {
      await api.patchAdminIncident(incident.id, { status: 'RESOLVED', resolution_comment: closeComment.trim() });
      toast('Інцидент закрито.', 'success');
      setCloseModalOpen(false);
      setCloseComment('');
      await load();
    } catch {
      toast('Не вдалося змінити статус. Спробуйте ще раз.', 'error');
    } finally {
      setActing(false);
    }
  };

  const retryIncident = async () => {
    if (!incident) return;
    if (!canRetry) {
      toast('Повтор недоступний для цього типу інциденту.', 'error');
      return;
    }
    if (!window.confirm('Повторити операцію?')) return;
    setActing(true);
    try {
      const resp: any = await api.retryAdminIncident(incident.id);
      const ref = resp?.session_id ? `Сесія: ${resp.session_id}` : resp?.job_id ? `Задача: ${resp.job_id}` : '';
      toast(ref ? `Повторну спробу запущено. ${ref}` : 'Повторну спробу запущено.', 'success');
      await load();
    } catch (e: any) {
      if ((e?.message || '').toLowerCase().includes('retry not available')) {
        toast('Повтор недоступний для цього типу інциденту.', 'error');
      } else {
        toast(e.message || 'Не вдалося змінити статус. Спробуйте ще раз.', 'error');
      }
    } finally {
      setActing(false);
    }
  };

  const detailsText = useMemo(
    () => JSON.stringify(incident?.details_json || {}, null, 2),
    [incident?.details_json],
  );

  if (loading) return <div className="text-gray-400">Завантаження...</div>;
  if (!incident) return <div className="text-gray-500">Інцидент не знайдено</div>;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Інцидент ${incident.id}`}
        subtitle={incidentTypeLabel(incident.type)}
        actions={(
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" onClick={() => navigate('/admin/incidents')}>Назад</button>
            {incident.status === 'NEW' && (
              <button className="btn-secondary" disabled={acting} onClick={setInProgress}>Взяти в роботу</button>
            )}
            <button className="btn-secondary" disabled={acting || !canRetry} onClick={retryIncident}>Повторити</button>
            {incident.status !== 'RESOLVED' && (
              <button className="btn-primary" disabled={acting} onClick={() => setCloseModalOpen(true)}>Закрити</button>
            )}
          </div>
        )}
      />

      <div className="card">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500">Тип:</span>
          <span className="text-sm text-gray-200">{incidentTypeLabel(incident.type)}</span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs ${severityClass[incident.severity] || 'bg-mil-800 text-gray-300 border-mil-700'}`}>
            {incidentSeverityLabel(incident.severity)}
          </span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs ${statusClass[incident.status] || 'bg-mil-800 text-gray-300 border-mil-700'}`}>
            {incidentStatusLabel(incident.status)}
          </span>
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Коротко про проблему</h3>
        <div className="text-sm text-gray-200">{incident.message}</div>
        <div className="text-xs text-gray-500">
          Створено: {incident.created_at ? new Date(incident.created_at).toLocaleString('uk-UA') : '—'}
          {` • ${userActorLabel(incident.created_by)}`}
        </div>
        {incident.request_summary && (
          <div className="text-sm text-gray-300">
            Заявка:{' '}
            <Link to={`/admin/requests/${incident.request_summary.id}`} className="text-accent hover:underline">
              {incident.request_summary.request_number}
            </Link>{' '}
            • {incident.request_summary.department_name || `#${incident.request_summary.department_id}`} • {requestStatusLabel(incident.request_summary.status)}
          </div>
        )}
        {incident.resolved_at && (
          <div className="text-xs text-accent">
            Закрито: {new Date(incident.resolved_at).toLocaleString('uk-UA')}
            {incident.resolution_comment ? ` • ${incident.resolution_comment}` : ''}
          </div>
        )}
      </div>

      <div className="card space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Технічні деталі</h3>
          <div className="flex gap-2">
            <button className="btn-secondary !py-1 !px-2 text-xs" onClick={() => setDetailsOpen(v => !v)}>
              {detailsOpen ? 'Згорнути' : 'Розгорнути'}
            </button>
            <button
              className="btn-secondary !py-1 !px-2 text-xs"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(detailsText);
                  toast('Скопійовано', 'success');
                } catch {
                  toast('Не вдалося скопіювати', 'error');
                }
              }}
            >
              Копіювати
            </button>
          </div>
        </div>
        {detailsOpen && (
          <pre className="bg-mil-950/50 border border-mil-700 rounded-xl p-3 text-xs text-gray-300 overflow-x-auto">
            {detailsText}
          </pre>
        )}

        {incident.posting_session_summary && (
          <div className="rounded-xl border border-mil-700 p-3 text-sm">
            <div className="text-gray-400 mb-1">Сесія проведення</div>
            <div className="text-gray-200">Номер: {incident.posting_session_summary.id}</div>
            <div className="text-gray-300 text-xs">Операція: {operationLabel(incident.posting_session_summary.operation)} • Статус: {jobStatusLabel(incident.posting_session_summary.status)}</div>
            {incident.posting_session_summary.error_message && (
              <div className="text-danger text-xs mt-1">{incident.posting_session_summary.error_message}</div>
            )}
          </div>
        )}

        {incident.job_summary && (
          <div className="rounded-xl border border-mil-700 p-3 text-sm">
            <div className="text-gray-400 mb-1">Фонова задача</div>
            <div className="text-gray-200">Номер: {incident.job_summary.id}</div>
            <div className="text-gray-300 text-xs">Тип: {jobTypeLabel(incident.job_summary.type)} • Статус: {jobStatusLabel(incident.job_summary.status)}</div>
            {incident.job_summary.error_message && (
              <div className="text-danger text-xs mt-1">{incident.job_summary.error_message}</div>
            )}
          </div>
        )}
      </div>

      <Modal
        open={closeModalOpen}
        onClose={() => setCloseModalOpen(false)}
        title="Закрити інцидент"
        size="sm"
        footer={(
          <>
            <button className="btn-secondary" onClick={() => setCloseModalOpen(false)}>Скасувати</button>
            <button className="btn-primary" disabled={acting} onClick={resolveIncident}>Підтвердити</button>
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

export default IncidentDetail;
