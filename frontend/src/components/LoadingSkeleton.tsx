import React from 'react';

interface Props {
  rows?: number;
  type?: 'table' | 'cards' | 'form';
}

const Shimmer: React.FC = () => (
  <div className="pointer-events-none absolute inset-0 overflow-hidden">
    <div className="absolute inset-0 -translate-x-full bg-accent-sheen opacity-40 animate-shimmer" />
  </div>
);

const LoadingSkeleton: React.FC<Props> = ({ rows = 5, type = 'table' }) => {
  if (type === 'cards') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card relative overflow-hidden">
            <Shimmer />
            <div className="h-3 bg-mil-700/70 rounded w-1/2 mb-3" />
            <div className="h-8 bg-mil-700/60 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'form') {
    return (
      <div className="card relative overflow-hidden space-y-4">
        <Shimmer />
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i}>
            <div className="h-3 bg-mil-700/70 rounded w-1/4 mb-2" />
            <div className="h-10 bg-mil-700/60 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="card p-0 overflow-hidden relative">
      <Shimmer />
      <div className="border-b border-mil-700 bg-mil-800/50 px-4 py-3 flex gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-3 bg-mil-700/70 rounded w-24" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-3 border-b border-mil-700/50 flex gap-4">
          {Array.from({ length: 4 }).map((_, j) => (
            <div key={j} className="h-4 bg-mil-700/60 rounded w-24" />
          ))}
        </div>
      ))}
    </div>
  );
};

export default LoadingSkeleton;
