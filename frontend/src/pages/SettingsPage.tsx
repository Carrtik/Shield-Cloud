import React, { useState } from 'react';
import {
  User, Mail, Lock, Shield, Eye, EyeOff, Loader2, CheckCircle2,
  Bell, BellOff, Smartphone, LogOut, Key
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import axios from 'axios';
import { API } from '../config/api';
import { useNavigate } from 'react-router-dom';

const SectionCard = ({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) => (
  <div className="glass-card overflow-hidden">
    <div className="px-6 py-4 border-b border-white/5 flex items-center gap-2">
      <Icon className="w-4 h-4 text-primary" />
      <h2 className="font-semibold text-white">{title}</h2>
    </div>
    <div className="p-6">{children}</div>
  </div>
);

export const SettingsPage = () => {
  const { user, token, logout, addNotification } = useAppStore();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [changingPw, setChangingPw] = useState(false);
  const [pwSuccess, setPwSuccess] = useState(false);

  const [emailAlerts, setEmailAlerts] = useState(true);
  const [toastAlerts, setToastAlerts] = useState(true);

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      addNotification('New passwords do not match.', 'error');
      return;
    }
    if (newPassword.length < 6) {
      addNotification('Password must be at least 6 characters.', 'error');
      return;
    }
    setChangingPw(true);
    setPwSuccess(false);
    try {
      await axios.post(`${API.auth}/change-password`, { currentPassword, newPassword }, { headers: authHeaders });
      addNotification('Password updated successfully!', 'success');
      setPwSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (e: any) {
      addNotification(e?.response?.data?.message || 'Failed to change password.', 'error');
    } finally {
      setChangingPw(false);
    }
  };

  const handleSignOut = () => {
    logout();
    addNotification('Signed out of all devices.', 'info');
    navigate('/login');
  };

  const Toggle = ({ value, onChange }: { value: boolean; onChange: () => void }) => (
    <button
      onClick={onChange}
      className={`relative w-12 h-6 rounded-full transition-colors duration-200 flex-shrink-0 ${value ? 'bg-primary' : 'bg-gray-700'}`}
    >
      <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${value ? 'translate-x-6' : 'translate-x-0'}`} />
    </button>
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header>
        <h1 className="text-3xl font-bold text-white tracking-tight">Account Settings</h1>
        <p className="text-gray-400 mt-1">Manage your ShieldCloud account and security preferences</p>
      </header>

      {/* Profile */}
      <SectionCard title="Profile" icon={User}>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center text-2xl font-black text-primary">
            {user?.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <p className="text-white font-bold text-lg">{user?.name || 'Unknown User'}</p>
            <p className="text-gray-400 flex items-center gap-1.5 text-sm"><Mail className="w-3.5 h-3.5" />{user?.email}</p>
            <span className={`mt-1 inline-block text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${user?.role === 'admin' ? 'bg-warning/10 text-warning border-warning/20' : 'bg-primary/10 text-primary border-primary/20'}`}>
              {user?.role || 'user'}
            </span>
          </div>
        </div>
        <div className="bg-black/20 rounded-xl p-4 border border-white/5">
          <p className="text-xs text-gray-500 mb-1">Account ID</p>
          <p className="text-gray-400 font-mono text-sm break-all">{user?.id || '—'}</p>
        </div>
      </SectionCard>

      {/* Change Password */}
      <SectionCard title="Change Password" icon={Lock}>
        <form onSubmit={handleChangePassword} className="space-y-4">
          {/* Current password */}
          <div>
            <label className="block text-gray-400 text-sm mb-1.5">Current Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type={showCurrent ? 'text' : 'password'}
                value={currentPassword}
                onChange={e => setCurrentPassword(e.target.value)}
                required
                placeholder="Enter current password"
                className="w-full bg-black/30 border border-white/10 rounded-xl pl-10 pr-10 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              />
              <button type="button" onClick={() => setShowCurrent(!showCurrent)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          {/* New password */}
          <div>
            <label className="block text-gray-400 text-sm mb-1.5">New Password</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                required
                minLength={6}
                placeholder="At least 6 characters"
                className="w-full bg-black/30 border border-white/10 rounded-xl pl-10 pr-10 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              />
              <button type="button" onClick={() => setShowNew(!showNew)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          {/* Confirm */}
          <div>
            <label className="block text-gray-400 text-sm mb-1.5">Confirm New Password</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                placeholder="Repeat new password"
                className={`w-full bg-black/30 border rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-1 transition-all ${confirmPassword && newPassword !== confirmPassword ? 'border-danger/50 focus:ring-danger/30 focus:border-danger/50' : 'border-white/10 focus:border-primary/50 focus:ring-primary/30'}`}
              />
            </div>
            {confirmPassword && newPassword !== confirmPassword && (
              <p className="text-danger text-xs mt-1">Passwords do not match</p>
            )}
          </div>

          <button type="submit" disabled={changingPw} className="btn-primary flex items-center gap-2">
            {changingPw ? <><Loader2 className="w-4 h-4 animate-spin" /> Updating...</> : pwSuccess ? <><CheckCircle2 className="w-4 h-4" /> Updated!</> : 'Update Password'}
          </button>
        </form>
      </SectionCard>

      {/* Notification Preferences */}
      <SectionCard title="Notification Preferences" icon={Bell}>
        <div className="space-y-4">
          {[
            { label: 'Email Security Alerts', description: 'Receive email notifications when a threat is detected and neutralized', icon: Mail, value: emailAlerts, onChange: () => setEmailAlerts(!emailAlerts) },
            { label: 'In-App Toast Alerts', description: 'Show real-time toast notifications in the dashboard', icon: Bell, value: toastAlerts, onChange: () => setToastAlerts(!toastAlerts) },
          ].map(({ label, description, icon: Icon, value, onChange }) => (
            <div key={label} className="flex items-center justify-between gap-4 p-4 bg-black/20 rounded-xl border border-white/5">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary/10 rounded-lg border border-primary/20 flex-shrink-0">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-white font-medium text-sm">{label}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{description}</p>
                </div>
              </div>
              <Toggle value={value} onChange={onChange} />
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Security */}
      <SectionCard title="Session & Security" icon={Shield}>
        <div className="space-y-3">
          <div className="p-4 bg-black/20 rounded-xl border border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent/10 rounded-lg border border-accent/20">
                <Smartphone className="w-4 h-4 text-accent" />
              </div>
              <div>
                <p className="text-white font-medium text-sm">Current Session</p>
                <p className="text-gray-500 text-xs">Active — JWT expires in 7 days</p>
              </div>
            </div>
            <span className="w-2 h-2 bg-accent rounded-full" />
          </div>

          <div className="p-4 bg-black/20 rounded-xl border border-white/5">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                <Shield className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-white font-medium text-sm">Encryption Status</p>
                <p className="text-gray-500 text-xs">All files protected with ML-KEM-1024 + AES-256-GCM</p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {['AES-256-GCM', 'ML-KEM-1024', 'bcrypt (x12)', 'JWT RS256'].map(t => (
                <span key={t} className="text-[10px] font-mono text-primary/80 bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">{t}</span>
              ))}
            </div>
          </div>

          <button
            onClick={handleSignOut}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-danger/10 hover:bg-danger/20 text-danger border border-danger/20 rounded-xl font-medium transition-all duration-200"
          >
            <LogOut className="w-4 h-4" /> Sign Out of All Devices
          </button>
        </div>
      </SectionCard>
    </div>
  );
};
