import React, { useEffect, useState, useRef, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import {
  HardDrive, ShieldAlert, Cpu, ActivitySquare, ShieldCheck, DownloadCloud,
  Skull, Code, RefreshCw, CheckCircle2, X, WifiOff, Search, Trash2, File, FileText, FileImage, Archive
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import axios from 'axios';
import { API } from '../config/api';

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(ts: string): string {
  if (!ts) return '—';
  return new Date(ts).toLocaleString();
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (['jpg','jpeg','png','gif','webp','svg'].includes(ext || '')) return FileImage;
  if (['txt','md','csv','json','xml'].includes(ext || '')) return FileText;
  if (['zip','tar','gz','7z','rar'].includes(ext || '')) return Archive;
  return File;
}

export const FilesPage = () => {
  const { token, addNotification } = useAppStore();
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchFiles = useCallback(async () => {
    try {
      const res = await axios.get(`${API.storage}/files`, { headers: authHeaders });
      setFiles(res.data.files || []);
    } catch (e) {
      addNotification('Failed to load files', 'error');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    try {
      await axios.post(`${API.storage}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data', ...authHeaders }
      });
      addNotification(`"${file.name}" encrypted with Kyber-1024 and stored!`, 'success');
      await fetchFiles();
    } catch (e: any) {
      addNotification('Upload failed: ' + e.message, 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (fileId: string, fileName: string) => {
    if (!confirm(`Permanently delete "${fileName}"? This cannot be undone.`)) return;
    setDeleting(fileId);
    try {
      await axios.delete(`${API.storage}/files/${fileId}`, { headers: authHeaders });
      addNotification(`"${fileName}" securely deleted.`, 'success');
      setFiles(prev => prev.filter(f => f.id !== fileId));
    } catch (e: any) {
      addNotification('Delete failed: ' + e.message, 'error');
    } finally {
      setDeleting(null);
    }
  };

  const filtered = files.filter(f =>
    f.original_name?.toLowerCase().includes(search.toLowerCase())
  );

  const totalSize = files.reduce((acc, f) => acc + (f.size_bytes || 0), 0);

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Secure File Vault</h1>
          <p className="text-gray-400 mt-1">{files.length} files · {formatBytes(totalSize)} total · ML-KEM-1024 protected</p>
        </div>
        <div className="flex gap-3">
          <input type="file" ref={fileInputRef} className="hidden" onChange={handleUpload} />
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn-primary flex items-center gap-2">
            {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <HardDrive className="w-4 h-4" />}
            {uploading ? 'Encrypting...' : 'Upload File'}
          </button>
        </div>
      </header>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search files..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-surface/50 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
        />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Files', value: files.length, icon: HardDrive },
          { label: 'Encrypted', value: files.filter(f => f.kyber_ciphertext).length, icon: ShieldCheck },
          { label: 'Total Storage', value: formatBytes(totalSize), icon: Cpu },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="glass-card p-4 flex items-center gap-4">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
              <Icon className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">{label}</p>
              <p className="text-white font-bold text-xl">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* File Table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
          <h2 className="font-semibold text-white">All Files</h2>
          <span className="text-gray-500 text-sm">{filtered.length} results</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <HardDrive className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>{search ? 'No files match your search.' : 'No files in your vault. Upload your first file!'}</p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {filtered.map(f => {
              const FileIcon = getFileIcon(f.original_name || '');
              return (
                <div key={f.id} className="group">
                  <div className="flex items-center gap-4 px-6 py-4 hover:bg-white/5 transition-colors">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                      <FileIcon className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium truncate">{f.original_name}</p>
                      <p className="text-gray-500 text-xs mt-0.5">{formatBytes(f.size_bytes)} · Uploaded {formatDate(f.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {f.kyber_ciphertext && (
                        <span className="text-[10px] font-bold bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded-full">ML-KEM-1024</span>
                      )}
                      <button
                        onClick={() => setExpandedFile(expandedFile === f.id ? null : f.id)}
                        className="p-2 rounded-lg bg-purple-500/10 hover:bg-purple-500/30 text-purple-400 transition-colors"
                        title="Inspect crypto keys"
                      >
                        <Code className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => window.open(`${API.encrypt}/decrypt/${f.id}`, '_blank')}
                        className="p-2 rounded-lg bg-primary/10 hover:bg-primary/30 text-primary transition-colors"
                        title="Download & decrypt"
                      >
                        <DownloadCloud className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(f.id, f.original_name)}
                        disabled={deleting === f.id}
                        className="p-2 rounded-lg bg-danger/10 hover:bg-danger/30 text-danger transition-colors"
                        title="Delete file"
                      >
                        {deleting === f.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  {expandedFile === f.id && (
                    <div className="px-6 pb-4 bg-black/20">
                      <div className="rounded-xl border border-white/5 overflow-hidden">
                        <div className="p-3 bg-black/40">
                          <p className="text-[9px] font-bold text-purple-400 uppercase tracking-widest mb-1.5">Live PostgreSQL · kyber_ciphertext (ML-KEM-1024)</p>
                          <p className="text-[10px] font-mono text-emerald-400/80 break-all leading-relaxed">
                            {f.kyber_ciphertext ? f.kyber_ciphertext.substring(0, 200) + '...' : <span className="text-gray-600">No key found — upload first</span>}
                          </p>
                        </div>
                        <div className="p-3 bg-black/30 border-t border-white/5">
                          <p className="text-[9px] font-bold text-blue-400 uppercase tracking-widest mb-1.5">encrypted_aes_key (AES-256-GCM)</p>
                          <p className="text-[10px] font-mono text-blue-300/80 break-all">
                            {f.encrypted_aes_key ? f.encrypted_aes_key.substring(0, 80) + '...' : <span className="text-gray-600">No key found</span>}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
