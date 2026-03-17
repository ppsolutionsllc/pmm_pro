import React from 'react';
import { Outlet } from 'react-router-dom';
import TopStatusBar from '../components/TopStatusBar';
import SidebarNav from '../components/SidebarNav';
import Drawer from '../components/Drawer';
import { Menu, Fuel } from 'lucide-react';

const MobileLayout: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const handleMove = (el: HTMLDivElement, clientX: number, clientY: number) => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--x', `${clientX - r.left}px`);
    el.style.setProperty('--y', `${clientY - r.top}px`);
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      onMouseMove={(e) => handleMove(e.currentTarget, e.clientX, e.clientY)}
      onTouchMove={(e) => {
        const t = e.touches[0];
        if (!t) return;
        handleMove(e.currentTarget, t.clientX, t.clientY);
      }}
    >
      <TopStatusBar />

      <div className="flex flex-1 min-h-0">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex flex-col w-56 bg-surface border-r border-mil-700 flex-shrink-0">
          <div className="flex items-center gap-2 px-4 py-4 border-b border-mil-700">
            <Fuel size={24} className="text-accent" />
            <span className="font-bold text-accent text-lg">ПММ</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <SidebarNav />
          </div>
        </aside>

        {/* Mobile header + drawer */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-surface border-b border-mil-700">
            <button onClick={() => setDrawerOpen(true)} className="p-1 rounded-lg hover:bg-mil-700 text-gray-400">
              <Menu size={22} />
            </button>
            <Fuel size={22} className="text-accent" />
            <span className="font-bold text-accent">ПММ</span>
          </div>
          <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
            <SidebarNav onNavigate={() => setDrawerOpen(false)} />
          </Drawer>
          <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};

export default MobileLayout;
