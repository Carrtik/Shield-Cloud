import React, { useEffect, useState } from 'react';
import { Users, Shield, HardDrive, RefreshCw, Crown, User, AlertTriangle } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import axios from 'axios';
import { API } from '../config/api';

function formatDate(ts: string): string {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString();
}

export const AdminPanel = () => {
  const { token, user, addNotification } = useAppStore();
  const [users, setUsers] = useState<any[]>([]);
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [healing, setHealing] = useState(false);

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Always fetch files (accessible)
        const filesRes = await axios.get(`${API.storage}/files`, { headers: authHeaders });
        setFiles(filesRes.data.files || []);

        // Only fetch users if admin
        if (isAdmin) {
          const usersRes = await axios.get(`${API.auth}/users`, { headers: authHeaders });
          setUsers(usersRes.data.users || []);
        }
      } catch (e: any) {
        // If not admin, users list is empty — still show file stats
        console.log('[Admin] User list unavailable (non-admin)');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const triggerGlobalRotation = async () => {
    setHealing(true);
    try {
      const res = await axios.post(`${API.encrypt}/self-heal/rotate-keys`);
      addNotification(`Global rotation complete! ${res.data.files_rotated} files re-encrypted.`, 'success');
    } catch (e: any) {
      addNotification('Rotation failed: ' + e.message, 'error');
    } finally {
      setHealing(false);
    }
  };

  // Build per-user file stats
  const filesByUser = files.reduce((acc: Record<string, number>, f: any) => {
    acc[f.owner_id] = (acc[f.owner_id] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Admin Panel</h1>
          <p className="text-gray-400 mt-1">
            {isAdmin ? 'Full system control and user management' : 'System overview (admin login required for user management)'}
          </p>
        </div>
        <button
          onClick={triggerGlobalRotation}
          disabled={healing}
          className="btn-primary flex items-center gap-2 bg-warning/80 hover:bg-warning shadow-[0_0_15px_rgba(245,158,11,0.4)]"
        >
          {healing ? <><RefreshCw className="w-4 h-4 animate-spin" /> Rotating...</> : <><Shield className="w-4 h-4" /> Trigger Global Key Rotation</>}
        </button>
      </header>

      {/* System Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Users', value: isAdmin ? users.length : '—', icon: Users, note: isAdmin ? 'registered accounts' : 'admin only' },
          { label: 'Total Files', value: files.length, icon: HardDrive, note: 'across all vaults' },
          { label: 'Encrypted Files', value: files.filter(f => f.kyber_ciphertext).length, icon: Shield, note: 'ML-KEM-1024 protected' },
        ].map(({ label, value, icon: Icon, note }) => (
          <div key={label} className="glass-card p-6">
            <div className="flex items-start justify-between mb-3">
              <p className="text-gray-400 font-medium">{label}</p>
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                <Icon className="w-5 h-5 text-primary" />
              </div>
            </div>
            <p className="text-4xl font-black text-white">{loading ? '—' : value}</p>
            <p className="text-gray-600 text-xs mt-1">{note}</p>
          </div>
        ))}
      </div>

      {/* User Table — only if admin */}
      {isAdmin ? (
        <div className="glass-card overflow-hidden">
          <div className="px-6 py-4 border-b border-white/5">
            <h2 className="font-semibold text-white flex items-center gap-2"><Users className="w-4 h-4" /> Registered Users</h2>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-16"><RefreshCw className="w-8 h-8 text-primary animate-spin" /></div>
          ) : users.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No users registered yet.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {users.map(u => (
                <div key={u.id} className="flex items-center gap-4 px-6 py-4 hover:bg-white/5 transition-colors">
                  <div className="w-10 h-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                    {u.role === 'admin'
                      ? <Crown className="w-5 h-5 text-warning" />
                      : <User className="w-5 h-5 text-primary" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{u.email}</p>
                    <p className="text-gray-500 text-xs">Joined {formatDate(u.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-white font-bold">{filesByUser[u.id] || 0}</p>
                      <p className="text-gray-500 text-xs">files</p>
                    </div>
                    <span className={`text-[10px] font-bold uppercase px-2.5 py-1 rounded-full border ${u.role === 'admin' ? 'bg-warning/10 text-warning border-warning/20' : 'bg-primary/10 text-primary border-primary/20'}`}>
                      {u.role}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card p-8 text-center border border-warning/20">
          <AlertTriangle className="w-12 h-12 text-warning mx-auto mb-3 opacity-60" />
          <h2 className="text-white font-bold text-lg mb-2">Admin Access Required</h2>
          <p className="text-gray-400 text-sm">Sign in with an admin account to view user management. You can still trigger key rotations above.</p>
        </div>
      )}

      {/* Recent Files Overview */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5">
          <h2 className="font-semibold text-white flex items-center gap-2"><HardDrive className="w-4 h-4" /> Recent Vault Activity</h2>
        </div>
        <div className="divide-y divide-white/5">
          {files.slice(0, 10).map(f => (
            <div key={f.id} className="flex items-center gap-4 px-6 py-3 hover:bg-white/5 transition-colors">
              <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
                <Shield className="w-4 h-4 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{f.original_name}</p>
                <p className="text-gray-600 text-xs truncate font-mono">Owner: {f.owner_id?.slice(0, 16)}...</p>
              </div>
              <span className="text-[10px] font-bold bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded-full flex-shrink-0">
                {f.kyber_ciphertext ? 'ML-KEM-1024' : 'Pending'}
              </span>
            </div>
          ))}
          {files.length === 0 && !loading && (
            <div className="text-center py-12 text-gray-500">No files in vault yet.</div>
          )}
        </div>
      </div>
    </div>
  );
};
