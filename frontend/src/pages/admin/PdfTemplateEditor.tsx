import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { pdfAlignLabel, pdfFormatLabel } from '../../utils/humanLabels';

function move<T>(arr: T[], from: number, to: number): T[] {
  const copy = [...arr];
  const [v] = copy.splice(from, 1);
  copy.splice(to, 0, v);
  return copy;
}

type BlockKey = 'header' | 'service' | 'table' | 'totals' | 'signatures' | 'footer';

const PdfTemplateEditor: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<any>(null);
  const [versionState, setVersionState] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const [activeBlock, setActiveBlock] = useState<BlockKey>('table');

  const [addOpen, setAddOpen] = useState(false);
  const [newCol, setNewCol] = useState<any>({
    title: 'Нова колонка',
    source: 'request.request_number',
    width: 10,
    align: 'left',
    format: 'text',
    font_size_pt: 11,
    text_style: 'normal',
  });

  const [previewRequestId, setPreviewRequestId] = useState<string>('');
  const [requests, setRequests] = useState<any[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const sources: string[] = detail?.available_sources || [];
  const formats: string[] = detail?.available_formats || ['text', 'number_0', 'number_2', 'date', 'datetime'];
  const textStyleOptions = [
    { value: 'normal', label: 'Звичайний' },
    { value: 'bold', label: 'Жирний' },
    { value: 'italic', label: 'Курсив' },
  ];
  const sourceLabels: Record<string, string> = {
    'request.request_number': 'Номер заявки',
    'request.created_at': 'Створено (дата/час)',
    'request.submitted_at': 'Подано (дата/час)',
    'request.approved_at': 'Затверджено (дата/час)',
    'request.operator_issued_at': 'Видано оператором (дата/час)',
    'request.dept_confirmed_at': 'Підтверджено підрозділом (дата/час)',
    'request.stock_posted_at': 'Проведено складом (дата/час)',
    'request.status': 'Статус заявки',
    'request.route_text': 'Маршрут',
    'request.distance_km_per_trip': 'Плече підвезення (км)',
    'request.justification_text': 'Коментар / обґрунтування',
    'request.period_text': 'Період',
    'request.persons_involved_count': 'Кількість осіб',
    'request.training_days_count': 'Кількість днів',
    'request.coeff_snapshot_ab': 'Коефіцієнт АБ',
    'request.coeff_snapshot_dp': 'Коефіцієнт ДП',
    'request.coeff_snapshot_at': 'Дата фіксації коефіцієнтів',
    'request.has_debt': 'Є заборгованість',
    'department.name': 'Підрозділ',
    'issue.issue_doc_no': 'Номер акта',
    'issue.posted_at': 'Дата проведення акта',
    'system.backend_version': 'Версія backend',
    'system.frontend_version': 'Версія frontend',
    'system.db_schema_version': 'Версія схеми БД',
    'computed.row_no': '№ рядка',
    'computed.need_10_days_ab': 'Потреба 10 діб АБ (л)',
    'computed.need_10_days_dp': 'Потреба 10 діб ДП (л)',
    'computed.total_ab_liters': 'Всього АБ (л)',
    'computed.total_dp_liters': 'Всього ДП (л)',
    'computed.debt_ab_liters': 'Борг АБ (л)',
    'computed.debt_dp_liters': 'Борг ДП (л)',
    'item.planned_activity_name': 'Заплановані заходи',
    'item.vehicle_name': 'Автомобіль',
    'item.vehicle_plate': 'Номерний знак',
    'item.vehicle_fuel_type': 'Тип пального',
    'item.route_text': 'Маршрут (рядок)',
    'item.distance_km_per_trip': 'Плече підвезення (км, рядок)',
    'item.total_km': 'Пробіг (км)',
    'item.required_liters': 'Потреба (л)',
    'item.required_kg': 'Потреба (кг)',
    'item.consumption_l_per_100km': 'Витрата (л/100км)',
    'item.justification_text': 'Примітка (рядок)',
  };
  const sourceOptions = useMemo(
    () => sources.map((s) => ({ value: s, label: sourceLabels[s] || s })),
    [sources],
  );

  const labelForSource = (source: string) => sourceLabels[source] || source;

  const blockItems: Array<{ key: BlockKey; label: string }> = [
    { key: 'header', label: 'Шапка' },
    { key: 'table', label: 'Таблиця' },
    { key: 'totals', label: 'Підсумки' },
    { key: 'signatures', label: 'Підписи' },
    { key: 'footer', label: 'Нижній колонтитул' },
    { key: 'service', label: 'Службова інформація' },
  ];

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getPdfTemplate(id);
      setDetail(data);
      const vs = data?.versions || [];
      const v = vs.find((x: any) => x.status === 'PUBLISHED') || vs[0] || null;
      setVersionState(v ? JSON.parse(JSON.stringify(v)) : null);
    } catch (e: any) {
      toast(e.message || 'Не вдалося завантажити шаблон', 'error');
    } finally {
      setLoading(false);
    }
  };

  const normalizeRequestRows = (payload: any): any[] => {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.items)) return payload.items;
    if (Array.isArray(payload?.data)) return payload.data;
    return [];
  };

  const loadRequests = async () => {
    try {
      const allRaw = await api.getRequests({});
      let rows = normalizeRequestRows(allRaw);
      if (!rows.length) {
        const submittedRaw = await api.getRequests({ status: 'SUBMITTED' });
        rows = normalizeRequestRows(submittedRaw);
      }
      const prepared = rows.filter((r: any) => r && r.id != null).slice(0, 100);
      setRequests(prepared);
      setPreviewRequestId((prev) => {
        if (!prepared.length) return '';
        if (!prev) return String(prepared[0].id);
        const exists = prepared.some((r: any) => String(r.id) === prev);
        return exists ? prev : String(prepared[0].id);
      });
    } catch (e: any) {
      setRequests([]);
      setPreviewRequestId('');
      toast(e?.message || 'Не вдалося завантажити заявки для превʼю', 'error');
    }
  };

  useEffect(() => {
    load();
    loadRequests();
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [id]);

  const save = async () => {
    if (!versionState?.id) return;
    setSaving(true);
    try {
      const payload = {
        name: versionState.name,
        layout_json: versionState.layout_json,
        table_columns_json: versionState.table_columns_json,
        mapping_json: versionState.mapping_json,
        rules_json: versionState.rules_json,
        service_block_json: versionState.service_block_json,
      };
      await api.updatePdfTemplateVersion(versionState.id, payload);
      toast('Форму збережено', 'success');
      await load();
    } catch (e: any) {
      toast(e.message || 'Не вдалося зберегти форму', 'error');
    } finally {
      setSaving(false);
    }
  };

  const patchColumn = (index: number, patch: any) => {
    const cols = [...(versionState?.table_columns_json || [])];
    cols[index] = { ...cols[index], ...patch };
    setVersionState({ ...versionState, table_columns_json: cols });
  };

  const removeColumn = (index: number) => {
    const cols = [...(versionState?.table_columns_json || [])];
    cols.splice(index, 1);
    setVersionState({ ...versionState, table_columns_json: cols });
  };

  const duplicateColumn = (index: number) => {
    const cols = [...(versionState?.table_columns_json || [])];
    const c = cols[index];
    cols.splice(index + 1, 0, { ...c, id: `${c.id}_copy_${Date.now()}` });
    setVersionState({ ...versionState, table_columns_json: cols });
  };

  const addColumn = () => {
    const cols = [...(versionState?.table_columns_json || [])];
    cols.push({
      id: `custom_${Date.now()}`,
      title: newCol.title,
      width: Number(newCol.width || 10),
      align: newCol.align,
      format: newCol.format,
      font_size_pt: Number(newCol.font_size_pt || 11),
      text_style: newCol.text_style || 'normal',
      source: newCol.source,
      visible: true,
      rules: { visibility_rule: 'ALWAYS' },
    });
    setVersionState({ ...versionState, table_columns_json: cols });
    setAddOpen(false);
  };

  const updateServiceFlag = (key: string, value: boolean) => {
    setVersionState({
      ...versionState,
      service_block_json: {
        ...(versionState?.service_block_json || {}),
        [key]: value,
      },
    });
  };

  const updateLayoutNode = (node: string, patch: any) => {
    setVersionState({
      ...versionState,
      layout_json: {
        ...(versionState?.layout_json || {}),
        [node]: {
          ...((versionState?.layout_json || {})[node] || {}),
          ...patch,
        },
      },
    });
  };

  const refreshPreview = async () => {
    const requestIdNum = Number(previewRequestId);
    if (!versionState?.id || !requestIdNum || Number.isNaN(requestIdNum)) {
      toast('Оберіть заявку для превʼю', 'warning');
      return;
    }
    setPreviewLoading(true);
    try {
      const blob = await api.previewPdfTemplateVersion(versionState.id, {
        request_id: requestIdNum,
        name: versionState?.name,
        layout_json: versionState?.layout_json,
        table_columns_json: versionState?.table_columns_json,
        mapping_json: versionState?.mapping_json,
        rules_json: versionState?.rules_json,
        service_block_json: versionState?.service_block_json,
      });
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch (e: any) {
      toast(e.message || 'Не вдалося сформувати превʼю', 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  const downloadPreview = async () => {
    if (!previewUrl) {
      await refreshPreview();
      return;
    }
    window.open(previewUrl, '_blank');
  };

  if (loading) return <LoadingSkeleton rows={8} />;
  if (!detail || !versionState) return <div className="text-gray-400">Шаблон не знайдено</div>;

  return (
    <div className="space-y-5">
      <PageHeader
        title={`Шаблон: ${detail?.template?.name || '—'}`}
        subtitle="Єдина друкована форма"
        actions={
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => navigate('/admin/settings/pdf-templates')}>Назад</button>
            <button className="btn-primary" onClick={save} disabled={saving}>{saving ? 'Збереження...' : 'Зберегти'}</button>
          </div>
        }
      />

      <div className="card">
        <label className="label">Назва форми</label>
        <input
          className="input-field"
          value={versionState?.name || ''}
          onChange={(e) => setVersionState({ ...versionState, name: e.target.value })}
          placeholder="Наприклад: Основна форма друку"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="card xl:col-span-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">Блоки</h3>
          <div className="space-y-2 text-sm">
            {blockItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setActiveBlock(item.key)}
                className={`w-full text-left rounded-lg px-2 py-1 transition ${
                  activeBlock === item.key ? 'text-accent font-semibold bg-mil-800/60' : 'text-gray-300 hover:bg-mil-800/40'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="card xl:col-span-10 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400">
              {activeBlock === 'table' && 'Таблиця (колонки)'}
              {activeBlock === 'service' && 'Службова інформація'}
              {activeBlock === 'header' && 'Шапка'}
              {activeBlock === 'totals' && 'Підсумки'}
              {activeBlock === 'signatures' && 'Підписи'}
              {activeBlock === 'footer' && 'Нижній колонтитул'}
            </h3>
            {activeBlock === 'table' && (
              <button className="btn-secondary" onClick={() => setAddOpen(true)}>+ Додати колонку</button>
            )}
          </div>

          {activeBlock === 'table' && (
            <div className="space-y-3">
              {(versionState.table_columns_json || []).map((c: any, i: number) => (
                <div key={c.id || i} className="rounded-xl border border-mil-700 p-3 bg-mil-900/30">
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2 items-end">
                    <div>
                      <label className="label">Назва</label>
                      <input className="input-field" value={c.title || ''} onChange={(e) => patchColumn(i, { title: e.target.value })} />
                    </div>
                    <div>
                      <label className="label">Джерело</label>
                      <select className="input-field" value={c.source || ''} onChange={(e) => patchColumn(i, { source: e.target.value })}>
                        {!!c.source && !sourceOptions.some((o) => o.value === c.source) && (
                          <option value={c.source}>{labelForSource(c.source)}</option>
                        )}
                        {sourceOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="label">Шир.</label>
                      <input type="number" className="input-field" value={c.width || 8} onChange={(e) => patchColumn(i, { width: Number(e.target.value || 0) })} />
                    </div>
                    <div>
                      <label className="label">Розмір шрифту (pt)</label>
                      <input
                        type="number"
                        min={8}
                        max={24}
                        className="input-field"
                        value={c.font_size_pt || 11}
                        onChange={(e) => patchColumn(i, { font_size_pt: Number(e.target.value || 11) })}
                      />
                    </div>
                    <div>
                      <label className="label">Стиль</label>
                      <select className="input-field" value={c.text_style || 'normal'} onChange={(e) => patchColumn(i, { text_style: e.target.value })}>
                        {textStyleOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="label">Вирівн.</label>
                      <select className="input-field" value={c.align || 'left'} onChange={(e) => patchColumn(i, { align: e.target.value })}>
                        <option value="left">{pdfAlignLabel('left')}</option>
                        <option value="center">{pdfAlignLabel('center')}</option>
                        <option value="right">{pdfAlignLabel('right')}</option>
                      </select>
                    </div>
                    <div>
                      <label className="label">Формат</label>
                      <select className="input-field" value={c.format || 'text'} onChange={(e) => patchColumn(i, { format: e.target.value })}>
                        {formats.map((f) => <option key={f} value={f}>{pdfFormatLabel(f)}</option>)}
                      </select>
                    </div>
                    <div className="flex items-center justify-end">
                      <label className="inline-flex items-center gap-2 text-xs text-gray-300">
                        <input type="checkbox" checked={Boolean(c.visible ?? true)} onChange={(e) => patchColumn(i, { visible: e.target.checked })} />
                        Показ
                      </label>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button className="btn-ghost" disabled={i === 0} onClick={() => setVersionState({ ...versionState, table_columns_json: move(versionState.table_columns_json || [], i, i - 1) })}>↑</button>
                    <button className="btn-ghost" disabled={i === (versionState.table_columns_json || []).length - 1} onClick={() => setVersionState({ ...versionState, table_columns_json: move(versionState.table_columns_json || [], i, i + 1) })}>↓</button>
                    <button className="btn-ghost" onClick={() => duplicateColumn(i)}>Дублювати</button>
                    <button className="btn-danger" onClick={() => removeColumn(i)}>Видалити</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeBlock === 'service' && (
            <div className="pt-2 border-t border-mil-700">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">Службова інформація</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-300">
                {[
                  ['show_request_number', 'Номер заявки'],
                  ['show_generated_at', 'Дата/час формування'],
                  ['show_department', 'Підрозділ'],
                  ['show_system_version', 'Версія системи'],
                  ['show_qr', 'QR-код перевірки'],
                ].map(([key, label]) => (
                  <label key={key} className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={Boolean(versionState?.service_block_json?.[key])}
                      onChange={(e) => updateServiceFlag(key, e.target.checked)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {activeBlock === 'header' && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div>
                  <label className="label">Базовий розмір шрифту (pt)</label>
                  <input
                    type="number"
                    min={8}
                    max={24}
                    className="input-field"
                    value={versionState?.layout_json?.typography?.font_size_pt || 11}
                    onChange={(e) => updateLayoutNode('typography', { font_size_pt: Number(e.target.value || 11) })}
                  />
                </div>
                <div>
                  <label className="label">Базовий стиль</label>
                  <select
                    className="input-field"
                    value={versionState?.layout_json?.typography?.text_style || 'normal'}
                    onChange={(e) => updateLayoutNode('typography', { text_style: e.target.value })}
                  >
                    {textStyleOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Кому</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.header?.commander_line || ''}
                  onChange={(e) => updateLayoutNode('header', { commander_line: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Заголовок 1</label>
                <input className="input-field" value={versionState?.layout_json?.header?.title || ''} onChange={(e) => updateLayoutNode('header', { title: e.target.value })} />
              </div>
              <div>
                <label className="label">Підзаголовок</label>
                <input className="input-field" value={versionState?.layout_json?.header?.subtitle || ''} onChange={(e) => updateLayoutNode('header', { subtitle: e.target.value })} />
              </div>
            </div>
          )}

          {activeBlock === 'totals' && (
            <div className="space-y-2">
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={Boolean(versionState?.layout_json?.totals?.show ?? true)}
                  onChange={(e) => updateLayoutNode('totals', { show: e.target.checked })}
                />
                Показувати блок підсумків
              </label>
            </div>
          )}

          {activeBlock === 'signatures' && (
            <div className="space-y-3">
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={Boolean(versionState?.layout_json?.signatures?.show ?? true)}
                  onChange={(e) => updateLayoutNode('signatures', { show: e.target.checked })}
                />
                Показувати блок підписів
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={Boolean(versionState?.layout_json?.signatures?.use_department_signatures ?? true)}
                  onChange={(e) => updateLayoutNode('signatures', { use_department_signatures: e.target.checked })}
                />
                Використовувати підписи підрозділу (якщо вимкнено — використовуються підписи з адмінки)
              </label>
              <div>
                <label className="label">З розрахунком згоден (заголовок)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.approval_title || 'З розрахунком згоден:'}
                  onChange={(e) => updateLayoutNode('signatures', { approval_title: e.target.value })}
                />
              </div>
              <div>
                <label className="label">З розрахунком згоден — посада (адмінка)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.approval_position || ''}
                  onChange={(e) => updateLayoutNode('signatures', { approval_position: e.target.value })}
                />
              </div>
              <div>
                <label className="label">З розрахунком згоден — ПІБ (адмінка)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.approval_name || ''}
                  onChange={(e) => updateLayoutNode('signatures', { approval_name: e.target.value })}
                />
              </div>
              <div>
                <label className="label">ПОГОДЖЕНО (заголовок)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.agreed_title || 'ПОГОДЖЕНО:'}
                  onChange={(e) => updateLayoutNode('signatures', { agreed_title: e.target.value })}
                />
              </div>
              <div>
                <label className="label">ПОГОДЖЕНО — посада (адмінка)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.agreed_position || ''}
                  onChange={(e) => updateLayoutNode('signatures', { agreed_position: e.target.value })}
                />
              </div>
              <div>
                <label className="label">ПОГОДЖЕНО — ПІБ (адмінка)</label>
                <input
                  className="input-field"
                  value={versionState?.layout_json?.signatures?.agreed_name || ''}
                  onChange={(e) => updateLayoutNode('signatures', { agreed_name: e.target.value })}
                />
              </div>
              <div className="text-xs text-gray-500">
                Якщо перемикач увімкнено, беруться підписанти з профілю підрозділу. Якщо вимкнено — беруться значення з цього блоку адмінки.
              </div>
            </div>
          )}

          {activeBlock === 'footer' && (
            <div>
              <label className="label">Текст у нижньому колонтитулі</label>
              <textarea className="input-field min-h-[90px]" value={versionState?.layout_json?.footer?.disclaimer || ''} onChange={(e) => updateLayoutNode('footer', { disclaimer: e.target.value })} />
            </div>
          )}
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400">Попередній перегляд</h3>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="lg:col-span-2">
            <label className="label">Заявка для превʼю</label>
            <select className="input-field" value={previewRequestId} onChange={(e) => setPreviewRequestId(e.target.value)}>
              <option value="" disabled>Оберіть заявку</option>
              {(requests || []).map((r: any) => (
                <option key={r.id} value={String(r.id)}>{r.request_number || `Заявка #${r.id}`}</option>
              ))}
            </select>
            {requests.length === 0 && (
              <div className="text-xs text-gray-500 mt-2">Немає доступних заявок для превʼю. Створіть або відкрийте існуючу заявку.</div>
            )}
          </div>
          <div className="flex items-end gap-2">
            <button className="btn-secondary w-full" onClick={refreshPreview} disabled={previewLoading || !previewRequestId}>{previewLoading ? 'Генерація...' : 'Оновити превʼю'}</button>
            <button className="btn-ghost w-full" onClick={downloadPreview} disabled={!previewRequestId}>Завантажити PDF превʼю</button>
          </div>
        </div>
        <div className="rounded-xl border border-mil-700 min-h-[620px] overflow-hidden bg-black/20">
          {previewUrl ? (
            <iframe title="pdf-preview" src={previewUrl} className="w-full h-[620px]" />
          ) : (
            <div className="text-xs text-gray-500 p-3">Сформуйте превʼю для перегляду</div>
          )}
        </div>
      </div>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Додати колонку">
        <div className="space-y-3">
          <div>
            <label className="label">Назва</label>
            <input className="input-field" value={newCol.title} onChange={(e) => setNewCol({ ...newCol, title: e.target.value })} />
          </div>
          <div>
            <label className="label">Джерело</label>
            <select className="input-field" value={newCol.source} onChange={(e) => setNewCol({ ...newCol, source: e.target.value })}>
              {sourceOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
            <div>
              <label className="label">Ширина</label>
              <input type="number" className="input-field" value={newCol.width} onChange={(e) => setNewCol({ ...newCol, width: Number(e.target.value || 10) })} />
            </div>
            <div>
              <label className="label">Розмір (pt)</label>
              <input type="number" min={8} max={24} className="input-field" value={newCol.font_size_pt} onChange={(e) => setNewCol({ ...newCol, font_size_pt: Number(e.target.value || 11) })} />
            </div>
            <div>
              <label className="label">Стиль</label>
              <select className="input-field" value={newCol.text_style} onChange={(e) => setNewCol({ ...newCol, text_style: e.target.value })}>
                {textStyleOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Вирівн.</label>
              <select className="input-field" value={newCol.align} onChange={(e) => setNewCol({ ...newCol, align: e.target.value })}>
                <option value="left">{pdfAlignLabel('left')}</option>
                <option value="center">{pdfAlignLabel('center')}</option>
                <option value="right">{pdfAlignLabel('right')}</option>
              </select>
            </div>
            <div>
              <label className="label">Формат</label>
              <select className="input-field" value={newCol.format} onChange={(e) => setNewCol({ ...newCol, format: e.target.value })}>
                {formats.map((f) => <option key={f} value={f}>{pdfFormatLabel(f)}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setAddOpen(false)}>Скасувати</button>
            <button className="btn-primary" onClick={addColumn}>Додати</button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default PdfTemplateEditor;
