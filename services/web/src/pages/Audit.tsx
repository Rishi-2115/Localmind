import React, { useState, useEffect } from 'react';
import { ShieldCheck, Filter, Clock, User, Activity, Hash, Database, SearchX, CheckCircle, AlertCircle, FileUp, Sparkles } from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';

interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  timestamp: string;
  doc_ids_accessed: string[] | null;
  query_hash: string | null;
}

const Audit: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    const fetchAuditLogs = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/audit/`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          if (res.status === 403) {
            throw new Error('Admin access required to view audit logs');
          }
          throw new Error(`Failed to fetch audit logs (${res.status})`);
        }
        const data = await res.json();
        setLogs(data.logs || []);
      } catch (err: any) {
        setError(err.message || 'Failed to load audit logs');
      } finally {
        setLoading(false);
      }
    };

    fetchAuditLogs();
    const interval = setInterval(fetchAuditLogs, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const filteredLogs = logs.filter((log) => (filter === 'all' ? true : log.action === filter));

  const getActionBadge = (action: string) => {
    if (action === 'query') return { color: 'text-blue-400 bg-blue-500/10 border-blue-500/20', icon: <Activity size={12} className="mr-1.5" />, label: 'Query' };
    if (action === 'query_cache_hit') return { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', icon: <Sparkles size={12} className="mr-1.5" />, label: 'Cache Hit' };
    if (action === 'ingest_upload') return { color: 'text-purple-400 bg-purple-500/10 border-purple-500/20', icon: <FileUp size={12} className="mr-1.5" />, label: 'Ingest' };
    if (action === 'query_failed') return { color: 'text-rose-400 bg-rose-500/10 border-rose-500/20', icon: <AlertCircle size={12} className="mr-1.5" />, label: 'Failed' };
    return { color: 'text-slate-400 bg-slate-500/10 border-slate-500/20', icon: <Activity size={12} className="mr-1.5" />, label: action };
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-800/50 bg-[#0F172A]/40 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Compliance & Audit Trail</h1>
              <p className="text-[13px] text-slate-400 font-medium">Immutable activity log for DPDP Act compliance.</p>
            </div>
          </div>
          
          <div className="flex items-center bg-[#1E293B]/60 border border-slate-700/50 rounded-xl px-3 py-1.5">
            <Filter size={14} className="text-slate-400 mr-2" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-transparent text-sm text-slate-200 focus:outline-none cursor-pointer font-medium"
            >
              <option value="all">All Actions</option>
              <option value="query">Queries</option>
              <option value="query_cache_hit">Cache Hits</option>
              <option value="ingest_upload">Uploads</option>
              <option value="query_failed">Failures</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
        <div className="max-w-6xl mx-auto space-y-6">
          
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl flex items-center">
              <AlertCircle size={18} className="mr-2" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          {/* Metrics Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <CheckCircle size={48} className="text-blue-500" />
              </div>
              <div className="text-3xl font-bold text-white mb-1 tracking-tight">
                {logs.filter((l) => l.action.includes('query')).length}
              </div>
              <div className="text-sm font-medium text-slate-400">Total Queries</div>
            </div>
            
            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Database size={48} className="text-purple-500" />
              </div>
              <div className="text-3xl font-bold text-white mb-1 tracking-tight">
                {logs.filter((l) => l.action === 'ingest_upload').length}
              </div>
              <div className="text-sm font-medium text-slate-400">Documents Indexed</div>
            </div>

            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <AlertCircle size={48} className="text-rose-500" />
              </div>
              <div className="text-3xl font-bold text-white mb-1 tracking-tight">
                {logs.filter((l) => l.action === 'query_failed').length}
              </div>
              <div className="text-sm font-medium text-slate-400">Failed Queries</div>
            </div>
          </div>

          {/* Data Table */}
          <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl shadow-xl overflow-hidden backdrop-blur-md">
            {loading ? (
              <div className="px-6 py-20 flex flex-col items-center justify-center text-slate-400">
                <Activity size={32} className="animate-spin mb-4 text-blue-500" />
                <p className="text-sm font-medium">Loading secure audit logs...</p>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="px-6 py-20 flex flex-col items-center justify-center text-slate-500">
                <SearchX size={32} className="mb-4 opacity-50" />
                <p className="text-sm font-medium">No audit logs found for the selected filter.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-700/50">
                  <thead className="bg-slate-800/40">
                    <tr>
                      <th className="px-6 py-4 text-left text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        <div className="flex items-center"><Clock size={12} className="mr-1.5" /> Timestamp</div>
                      </th>
                      <th className="px-6 py-4 text-left text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        <div className="flex items-center"><User size={12} className="mr-1.5" /> User ID</div>
                      </th>
                      <th className="px-6 py-4 text-left text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Action
                      </th>
                      <th className="px-6 py-4 text-left text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        <div className="flex items-center"><Hash size={12} className="mr-1.5" /> Audit Metadata</div>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredLogs.map((log) => {
                      const badge = getActionBadge(log.action);
                      return (
                        <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-[13px] font-medium text-slate-300">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-[13px] font-mono text-slate-400">
                            UID_{log.user_id.toString().padStart(4, '0')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-bold tracking-wide uppercase border ${badge.color}`}>
                              {badge.icon}
                              {badge.label}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-[13px] text-slate-400 font-mono">
                            <div className="flex flex-col space-y-1">
                              {log.query_hash && <span>hash: <span className="text-slate-300">{log.query_hash.substring(0, 12)}...</span></span>}
                              {log.doc_ids_accessed && log.doc_ids_accessed.length > 0 && (
                                <span>
                                  docs: <span className="text-blue-400">[{log.doc_ids_accessed.slice(0, 2).join(', ')}{log.doc_ids_accessed.length > 2 ? '...' : ''}]</span>
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Audit;
