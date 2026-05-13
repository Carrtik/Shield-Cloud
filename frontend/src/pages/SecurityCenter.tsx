import React, { useEffect, useState, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import {
  Activity, Skull, CheckCircle2, ShieldAlert, Clock, Zap, RefreshCw,
  TrendingUp, AlertOctagon, Shield, X
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import axios from 'axios';
import { API } from '../config/api';

interface ThreatEvent {
  id: string;
  timestamp: string;
  type: string;
  score: number;
  action: string;
  status: 'neutralized' | 'monitoring';
}

const dummyHistory = Array.from({ length: 48 }).map((_, i) => ({
  time: `${Math.floor(i / 2)}:${i % 2 === 0 ? '00' : '30'}`,
  score: Math.random() * 0.2 + (i === 28 ? 0.75 : 0),
}));

export const SecurityCenter = () => {
  const { riskLevel, riskScore, setRisk, addNotification } = useAppStore();
  const [data, setData] = useState(dummyHistory);
  const [events, setEvents] = useState<ThreatEvent[]>([
    { id: '1', timestamp: new Date(Date.now() - 3600000).toISOString(), type: 'Geo-velocity Anomaly', score: 0.82, action: 'Key rotation triggered', status: 'neutralized' },
    { id: '2', timestamp: new Date(Date.now() - 7200000).toISOString(), type: 'Bulk Download Pattern', score: 0.67, action: 'Session monitoring elevated', status: 'monitoring' },
  ]);
  const [selfHealingActive, setSelfHealingActive] = useState(false);
  const [rotationLog, setRotationLog] = useState<any[]>([]);
  const [showRotationModal, setShowRotationModal] = useState(false);

  const authHeaders = useAppStore(s => s.token) ? { Authorization: `Bearer ${useAppStore.getState().token}` } : {};

  const simulateAttack = async () => {
    setData(prev => [...prev.slice(-47), { time: 'Now', score: 0.98 }]);
    setRisk(0.98, 'CRITICAL');
    setSelfHealingActive(true);
    setRotationLog([]);
    addNotification('⚠ Harvesting attack injected! CRITICAL state. Self-healing activated.', 'warning');

    try {
      // Fire through risk engine → RabbitMQ → Notification Service toast + email
      const userId = useAppStore.getState().user?.id || 'attacker-sim-001';
      axios.post(`${API.risk}/inject-attack`, { user_id: userId }).catch(() => {});

      // Rotate ONLY the current user's files
      const res = await axios.post(`${API.encrypt}/self-heal/rotate-keys?owner_id=${userId}`);
      const result = res.data;
      setRotationLog(result.rotation_log);
      setRisk(0.12, 'LOW');
      setSelfHealingActive(false);
      setData(prev => [...prev.slice(-47), { time: 'Now', score: 0.08 }]);
      setShowRotationModal(true);
      addNotification(`Self-healing complete! ${result.files_rotated} files re-encrypted.`, 'success');
      setEvents(prev => [{
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        type: 'HNDL Attack Simulation',
        score: 0.98,
        action: `${result.files_rotated} files rotated (Kyber-1024 + AES-256)`,
        status: 'neutralized',
      }, ...prev]);
    } catch (e: any) {
      setSelfHealingActive(false);
      setRisk(0.12, 'LOW');
      addNotification('Self-heal error: ' + e.message, 'error');
    }
  };

  const riskColor = riskLevel === 'CRITICAL' ? '#EF4444' : riskLevel === 'HIGH' ? '#F59E0B' : '#3B82F6';

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Key Rotation Modal */}
      {showRotationModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="glass-card w-full max-w-2xl mx-4 p-6 border border-accent/30 shadow-[0_0_40px_rgba(59,130,246,0.3)]">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-5 h-5 text-accent" />
                  <h2 className="text-xl font-bold text-white">Self-Healing Complete</h2>
                </div>
                <p className="text-gray-400 text-sm">Real Kyber-1024 key rotation audit log.</p>
              </div>
              <button onClick={() => setShowRotationModal(false)} className="text-gray-500 hover:text-white p-1"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {rotationLog.map((entry, i) => (
                <div key={i} className={`rounded-lg border p-3 ${entry.status === 'rotated' ? 'border-accent/30 bg-accent/5' : 'border-danger/30 bg-danger/5'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {entry.status === 'rotated' ? <CheckCircle2 className="w-4 h-4 text-accent" /> : <ShieldAlert className="w-4 h-4 text-danger" />}
                    <span className="text-white font-medium text-sm truncate">{entry.file_name}</span>
                    <span className={`ml-auto text-xs font-bold uppercase px-2 py-0.5 rounded-full ${entry.status === 'rotated' ? 'bg-accent/20 text-accent' : 'bg-danger/20 text-danger'}`}>{entry.status}</span>
                  </div>
                  {entry.status === 'rotated' && (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div><p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">OLD Kyber Key</p><p className="text-[10px] font-mono text-danger/80 bg-black/40 p-1 rounded break-all">{entry.old_kyber_preview}</p></div>
                      <div><p className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">NEW Kyber Key</p><p className="text-[10px] font-mono text-accent bg-black/40 p-1 rounded break-all">{entry.new_kyber_preview}</p></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-end">
              <button onClick={() => setShowRotationModal(false)} className="btn-primary text-sm px-4 py-2">Close</button>
            </div>
          </div>
        </div>
      )}

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Security Center</h1>
          <p className="text-gray-400 mt-1">Real-time XGBoost anomaly detection & autonomous self-healing</p>
        </div>
        <button onClick={simulateAttack} disabled={selfHealingActive} className="btn-secondary flex items-center gap-2 text-danger hover:bg-danger/20 border-danger/30">
          {selfHealingActive ? <><RefreshCw className="w-4 h-4 animate-spin" /> Rotating Keys...</> : <><Skull className="w-4 h-4" /> Inject Harvesting Attack</>}
        </button>
      </header>

      {/* Risk metric cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Current Risk', value: riskLevel, icon: Shield, color: riskLevel === 'CRITICAL' ? 'text-danger' : riskLevel === 'HIGH' ? 'text-warning' : 'text-accent' },
          { label: 'ML Score', value: `${(riskScore * 100).toFixed(0)}%`, icon: Zap, color: 'text-primary' },
          { label: 'Threats Neutralized', value: events.filter(e => e.status === 'neutralized').length, icon: CheckCircle2, color: 'text-accent' },
          { label: 'Monitoring', value: events.filter(e => e.status === 'monitoring').length, icon: Activity, color: 'text-warning' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass-card p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-gray-400 text-sm mb-1">{label}</p>
                <p className={`text-2xl font-black ${color}`}>{value}</p>
              </div>
              <Icon className={`w-5 h-5 ${color} opacity-60`} />
            </div>
          </div>
        ))}
      </div>

      {/* Full chart */}
      <div className={`glass-card p-6 transition-all duration-500 ${riskLevel === 'CRITICAL' ? 'border-danger/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]' : ''}`}>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className={`text-xl font-bold ${riskLevel === 'CRITICAL' ? 'text-danger' : 'text-white'}`}>
              {selfHealingActive ? 'CRITICAL ANOMALY DETECTED — ROTATING KEYS' : '48-Hour Anomaly Timeline'}
            </h2>
            <p className="text-gray-400 text-sm mt-1">XGBoost ML anomaly scores · 30-min intervals</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${riskLevel === 'CRITICAL' ? 'bg-danger' : 'bg-accent'}`} />
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${riskLevel === 'CRITICAL' ? 'bg-danger' : 'bg-accent'}`} />
            </span>
            <span className={`text-sm font-medium uppercase tracking-wider ${riskLevel === 'CRITICAL' ? 'text-danger animate-pulse' : 'text-accent'}`}>Live</span>
          </div>
        </div>
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorScore2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={riskColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={riskColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="time" stroke="#4B5563" fontSize={10} tickLine={false} axisLine={false} interval={5} />
              <YAxis stroke="#4B5563" fontSize={10} tickLine={false} axisLine={false} domain={[0, 1]} />
              <Tooltip contentStyle={{ backgroundColor: '#1A233A', borderColor: riskColor, borderRadius: '8px' }} itemStyle={{ color: '#E5E7EB' }} />
              <Area type="monotone" dataKey="score" stroke={riskColor} strokeWidth={2} fillOpacity={1} fill="url(#colorScore2)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Threat History */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5">
          <h2 className="font-semibold text-white flex items-center gap-2"><AlertOctagon className="w-4 h-4 text-warning" /> Threat Event Log</h2>
        </div>
        <div className="divide-y divide-white/5">
          {events.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No threat events recorded.</div>
          ) : events.map(ev => (
            <div key={ev.id} className="flex items-center gap-4 px-6 py-4">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${ev.status === 'neutralized' ? 'bg-accent' : 'bg-warning'}`} />
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium text-sm">{ev.type}</p>
                <p className="text-gray-500 text-xs">{ev.action}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className={`text-sm font-bold ${ev.score >= 0.85 ? 'text-danger' : ev.score >= 0.6 ? 'text-warning' : 'text-accent'}`}>{(ev.score * 100).toFixed(0)}%</p>
                <p className="text-gray-600 text-xs flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(ev.timestamp).toLocaleTimeString()}</p>
              </div>
              <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded-full flex-shrink-0 ${ev.status === 'neutralized' ? 'bg-accent/10 text-accent border border-accent/20' : 'bg-warning/10 text-warning border border-warning/20'}`}>
                {ev.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
