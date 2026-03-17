import React from 'react';
import { requestStatusLabel } from '../utils/humanLabels';

const statusConfig: Record<string, { label: string; className: string }> = {
  DRAFT: { label: 'Чернетка', className: 'bg-gray-600/30 text-gray-300' },
  SUBMITTED: { label: 'Подано', className: 'bg-blue-500/20 text-blue-400' },
  APPROVED: { label: 'Затверджено', className: 'bg-accent/20 text-accent' },
  ISSUED_BY_OPERATOR: { label: 'Видано', className: 'bg-warn/20 text-warn' },
  POSTED: { label: 'Проведено', className: 'bg-emerald-500/20 text-emerald-400' },
  REJECTED: { label: 'Відхилено', className: 'bg-danger/20 text-danger' },
  CANCELED: { label: 'Скасовано', className: 'bg-gray-500/20 text-gray-400' },
};

interface Props {
  status: string;
  isRejected?: boolean;
}

const StatusBadge: React.FC<Props> = ({ status, isRejected }) => {
  if (status === 'DRAFT' && isRejected) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-danger/20 text-danger">
        Відхилено
      </span>
    );
  }
  const cfg = statusConfig[status] || { label: requestStatusLabel(status), className: 'bg-gray-600/30 text-gray-300' };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.className}`}>
      {cfg.label}
    </span>
  );
};

export default StatusBadge;
