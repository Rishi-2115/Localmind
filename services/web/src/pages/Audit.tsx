import React, { useState, useEffect } from 'react';
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

  const actionBadgeColor = (action: string) => {
    if (action === 'query' || action === 'query_cache_hit') return 'bg-blue-100 text-blue-700';
    if (action === 'ingest_upload') return 'bg-green-100 text-green-700';
    if (action === 'query_failed') return 'bg-red-100 text-red-700';
    return 'bg-gray-100 text-gray-700';
  };

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-gray-500">Loading audit logs...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">Compliance & Audit Log</h1>
      <p className="text-slate-600 mb-6">
        Complete activity log for DPDP Act compliance. All queries, uploads, and system actions are
        recorded.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Filter */}
      <div className="mb-6 flex gap-2">
        <label className="text-sm font-medium text-slate-600">Filter by action:</label>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-3 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Actions</option>
          <option value="query">Queries</option>
          <option value="query_cache_hit">Cache Hits</option>
          <option value="ingest_upload">Uploads</option>
          <option value="query_failed">Failed Queries</option>
        </select>
      </div>

      {/* Audit Table */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        {filteredLogs.length === 0 ? (
          <div className="px-6 py-8 text-center text-slate-500">
            No audit logs found for the selected filter.
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                    {log.user_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${actionBadgeColor(
                        log.action
                      )}`}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 font-mono text-xs">
                    {log.query_hash ? `hash: ${log.query_hash.substring(0, 8)}...` : ''}
                    {log.doc_ids_accessed && log.doc_ids_accessed.length > 0
                      ? ` docs: [${log.doc_ids_accessed.slice(0, 2).join(', ')}${
                          log.doc_ids_accessed.length > 2 ? '...' : ''
                        }]`
                      : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Summary */}
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <div className="text-2xl font-bold text-blue-700">
            {logs.filter((l) => l.action.includes('query')).length}
          </div>
          <div className="text-sm text-blue-600">Queries Processed</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded p-4">
          <div className="text-2xl font-bold text-green-700">
            {logs.filter((l) => l.action === 'ingest_upload').length}
          </div>
          <div className="text-sm text-green-600">Documents Uploaded</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded p-4">
          <div className="text-2xl font-bold text-red-700">
            {logs.filter((l) => l.action === 'query_failed').length}
          </div>
          <div className="text-sm text-red-600">Failed Queries</div>
        </div>
      </div>
    </div>
  );
};

export default Audit;
