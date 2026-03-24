import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Fuel, Eye, EyeOff } from 'lucide-react';
import { api } from '../api';

type SupportLink = {
  enabled: boolean;
  label: string;
  url: string;
};

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [support, setSupport] = useState<SupportLink | null>(null);

  useEffect(() => {
    let alive = true;
    api.getSupportPublic()
      .then((res) => {
        if (!alive) return;
        setSupport({
          enabled: Boolean(res?.enabled),
          label: (res?.label || '').trim(),
          url: (res?.url || '').trim(),
        });
      })
      .catch(() => {
        if (!alive) return;
        setSupport(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      const role = sessionStorage.getItem('role') || localStorage.getItem('role');
      if (role === 'ADMIN') navigate('/admin');
      else if (role === 'OPERATOR') navigate('/operator');
      else navigate('/dept');
    } catch (err: any) {
      setError(err.message || 'Помилка входу');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-dark p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
            <Fuel size={32} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-gray-100">Облік ПММ</h1>
          <p className="text-sm text-gray-500 mt-1">Увійдіть до системи</p>
        </div>

        <form onSubmit={submit} className="card space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Логін</label>
            <input
              className="input-field"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Введіть логін"
              autoFocus
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Пароль</label>
            <div className="relative">
              <input
                className="input-field pr-10"
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Введіть пароль"
                required
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
            {loading ? 'Вхід...' : 'Увійти'}
          </button>

          <button
            type="button"
            className="btn-secondary w-full justify-center"
            onClick={() => {
              if (support?.enabled && support.url) {
                window.open(support.url, '_blank', 'noopener,noreferrer');
                return;
              }
              setError('Підтримка тимчасово недоступна: не налаштовано посилання');
            }}
          >
            {support?.label || 'Підтримка'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
