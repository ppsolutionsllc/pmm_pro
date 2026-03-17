import React from 'react';
import { useAuth } from '../auth';
import PageHeader from '../components/PageHeader';
import { User, Shield, Building2, Phone } from 'lucide-react';
import { api } from '../api';

const roleLabels: Record<string, string> = {
  ADMIN: 'Адміністратор',
  OPERATOR: 'Оператор ПММ',
  DEPT_USER: 'Користувач підрозділу',
};

const Profile: React.FC = () => {
  const { user } = useAuth();
  const [departments, setDepartments] = React.useState<any[]>([]);
  const [signatures, setSignatures] = React.useState<any>({
    approval_title: 'З розрахунком згоден:',
    approval_position: '',
    approval_name: '',
    agreed_title: 'ПОГОДЖЕНО:',
    agreed_position: '',
    agreed_name: '',
  });
  const [signaturesLoading, setSignaturesLoading] = React.useState(false);
  const [signaturesSaving, setSignaturesSaving] = React.useState(false);
  const [signaturesMessage, setSignaturesMessage] = React.useState('');

  React.useEffect(() => {
    if (user?.department_id) {
      api.getDepartments().then(setDepartments);
    }
  }, [user?.department_id]);

  React.useEffect(() => {
    if (user?.role !== 'DEPT_USER' || !user?.department_id) return;
    let mounted = true;
    setSignaturesLoading(true);
    api
      .getMyDepartmentPrintSignatures()
      .then((row: any) => {
        if (!mounted) return;
        setSignatures({
          approval_title: row?.approval_title || 'З розрахунком згоден:',
          approval_position: row?.approval_position || '',
          approval_name: row?.approval_name || '',
          agreed_title: row?.agreed_title || 'ПОГОДЖЕНО:',
          agreed_position: row?.agreed_position || '',
          agreed_name: row?.agreed_name || '',
        });
      })
      .catch((err: any) => {
        if (!mounted) return;
        setSignaturesMessage(err?.message || 'Не вдалося завантажити підписантів');
      })
      .finally(() => {
        if (mounted) setSignaturesLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [user?.role, user?.department_id]);

  if (!user) return null;

  const deptName = user.department_id ? departments.find((d: any) => d.id === user.department_id)?.name || `#${user.department_id}` : null;
  const canEditDeptSignatures = user.role === 'DEPT_USER' && Boolean(user.department_id);

  const saveSignatures = async () => {
    if (!canEditDeptSignatures) return;
    setSignaturesSaving(true);
    setSignaturesMessage('');
    try {
      await api.updateMyDepartmentPrintSignatures({
        approval_title: signatures.approval_title,
        approval_position: signatures.approval_position,
        approval_name: signatures.approval_name,
      });
      setSignaturesMessage('Підписантів збережено.');
    } catch (err: any) {
      setSignaturesMessage(err?.message || 'Не вдалося зберегти підписантів');
    } finally {
      setSignaturesSaving(false);
    }
  };

  return (
    <div>
      <PageHeader title="Профіль" />
      <div className="card max-w-lg">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center">
            <User size={28} className="text-accent" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-100">{user.full_name || user.login}</h2>
            <p className="text-sm text-gray-500">@{user.login}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Shield size={18} className="text-gray-500" />
            <div>
              <p className="text-xs text-gray-500">Роль</p>
              <p className="text-sm text-gray-200">{roleLabels[user.role] || user.role}</p>
            </div>
          </div>
          {deptName && (
            <div className="flex items-center gap-3">
              <Building2 size={18} className="text-gray-500" />
              <div>
                <p className="text-xs text-gray-500">Підрозділ</p>
                <p className="text-sm text-gray-200">{deptName}</p>
              </div>
            </div>
          )}
          {user.phone && (
            <div className="flex items-center gap-3">
              <Phone size={18} className="text-gray-500" />
              <div>
                <p className="text-xs text-gray-500">Телефон</p>
                <p className="text-sm text-gray-200">{user.phone}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {canEditDeptSignatures && (
        <div className="card max-w-3xl mt-5">
          <h3 className="text-lg font-semibold text-gray-100 mb-1">Підписанти для друку заявки</h3>
          <p className="text-sm text-gray-500 mb-4">
            Ці дані підставляються в друковану форму заявки вашого підрозділу.
          </p>
          <div className="space-y-3">
            <div>
              <label className="label">З розрахунком згоден (заголовок)</label>
              <input
                className="input-field"
                value={signatures.approval_title}
                onChange={(e) => setSignatures({ ...signatures, approval_title: e.target.value })}
                disabled={signaturesLoading || signaturesSaving}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="label">З розрахунком згоден — посада</label>
                <input
                  className="input-field"
                  value={signatures.approval_position}
                  onChange={(e) => setSignatures({ ...signatures, approval_position: e.target.value })}
                  disabled={signaturesLoading || signaturesSaving}
                />
              </div>
              <div>
                <label className="label">З розрахунком згоден — ПІБ</label>
                <input
                  className="input-field"
                  value={signatures.approval_name}
                  onChange={(e) => setSignatures({ ...signatures, approval_name: e.target.value })}
                  disabled={signaturesLoading || signaturesSaving}
                />
              </div>
            </div>
            <div>
              <label className="label">ПОГОДЖЕНО (заголовок)</label>
              <input className="input-field" value={signatures.agreed_title} disabled />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="label">ПОГОДЖЕНО — посада</label>
                <input className="input-field" value={signatures.agreed_position} disabled />
              </div>
              <div>
                <label className="label">ПОГОДЖЕНО — ПІБ</label>
                <input className="input-field" value={signatures.agreed_name} disabled />
              </div>
            </div>
            <div className="text-xs text-gray-500">
              Блок «ПОГОДЖЕНО» редагує тільки адміністратор.
            </div>
          </div>
          {signaturesMessage && (
            <div className="text-sm mt-3 text-gray-300">{signaturesMessage}</div>
          )}
          <div className="mt-4">
            <button className="btn-primary" onClick={saveSignatures} disabled={signaturesLoading || signaturesSaving}>
              {signaturesSaving ? 'Збереження...' : 'Зберегти підписантів'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
