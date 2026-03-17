import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from './api';

export type UserRole = 'ADMIN' | 'OPERATOR' | 'DEPT_USER';

export interface User {
  id: number;
  login: string;
  full_name: string | null;
  phone: string | null;
  rank?: string | null;
  position?: string | null;
  role: UserRole;
  department_id: number | null;
  is_active: boolean;
}

interface AuthCtx {
  token: string | null;
  user: User | null;
  role: UserRole | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthCtx>({
  token: null,
  user: null,
  role: null,
  login: async () => {},
  logout: () => {},
  loading: true,
});

export const useAuth = () => useContext(AuthContext);

function getStoredToken(): string | null {
  return sessionStorage.getItem('token');
}

function getStoredRole(): UserRole | null {
  return sessionStorage.getItem('role') as UserRole | null;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const u = await api.me();
      setUser(u);
    } catch {
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('role');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  const login = async (username: string, password: string) => {
    const data = await api.login(username, password);
    const t = data.access_token;
    const payload = JSON.parse(atob(t.split('.')[1]));
    sessionStorage.setItem('token', t);
    sessionStorage.setItem('role', payload.role);
    setToken(t);
    setLoading(true);
  };

  const logout = () => {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('role');
    setToken(null);
    setUser(null);
  };

  const role = user?.role ?? getStoredRole();

  return (
    <AuthContext.Provider value={{ token, user, role, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
