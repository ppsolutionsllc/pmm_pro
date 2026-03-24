import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import {
  incidentSeverityLabel,
  incidentTypeLabel,
  jobStatusLabel,
  operationLabel,
  updateOperationLabel,
} from '../../utils/humanLabels';

// we reuse the existing SettingsPWA component for the configuration UI
import SettingsPWA from './SettingsPWA';

const SystemLogs: React.FC = () => {
  const { toast } = useToast();
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const resp: any = await api.getSystemLogs();
      setLogs(resp.logs || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося отримати логи', 'error');
    } finally {
      setLoading(false);
    }
  };

  const onClear = async () => {
    setClearing(true);
    try {
      await api.clearSystemLogs();
      toast('Логи очищено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Помилка при очищенні', 'error');
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Логи помилок</h2>
      {loading ? (
        <LoadingSkeleton type="form" rows={6} />
      ) : (
        <div className="bg-gray-900 text-gray-100 font-mono text-xs p-4 rounded h-64 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-center text-gray-500">Логів немає</p>
          ) : (
            logs.map((line, i) => <div key={i}>{line}</div>)
          )}
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <button
          onClick={async () => {
            try {
              const blob = await api.exportSystemLogs();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'logs.txt';
              a.click();
              URL.revokeObjectURL(url);
            } catch (e: any) {
              toast(e.message || 'Помилка експорту', 'error');
            }
          }}
          className="btn-secondary"
        >
          Експорт
        </button>
        <button onClick={onClear} className="btn-danger" disabled={clearing || loading}>
          {clearing ? 'Очищення...' : 'Очистити'}
        </button>
      </div>
    </div>
  );
};

const SettingsSystem: React.FC = () => {
  return (
    <div className="space-y-8">
      <PageHeader title="Системні налаштування" />

      {/* PWA configuration section */}
      <SettingsPWA />

      {/* logs viewer */}
      <SystemLogs />

      {/* update center */}
      <SystemUpdatePanel />

      {/* incidents */}
      <IncidentsPanel />

      {/* backup / restore */}
      <BackupRestore />

      {/* destructive reset */}
      <SystemResetPanel />
    </div>
  );
};

function SystemUpdatePanel() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [check, setCheck] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [targetVersion, setTargetVersion] = useState('');
  const [withBackup, setWithBackup] = useState(true);
  const [applying, setApplying] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<any>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [cfg, m, ch, lg] = await Promise.all([
        api.getSystemUpdateConfig().catch(() => null),
        api.getSystemUpdateMeta().catch(() => null),
        api.getSystemUpdateCheck().catch(() => null),
        api.getSystemUpdateLogs(20).catch(() => ({ items: [] })),
      ]);
      setConfig(cfg);
      setMeta(m);
      setCheck(ch);
      setLogs(lg?.items || []);
      if (!targetVersion) {
        if (ch?.latest_version) setTargetVersion(ch.latest_version);
        else if (m?.backend_version) setTargetVersion(m.backend_version);
      }
      if (cfg) {
        setWithBackup(Boolean(cfg.default_with_backup ?? true));
      }
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити оновлення', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!activeJobId) return;
    const poll = async () => {
      try {
        const j = await api.getSystemUpdateStatus(activeJobId);
        setActiveJob(j);
        if (j?.job_status === 'SUCCESS') {
          const op = String(j?.update_log?.details_json?.operation || '').toUpperCase();
          toast(op === 'ROLLBACK' ? 'Відкат завершено успішно' : 'Оновлення завершено успішно', 'success');
          setActiveJobId(null);
          await load();
          return;
        }
        if (j?.job_status === 'FAILED') {
          const err = j?.update_log?.error_message || j?.message || 'Оновлення завершилось помилкою';
          toast(err, 'error');
          setActiveJobId(null);
          await load();
        }
      } catch {
        // keep polling
      }
    };
    poll();
    const timer = window.setInterval(poll, 5000);
    return () => window.clearInterval(timer);
  }, [activeJobId, toast]);

  const onApply = async () => {
    setApplying(true);
    try {
      const r: any = await api.applySystemUpdate(targetVersion || undefined, withBackup);
      setActiveJobId(r.job_id);
      toast('Оновлення запущено як фонову задачу', 'success');
    } catch (e: any) {
      toast(e.message || 'Не вдалося запустити оновлення', 'error');
    } finally {
      setApplying(false);
    }
  };

  const onSaveConfig = async () => {
    setSavingConfig(true);
    try {
      const cfg: any = await api.setSystemUpdateConfig({
        default_with_backup: withBackup,
      });
      setConfig(cfg);
      toast('Налаштування оновлень збережено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося зберегти налаштування', 'error');
    } finally {
      setSavingConfig(false);
    }
  };

  const onRollback = async () => {
    const candidate = (logs || []).find(
      (r: any) => r.status === 'SUCCESS' && (r.details_json?.operation || 'UPDATE') === 'UPDATE',
    );
    if (!candidate) {
      toast('Немає успішного оновлення для відкату', 'warning');
      return;
    }
    if (!window.confirm(`Виконати відкат контейнерів для оновлення #${candidate.id}?`)) return;

    setRollingBack(true);
    try {
      const r: any = await api.rollbackSystemUpdateByLogId(candidate.id);
      setActiveJobId(r.job_id);
      toast('Відкат запущено як фонову задачу', 'success');
    } catch (e: any) {
      toast(e.message || 'Не вдалося запустити відкат', 'error');
    } finally {
      setRollingBack(false);
    }
  };

  const steps = (activeJob?.steps || []) as any[];
  const availableVersions = (check?.available_versions || []) as string[];
  const selectedVersion = targetVersion || check?.latest_version || meta?.backend_version || '';
  const rollbackCandidate = (logs || []).find(
    (r: any) => r.status === 'SUCCESS' && (r.details_json?.operation || 'UPDATE') === 'UPDATE',
  );
  const progressPct = Number(activeJob?.progress_pct || 0);
  const statusLabel = activeJob?.job_status || activeJob?.phase || '';

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Оновлення системи</h2>
      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : (
        <div className="space-y-4">
          <div className="card grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-gray-400">Версія backend</div>
              <div>{meta?.backend_version || '—'}</div>
            </div>
            <div>
              <div className="text-gray-400">Версія frontend</div>
              <div>{meta?.frontend_version || '—'}</div>
            </div>
            <div>
              <div className="text-gray-400">Версія схеми БД</div>
              <div>{meta?.db_schema_version || '—'}</div>
            </div>
          </div>

          <div className="card space-y-3">
            <div className="text-sm text-gray-300">
              Репозиторій: <span className="text-gray-200 break-all">{config?.update_repo || '—'}</span>
            </div>
            <div className="text-sm text-gray-300">
              Режим: <span className="text-gray-200">{config?.updater_mode || 'server_build'}</span>
              {' '}• Джерело перевірки: <span className="text-gray-200 break-all">{check?.source || '—'}</span>
            </div>
            <div className="text-sm text-gray-300">
              Актуальна версія: <span className="text-gray-200">{check?.current_version || meta?.backend_version || '—'}</span>
              {' '}→ Остання: <span className="font-semibold text-accent">{check?.latest_version ? `v${check.latest_version}` : '—'}</span>
              {check?.update_available ? (
                <span className="ml-2 text-warn">Доступне оновлення</span>
              ) : (
                <span className="ml-2 text-accent">Оновлень немає</span>
              )}
            </div>
            <div className="flex flex-col md:flex-row gap-2 md:items-center md:flex-wrap">
              <select
                className="input-field md:max-w-xs"
                value={selectedVersion}
                onChange={(e) => setTargetVersion(e.target.value)}
              >
                {availableVersions.length === 0 && <option value="">Немає доступних версій</option>}
                {availableVersions.map((ver) => (
                  <option key={ver} value={ver}>{`v${ver}`}</option>
                ))}
              </select>
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input type="checkbox" checked={withBackup} onChange={(e) => setWithBackup(e.target.checked)} />
                Резервна копія + перевірка перед оновленням
              </label>
              <button className="btn-primary" onClick={onApply} disabled={applying || !!activeJobId}>
                {applying ? 'Запуск...' : 'Застосувати оновлення'}
              </button>
              <button
                className="btn-secondary"
                onClick={onRollback}
                disabled={rollingBack || !!activeJobId || !rollbackCandidate}
              >
                {rollingBack ? 'Запуск відкату...' : 'Відкат контейнерів'}
              </button>
              <button className="btn-secondary" onClick={onSaveConfig} disabled={savingConfig}>
                {savingConfig ? 'Збереження...' : 'Зберегти налаштування'}
              </button>
              <button className="btn-secondary" onClick={load}>Оновити стан</button>
            </div>
            {activeJobId && (
              <div className="space-y-2 text-sm text-gray-400">
                Задача: <span className="text-gray-200">{activeJobId}</span>
                {statusLabel ? ` • ${jobStatusLabel(statusLabel)}` : ''}
                {activeJob?.phase ? ` • ${operationLabel(activeJob.phase)}` : ''}
                {activeJob?.progress_pct !== undefined ? ` • ${activeJob.progress_pct}%` : ''}
                <div className="w-full h-2 bg-mil-800 rounded overflow-hidden">
                  <div className="h-2 bg-accent" style={{ width: `${Math.max(0, Math.min(progressPct, 100))}%` }} />
                </div>
                {activeJob?.message && <div>{activeJob.message}</div>}
              </div>
            )}
            {steps.length > 0 && (
              <div className="space-y-1 text-xs text-gray-300">
                {steps.map((s: any, idx: number) => (
                  <div key={`${s.name}-${idx}`} className="flex items-center justify-between gap-3 bg-mil-800/50 rounded px-2 py-1">
                    <span>{operationLabel(s.step_name || s.name)}</span>
                    <span className={s.status === 'FAILED' ? 'text-danger' : s.status === 'SUCCESS' ? 'text-accent' : 'text-warn'}>
                      {jobStatusLabel(s.status)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card space-y-2">
            <div className="font-medium">Список змін</div>
            {(check?.changelog || []).length > 0 ? (
              <div className="space-y-2">
                {(check.changelog || []).slice(0, 10).map((entry: any) => (
                  <div key={entry.version} className="rounded border border-mil-700 p-2">
                    <div className="text-sm font-semibold">{`v${entry.version}`}{entry.date ? ` • ${entry.date}` : ''}</div>
                    {(entry.notes || []).length > 0 ? (
                      <ul className="text-xs text-gray-300 mt-1 list-disc list-inside">
                        {(entry.notes || []).slice(0, 8).map((note: string, idx: number) => <li key={`${entry.version}-${idx}`}>{note}</li>)}
                      </ul>
                    ) : (
                      <div className="text-xs text-gray-500 mt-1">Нотатки релізу відсутні</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">Немає даних про зміни</div>
            )}
          </div>

          <div className="card">
            <div className="font-medium mb-2">Журнал оновлень</div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-mil-700">
                    <th className="py-2 pr-4">Коли</th>
                    <th className="py-2 pr-4">Операція</th>
                    <th className="py-2 pr-4">З версії</th>
                    <th className="py-2 pr-4">На версію</th>
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Задача</th>
                    <th className="py-2 pr-4">Помилка</th>
                  </tr>
                </thead>
                <tbody>
                  {(logs || []).map((r: any) => (
                    <tr key={r.id} className="border-b border-mil-800">
                      <td className="py-2 pr-4">{r.started_at ? new Date(r.started_at).toLocaleString('uk-UA') : '—'}</td>
                      <td className="py-2 pr-4">{updateOperationLabel(r.details_json?.operation || 'UPDATE')}</td>
                      <td className="py-2 pr-4">{r.from_version || '—'}</td>
                      <td className="py-2 pr-4">{r.to_version || '—'}</td>
                      <td className="py-2 pr-4">{jobStatusLabel(r.status)}</td>
                      <td className="py-2 pr-4">{r.job_id || '—'}</td>
                      <td className="py-2 pr-4 text-danger">{r.error_message || '—'}</td>
                    </tr>
                  ))}
                  {(logs || []).length === 0 && (
                    <tr>
                      <td className="py-2 text-gray-500" colSpan={7}>Записів оновлень ще немає</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



// component for downloading and uploading backup JSON
function BackupRestore() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadingAndRestoring, setUploadingAndRestoring] = useState(false);
  const [backups, setBackups] = useState<any[]>([]);
  const [selectedDump, setSelectedDump] = useState<File | null>(null);
  const [config, setConfig] = useState({
    schedule_enabled: false,
    schedule_interval_hours: 24,
    rotation_keep: 10,
    last_auto_backup_at: '',
    last_auto_backup_file: '',
  });
  const [savingConfig, setSavingConfig] = useState(false);
  const [restoringFile, setRestoringFile] = useState<string | null>(null);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [rows, cfg]: any = await Promise.all([
        api.listDbBackups(),
        api.getDbBackupConfig().catch(() => null),
      ]);
      setBackups(rows || []);
      if (cfg) {
        setConfig({
          schedule_enabled: Boolean(cfg.schedule_enabled),
          schedule_interval_hours: Number(cfg.schedule_interval_hours || 24),
          rotation_keep: Number(cfg.rotation_keep || 10),
          last_auto_backup_at: String(cfg.last_auto_backup_at || ''),
          last_auto_backup_file: String(cfg.last_auto_backup_file || ''),
        });
      }
    } catch {
      setBackups([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <div className="mt-8">
      <h2 className="text-xl font-semibold mb-4">Резервна копія / Відновлення</h2>
      <div className="mb-3 flex gap-2">
        <button
          onClick={async () => {
            setCreating(true);
            try {
              await api.createDbBackup();
              toast('Бекап створено (pg_dump)', 'success');
              await loadAll();
            } catch (e: any) {
              toast(e.message || 'Помилка pg_dump', 'error');
            } finally {
              setCreating(false);
            }
          }}
          className="btn-primary"
          disabled={creating}
        >
          {creating ? 'Створення...' : 'Створити бекап (pg_dump)'}
        </button>
      </div>

      <div className="card mb-4 space-y-3">
        <div className="font-medium">Імпорт дампа</div>
        <div className="text-xs text-gray-500">
          Для повної переустановки: завантажте `.dump` файл і виконайте відновлення.
        </div>
        <input
          type="file"
          accept=".dump,.backup,.bak,application/octet-stream"
          onChange={(e) => setSelectedDump(e.target.files?.[0] || null)}
          className="input-field"
        />
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-secondary"
            disabled={!selectedDump || uploading}
            onClick={async () => {
              if (!selectedDump) return;
              setUploading(true);
              try {
                await api.uploadDbBackup(selectedDump);
                toast('Дамп завантажено', 'success');
                setSelectedDump(null);
                await loadAll();
              } catch (e: any) {
                toast(e.message || 'Помилка завантаження дампа', 'error');
              } finally {
                setUploading(false);
              }
            }}
          >
            {uploading ? 'Завантаження...' : 'Завантажити дамп'}
          </button>
          <button
            className="btn-danger"
            disabled={!selectedDump || uploadingAndRestoring}
            onClick={async () => {
              if (!selectedDump) return;
              const confirmText = window.prompt('Для відновлення введіть RESTORE');
              if ((confirmText || '').trim().toUpperCase() !== 'RESTORE') {
                toast('Відновлення скасовано', 'warning');
                return;
              }
              setUploadingAndRestoring(true);
              try {
                await api.uploadAndRestoreDbBackup(selectedDump, 'RESTORE');
                toast('Дамп завантажено та відновлено. Рекомендується перезайти в систему.', 'success');
                setSelectedDump(null);
                await loadAll();
              } catch (e: any) {
                toast(e.message || 'Помилка відновлення з дампа', 'error');
              } finally {
                setUploadingAndRestoring(false);
              }
            }}
          >
            {uploadingAndRestoring ? 'Відновлення...' : 'Завантажити та відновити'}
          </button>
        </div>
      </div>

      <div className="card mb-4 space-y-3">
        <div className="font-medium">Розклад та ротація</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={config.schedule_enabled}
              onChange={(e) => setConfig((prev) => ({ ...prev, schedule_enabled: e.target.checked }))}
            />
            Автоматичні бекапи
          </label>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Інтервал (години)</label>
            <input
              type="number"
              min={1}
              max={720}
              className="input-field"
              value={config.schedule_interval_hours}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  schedule_interval_hours: Math.max(1, Number(e.target.value || 1)),
                }))
              }
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Зберігати останніх</label>
            <input
              type="number"
              min={1}
              max={1000}
              className="input-field"
              value={config.rotation_keep}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  rotation_keep: Math.max(1, Number(e.target.value || 1)),
                }))
              }
            />
          </div>
        </div>
        <div className="text-xs text-gray-500">
          Останній авто-бекап: {config.last_auto_backup_at ? new Date(config.last_auto_backup_at).toLocaleString('uk-UA') : '—'}
          {config.last_auto_backup_file ? ` (${config.last_auto_backup_file})` : ''}
        </div>
        <div>
          <button
            className="btn-secondary"
            disabled={savingConfig}
            onClick={async () => {
              setSavingConfig(true);
              try {
                const updated: any = await api.setDbBackupConfig({
                  schedule_enabled: config.schedule_enabled,
                  schedule_interval_hours: Number(config.schedule_interval_hours),
                  rotation_keep: Number(config.rotation_keep),
                });
                setConfig((prev) => ({
                  ...prev,
                  schedule_enabled: Boolean(updated.schedule_enabled),
                  schedule_interval_hours: Number(updated.schedule_interval_hours || prev.schedule_interval_hours),
                  rotation_keep: Number(updated.rotation_keep || prev.rotation_keep),
                  last_auto_backup_at: String(updated.last_auto_backup_at || prev.last_auto_backup_at || ''),
                  last_auto_backup_file: String(updated.last_auto_backup_file || prev.last_auto_backup_file || ''),
                }));
                toast('Налаштування бекапів збережено', 'success');
              } catch (e: any) {
                toast(e.message || 'Помилка збереження налаштувань', 'error');
              } finally {
                setSavingConfig(false);
              }
            }}
          >
            {savingConfig ? 'Збереження...' : 'Зберегти розклад'}
          </button>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-mil-700">
              <th className="py-2 pr-4">Файл</th>
              <th className="py-2 pr-4">Розмір</th>
              <th className="py-2 pr-4">Створено</th>
              <th className="py-2 pr-4">Дії</th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b: any) => (
              <tr key={b.filename} className="border-b border-mil-800">
                <td className="py-2 pr-4">{b.filename}</td>
                <td className="py-2 pr-4">{(Number(b.size || 0) / 1024).toFixed(1)} KB</td>
                <td className="py-2 pr-4">{b.created_at ? new Date(b.created_at).toLocaleString('uk-UA') : '—'}</td>
                <td className="py-2 pr-4 flex gap-2">
                  <button
                    className="btn-secondary !py-1"
                    onClick={async () => {
                      try {
                        const r: any = await api.verifyDbBackup(b.filename);
                        toast(r.ok ? 'Бекап валідний' : `Перевірка: ${r.reason || 'помилка'}`, r.ok ? 'success' : 'error');
                      } catch (e: any) {
                        toast(e.message || 'Помилка перевірки', 'error');
                      }
                    }}
                  >
                    Перевірити
                  </button>
                  <button
                    className="btn-secondary !py-1"
                    onClick={async () => {
                      try {
                        const blob = await api.downloadDbBackup(b.filename);
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = b.filename;
                        a.click();
                        URL.revokeObjectURL(url);
                      } catch (e: any) {
                        toast(e.message || 'Помилка завантаження', 'error');
                      }
                    }}
                  >
                    Завантажити
                  </button>
                  <button
                    className="btn-secondary !py-1"
                    disabled={restoringFile === b.filename}
                    onClick={async () => {
                      const confirmText = window.prompt('Для відновлення введіть RESTORE');
                      if ((confirmText || '').trim().toUpperCase() !== 'RESTORE') {
                        toast('Відновлення скасовано', 'warning');
                        return;
                      }
                      setRestoringFile(b.filename);
                      try {
                        await api.restoreDbBackup(b.filename, 'RESTORE');
                        toast('Відновлення завершено. Рекомендується перезайти в систему.', 'success');
                        await loadAll();
                      } catch (e: any) {
                        toast(e.message || 'Помилка відновлення', 'error');
                      } finally {
                        setRestoringFile(null);
                      }
                    }}
                  >
                    {restoringFile === b.filename ? 'Відновлення...' : 'Відновити'}
                  </button>
                  <button
                    className="btn-danger !py-1"
                    disabled={deletingFile === b.filename}
                    onClick={async () => {
                      if (!window.confirm(`Видалити бекап ${b.filename}?`)) return;
                      setDeletingFile(b.filename);
                      try {
                        await api.deleteDbBackup(b.filename);
                        toast('Бекап видалено', 'success');
                        await loadAll();
                      } catch (e: any) {
                        toast(e.message || 'Помилка видалення', 'error');
                      } finally {
                        setDeletingFile(null);
                      }
                    }}
                  >
                    {deletingFile === b.filename ? 'Видалення...' : 'Видалити'}
                  </button>
                </td>
              </tr>
            ))}
            {backups.length === 0 && (
              <tr>
                <td className="py-2 text-gray-500" colSpan={4}>
                  {loading ? 'Завантаження...' : 'Немає pg_dump бекапів'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SystemResetPanel() {
  const { toast } = useToast();
  const [form, setForm] = useState({
    admin_login: '',
    admin_full_name: '',
    admin_password: '',
    admin_password_repeat: '',
    confirm: '',
    create_backup: true,
  });
  const [resetting, setResetting] = useState(false);

  const onReset = async () => {
    if (!form.admin_login.trim()) {
      toast('Вкажіть логін нового адміністратора', 'warning');
      return;
    }
    if (!form.admin_password) {
      toast('Вкажіть пароль нового адміністратора', 'warning');
      return;
    }
    if (form.admin_password.length < 8) {
      toast('Пароль має містити щонайменше 8 символів', 'warning');
      return;
    }
    if (form.admin_password !== form.admin_password_repeat) {
      toast('Паролі не співпадають', 'warning');
      return;
    }
    if (form.confirm.trim().toUpperCase() !== 'RESET') {
      toast('Для скидання введіть RESET', 'warning');
      return;
    }
    if (!window.confirm('Ви дійсно хочете повністю видалити всі дані та перезапустити систему з новим адміністратором?')) {
      return;
    }

    setResetting(true);
    try {
      const result: any = await api.resetSystemData({
        confirm: form.confirm,
        admin_login: form.admin_login.trim(),
        admin_password: form.admin_password,
        admin_full_name: form.admin_full_name.trim() || undefined,
        create_backup: form.create_backup,
      });
      toast(
        result?.backup?.filename
          ? `Систему скинуто. Створено бекап ${result.backup.filename}`
          : 'Систему скинуто',
        'success',
      );
      sessionStorage.removeItem('token');
      window.setTimeout(() => {
        window.location.assign('/login');
      }, 500);
    } catch (e: any) {
      toast(e.message || 'Не вдалося виконати повний скидання', 'error');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="mt-8">
      <h2 className="text-xl font-semibold mb-4 text-danger">Повний скидання системи</h2>
      <div className="card space-y-4 border border-danger/40">
        <div className="text-sm text-gray-300">
          Видаляє всі дані в базі, створює чисту схему та заводить нового адміністратора.
          Для безпечного завершення поточної сесії використайте новий логін, відмінний від поточного.
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Новий логін адміністратора</label>
            <input
              className="input-field"
              value={form.admin_login}
              onChange={(e) => setForm((prev) => ({ ...prev, admin_login: e.target.value }))}
              placeholder="admin_reset"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">ПІБ адміністратора</label>
            <input
              className="input-field"
              value={form.admin_full_name}
              onChange={(e) => setForm((prev) => ({ ...prev, admin_full_name: e.target.value }))}
              placeholder="System Admin"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Новий пароль</label>
            <input
              type="password"
              className="input-field"
              value={form.admin_password}
              onChange={(e) => setForm((prev) => ({ ...prev, admin_password: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Повторіть пароль</label>
            <input
              type="password"
              className="input-field"
              value={form.admin_password_repeat}
              onChange={(e) => setForm((prev) => ({ ...prev, admin_password_repeat: e.target.value }))}
            />
          </div>
        </div>

        <label className="inline-flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={form.create_backup}
            onChange={(e) => setForm((prev) => ({ ...prev, create_backup: e.target.checked }))}
          />
          Створити резервну копію перед скиданням
        </label>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Підтвердження</label>
          <input
            className="input-field md:max-w-xs"
            value={form.confirm}
            onChange={(e) => setForm((prev) => ({ ...prev, confirm: e.target.value }))}
            placeholder="Введіть RESET"
          />
        </div>

        <div className="text-xs text-gray-500">
          Після успішного скидання поточна сесія завершиться, і потрібно буде увійти під новим адміністратором.
        </div>

        <div>
          <button className="btn-danger" disabled={resetting} onClick={onReset}>
            {resetting ? 'Скидання...' : 'Повністю скинути систему'}
          </button>
        </div>
      </div>
    </div>
  );
}

function IncidentsPanel() {
  const { toast } = useToast();
  const [rows, setRows] = useState<any[]>([]);

  const load = async () => {
    try {
      const data: any = await api.getAdminAlerts();
      setRows(data || []);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити інциденти', 'error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Інциденти проведення</h2>
      <div className="space-y-2">
        {(rows || []).slice(0, 30).map((r: any) => (
          <div key={r.id} className="card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm text-gray-300">{incidentTypeLabel(r.type)} / {incidentSeverityLabel(r.severity || 'HIGH')}</div>
                <div className="text-sm text-gray-500">Заявка: {r.request_id || '—'}; Сесія проведення: {r.posting_session_id || '—'}</div>
                <div className="text-sm mt-1">{r.message}</div>
              </div>
              {r.resolved_at ? (
                <span className="text-xs text-accent">Закрито</span>
              ) : (
                <button
                  className="btn-secondary !py-1"
                  onClick={async () => {
                    const comment = prompt('Коментар до закриття інциденту') || '';
                    try {
                      await api.resolveAdminAlert(r.id, comment);
                      await load();
                    } catch (e: any) {
                      toast(e.message || 'Не вдалося закрити інцидент', 'error');
                    }
                  }}
                >
                  Закрити
                </button>
              )}
            </div>
          </div>
        ))}
        {rows.length === 0 && <div className="text-gray-500 text-sm">Інцидентів немає</div>}
      </div>
    </div>
  );
}

export default SettingsSystem;
