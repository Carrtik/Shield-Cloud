import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { FilesPage } from './pages/FilesPage';
import { SecurityCenter } from './pages/SecurityCenter';
import { AdminPanel } from './pages/AdminPanel';
import { SettingsPage } from './pages/SettingsPage';
import { useAppStore } from './store/useAppStore';

// Guard that redirects to /login if no token
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAppStore();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/files"     element={<FilesPage />} />
          <Route path="/security"  element={<SecurityCenter />} />
          <Route path="/admin"     element={<AdminPanel />} />
          <Route path="/settings"  element={<SettingsPage />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default App;
