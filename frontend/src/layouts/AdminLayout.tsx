import React from 'react';
import { Outlet } from 'react-router-dom';
import TopStatusBar from '../components/TopStatusBar';
import SidebarNav from '../components/SidebarNav';
import Drawer from '../components/Drawer';
import { Menu, Fuel } from 'lucide-react';
import { api } from '../api';

const AdminLayout: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [unresolvedIncidents, setUnresolvedIncidents] = React.useState(0);
  const [newRequestsCount, setNewRequestsCount] = React.useState(0);

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--x', `${e.clientX - r.left}px`);
    el.style.setProperty('--y', `${e.clientY - r.top}px`);
  };

  const loadIncidentsBadge = React.useCallback(async () => {
    try {
      const resp: any = await api.getAdminIncidentsUnresolvedCount();
      setUnresolvedIncidents(Number(resp?.unresolved_count || 0));
    } catch {
      // no-op; badge can remain stale if API temporary unavailable
    }
  }, []);

  const loadRequestsBadge = React.useCallback(async () => {
    try {
      const rows: any[] = await api.getRequests({ status: 'SUBMITTED' });
      setNewRequestsCount(Array.isArray(rows) ? rows.length : 0);
    } catch {
      // no-op; badge can remain stale if API temporary unavailable
    }
  }, []);

  React.useEffect(() => {
    loadIncidentsBadge();
    loadRequestsBadge();
    const timer = window.setInterval(() => {
      loadIncidentsBadge();
      loadRequestsBadge();
    }, 45000);
    const onUpdated = () => {
      loadIncidentsBadge();
      loadRequestsBadge();
    };
    window.addEventListener('admin-incidents-updated', onUpdated as EventListener);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('admin-incidents-updated', onUpdated as EventListener);
    };
  }, [loadIncidentsBadge, loadRequestsBadge]);

  return (
    <div className="min-h-screen flex flex-col" onMouseMove={handleMove}>
      <TopStatusBar />
      <div className="flex flex-1">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex flex-col w-56 bg-surface border-r border-mil-700 flex-shrink-0">
          <div className="flex items-center gap-2 px-4 py-4 border-b border-mil-700">
            <Fuel size={24} className="text-accent" />
            <span className="font-bold text-accent text-lg">ПММ</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <SidebarNav adminIncidentsBadge={unresolvedIncidents} adminRequestsBadge={newRequestsCount} />
          </div>
        </aside>

        {/* Mobile drawer */}
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
          <SidebarNav
            onNavigate={() => setDrawerOpen(false)}
            adminIncidentsBadge={unresolvedIncidents}
            adminRequestsBadge={newRequestsCount}
          />
        </Drawer>

        {/* Main content */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Mobile header */}
          <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-surface border-b border-mil-700">
            <button onClick={() => setDrawerOpen(true)} className="p-1 rounded-lg hover:bg-mil-700 text-gray-400">
              <Menu size={22} />
            </button>
            <span className="font-bold text-accent">ПММ</span>
          </div>
          <div className="flex-1 p-4 lg:p-6 overflow-y-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
