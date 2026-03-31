import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import ConfirmModal from '../../components/ConfirmModal';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../auth';
import { api } from '../../api';
import { Plus, Send, Save, Trash2 } from 'lucide-react';
import { formatQuantity, roundUpQuantity } from '../../utils/quantities';

const CreateRequest: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const isEdit = !!id;

  const isBlank = (v: any) => v === undefined || v === null || String(v).trim() === '';
  const toNumberOrNull = (v: any) => {
    if (isBlank(v)) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const toIntOrNull = (v: any) => {
    if (isBlank(v)) return null;
    const n = Number.parseInt(String(v), 10);
    return Number.isFinite(n) ? n : null;
  };

  const [form, setForm] = useState({ route_text: '', distance_km_per_trip: '', justification_text: '', persons_involved_count: '0', training_days_count: '0' });
  const [reqId, setReqId] = useState<number | null>(id ? Number(id) : null);
  const [items, setItems] = useState<any[]>([]);
  const [draftItems, setDraftItems] = useState<any[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [routes, setRoutes] = useState<any[]>([]);
  const [density, setDensity] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [vehModalOpen, setVehModalOpen] = useState(false);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [paList, setPaList] = useState<any[]>([]);
  const [itemForm, setItemForm] = useState({ planned_activity_id: '', vehicle_id: '' });
  const [vehForm, setVehForm] = useState({ brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '' });
  const [vehSaving, setVehSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getVehicles(),
      api.getDensity().catch(() => null),
      api.listRoutes({}).catch(() => []),
      api.listPlannedActivities({ only_active: true }).catch(() => []),
    ]).then(([v, d, r]) => { setVehicles(v); setDensity(d); setRoutes(r || []); });

    api.listPlannedActivities({ only_active: true }).then((list: any) => setPaList(list || [])).catch(() => setPaList([]));

    if (isEdit && id) {
      api.getRequest(Number(id)).then(r => {
        setItems(r.items || []);
        setReqId(r.id);
      });
    }
  }, [id]);

  const deptRoutes = routes.filter((r: any) => String(r.department_id) === String(user?.department_id ?? ''));

  const deptVehicles = vehicles.filter((v: any) => v.department_id === user?.department_id);
  const approvedVehicles = deptVehicles.filter((v: any) => v.is_active && v.is_approved);
  const pendingMine = deptVehicles.filter((v: any) => !v.is_approved);

  const visibleItems = reqId ? items : draftItems;

  const computeItem = () => {
    const distance = toNumberOrNull(form.distance_km_per_trip);
    const trainingDays = toIntOrNull((form as any).training_days_count);
    if (!itemForm.vehicle_id || trainingDays === null || trainingDays <= 0 || distance === null) return null;
    const veh = vehicles.find((v: any) => v.id === Number(itemForm.vehicle_id));
    if (!veh || !density) return null;
    const totalKm = distance * trainingDays;
    const liters = roundUpQuantity(totalKm * veh.consumption_l_per_km);
    const factor = veh.fuel_type === 'АБ' ? density.density_factor_ab : density.density_factor_dp;
    const kg = roundUpQuantity(liters * factor);
    return { totalKm: totalKm.toFixed(1), liters: String(liters), kg: String(kg), fuelType: veh.fuel_type };
  };

  const computeDraftRow = (vehicleId: number) => {
    const veh = vehicles.find((v: any) => v.id === vehicleId);
    const distance = toNumberOrNull(form.distance_km_per_trip);
    const trainingDays = toIntOrNull((form as any).training_days_count);
    if (!veh || distance === null || trainingDays === null || trainingDays <= 0) return null;
    const totalKm = distance * trainingDays;
    const liters = roundUpQuantity(totalKm * veh.consumption_l_per_km);
    const factor = density ? (veh.fuel_type === 'АБ' ? density.density_factor_ab : density.density_factor_dp) : null;
    const kg = factor !== null ? roundUpQuantity(liters * factor) : null;
    return {
      vehicle_name: veh.brand,
      vehicle_plate: veh.identifier,
      vehicle_fuel_type: veh.fuel_type,
      total_km: totalKm,
      required_liters: liters,
      required_kg: kg,
    };
  };

  const handleSave = async () => {
    const hasAny = (reqId ? (items || []).length : (draftItems || []).length) > 0;
    if (!hasAny) {
      toast('Додайте хоча б один транспортний блок перед збереженням', 'warning');
      return;
    }
    setSaving(true);
    try {
      if (reqId) {
        toast('Заявку збережено', 'success');
      } else {
        const r = await api.createRequest({ department_id: user!.department_id });
        setReqId(r.id);
        toast('Заявку створено', 'success');
        if (draftItems.length > 0) {
          for (const di of draftItems) {
            await api.addRequestItem(r.id, {
              planned_activity_id: di.planned_activity_id,
              vehicle_id: di.vehicle_id,
              route_id: di.route_id ? Number(di.route_id) : null,
              route_is_manual: !!di.route_is_manual,
              route_text: di.route_text || null,
              distance_km_per_trip: di.distance_km_per_trip,
              justification_text: di.justification_text || null,
              persons_involved_count: di.persons_involved_count,
              training_days_count: di.training_days_count,
            });
          }
          setDraftItems([]);
          const rr = await api.getRequest(r.id);
          setItems(rr.items || []);
        }
        navigate(`/dept/edit/${r.id}`, { replace: true });
      }
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const handleAddItem = async () => {
    const plannedActivityId = toIntOrNull((itemForm as any).planned_activity_id);
    const vehicleId = toIntOrNull(itemForm.vehicle_id);
    if (!plannedActivityId) {
      toast('Оберіть запланований захід перед вибором транспорту', 'warning');
      return;
    }
    if (!vehicleId) {
      toast('Оберіть транспорт', 'warning');
      return;
    }

    const distance = toNumberOrNull(form.distance_km_per_trip);
    const persons = toIntOrNull((form as any).persons_involved_count);
    const trainingDays = toIntOrNull((form as any).training_days_count);
    const hasRoute = !!(form as any).route_id || !!form.route_text?.trim();
    if (!hasRoute) {
      toast('Оберіть маршрут або введіть маршрут вручну', 'warning');
      return;
    }
    if (distance === null || distance <= 0) {
      toast('Заповніть поле "Плече підвезення" (число більше 0)', 'warning');
      return;
    }
    if (persons === null || persons <= 0) {
      toast('Заповніть поле "Кількість о/с" (ціле число більше 0)', 'warning');
      return;
    }
    if (trainingDays === null || trainingDays <= 0) {
      toast('Заповніть поле "Кількість навчальних (робочих) днів" (ціле число більше 0)', 'warning');
      return;
    }

    const routePayload: any = {};
    if ((form as any).route_id) {
      routePayload.route_id = Number((form as any).route_id);
      routePayload.route_is_manual = false;
      routePayload.route_text = null;
    } else {
      routePayload.route_id = null;
      routePayload.route_is_manual = true;
      routePayload.route_text = form.route_text;
    }

    if (!reqId) {
      const row = computeDraftRow(vehicleId);
      if (!row) {
        toast('Заповніть дані заявки (маршрут і плече) перед додаванням транспорту', 'warning');
        return;
      }
      setDraftItems(prev => ([
        ...prev,
        {
          id: `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          planned_activity_id: plannedActivityId,
          vehicle_id: vehicleId,
          ...routePayload,
          distance_km_per_trip: distance,
          justification_text: form.justification_text,
          persons_involved_count: persons,
          training_days_count: trainingDays,
          ...row,
        },
      ]));
      toast('Транспорт додано (чернетка)', 'success');
      setItemForm({ planned_activity_id: '', vehicle_id: '' } as any);
      setForm({ route_text: '', distance_km_per_trip: '', justification_text: '', persons_involved_count: '0', training_days_count: '0' } as any);
      return;
    }
    try {
      await api.addRequestItem(reqId, {
        planned_activity_id: plannedActivityId,
        vehicle_id: vehicleId,
        ...routePayload,
        distance_km_per_trip: distance,
        justification_text: form.justification_text,
        persons_involved_count: persons,
        training_days_count: trainingDays,
      });
      toast('Транспорт додано', 'success');
      setItemForm({ planned_activity_id: '', vehicle_id: '' } as any);
      setForm({ route_text: '', distance_km_per_trip: '', justification_text: '', persons_involved_count: '0', training_days_count: '0' } as any);
      const r = await api.getRequest(reqId);
      setItems(r.items || []);
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!reqId) {
      setDraftItems(prev => prev.filter((x: any) => String(x.id) !== String(itemId)));
      return;
    }
    try {
      await api.deleteRequestItem(reqId, itemId);
      toast('Рядок видалено', 'success');
      const r = await api.getRequest(reqId);
      setItems(r.items || []);
    } catch (e: any) { toast(e.message, 'error'); }
  };

  const handleSubmit = async () => {
    if (!reqId) return;
    if (!items || items.length === 0) {
      toast('Додайте транспорт до заявки перед поданням', 'warning');
      return;
    }
    try {
      await api.submitRequest(reqId);
      toast('Заявку подано на затвердження', 'success');
      navigate('/dept');
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSubmitOpen(false); }
  };

  const calc = computeItem();

  const canSaveRequest = (() => {
    const hasAny = (reqId ? (items || []).length : (draftItems || []).length) > 0;
    return hasAny;
  })();

  const proposeVehicle = async () => {
    if (!user?.department_id) return;
    setVehSaving(true);
    try {
      await api.createVehicle({
        department_id: user.department_id,
        brand: vehForm.brand,
        identifier: vehForm.identifier || null,
        fuel_type: vehForm.fuel_type,
        consumption_l_per_100km: parseFloat(vehForm.consumption_l_per_100km),
        is_active: true,
      });
      toast('Транспорт додано. Очікує підтвердження адміністратора', 'success');
      setVehModalOpen(false);
      setVehForm({ brand: '', identifier: '', fuel_type: 'АБ', consumption_l_per_100km: '' });
      const v = await api.getVehicles();
      setVehicles(v);
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setVehSaving(false); }
  };

  const itemCols = [
    { key: 'planned_activity_name', title: 'Захід', render: (r: any) => r.planned_activity_name || (paList || []).find((a: any) => Number(a.id) === Number(r.planned_activity_id))?.name || '—' },
    { key: 'vehicle_name', title: 'Транспорт', render: (r: any) => `${r.vehicle_name || ''} ${r.vehicle_plate || ''}` },
    { key: 'vehicle_fuel_type', title: 'Паливо' },
    { key: 'total_km', title: 'Км', render: (r: any) => r.total_km?.toFixed(1) },
    { key: 'required_liters', title: 'Літри', render: (r: any) => formatQuantity(r.required_liters) },
    { key: 'required_kg', title: 'Кг', render: (r: any) => formatQuantity(r.required_kg) },
    { key: 'actions', title: '', render: (r: any) => (
      <button onClick={(e) => { e.stopPropagation(); handleDeleteItem(r.id); }} className="text-danger hover:text-danger/80"><Trash2 size={16} /></button>
    )},
  ];

  return (
    <div>
      <PageHeader title={isEdit ? 'Редагувати заявку' : 'Нова заявка'} />

      <div className="space-y-6 max-w-3xl">
        <div className="card space-y-4">
          <div className="flex items-center">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Транспортний блок</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Запланований захід *</label>
              <select
                className="input-field"
                value={(itemForm as any).planned_activity_id}
                onChange={e => setItemForm({ ...(itemForm as any), planned_activity_id: e.target.value })}
              >
                <option value="">Оберіть...</option>
                {(paList || []).map((a: any) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Транспорт *</label>
              <select className="input-field" value={itemForm.vehicle_id} onChange={e => setItemForm({ ...itemForm, vehicle_id: e.target.value })}>
                <option value="">Оберіть...</option>
                {approvedVehicles.map((v: any) => (
                  <option key={v.id} value={v.id}>{v.brand}{v.identifier ? ` (${v.identifier})` : ''} — {v.fuel_type} — {v.consumption_l_per_100km?.toFixed?.(2) || v.consumption_l_per_100km} л/100км</option>
                ))}
              </select>
            </div>
          </div>

          {!!itemForm.vehicle_id && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Маршрут *</label>
                <div className="space-y-2">
                  <select
                    className="input-field"
                    value={(form as any).route_id || ''}
                    onChange={e => {
                      const rid = e.target.value;
                      if (!rid) {
                        setForm({ ...(form as any), route_id: '', route_is_manual: true });
                        return;
                      }
                      const r = deptRoutes.find((x: any) => x.id === Number(rid));
                      setForm({
                        ...(form as any),
                        route_id: rid,
                        route_is_manual: false,
                        route_text: '',
                        distance_km_per_trip: r?.distance_km !== undefined && r?.distance_km !== null ? String(r.distance_km) : (form as any).distance_km_per_trip,
                      });
                    }}
                  >
                    <option value="">Ввести вручну</option>
                    {deptRoutes.map((r: any) => (
                      <option key={r.id} value={r.id}>{r.name} — {(r.points || []).join(' — ')}{r.is_approved ? '' : ' (очікує підтвердження)'}</option>
                    ))}
                  </select>
                  {!(form as any).route_id && (
                    <input
                      className="input-field"
                      value={form.route_text}
                      onChange={e => setForm({ ...(form as any), route_text: e.target.value, route_is_manual: true })}
                      placeholder="Наприклад: Київ — Одеса — Миколаїв"
                    />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Плече підвезення *</label>
                  <input
                    className="input-field"
                    type="number"
                    step="0.1"
                    value={form.distance_km_per_trip}
                    onChange={e => setForm({ ...form, distance_km_per_trip: e.target.value })}
                    placeholder="0"
                    disabled={!!(form as any).route_id}
                    title={!!(form as any).route_id ? 'Плече підвезення береться з маршруту' : undefined}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Кількість о/с, що залучались до навчань (занять) *</label>
                  <input
                    className="input-field"
                    type="number"
                    step="1"
                    value={(form as any).persons_involved_count}
                    onChange={e => setForm({ ...(form as any), persons_involved_count: e.target.value })}
                    placeholder="0"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Кількість навчальних (робочих) днів *</label>
                <input
                  className="input-field"
                  type="number"
                  step="1"
                  value={(form as any).training_days_count}
                  onChange={e => setForm({ ...(form as any), training_days_count: e.target.value })}
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Коментарі</label>
                <textarea className="input-field min-h-[80px]" value={form.justification_text} onChange={e => setForm({ ...form, justification_text: e.target.value })} placeholder="Коментар..." />
              </div>

              {calc && (
                <div className="bg-mil-800 rounded-lg p-3 text-sm space-y-1">
                  <p className="text-gray-400">Розрахунок:</p>
                  <p className="text-gray-200">Паливо: <strong>{calc.fuelType}</strong></p>
                  <p className="text-gray-200">Загальна відстань: <strong>{calc.totalKm} км</strong></p>
                  <p className="text-gray-200">Потреба: <strong>{calc.liters} л</strong> / <strong>{calc.kg} кг</strong></p>
                </div>
              )}

              <div className="flex justify-end">
                <button onClick={handleAddItem} className="btn-primary">
                  <Plus size={16} /> Додати транспортний блок
                </button>
              </div>
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Додані блоки</h3>
            <button onClick={handleSave} className="btn-secondary" disabled={saving || !canSaveRequest}>
              <Save size={16} /> {saving ? 'Збереження...' : 'Зберегти'}
            </button>
          </div>
          <DataTable columns={itemCols} data={visibleItems} emptyText="Додайте транспорт до заявки" />
          {pendingMine.length > 0 && (
            <div className="mt-3 text-xs text-warn bg-warn/10 border border-warn/20 rounded-lg px-3 py-2">
              Є транспорт, який очікує підтвердження адміністратора: {pendingMine.map((v: any) => `${v.brand}${v.identifier ? ` (${v.identifier})` : ''}`).join(', ')}
            </div>
          )}
        </div>

        {reqId && items.length > 0 && (
          <div className="flex gap-3">
            <button onClick={() => setSubmitOpen(true)} className="btn-primary"><Send size={16} /> Подати заявку</button>
          </div>
        )}
      </div>

      <Modal
        open={vehModalOpen}
        onClose={() => setVehModalOpen(false)}
        title="Новий транспорт (потрібне підтвердження)"
        size="sm"
        footer={
          <>
            <button onClick={() => setVehModalOpen(false)} className="btn-secondary">Скасувати</button>
            <button onClick={proposeVehicle} className="btn-primary" disabled={vehSaving || !vehForm.brand || !vehForm.consumption_l_per_100km}>
              {vehSaving ? 'Збереження...' : 'Додати'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Марка *</label>
            <input className="input-field" value={vehForm.brand} onChange={e => setVehForm({ ...vehForm, brand: e.target.value })} placeholder="Напр.: Toyota Hilux" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Номер / ідентифікатор</label>
            <input className="input-field" value={vehForm.identifier} onChange={e => setVehForm({ ...vehForm, identifier: e.target.value })} placeholder="Напр.: АА1234ВК або Борт-12" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Тип палива *</label>
            <select className="input-field" value={vehForm.fuel_type} onChange={e => setVehForm({ ...vehForm, fuel_type: e.target.value })}>
              <option value="АБ">АБ (Бензин)</option>
              <option value="ДП">ДП (Дизель)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Витрата (л/100км) *</label>
            <input className="input-field" type="number" step="0.01" value={vehForm.consumption_l_per_100km} onChange={e => setVehForm({ ...vehForm, consumption_l_per_100km: e.target.value })} />
            {!!vehForm.consumption_l_per_100km && (
              <p className="text-xs text-gray-500 mt-1">На 1 км: {(parseFloat(vehForm.consumption_l_per_100km) / 100).toFixed(3)} л/км</p>
            )}
          </div>
          <div className="text-xs text-gray-500">
            Після додавання транспорт буде доступний у заявках тільки після підтвердження адміністратора.
          </div>
        </div>
      </Modal>

      <ConfirmModal
        open={submitOpen}
        onClose={() => setSubmitOpen(false)}
        onConfirm={handleSubmit}
        title="Подати заявку"
        message="Після подання заявку не можна буде редагувати. Продовжити?"
        confirmText="Подати"
      />
    </div>
  );
};

export default CreateRequest;
