import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth';

import AdminLayout from './layouts/AdminLayout';
import MobileLayout from './layouts/MobileLayout';

import Login from './pages/Login';
import NotFound from './pages/NotFound';
import Profile from './pages/Profile';
import Support from './pages/Support';

import Dashboard from './pages/admin/Dashboard';
import RequestsList from './pages/admin/RequestsList';
import AdminRequestDetail from './pages/admin/RequestDetail';
import StockReceipts from './pages/admin/StockReceipts';
import StockBalance from './pages/admin/StockBalance';
import StockLedger from './pages/admin/StockLedger';
import StockReconcile from './pages/admin/StockReconcile';
import StockAdjustments from './pages/admin/StockAdjustments';
import StockAdjustmentDetail from './pages/admin/StockAdjustmentDetail';
import Departments from './pages/admin/Departments';
import DepartmentDetail from './pages/admin/DepartmentDetail';
import Vehicles from './pages/admin/Vehicles';
import AdminRoutes from './pages/admin/Routes';
import SettingsDensity from './pages/admin/SettingsDensity';
import SettingsOperators from './pages/admin/SettingsOperators';
import SettingsSystem from './pages/admin/SettingsSystem';
import SettingsSupport from './pages/admin/SettingsSupport';
import SettingsRequests from './pages/admin/SettingsRequests';
import References from './pages/admin/References';
import VehicleReport from './pages/admin/VehicleReport';
import DepartmentReport from './pages/admin/DepartmentReport';
import Incidents from './pages/admin/Incidents';
import IncidentDetail from './pages/admin/IncidentDetail';
import PdfTemplates from './pages/admin/PdfTemplates';
import PdfTemplateEditor from './pages/admin/PdfTemplateEditor';

import ReadyToIssue from './pages/operator/ReadyToIssue';
import Issued from './pages/operator/Issued';

import MyRequests from './pages/dept/MyRequests';
import CreateRequest from './pages/dept/CreateRequest';
import DeptRequestDetail from './pages/dept/RequestDetail';
import DeptVehicles from './pages/dept/Vehicles';
import DeptRoutes from './pages/dept/Routes';

function RequireAuth({ children, roles }: { children: React.ReactNode; roles: string[] }) {
  const { token, role, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Завантаження...</div>;
  if (!token || !role) return <Navigate to="/login" replace />;
  if (!roles.includes(role)) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectHome() {
  const { role, token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (role === 'ADMIN') return <Navigate to="/admin" replace />;
  if (role === 'OPERATOR') return <Navigate to="/operator" replace />;
  return <Navigate to="/dept" replace />;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RedirectHome />} />

      {/* ADMIN routes */}
      <Route path="/admin" element={<RequireAuth roles={['ADMIN']}><AdminLayout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="requests" element={<RequestsList />} />
        <Route path="requests/:id" element={<AdminRequestDetail />} />
        <Route path="stock/receipts" element={<StockReceipts />} />
        <Route path="stock/balance" element={<StockBalance />} />
        <Route path="stock/ledger" element={<StockLedger />} />
        <Route path="stock/adjustments" element={<StockAdjustments />} />
        <Route path="stock/adjustments/:id" element={<StockAdjustmentDetail />} />
        <Route path="stock/reconcile" element={<StockReconcile />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="incidents/:id" element={<IncidentDetail />} />
        <Route path="reports/vehicles" element={<VehicleReport />} />
        <Route path="reports/departments" element={<DepartmentReport />} />
        <Route path="departments" element={<Departments />} />
        <Route path="departments/:id" element={<DepartmentDetail />} />
        <Route path="vehicles" element={<Vehicles />} />
        <Route path="routes" element={<AdminRoutes />} />
        <Route path="references" element={<References />} />
        <Route path="settings/density" element={<SettingsDensity />} />
        <Route path="settings/operators" element={<SettingsOperators />} />
        <Route path="settings/system" element={<SettingsSystem />} />
        <Route path="settings/pdf-templates" element={<PdfTemplates />} />
        <Route path="settings/pdf-templates/:id" element={<PdfTemplateEditor />} />
        <Route path="settings/requests" element={<SettingsRequests />} />
        <Route path="settings/support" element={<SettingsSupport />} />
        <Route path="profile" element={<Profile />} />
      </Route>

      {/* OPERATOR routes */}
      <Route path="/operator" element={<RequireAuth roles={['OPERATOR']}><MobileLayout /></RequireAuth>}>
        <Route index element={<ReadyToIssue />} />
        <Route path="issued" element={<Issued />} />
        <Route path="profile" element={<Profile />} />
        <Route path="support" element={<Support />} />
      </Route>

      {/* DEPT_USER routes */}
      <Route path="/dept" element={<RequireAuth roles={['DEPT_USER']}><MobileLayout /></RequireAuth>}>
        <Route index element={<MyRequests />} />
        <Route path="create" element={<CreateRequest />} />
        <Route path="edit/:id" element={<CreateRequest />} />
        <Route path="requests/:id" element={<DeptRequestDetail />} />
        <Route path="vehicles" element={<DeptVehicles />} />
        <Route path="routes" element={<DeptRoutes />} />
        <Route path="profile" element={<Profile />} />
        <Route path="support" element={<Support />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
