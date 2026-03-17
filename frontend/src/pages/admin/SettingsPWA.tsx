import React, { useEffect, useState } from 'react';
import PageHeader from '../../components/PageHeader';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import { useToast } from '../../components/Toast';
import { api } from '../../api';

const SettingsPWA: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ app_name: '', short_name: '', theme_color: '', background_color: '' });
  const [icons, setIcons] = useState({ has_icons: false, icon_192_url: '/icon-192.png', icon_512_url: '/icon-512.png' });
  const [iconFile, setIconFile] = useState<File | null>(null);
  const [iconVersion, setIconVersion] = useState(Date.now());
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    Promise.all([api.getPwa(), api.getPwaIcons()])
      .then(([d, i]) => {
        setForm({ app_name: d.app_name || '', short_name: d.short_name || '', theme_color: d.theme_color || '', background_color: d.background_color || '' });
        setIcons({
          has_icons: !!i.has_icons,
          icon_192_url: i.icon_192_url || '/icon-192.png',
          icon_512_url: i.icon_512_url || '/icon-512.png',
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.setPwa(form);
      toast('PWA налаштування збережено', 'success');
    } catch (e: any) { toast(e.message, 'error'); }
    finally { setSaving(false); }
  };

  const uploadIcon = async () => {
    if (!iconFile) {
      toast('Оберіть файл іконки', 'error');
      return;
    }
    setUploading(true);
    try {
      const res: any = await api.uploadPwaIcon(iconFile);
      setIcons({
        has_icons: !!res.has_icons,
        icon_192_url: res.icon_192_url || '/icon-192.png',
        icon_512_url: res.icon_512_url || '/icon-512.png',
      });
      setIconVersion(Date.now());
      setIconFile(null);
      toast('Іконки PWA оновлено', 'success');
    } catch (e: any) {
      toast(e.message || 'Помилка завантаження іконки', 'error');
    } finally {
      setUploading(false);
    }
  };

  const resetIcon = async () => {
    setUploading(true);
    try {
      const res: any = await api.deletePwaIcon();
      setIcons({
        has_icons: !!res.has_icons,
        icon_192_url: res.icon_192_url || '/icon-192.png',
        icon_512_url: res.icon_512_url || '/icon-512.png',
      });
      setIconVersion(Date.now());
      setIconFile(null);
      toast('Іконки PWA скинуто до стандартних', 'success');
    } catch (e: any) {
      toast(e.message || 'Помилка скидання іконки', 'error');
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <LoadingSkeleton type="form" rows={4} />;

  return (
    <div>
      <PageHeader title="PWA Налаштування" subtitle="Назва та кольори для мобільного застосунку" />
      <div className="card max-w-lg space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Назва додатку</label>
          <input className="input-field" value={form.app_name} onChange={e => setForm({ ...form, app_name: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Коротка назва</label>
          <input className="input-field" value={form.short_name} onChange={e => setForm({ ...form, short_name: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Колір теми</label>
          <div className="flex items-center gap-3">
            <input type="color" value={form.theme_color} onChange={e => setForm({ ...form, theme_color: e.target.value })} className="w-10 h-10 rounded border border-mil-600 cursor-pointer" />
            <input className="input-field" value={form.theme_color} onChange={e => setForm({ ...form, theme_color: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Колір фону</label>
          <div className="flex items-center gap-3">
            <input type="color" value={form.background_color} onChange={e => setForm({ ...form, background_color: e.target.value })} className="w-10 h-10 rounded border border-mil-600 cursor-pointer" />
            <input className="input-field" value={form.background_color} onChange={e => setForm({ ...form, background_color: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Іконки</label>
          <div className="bg-mil-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-4">
              <img
                src={`${icons.icon_192_url}?v=${iconVersion}`}
                alt="PWA 192"
                className="w-12 h-12 rounded border border-mil-600 bg-mil-700"
              />
              <img
                src={`${icons.icon_512_url}?v=${iconVersion}`}
                alt="PWA 512"
                className="w-12 h-12 rounded border border-mil-600 bg-mil-700"
              />
              <span className="text-xs text-gray-500">
                {icons.has_icons ? 'Кастомні іконки активні' : 'Використовуються стандартні іконки'}
              </span>
            </div>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={e => setIconFile(e.target.files?.[0] || null)}
              className="input-field"
            />
            <div className="flex gap-2">
              <button onClick={uploadIcon} className="btn-secondary" disabled={uploading || !iconFile}>
                {uploading ? 'Завантаження...' : 'Завантажити іконку'}
              </button>
              <button onClick={resetIcon} className="btn-secondary" disabled={uploading || !icons.has_icons}>
                Скинути
              </button>
            </div>
            <p className="text-gray-500 text-xs">
              Рекомендовано квадратне зображення (PNG/JPG/WebP), мінімум 512x512.
            </p>
          </div>
        </div>
        <button onClick={save} className="btn-primary" disabled={saving}>
          {saving ? 'Збереження...' : 'Зберегти'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPWA;
