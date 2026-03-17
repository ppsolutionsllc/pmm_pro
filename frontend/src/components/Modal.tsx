import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' };

const Modal: React.FC<Props> = ({ open, onClose, title, children, footer, size = 'md' }) => {
  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/65 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative w-full ${sizeMap[size]} border border-mil-600/80 rounded-2xl shadow-glowStrong bg-surface bg-glass backdrop-blur overflow-hidden animate-modalIn`}>
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-40" />
        <div className="relative flex items-center justify-between px-5 py-4 border-b border-mil-700/70">
          <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-mil-700 text-gray-400 hover:text-gray-200 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="relative px-5 py-4 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && <div className="relative flex items-center justify-end gap-2 px-5 py-3 border-t border-mil-700/70">{footer}</div>}
      </div>
    </div>
  );
};

export default Modal;
