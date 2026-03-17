import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import ConfirmModal from '../../components/ConfirmModal';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { api } from '../../api';
import { ArrowLeft, Edit, CheckCircle, Printer, Trash2 } from 'lucide-react';

const DeptRequestDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [req, setReq] = useState<any>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [acting, setActing] = useState(false);
  const [routeInfoOpen, setRouteInfoOpen] = useState(false);
  const [routeInfoItem, setRouteInfoItem] = useState<any>(null);

  const load = () => {
    setLoading(true);
    api.getRequest(Number(id)).then(setReq).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleConfirm = async () => {
    setActing(true);
    try {
      const res: any = await api.confirmRequest(Number(id));
      if (res?.result === 'POSTED_WITH_DEBT' || res?.has_debt) {
        toast(res?.message || 'Отримання підтверджено частково. Створено заборгованість.', 'warning');
      } else if (res?.result === 'ALREADY_CONFIRMED') {
        toast(res?.message || 'Отримання вже підтверджено.', 'info');
      } else {
        toast(res?.message || 'Отримання підтверджено. Списання виконано.', 'success');
      }
      setConfirmOpen(false);
      load();
    } catch (e: any) {
      const msg = String(e?.message || '');
      if (msg.includes('Проведення виконується')) {
        toast('Проведення виконується… Спробуйте ще раз через кілька секунд.', 'warning');
      } else {
        toast(msg || 'Помилка підтвердження', 'error');
      }
    }
    finally { setActing(false); }
  };

  const handlePrint = async () => {
    if (!id) return;
    try {
      const artifact = await api.printRequestPdf(Number(id), {});
      const blob = await api.downloadPrintArtifact(artifact.artifact_id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (e: any) {
      toast(e.message || 'Помилка при друку', 'error');
    }
  };

  const handleDeleteDraft = async () => {
    if (!req || req.status !== 'DRAFT') return;
    const accepted = window.confirm(`Видалити чернетку ${req.request_number}?`);
    if (!accepted) return;
    try {
      await api.deleteDraftRequest(Number(id));
      toast('Чернетку видалено', 'success');
      navigate('/dept/requests');
    } catch (e: any) {
      toast(e?.message || 'Не вдалося видалити чернетку', 'error');
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
    { key: 'required_liters', title: 'Літри', render: (r: any) => r.required_liters?.toFixed(2) },
    { key: 'required_kg', title: 'Кг', render: (r: any) => r.required_kg?.toFixed(2) },
  ];

  const timeline = [
    { label: 'Створено', at: req.created_at },
    { label: 'Подано', at: req.submitted_at },
    { label: 'Затверджено', at: req.approved_at },
    { label: 'Видано оператором', at: req.operator_issued_at },
    { label: 'Підтверджено', at: req.dept_confirmed_at },
    { label: 'Проведено', at: req.stock_posted_at },
  ];

  return (
    <div>
      <PageHeader
        title={`Заявка ${req.request_number}`}
        actions={
          <div className="flex gap-2">
            <button onClick={() => navigate(-1)} className="btn-ghost"><ArrowLeft size={16} /> Назад</button>
            <button onClick={handlePrint} className="btn-secondary"><Printer size={16} /> Друк</button>
            {req.status === 'DRAFT' && (
              <>
                <button onClick={() => navigate(`/dept/edit/${req.id}`)} className="btn-secondary"><Edit size={16} /> Редагувати</button>
                <button onClick={handleDeleteDraft} className="btn-danger"><Trash2 size={16} /> Видалити</button>
              </>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Транспорт</h3>
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
                      <td className="py-2 pr-3 text-gray-300">{Number(r.requested_liters || 0).toFixed(2)}</td>
                      <td className="py-2 pr-3 text-gray-300">{Number(r.issued_liters || 0).toFixed(2)}</td>
                      <td className={`py-2 pr-3 ${Number(r.missing_liters || 0) > 0 ? 'text-danger' : 'text-gray-300'}`}>{Number(r.missing_liters || 0).toFixed(2)}</td>
                      <td className={`py-2 pr-3 ${Number(r.missing_kg || 0) > 0 ? 'text-danger' : 'text-gray-300'}`}>{Number(r.missing_kg || 0).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {req.status === 'ISSUED_BY_OPERATOR' && (
            <button onClick={() => setConfirmOpen(true)} className="btn-primary">
              <CheckCircle size={16} /> Підтвердити отримання
            </button>
          )}
        </div>

        <div className="space-y-6">
          {req.is_rejected && req.rejection_comment && (
            <div className="card h-fit border border-danger/30">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">Коментар адміністратора</h3>
              <div className="text-sm text-gray-200 whitespace-pre-wrap">{req.rejection_comment}</div>
            </div>
          )}

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
              {(req.audits || []).slice(0, 20).map((a: any) => (
                <div key={a.id} className="text-xs border-b border-mil-800 pb-2">
                  <div className="text-gray-300 font-medium">{a.action}</div>
                  <div className="text-gray-500">{a.created_at ? new Date(a.created_at).toLocaleString('uk-UA') : '—'}</div>
                  {a.message && <div className="text-gray-400 mt-1">{a.message}</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirm}
        title="Підтвердити отримання"
        message={`Ви підтверджуєте отримання палива за заявкою ${req.request_number}? Це спишеться зі складу.`}
        confirmText="Підтвердити"
        loading={acting}
      />

      <Modal
        open={routeInfoOpen}
        onClose={() => setRouteInfoOpen(false)}
        title="Інформація про маршрут"
        size="sm"
        footer={
          <>
            <button onClick={() => setRouteInfoOpen(false)} className="btn-secondary">Закрити</button>
            <button onClick={() => navigate('/dept/routes')} className="btn-primary">Відкрити маршрути</button>
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

export default DeptRequestDetail;
