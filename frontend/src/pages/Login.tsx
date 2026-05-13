import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Mail, Lock, User, Eye, EyeOff, Loader2 } from 'lucide-react';
import axios from 'axios';
import { useAppStore } from '../store/useAppStore';
import { API } from '../config/api';

export const Login = () => {
  const navigate = useNavigate();
  const { setUser, addNotification } = useAppStore();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const AUTH_URL = API.auth;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = mode === 'login' ? `${AUTH_URL}/login` : `${AUTH_URL}/register`;
      const payload = mode === 'login' ? { email, password } : { email, name, password };
      const res = await axios.post(endpoint, payload);
      const { token, user } = res.data;

      setUser(user, token);
      addNotification(`Welcome back, ${user.name}! Vault loaded.`, 'success');
      navigate('/dashboard');
    } catch (e: any) {
      const msg = e?.response?.data?.message || e.message || 'Something went wrong';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
      {/* Ambient background blobs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-accent/15 rounded-full blur-[150px] pointer-events-none" />

      <div className="w-full max-w-md mx-4 z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(59,130,246,0.3)]">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">ShieldCloud</h1>
          <p className="text-gray-400 text-sm mt-1 font-medium tracking-widest uppercase">Post-Quantum Security</p>
        </div>

        {/* Card */}
        <div className="glass-card p-8">
          {/* Mode toggle */}
          <div className="flex rounded-xl bg-black/30 p-1 mb-6 border border-white/5">
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(''); }}
                className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all duration-200 ${
                  mode === m ? 'bg-primary text-white shadow-lg' : 'text-gray-400 hover:text-white'
                }`}
              >
                {m === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-black/30 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
                />
              </div>
            )}

            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-black/30 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full bg-black/30 border border-white/10 rounded-xl pl-10 pr-12 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>

            {error && (
              <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-4 py-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> {mode === 'login' ? 'Signing In...' : 'Creating Account...'}</>
              ) : (
                mode === 'login' ? 'Sign In to Vault' : 'Create Secure Account'
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/5 text-center">
            <p className="text-gray-500 text-xs">
              Protected by ML-KEM-1024 Post-Quantum Cryptography
            </p>
            <div className="flex items-center justify-center gap-4 mt-3">
              {['AES-256-GCM', 'Kyber-1024', 'bcrypt'].map((tech) => (
                <span key={tech} className="text-[10px] font-mono text-primary/70 bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
