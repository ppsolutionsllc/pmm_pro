import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Wifi, WifiOff, MessageSquare } from 'lucide-react';
import { useAuth } from '../auth';

const TopStatusBar: React.FC = () => {
  const { role } = useAuth();
  const [online, setOnline] = useState(navigator.onLine);

  const supportTo = role === 'ADMIN' ? '/admin/settings/support' : role === 'OPERATOR' ? '/operator/support' : '/dept/support';

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);

  return (
    <div className={`flex items-center justify-between gap-3 py-1 px-4 text-xs font-medium ${online ? 'bg-accent/10 text-accent' : 'bg-danger/20 text-danger'}`}>
      <div className="flex items-center justify-center gap-2">
        {online ? <Wifi size={14} /> : <WifiOff size={14} />}
        {online ? 'Онлайн' : 'Офлайн — зміни не зберігаються'}
      </div>
      <NavLink
        to={supportTo}
        className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-colors"
        title="Підтримка"
      >
        <MessageSquare size={14} />
        Підтримка
      </NavLink>
    </div>
  );
};

export default TopStatusBar;
