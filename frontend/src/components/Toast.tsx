import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastCtx {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastCtx>({ toast: () => {} });
export const useToast = () => useContext(ToastContext);

let idCounter = 0;

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={18} />,
  error: <XCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
};

const colors: Record<ToastType, string> = {
  success: 'bg-accent/10 border-accent/30 text-accent',
  error: 'bg-danger/10 border-danger/30 text-danger',
  warning: 'bg-warn/10 border-warn/30 text-warn',
  info: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, type: ToastType = 'success') => {
    const id = ++idCounter;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const remove = (id: number) => setToasts(prev => prev.filter(t => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
        {toasts.map(t => (
          <div key={t.id} className={`flex items-center gap-3 px-4 py-3 rounded-2xl border shadow-glow bg-glass backdrop-blur animate-toastIn ${colors[t.type]}`}>
            {icons[t.type]}
            <span className="text-sm flex-1">{t.message}</span>
            <button onClick={() => remove(t.id)} className="opacity-60 hover:opacity-100 transition-opacity"><X size={14} /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
