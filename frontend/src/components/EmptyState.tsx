import React from 'react';
import { Inbox } from 'lucide-react';

interface Props {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

const EmptyState: React.FC<Props> = ({ title = 'Немає даних', message, icon, action }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="text-gray-600 mb-4">{icon || <Inbox size={48} />}</div>
    <h3 className="text-lg font-medium text-gray-400 mb-1">{title}</h3>
    {message && <p className="text-sm text-gray-500 mb-4">{message}</p>}
    {action}
  </div>
);

export default EmptyState;
