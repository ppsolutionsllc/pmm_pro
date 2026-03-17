import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';
import {
  LayoutDashboard, FileText, Package, BookOpen, Building2, Truck,
  Settings, Users, Smartphone, MessageSquare, User, CheckSquare,
  Clock, PlusCircle, Fuel, Scale, LogOut, Map, BarChart3, ShieldAlert
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  children?: NavItem[];
}

const adminNav: NavItem[] = [
  { to: '/admin', label: 'Дашборд', icon: <LayoutDashboard size={18} /> },
  { to: '/admin/requests', label: 'Заявки', icon: <FileText size={18} /> },
  {
    to: '/admin/stock/receipts',
    label: 'Склад',
    icon: <Package size={18} />,
    children: [
      { to: '/admin/stock/receipts', label: 'Прихід', icon: <Package size={18} /> },
      { to: '/admin/stock/balance', label: 'Баланс', icon: <Scale size={18} /> },
      { to: '/admin/stock/ledger', label: 'Журнал руху палива', icon: <BookOpen size={18} /> },
      { to: '/admin/stock/adjustments', label: 'Коригування', icon: <BookOpen size={18} /> },
      { to: '/admin/stock/reconcile', label: 'Перевірка складу', icon: <CheckSquare size={18} /> },
    ],
  },
  { to: '/admin/incidents', label: 'Інциденти', icon: <ShieldAlert size={18} /> },
  { to: '/admin/reports/vehicles', label: 'Звіт ТЗ', icon: <BarChart3 size={18} /> },
  {
    to: '/admin/references',
    label: 'Довідники',
    icon: <BookOpen size={18} />,
    children: [
      { to: '/admin/departments', label: 'Підрозділи', icon: <Building2 size={18} /> },
      { to: '/admin/vehicles', label: 'Транспорт', icon: <Truck size={18} /> },
      { to: '/admin/routes', label: 'Маршрути', icon: <Map size={18} /> },
      { to: '/admin/settings/density', label: 'Густина', icon: <Fuel size={18} /> },
      { to: '/admin/settings/operators', label: 'Оператори', icon: <Users size={18} /> },
      { to: '/admin/settings/requests', label: 'Налаштування заявок', icon: <CheckSquare size={18} /> },
    ],
  },
  { to: '/admin/settings/system', label: 'Система', icon: <Settings size={18} /> },
  { to: '/admin/settings/pdf-templates', label: 'PDF шаблони', icon: <FileText size={18} /> },
  { to: '/admin/settings/support', label: 'Підтримка', icon: <MessageSquare size={18} /> },
  { to: '/admin/profile', label: 'Профіль', icon: <User size={18} /> },
];

const operatorNav: NavItem[] = [
  { to: '/operator', label: 'Готово до видачі', icon: <CheckSquare size={18} /> },
  { to: '/operator/issued', label: 'Видано', icon: <Clock size={18} /> },
  { to: '/operator/profile', label: 'Профіль', icon: <User size={18} /> },
  { to: '/operator/support', label: 'Підтримка', icon: <MessageSquare size={18} /> },
];

const deptNav: NavItem[] = [
  { to: '/dept', label: 'Мої заявки', icon: <FileText size={18} /> },
  { to: '/dept/create', label: 'Створити заявку', icon: <PlusCircle size={18} /> },
  { to: '/dept/vehicles', label: 'Транспорт', icon: <Truck size={18} /> },
  { to: '/dept/routes', label: 'Маршрути', icon: <Map size={18} /> },
  { to: '/dept/profile', label: 'Профіль', icon: <User size={18} /> },
  { to: '/dept/support', label: 'Підтримка', icon: <MessageSquare size={18} /> },
];

const SidebarNav: React.FC<{ onNavigate?: () => void; adminIncidentsBadge?: number; adminRequestsBadge?: number }> = ({
  onNavigate,
  adminIncidentsBadge = 0,
  adminRequestsBadge = 0,
}) => {
  const { role, logout } = useAuth();

  const items = role === 'ADMIN' ? adminNav : role === 'OPERATOR' ? operatorNav : deptNav;
  const location = useLocation();

  const isItemActive = (item: NavItem) => {
    if (location.pathname === item.to) return true;
    if (location.pathname.startsWith(`${item.to}/`)) return true;
    if (item.children) {
      return item.children.some(c => location.pathname.startsWith(c.to));
    }
    return false;
  };

  return (
    <nav className="flex flex-col gap-1">
      <div className="mb-4">
        <div className="rounded-2xl border border-mil-700/70 bg-glass backdrop-blur px-4 py-3 shadow-soft">
          <div className="text-xs uppercase tracking-widest text-gray-400">Облік ПММ</div>
          <div className="text-sm font-semibold text-gray-200 mt-1">
            {role === 'ADMIN' ? 'Адміністратор' : role === 'OPERATOR' ? 'Оператор' : 'Підрозділ'}
          </div>
        </div>
      </div>
      {items.map(item => {
        const active = isItemActive(item);
        const hasChildren = item.children && item.children.length > 0;
        const badge = item.to === '/admin/incidents'
          ? adminIncidentsBadge
          : item.to === '/admin/requests'
            ? adminRequestsBadge
            : item.badge;
        return (
          <React.Fragment key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/admin' || item.to === '/operator' || item.to === '/dept'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `sidebar-link group relative overflow-hidden ${active ? 'sidebar-link-active' : ''}`
              }
            >
              {({ isActive }) => (
                <span className="relative flex items-center gap-3">
                  {active && (
                    <>
                      <span className="absolute -left-3 top-1/2 -translate-y-1/2 h-6 w-1 rounded-full bg-accent shadow-glowStrong" />
                      <span className="absolute inset-0 bg-accent/5" />
                    </>
                  )}
                  <span className={`relative ${active ? 'text-accent' : 'text-gray-500'} group-hover:text-gray-200 transition-colors`}>
                    {item.icon}
                  </span>
                  <span className={`relative flex-1 ${active ? 'text-accent' : ''}`}>{item.label}</span>
                  {badge && badge > 0 && (
                    <span className="relative inline-flex min-w-5 h-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold bg-danger/20 text-danger border border-danger/40">
                      {badge > 99 ? '99+' : badge}
                    </span>
                  )}
                  {hasChildren && (
                    <span className="relative opacity-0 group-hover:opacity-100 transition-opacity text-accent">›</span>
                  )}
                </span>
              )}
            </NavLink>
            {hasChildren && active && (
              <div className="ml-6 mt-1 flex flex-col gap-1">
                {item.children!.map(child => (
                  <NavLink
                    key={child.to}
                    to={child.to}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      `sidebar-link group relative overflow-hidden ${isActive ? 'sidebar-link-active' : ''}`
                    }
                  >
                    {({ isActive }) => (
                      <span className="relative flex items-center gap-3">
                        {isActive && (
                          <>
                            <span className="absolute -left-3 top-1/2 -translate-y-1/2 h-6 w-1 rounded-full bg-accent shadow-glowStrong" />
                            <span className="absolute inset-0 bg-accent/5" />
                          </>
                        )}
                        <span className={`relative ${isActive ? 'text-accent' : 'text-gray-500'} group-hover:text-gray-200 transition-colors`}>
                          {child.icon}
                        </span>
                        <span className={`relative flex-1 ${isActive ? 'text-accent' : ''}`}>{child.label}</span>
                        <span className="relative opacity-0 group-hover:opacity-100 transition-opacity text-accent">›</span>
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            )}
          </React.Fragment>
        );
      })}
      <div className="mt-4">
        <button onClick={logout} className="sidebar-link w-full text-danger hover:text-danger hover:bg-danger/10 shadow-none hover:shadow-soft">
          <LogOut size={18} />
          Вийти
        </button>
      </div>
    </nav>
  );
};

export default SidebarNav;
