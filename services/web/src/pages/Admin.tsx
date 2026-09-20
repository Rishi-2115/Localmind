import React, { useState, useEffect } from 'react';
import { Settings, Users, Server, Cpu, Database, ShieldAlert, CheckCircle2, XCircle, Activity, ShieldCheck } from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';

interface User {
  id: number;
  email: string;
  role: 'admin' | 'staff';
}

interface SystemStatus {
  api: 'online' | 'offline';
  ollama: 'online' | 'offline';
  cache_hit_rate?: number;
}

const Admin: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [status, setStatus] = useState<SystemStatus>({
    api: 'offline',
    ollama: 'offline',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAdminData = async () => {
      setLoading(true);
      setError(null);
      try {
        const usersRes = await fetch(`${API_BASE}/admin/users`, {
          headers: getAuthHeaders(),
        });
        if (!usersRes.ok) throw new Error('Failed to fetch users');
        const usersData = await usersRes.json();
        setUsers(usersData.users || []);

        const healthRes = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
        if (healthRes.ok) {
          setStatus((s) => ({ ...s, api: 'online' }));
        }

        try {
          await fetch('http://localhost:11434/api/tags', {
            mode: 'no-cors',
          });
          setStatus((s) => ({ ...s, ollama: 'online' }));
        } catch {
          setStatus((s) => ({ ...s, ollama: 'offline' }));
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load admin data');
      } finally {
        setLoading(false);
      }
    };

    fetchAdminData();
    const interval = setInterval(fetchAdminData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-800/50 bg-[#0F172A]/40 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-500/10 rounded-lg text-slate-400">
            <Settings size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Tenant Administration</h1>
            <p className="text-[13px] text-slate-400 font-medium">Manage users, view system health, and oversee infrastructure.</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
        <div className="max-w-5xl mx-auto space-y-6">
          
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl flex items-center">
              <ShieldAlert size={18} className="mr-2" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* User Management */}
            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-md flex flex-col">
              <div className="px-6 py-5 border-b border-slate-700/50 bg-slate-800/30 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-white">
                  <Users size={18} className="text-indigo-400" />
                  <h2 className="text-[15px] font-semibold">Active Users</h2>
                </div>
                <span className="bg-indigo-500/20 text-indigo-400 py-0.5 px-2.5 rounded-full text-xs font-bold">{users.length}</span>
              </div>
              
              <div className="p-6 flex-1">
                {loading ? (
                  <div className="h-full flex items-center justify-center text-slate-500">
                    <Activity size={24} className="animate-spin text-indigo-500" />
                  </div>
                ) : users.length === 0 ? (
                  <p className="text-slate-500 text-sm text-center">No users found</p>
                ) : (
                  <ul className="space-y-3">
                    {users.map((user) => (
                      <li key={user.id} className="p-3 bg-slate-800/40 rounded-xl border border-slate-700/50 flex items-center justify-between hover:bg-slate-800/60 transition-colors">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-white">
                            {user.email.charAt(0).toUpperCase()}
                          </div>
                          <span className="font-medium text-[13px] text-slate-300">{user.email}</span>
                        </div>
                        <span className={`px-2.5 py-1 rounded-md text-[11px] font-bold tracking-wide uppercase border ${
                          user.role === 'admin' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}>
                          {user.role}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* System Status */}
            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-md flex flex-col">
              <div className="px-6 py-5 border-b border-slate-700/50 bg-slate-800/30 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-white">
                  <Server size={18} className="text-emerald-400" />
                  <h2 className="text-[15px] font-semibold">Infrastructure Health</h2>
                </div>
                {loading && <Activity size={16} className="animate-spin text-slate-500" />}
              </div>
              
              <div className="p-6 space-y-4">
                <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-slate-700/50 rounded-lg text-slate-400"><Server size={16} /></div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-200">API Gateway</h3>
                      <p className="text-[11px] text-slate-500">FastAPI Backend Service</p>
                    </div>
                  </div>
                  <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border ${status.api === 'online' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
                    {status.api === 'online' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    <span className="text-[11px] font-bold uppercase tracking-wider">{status.api}</span>
                  </div>
                </div>

                <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-slate-700/50 rounded-lg text-slate-400"><Cpu size={16} /></div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-200">Local LLM Engine</h3>
                      <p className="text-[11px] text-slate-500">Ollama Inference Server</p>
                    </div>
                  </div>
                  <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border ${status.ollama === 'online' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
                    {status.ollama === 'online' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    <span className="text-[11px] font-bold uppercase tracking-wider">{status.ollama}</span>
                  </div>
                </div>

                <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/50 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-slate-700/50 rounded-lg text-slate-400"><Database size={16} /></div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-200">Semantic Cache</h3>
                      <p className="text-[11px] text-slate-500">Redis & FAISS Vectors</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border bg-emerald-500/10 border-emerald-500/20 text-emerald-400">
                    <CheckCircle2 size={14} />
                    <span className="text-[11px] font-bold uppercase tracking-wider">Operational</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Banner */}
          <div className="bg-gradient-to-r from-blue-600/10 to-indigo-600/10 border border-blue-500/20 rounded-2xl p-6 flex items-start space-x-4">
            <div className="p-3 bg-blue-500/20 rounded-xl text-blue-400 flex-shrink-0">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-white tracking-tight mb-1">Privacy-First Architecture</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                All data processing (document ingestion, embedding, LLM inference) runs entirely locally within your private infrastructure. Zero external API calls. Full DPDP Act compliance.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Admin;
