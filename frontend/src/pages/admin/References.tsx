import React from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import { Building2, Truck, Map, Fuel, Users } from 'lucide-react';

const cards = [
  { to: '/admin/departments', label: 'Підрозділи', icon: <Building2 size={24} /> },
  { to: '/admin/vehicles', label: 'Транспорт', icon: <Truck size={24} /> },
  { to: '/admin/routes', label: 'Маршрути', icon: <Map size={24} /> },
  { to: '/admin/settings/density', label: 'Густина', icon: <Fuel size={24} /> },
  { to: '/admin/settings/operators', label: 'Оператори', icon: <Users size={24} /> },
];

const References: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div>
      <PageHeader title="Довідники" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map(c => (
          <div
            key={c.to}
            className="card hover:shadow-lg cursor-pointer flex items-center gap-4 p-4"
            onClick={() => navigate(c.to)}
          >
            <div className="text-accent">{c.icon}</div>
            <div className="font-semibold text-gray-200">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default References;
