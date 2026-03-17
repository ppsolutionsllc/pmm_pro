import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

const Drawer: React.FC<Props> = ({ open, onClose, children }) => {
  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden" onClick={onClose} />}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-surface border-r border-mil-700 transform transition-transform duration-300 lg:hidden ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-mil-700">
          <span className="font-bold text-accent text-lg">☰ Меню</span>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-mil-700 text-gray-400">
            <X size={20} />
          </button>
        </div>
        <div className="p-3 overflow-y-auto h-full">{children}</div>
      </div>
    </>
  );
};

export default Drawer;
