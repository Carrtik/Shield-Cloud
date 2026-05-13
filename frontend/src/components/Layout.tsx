import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Shield, Home, FolderLock, Activity, Settings, Users, LogOut, Bell, Wifi, WifiOff, AlertTriangle, Key, X } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { NotificationToast } from './NotificationToast';
import { useEffect, useRef, useState } from 'react';
import { io as socketIO } from 'socket.io-client';
import { API } from '../config/api';

// ── Mobile-safe sidebar ───────────────────────────────────────────────────────
const Sidebar = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const { riskLevel, riskScore, user, logout, addNotification, notifications } = useAppStore();
  const navigate = useNavigate();
  const [connected, setConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [forceLogoutModal, setForceLogoutModal] = useState<{ reason: string; temp_password: string } | null>(null);
  const prevNotifCount = useRef(notifications.length);

  useEffect(() => {
    if (notifications.length > prevNotifCount.current) {
      setUnreadCount(c => c + (notifications.length - prevNotifCount.current));
    }
    prevNotifCount.current = notifications.length;
  }, [notifications]);

  // Connect to notification service Socket.IO
  useEffect(() => {
    const socket = socketIO(API.notifSocketUrl, {
      path: '/notifications',
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => { setConnected(true); });
    socket.on('disconnect', () => { setConnected(false); });

    socket.on('security_alert', (data: any) => {
      addNotification(`🚨 HNDL Attack neutralized! ML Score: ${((data.anomaly_score ?? 0) * 100).toFixed(0)}% · Re-login required.`, 'error');
    });

    socket.on('force_logout', (data: any) => {
      // Show modal with temp password BEFORE logging out
      setForceLogoutModal({ reason: data.reason, temp_password: data.temp_password });
      // Auto logout after 12 seconds
      setTimeout(() => {
        logout();
        navigate('/login');
      }, 12000);
    });

    socket.on('healing_complete', (data: any) => {
      addNotification(`✅ ${data.message}`, 'success');
    });

    return () => { socket.disconnect(); };
  }, []);

  const getRiskColor = () => {
    switch(riskLevel) {
      case 'LOW':      return 'text-accent border-accent';
      case 'MEDIUM':   return 'text-warning border-warning';
      case 'HIGH':     return 'text-danger border-danger';
      case 'CRITICAL': return 'text-danger border-danger bg-danger/20 animate-pulse';
      default:         return 'text-accent border-accent';
    }
  };

  const handleLogout = () => {
    logout();
    addNotification('Signed out successfully.', 'info');
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', icon: Home,       label: 'Dashboard' },
    { to: '/files',     icon: FolderLock, label: 'Files' },
    { to: '/security',  icon: Activity,   label: 'Security Center' },
    { to: '/admin',     icon: Users,      label: 'Admin Panel' },
    { to: '/settings',  icon: Settings,   label: 'Settings' },
  ];

  return (
    <>
      {/* Force Logout Modal */}
      {forceLogoutModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/90 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-md p-6 border-2 border-danger shadow-[0_0_60px_rgba(239,68,68,0.4)] text-center">
            <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-3 animate-pulse" />
            <h2 className="text-xl font-black text-danger mb-2 uppercase tracking-wider">Session Terminated</h2>
            <p className="text-gray-300 text-sm mb-4">{forceLogoutModal.reason}</p>
            <div className="bg-black/40 border border-purple-500/30 rounded-xl p-4 mb-4">
              <p className="text-purple-400 text-xs uppercase tracking-wider mb-2 flex items-center justify-center gap-1">
                <Key className="w-3 h-3" /> Temporary Password (valid 24h)
              </p>
              <p className="font-mono text-xl font-black text-purple-200 tracking-widest">{forceLogoutModal.temp_password}</p>
              <p className="text-gray-500 text-xs mt-2">Screenshot this or check your security email</p>
            </div>
            <p className="text-gray-500 text-xs">You will be redirected to login in 12 seconds...</p>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="mt-4 w-full btn-primary"
            >
              Sign in again now
            </button>
          </div>
        </div>
      )}

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={onClose} />
      )}

      {/* Sidebar panel */}
      <div className={`
        fixed left-0 top-0 h-full z-50 flex flex-col p-5
        w-64 glass-panel
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center border border-primary/30 flex-shrink-0">
            <Shield className="text-primary w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-lg tracking-tight text-white">ShieldCloud</h1>
            <p className="text-[10px] text-gray-400 font-medium tracking-wider">PQC SECURED</p>
          </div>
          <div className="ml-auto flex items-center gap-1">
            <button
              className="relative p-1.5 rounded-lg hover:bg-white/10 transition-colors"
              onClick={() => setUnreadCount(0)}
              title="Notifications"
            >
              <Bell className="w-4 h-4 text-gray-400" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-danger rounded-full flex items-center justify-center text-[9px] font-black text-white animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            {/* Close button (mobile only) */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 transition-colors lg:hidden"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* User badge */}
        {user && (
          <div className="mb-4 px-3 py-2.5 bg-white/5 rounded-xl border border-white/10 flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-primary/30 flex items-center justify-center text-primary font-bold text-sm flex-shrink-0">
              {user.name?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-semibold truncate">{user.name}</p>
              <p className="text-gray-500 text-xs truncate">{user.email}</p>
            </div>
          </div>
        )}

        {/* Risk indicator */}
        <div className={`mb-5 p-3 rounded-xl border ${getRiskColor()} bg-surfaceHighlight/30 flex items-center gap-3`}>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-0.5">System Risk</p>
            <div className="font-bold text-base">{riskLevel}</div>
          </div>
          <div className="text-2xl font-black flex-shrink-0">{(riskScore * 100).toFixed(0)}</div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm ${
                  isActive ? 'bg-primary/20 text-white border border-primary/30' : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" /> {label}
            </NavLink>
          ))}
        </nav>

        {/* Connection status */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg mt-2 text-xs font-medium ${connected ? 'text-accent' : 'text-gray-600'}`}>
          {connected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {connected ? 'Risk Engine Connected' : 'Reconnecting...'}
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 text-gray-400 hover:text-danger hover:bg-danger/10 rounded-lg transition-all mt-1 text-sm"
        >
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </div>
    </>
  );
};

export const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 rounded-full blur-[120px] pointer-events-none" />

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content — shifted right on desktop, full width on mobile */}
      <main className="flex-1 lg:ml-64 min-h-screen relative z-10 flex flex-col">
        {/* Mobile top bar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 glass-panel border-b border-white/10 sticky top-0 z-30">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <div className="w-5 h-4 flex flex-col justify-between">
              <span className="block h-0.5 bg-gray-300 rounded" />
              <span className="block h-0.5 bg-gray-300 rounded" />
              <span className="block h-0.5 bg-gray-300 rounded" />
            </div>
          </button>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <span className="font-bold text-white">ShieldCloud</span>
          </div>
          <div className="ml-auto">
            <span className="text-[10px] font-bold uppercase text-accent border border-accent/30 bg-accent/10 px-2 py-0.5 rounded-full">PQC</span>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </div>
      </main>

      {/* Global notification overlay */}
      <NotificationToast />
    </div>
  );
};

