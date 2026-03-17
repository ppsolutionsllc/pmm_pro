import React from 'react';

interface Props {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const PageHeader: React.FC<Props> = ({ title, subtitle, actions }) => (
  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
    <div className="relative">
      <h1 className="text-2xl font-extrabold text-gray-100 tracking-tight">
        <span className="bg-clip-text text-transparent bg-gradient-to-r from-gray-100 via-gray-100 to-accent/80">{title}</span>
      </h1>
      <div className="mt-2 h-px w-24 bg-gradient-to-r from-accent/70 to-transparent" />
      {subtitle && <p className="text-sm text-gray-400 mt-2 max-w-2xl">{subtitle}</p>}
    </div>
    {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
  </div>
);

export default PageHeader;
