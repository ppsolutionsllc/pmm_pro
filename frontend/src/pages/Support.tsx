import React, { useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import { MessageSquare, ExternalLink } from 'lucide-react';
import { api } from '../api';

const Support: React.FC = () => {
  const [support, setSupport] = useState<{ enabled: boolean; label: string; url: string } | null>(null);

  useEffect(() => {
    api.getSupport().then(setSupport).catch(() => {});
  }, []);

  return (
    <div>
      <PageHeader title="Підтримка" />
      <div className="card max-w-lg">
        <div className="flex flex-col items-center text-center py-8">
          <MessageSquare size={48} className="text-gray-600 mb-4" />
          {support?.enabled && support.url ? (
            <>
              <p className="text-gray-300 mb-4">{support.label || 'Зв\'язатися з підтримкою'}</p>
              <a href={support.url} target="_blank" rel="noopener noreferrer" className="btn-primary">
                <ExternalLink size={16} /> Відкрити
              </a>
            </>
          ) : (
            <p className="text-gray-500">Підтримка не налаштована. Зверніться до адміністратора.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Support;
