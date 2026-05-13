import React, { useEffect, useState, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { HardDrive, ShieldAlert, Cpu, ActivitySquare, ShieldCheck, DownloadCloud, Skull, Code, RefreshCw, CheckCircle2, X, WifiOff } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import axios from 'axios';
import { io as socketIO } from 'socket.io-client';
import { API } from '../config/api';

const dummyData = Array.from({ length: 24 }).map((_, i) => ({
  time: `${i}:00`,
  score: Math.random() * 0.3 + (i == 14 ? 0.6 : 0),
}));

const StatCard = ({ title, value, icon: Icon, change }: any) => (
  <div className="glass-card p-6 flex items-start justify-between">
    <div>
      <p className="text-gray-400 font-medium mb-1">{title}</p>
      <h3 className="text-3xl font-bold text-white">{value}</h3>
      <p className={`text-sm mt-2 font-medium ${change.startsWith('+') ? 'text-accent' : 'text-danger'}`}>
        {change} from last week
      </p>
    </div>
    <div className="p-3 bg-surface rounded-xl border border-white/5">
      <Icon className="w-6 h-6 text-primary" />
    </div>
  </div>
);

export const Dashboard = () => {
  const { user, riskLevel, setRisk, token, addNotification } = useAppStore();
  const [data, setData] = useState(dummyData);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [selfHealingActive, setSelfHealingActive] = useState(false);
  const [rotationLog, setRotationLog] = useState<any[]>([]);
  const [showRotationModal, setShowRotationModal] = useState(false);
  const [rotationCount, setRotationCount] = useState(89);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [isolatedModal, setIsolatedModal] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const storageApi = API.storage;
  const encryptApi = API.encrypt;
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${storageApi}/files`, { headers: authHeaders });
      setFiles(res.data.files || []);
    } catch (e) {
      console.error(e);
    }
  };

  // Connect to Risk Engine via gateway (works both locally and over Vercel+tunnel)
  useEffect(() => {
    const socket = socketIO(API.socketUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });

    socket.on('risk_update', (data: any) => {
      setRisk(data.final_composite_score, data.risk_level);
      setData(prev => {
        const next = [...prev.slice(-23), { time: 'Now', score: data.ml_anomaly_score }];
        return next;
      });
    });

    socket.on('account_isolated', (payload: any) => {
      // Show quarantine modal BEFORE clearing token so the user can see what happened
      setIsolatedModal(payload);
      setSelfHealingActive(false);
      // Clear session after 8 seconds to let the modal be read
      setTimeout(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }, 8000);
    });

    fetchFiles();
    return () => { socket.disconnect(); };
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    try {
      await axios.post(`${storageApi}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data', ...authHeaders }
      });
      addNotification(`"${file.name}" encrypted with Kyber-1024 and stored!`, 'success');
      fetchFiles();
    } catch (e: any) {
      addNotification('Upload failed: ' + e.message, 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const simulateAttack = async () => {
    // 1. Spike anomaly chart immediately
    const attackData = [...data];
    attackData[23] = { time: 'Now', score: 0.98 };
    setData(attackData);
    setRisk(0.98, 'CRITICAL');
    setSelfHealingActive(true);
    setRotationLog([]);
    addNotification('⚠ Harvesting attack injected! CRITICAL state. Self-healing activated.', 'warning');

    try {
      // 2. Fire through risk engine (triggers RabbitMQ → Notification Service → email)
      const userId = useAppStore.getState().user?.id || 'attacker-sim-001';
      axios.post(`${API.risk}/inject-attack`, { user_id: userId }).catch(() => {});

      // 3. Rotate ONLY the current user's files (pass owner_id as query param)
      const res = await axios.post(`${encryptApi}/self-heal/rotate-keys?owner_id=${userId}`);
      const result = res.data;

      // 3. Recovery
      setRotationCount(c => c + result.files_rotated);
      setRotationLog(result.rotation_log);

      // 4. Reset UI state and show real rotation results
      setRisk(0.12, 'LOW');
      setSelfHealingActive(false);
      const safeData = [...attackData];
      safeData[23] = { time: 'Now', score: 0.08 };
      setData(safeData);

      // 5. Re-fetch files so Code icon shows NEW kyber_ciphertext
      await fetchFiles();

      // 6. Show modal with rotation audit log
      setShowRotationModal(true);
      addNotification(`Self-healing complete! ${result.files_rotated} files re-encrypted with new Kyber keys.`, 'success');

    } catch (e: any) {
      setSelfHealingActive(false);
      setRisk(0.12, 'LOW');
      addNotification('Self-heal error: ' + e.message, 'error');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

      {/* ATTACKER QUARANTINE MODAL — force-logout countdown */}
      {isolatedModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in">
          <div className="glass-card w-full max-w-lg mx-4 p-8 border-2 border-danger shadow-[0_0_60px_rgba(239,68,68,0.5)] text-center">
            <WifiOff className="w-16 h-16 text-danger mx-auto mb-4 animate-pulse" />
            <h2 className="text-2xl font-black text-danger mb-2 uppercase tracking-wider">Session Terminated</h2>
            <p className="text-white font-semibold mb-4">Your account has been quarantined by the AI Security Engine.</p>
            <div className="bg-black/50 rounded-xl p-4 text-left space-y-2 mb-6 border border-danger/30">
              <p className="text-xs text-gray-400"><span className="text-danger font-bold">Reason:</span> {isolatedModal.reason}</p>
              <p className="text-xs text-gray-400"><span className="text-danger font-bold">ML Score:</span> {((isolatedModal.anomaly_score ?? 0) * 100).toFixed(1)}% probability of HNDL attack</p>
              <p className="text-xs text-gray-400"><span className="text-accent font-bold">Action Taken:</span> All Kyber-1024 keys rotated. Harvested ciphertext is now invalid.</p>
            </div>
            <p className="text-gray-500 text-sm">Redirecting to login in 8 seconds. If this was an error, contact your administrator.</p>
          </div>
        </div>
      )}

      {/* Key Rotation Audit Modal */}
      {showRotationModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="glass-card w-full max-w-2xl mx-4 p-6 border border-accent/30 shadow-[0_0_40px_rgba(59,130,246,0.3)]">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-5 h-5 text-accent" />
                  <h2 className="text-xl font-bold text-white">Self-Healing Complete</h2>
                </div>
                <p className="text-gray-400 text-sm">Real Kyber-1024 key rotation audit log. All files re-encrypted with fresh keys.</p>
              </div>
              <button onClick={() => setShowRotationModal(false)} className="text-gray-500 hover:text-white p-1"><X className="w-5 h-5" /></button>
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto">
              {rotationLog.map((entry, i) => (
                <div key={i} className={`rounded-lg border p-3 ${entry.status === 'rotated' ? 'border-accent/30 bg-accent/5' : 'border-danger/30 bg-danger/5'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {entry.status === 'rotated'
                      ? <CheckCircle2 className="w-4 h-4 text-accent flex-shrink-0" />
                      : <ShieldAlert className="w-4 h-4 text-danger flex-shrink-0" />}
                    <span className="text-white font-medium text-sm truncate">{entry.file_name}</span>
                    <span className={`ml-auto text-xs font-bold uppercase px-2 py-0.5 rounded-full ${entry.status === 'rotated' ? 'bg-accent/20 text-accent' : 'bg-danger/20 text-danger'}`}>
                      {entry.status}
                    </span>
                  </div>
                  {entry.status === 'rotated' && (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div>
                        <p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">OLD Kyber Key</p>
                        <p className="text-[10px] font-mono text-danger/80 bg-black/40 p-1 rounded break-all">{entry.old_kyber_preview}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">NEW Kyber Key (Rotated)</p>
                        <p className="text-[10px] font-mono text-accent bg-black/40 p-1 rounded break-all">{entry.new_kyber_preview}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">OLD AES-256 Key</p>
                        <p className="text-[10px] font-mono text-danger/80 bg-black/40 p-1 rounded break-all">{entry.old_aes_preview}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">NEW AES-256 Key (Rotated)</p>
                        <p className="text-[10px] font-mono text-accent bg-black/40 p-1 rounded break-all">{entry.new_aes_preview}</p>
                      </div>
                    </div>
                  )}
                  {entry.plaintext_size_bytes && (
                    <p className="text-gray-500 text-[10px] mt-1">Re-encrypted {entry.plaintext_size_bytes} bytes · ML-KEM-1024 + AES-256-GCM</p>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4 flex justify-between items-center">
              <p className="text-xs text-gray-500">Files rotated: <span className="text-accent font-bold">{rotationLog.filter(r => r.status === 'rotated').length}</span> · Files still accessible: <span className="text-accent font-bold">{rotationLog.filter(r => r.status === 'rotated').length}</span></p>
              <button onClick={() => setShowRotationModal(false)} className="btn-primary text-sm px-4 py-2">Close</button>
            </div>
          </div>
        </div>
      )}

      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Welcome back, {user?.name}</h1>
          <p className="text-gray-400 mt-1">Here is your security and storage overview.</p>
        </div>
        <div className="flex gap-4">
          <button onClick={simulateAttack} disabled={selfHealingActive} className="btn-secondary flex items-center gap-2 text-danger hover:bg-danger/20 border-danger/30">
            {selfHealingActive
              ? <><RefreshCw className="w-4 h-4 animate-spin" /> Rotating Keys...</>
              : <><Skull className="w-4 h-4" /> Inject Harvesting Attack</>}
          </button>
          <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn-primary flex items-center gap-2">
            {uploading ? <ActivitySquare className="w-4 h-4 animate-spin" /> : <HardDrive className="w-4 h-4" />}
            {uploading ? 'Encrypting...' : 'Upload Secure File'}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Secure Storage" value={`${files.length} Files`} icon={HardDrive} change="+2" />
        <StatCard title="Files Encrypted" value={files.length} icon={Cpu} change="+12" />
        <StatCard title="Key Rotations" value={rotationCount} icon={ActivitySquare} change="+3" />
        <StatCard title="Anomalies Blocked" value={selfHealingActive ? "8" : "7"} icon={ShieldAlert} change="+1" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={`lg:col-span-2 glass-card p-6 transition-all duration-500 ${riskLevel === 'CRITICAL' ? 'border-danger/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]' : ''}`}>
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className={`text-xl font-bold ${riskLevel === 'CRITICAL' ? 'text-danger' : 'text-white'}`}>
                {selfHealingActive ? "CRITICAL ANOMALY DETECTED — ROTATING KEYS" : "Live Anomaly Detection"}
              </h2>
              <p className="text-gray-400 text-sm">Real-time LSTM-Autoencoder scores</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${riskLevel === 'CRITICAL' ? 'bg-danger' : 'bg-accent'}`}></span>
                <span className={`relative inline-flex rounded-full h-3 w-3 ${riskLevel === 'CRITICAL' ? 'bg-danger' : 'bg-accent'}`}></span>
              </span>
              <span className={`text-sm font-medium uppercase tracking-wider ${riskLevel === 'CRITICAL' ? 'text-danger animate-pulse' : 'text-accent'}`}>Live</span>
            </div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={riskLevel === 'CRITICAL' ? '#EF4444' : '#3B82F6'} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={riskLevel === 'CRITICAL' ? '#EF4444' : '#3B82F6'} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#4B5563" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#4B5563" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1A233A', borderColor: riskLevel === 'CRITICAL' ? '#EF4444' : '#2A344A', borderRadius: '8px' }}
                  itemStyle={{ color: '#E5E7EB' }}
                />
                <Area type="monotone" dataKey="score" stroke={riskLevel === 'CRITICAL' ? '#EF4444' : '#3B82F6'} strokeWidth={3} fillOpacity={1} fill="url(#colorScore)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card p-6 flex flex-col">
          <h2 className="text-xl font-bold text-white mb-2">Secure File Vault</h2>
          <p className="text-gray-400 text-sm mb-4">ML-KEM-1024 encapsulated. Click <Code className="inline w-3 h-3" /> to inspect live DB keys.</p>

          {selfHealingActive && (
            <div className="mb-4 p-4 border border-warning/50 bg-warning/10 rounded-xl flex flex-col items-center text-center shadow-[0_0_15px_rgba(245,158,11,0.3)]">
              <RefreshCw className="w-8 h-8 text-warning mb-2 animate-spin" />
              <p className="text-warning font-bold uppercase text-sm">Self-Healing Active</p>
              <p className="text-white text-xs mt-1">Downloading → Decrypting → Re-encrypting → Re-uploading...</p>
            </div>
          )}

          <div className={`space-y-3 flex-1 overflow-y-auto pr-1 ${selfHealingActive ? 'opacity-30 pointer-events-none' : ''}`}>
            {files.map((f: any) => (
              <div key={f.id} className="flex flex-col bg-white/5 rounded-lg border border-white/10 overflow-hidden">
                <div className="flex justify-between items-center p-3 hover:bg-white/10 transition-colors">
                  <div className="truncate pr-2 flex-1">
                    <p className="text-white font-medium truncate text-sm">{f.original_name}</p>
                    <p className="text-[10px] text-primary flex items-center gap-1 mt-0.5">
                      <ShieldCheck className="w-3 h-3 flex-shrink-0" /> PQC Encapsulated
                    </p>
                  </div>
                  <button
                    onClick={() => setExpandedFile(expandedFile === f.id ? null : f.id)}
                    className="p-1.5 bg-purple-500/20 hover:bg-purple-500/40 rounded-lg text-purple-400 transition-colors flex-shrink-0"
                    title="View live DB key signatures"
                  >
                    <Code className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => window.open(`${encryptApi}/decrypt/${f.id}`, '_blank')}
                    className="p-1.5 bg-primary/20 hover:bg-primary/40 rounded-lg text-primary transition-colors ml-1.5 flex-shrink-0"
                    title="Decapsulate & Download"
                  >
                    <DownloadCloud className="w-3.5 h-3.5" />
                  </button>
                </div>
                {expandedFile === f.id && (
                  <div className="p-3 bg-black/50 border-t border-white/5">
                    <p className="text-[9px] font-bold text-purple-400 mb-1.5 uppercase tracking-widest">Live PostgreSQL · kyber_ciphertext (ML-KEM-1024 pubkey)</p>
                    <div className="text-[9px] font-mono text-emerald-400/80 break-all bg-black/60 p-2 rounded border border-emerald-900/40 leading-relaxed">
                      {f.kyber_ciphertext
                        ? f.kyber_ciphertext.substring(0, 180) + '...'
                        : <span className="text-gray-600">No key found — upload a new file</span>}
                    </div>
                    <p className="text-[9px] font-bold text-blue-400 mt-2 mb-1 uppercase tracking-widest">encrypted_aes_key (AES-256)</p>
                    <div className="text-[9px] font-mono text-blue-300/80 break-all bg-black/60 p-2 rounded border border-blue-900/40">
                      {f.encrypted_aes_key
                        ? f.encrypted_aes_key.substring(0, 64) + '...'
                        : <span className="text-gray-600">No key found</span>}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {files.length === 0 && (
              <div className="text-center py-10 text-gray-500 text-sm border border-dashed border-gray-600 rounded-xl">
                No secure files found
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
