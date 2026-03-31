import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import ConfirmModal from '../../components/ConfirmModal';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { ArrowLeft, Edit, CheckCircle, Printer, XCircle, FileText } from 'lucide-react';
import { formatQuantity } from '../../utils/quantities';

const RequestDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [req, setReq] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [acting, setActing] = useState(false);
  const [rejectComment, setRejectComment] = useState('');

  const [paOpen, setPaOpen] = useState(false);
  const [paLoading, setPaLoading] = useState(false);
  const [paSaving, setPaSaving] = useState(false);
  const [paList, setPaList] = useState<any[]>([]);
  const [paSelectedId, setPaSelectedId] = useState<number | null>(null);
  const [routeInfoOpen, setRouteInfoOpen] = useState(false);
  const [routeInfoItem, setRouteInfoItem] = useState<any>(null);

  const load = () => {
    setLoading(true);
    api.getRequest(Number(id))
      .then((r) => { setReq(r); })
      .finally(() => setLoading(false));
  };

  const openPlannedActivities = async () => {
    if (!req?.id) return;
    setPaOpen(true);
    setPaLoading(true);
    try {
      const list = await api.listPlannedActivities({});
      setPaList(list || []);
      const ids = (req.planned_activity_ids || (req.planned_activities || []).map((x: any) => x.id) || []) as number[];
      setPaSelectedId(ids && ids.length > 0 ? Number(ids[0]) : null);
    } catch (e: any) {
      setPaList([]);
    } finally {
      setPaLoading(false);
    }
  };

  const savePlannedActivities = async () => {
    if (!req?.id) return;
    if (!paSelectedId) return;
    setPaSaving(true);
    try {
      await api.setRequestPlannedActivities(req.id, [paSelectedId]);
      const r = await api.getRequest(req.id);
      setReq(r);
      setPaOpen(false);
    } finally {
      setPaSaving(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const handleApprove = async () => {
    setActing(true);
    try {
      await api.approveRequest(Number(id));
      toast('Заявку затверджено', 'success');
      setApproveOpen(false);
      load();
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setActing(false); }
  };

  const handleReject = () => {
    const comment = rejectComment.trim();
    if (!comment) {
      toast('Додайте коментар для відхилення', 'warning');
      return;
    }
    setActing(true);
    api.rejectRequest(Number(id), comment)
      .then(() => {
        toast('Заявку відхилено', 'success');
        setRejectOpen(false);
        setRejectComment('');
        load();
      })
      .catch((e: any) => toast(e.message, 'error'))
      .finally(() => setActing(false));
  };

  const handlePrint = async () => {
    if (!id) return;
    try {
      const artifact = await api.printRequestPdf(Number(id), { force_regenerate: true });
      const blob = await api.downloadPrintArtifact(artifact.artifact_id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (e: any) {
      toast(e.message || 'Помилка при друку', 'error');
    }
  };

  const handlePrintAct = async () => {
    if (!id) return;
    try {
      const blob = await api.printRequestActPdf(Number(id));
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (e: any) {
      toast(e.message || 'Помилка при друку акта', 'error');
    }
  };

  if (loading) return <LoadingSkeleton type="form" rows={6} />;
  if (!req) return <div className="text-gray-500">Заявку не знайдено</div>;

  const openRouteInfo = (item: any) => {
    setRouteInfoItem({
      ...item,
      display_route_text: item?.route_text || req?.route_text || null,
      display_distance_km_per_trip: item?.distance_km_per_trip ?? req?.distance_km_per_trip ?? null,
      display_route_id: item?.route_id ?? req?.route_id ?? null,
      display_route_is_manual: Boolean(item?.route_is_manual ?? req?.route_is_manual),
    });
    setRouteInfoOpen(true);
  };

  const itemCols = [
    { key: 'planned_activity_name', title: 'Захід', render: (r: any) => r.planned_activity_name || '—' },
    { key: 'vehicle_name', title: 'Транспорт', render: (r: any) => `${r.vehicle_name || ''} ${r.vehicle_plate || ''}` },
    {
      key: 'route_text',
      title: 'Маршрут',
      render: (r: any) => {
        const text = r.route_text || req.route_text || (r.route_id || req.route_id ? `ID ${r.route_id || req.route_id}` : '—');
        if (text === '—') return '—';
        return (
          <button type="button" className="text-accent hover:underline text-left" onClick={() => openRouteInfo(r)}>
            {text}
          </button>
        );
      },
    },
    { key: 'vehicle_fuel_type', title: 'Паливо' },
    { key: 'total_km', title: 'Км', render: (r: any) => r.total_km?.toFixed(1) },
    { key: 'required_liters', title: 'Літри', render: (r: any) => formatQuantity(r.required_liters) },
  ];

  const timeline = [
    { label: 'Створено', at: req.created_at, by: req.created_by },
    { label: 'Подано', at: req.submitted_at, by: req.submitted_by },
    { label: 'Затверджено', at: req.approved_at, by: req.approved_by },
    { label: 'Видано оператором', at: req.operator_issued_at, by: req.operator_issued_by },
    { label: 'Підтверджено', at: req.dept_confirmed_at, by: req.dept_confirmed_by },
    { label: 'Проведено', at: req.stock_posted_at, by: req.stock_posted_by },
  ];

  return (
    <div>
      <PageHeader
        title={`Заявка ${req.request_number}`}
        actions={
          <div className="flex gap-2">
            <button onClick={() => navigate(-1)} className="btn-ghost"><ArrowLeft size={16} /> Назад</button>
            <button onClick={handlePrint} className="btn-secondary"><Printer size={16} /> Друк</button>
            <button onClick={handlePrintAct} className="btn-secondary"><FileText size={16} /> Друк акта</button>
          </div>
        }
      />

      <div className="space-y-6">
        {req.route_is_manual && (
          <div className="text-xs text-warn bg-warn/10 border border-warn/20 rounded-lg px-3 py-2">
            У заявці вказано маршрут вручну. Перевірте коректність перед затвердженням.
          </div>
        )}
        {/* Items */}
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Транспорт (рядки)</h3>
          <DataTable columns={itemCols} data={req.items || []} emptyText="Рядків немає" />
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Паливо (запитано/видано/недовидано)</h3>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-mil-700">
                  <th className="py-2 pr-3">Паливо</th>
                  <th className="py-2 pr-3">Запитано, л</th>
                  <th className="py-2 pr-3">Видано, л</th>
                  <th className="py-2 pr-3">Недовидано, л</th>
                  <th className="py-2 pr-3">Недовидано, кг</th>
                </tr>
              </thead>
              <tbody>
                {(req.fuel_summary || []).map((r: any) => (
                  <tr key={r.fuel_type} className="border-b border-mil-800">
                    <td className="py-2 pr-3 text-gray-200">{r.fuel_type}</td>
                    <td className="py-2 pr-3 text-gray-300">{formatQuantity(r.requested_liters)}</td>
                    <td className="py-2 pr-3 text-gray-300">{formatQuantity(r.issued_liters)}</td>
                    <td className={`py-2 pr-3 ${Number(r.missing_liters || 0) > 0 ? 'text-danger' : 'text-gray-300'}`}>{formatQuantity(r.missing_liters)}</td>
                    <td className={`py-2 pr-3 ${Number(r.missing_kg || 0) > 0 ? 'text-danger' : 'text-gray-300'}`}>{formatQuantity(r.missing_kg)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Actions */}
        {req.status === 'SUBMITTED' && (
          <div className="flex gap-3">
            <button onClick={() => setApproveOpen(true)} className="btn-primary"><CheckCircle size={16} /> Затвердити</button>
            <button onClick={() => setRejectOpen(true)} className="btn-danger"><XCircle size={16} /> Відхилити</button>
          </div>
        )}

        <div className="card h-fit">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Акт видачі</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-500">Номер акта</div>
              <div className="text-gray-200 font-medium">{req.issue_doc_no || '—'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Дата проведення</div>
              <div className="text-gray-200">{req.stock_posted_at ? new Date(req.stock_posted_at).toLocaleString('uk-UA') : '—'}</div>
            </div>
          </div>
          {!req.issue_doc_no && (
            <p className="text-xs text-gray-500 mt-3">
              Акт з&apos;явиться після підтвердження підрозділом отримання пального.
            </p>
          )}
        </div>

        <div className="card h-fit">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Таймлайн</h3>
          <div className="space-y-4">
            {timeline.map((t, i) => (
              <div key={i} className={`flex gap-3 ${t.at ? 'opacity-100' : 'opacity-30'}`}>
                <div className="flex flex-col items-center">
                  <div className={`w-3 h-3 rounded-full ${t.at ? 'bg-accent' : 'bg-mil-600'}`} />
                  {i < timeline.length - 1 && <div className="w-px h-8 bg-mil-700" />}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-300">{t.label}</p>
                  {t.at && <p className="text-xs text-gray-500">{new Date(t.at).toLocaleString('uk-UA')}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card h-fit">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Історія дій</h3>
          <div className="space-y-3">
            {(req.audits || []).length === 0 && <div className="text-xs text-gray-500">Історія відсутня</div>}
            {(req.audits || []).slice(0, 25).map((a: any) => (
              <div key={a.id} className="text-xs border-b border-mil-800 pb-2">
                <div className="text-gray-300 font-medium">{a.action}</div>
                <div className="text-gray-500">{a.created_at ? new Date(a.created_at).toLocaleString('uk-UA') : '—'}</div>
                {a.message && <div className="text-gray-400 mt-1">{a.message}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      <ConfirmModal
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        onConfirm={handleApprove}
        title="Затвердити заявку"
        message={`Ви дійсно бажаєте затвердити заявку ${req.request_number}?`}
        confirmText="Затвердити"
        loading={acting}
      />
      <ConfirmModal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        onConfirm={handleReject}
        title="Відхилити заявку"
        message={(
          <div className="space-y-2">
            <div className="text-sm text-gray-300">Вкажіть причину відхилення (обов’язково):</div>
            <textarea
              className="input-field min-h-[90px]"
              value={rejectComment}
              onChange={e => setRejectComment(e.target.value)}
              placeholder="Напр.: уточніть маршрут/плече/обґрунтування..."
            />
          </div>
        ) as any}
        confirmText="Відхилити"
        loading={acting}
        confirmClass="btn-danger"
      />

      <Modal
        open={paOpen}
        onClose={() => setPaOpen(false)}
        title="Заплановані заходи"
        size="sm"
        footer={
          <>
            <button onClick={() => setPaOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={savePlannedActivities} className="btn-primary" disabled={paSaving}>
              {paSaving ? 'Збереження...' : 'Зберегти'}
            </button>
          </>
        }
      >
        {paLoading ? (
          <LoadingSkeleton type="form" rows={4} />
        ) : (
          <div className="space-y-2">
            {(paList || []).map((a: any) => (
              <label key={a.id} className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="radio"
                  name="planned_activity"
                  checked={Number(paSelectedId) === Number(a.id)}
                  onChange={(e) => {
                    if (e.target.checked) setPaSelectedId(Number(a.id));
                  }}
                  className="rounded"
                />
                <span className={a.is_active ? '' : 'text-gray-500'}>{a.name}</span>
              </label>
            ))}
            {(paList || []).length === 0 && <div className="text-sm text-gray-500">Немає заходів. Додайте їх в налаштуваннях.</div>}
          </div>
        )}
      </Modal>

      <Modal
        open={routeInfoOpen}
        onClose={() => setRouteInfoOpen(false)}
        title="Інформація про маршрут"
        size="sm"
        footer={
          <>
            <button onClick={() => setRouteInfoOpen(false)} className="btn-secondary">Закрити</button>
            <button
              onClick={() => navigate('/admin/routes')}
              className="btn-primary"
            >
              Відкрити маршрути
            </button>
          </>
        }
      >
        <div className="space-y-3 text-sm">
          <div>
            <div className="text-xs text-gray-500">Маршрут</div>
            <div className="text-gray-200 whitespace-pre-wrap">{routeInfoItem?.display_route_text || '—'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Плече підвезення</div>
            <div className="text-gray-200">
              {routeInfoItem?.display_distance_km_per_trip !== null && routeInfoItem?.display_distance_km_per_trip !== undefined
                ? `${Number(routeInfoItem.display_distance_km_per_trip).toFixed(2)} км`
                : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Джерело</div>
            <div className="text-gray-200">
              {routeInfoItem?.display_route_is_manual ? 'Ручний маршрут (заявка)' : 'Довідник маршрутів'}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Ідентифікатор маршруту</div>
            <div className="text-gray-200">{routeInfoItem?.display_route_id ?? '—'}</div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default RequestDetail;
