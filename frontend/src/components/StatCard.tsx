import React from 'react';

interface Props {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: 'green' | 'orange' | 'blue' | 'red' | 'gray';
  subtitle?: string;
  onClick?: () => void;
}

const colorMap = {
  green: 'border-l-accent text-accent',
  orange: 'border-l-warn text-warn',
  blue: 'border-l-blue-400 text-blue-400',
  red: 'border-l-danger text-danger',
  gray: 'border-l-gray-500 text-gray-400',
};

const StatCard: React.FC<Props> = ({ title, value, icon, color = 'green', subtitle, onClick }) => (
  <div
    onClick={onClick}
    className={`card border-l-4 ${colorMap[color]} ${onClick ? 'cursor-pointer hover:bg-surface-light hover:shadow-glowStrong' : ''} transition-all`}
  >
    <div className="flex items-center justify-between">
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{title}</p>
        <p className="text-3xl font-extrabold tracking-tight">{value}</p>
        {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {icon && (
        <div className="rounded-2xl border border-mil-700/70 bg-mil-900/40 p-3 shadow-soft">
          <div className="text-gray-400">{icon}</div>
        </div>
      )}
    </div>
  </div>
);

export default StatCard;
