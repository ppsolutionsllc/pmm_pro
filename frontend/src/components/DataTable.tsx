import React from 'react';

interface Column<T> {
  key: string;
  title: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

function DataTable<T extends Record<string, any>>({ columns, data, onRowClick, emptyText = 'Дані відсутні' }: Props<T>) {
  if (data.length === 0) {
    return (
      <div className="card flex items-center justify-center py-12 text-gray-500">
        <div className="text-center">
          <div className="text-sm font-medium text-gray-300">{emptyText}</div>
          <div className="text-xs text-gray-500 mt-1">Спробуйте змінити фільтри або додати дані</div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-0 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-mil-700 bg-mil-900/40">
              {columns.map(col => (
                <th key={col.key} className={`px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider ${col.className || ''}`}>
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                className={`border-b border-mil-700/50 last:border-0 ${onRowClick ? 'cursor-pointer hover:bg-mil-800/40 hover:shadow-glow' : ''} transition-all`}
              >
                {columns.map(col => (
                  <td key={col.key} className={`px-4 py-3 text-gray-300 ${col.className || ''}`}>
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;
