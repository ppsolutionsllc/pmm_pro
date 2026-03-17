import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';

const NotFound: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-surface-dark p-4">
    <div className="text-center">
      <ShieldOff size={64} className="text-gray-600 mx-auto mb-4" />
      <h1 className="text-4xl font-bold text-gray-300 mb-2">404</h1>
      <p className="text-gray-500 mb-6">Сторінку не знайдено або доступ заборонено</p>
      <Link to="/" className="btn-primary">На головну</Link>
    </div>
  </div>
);

export default NotFound;
