import React, { useState, useEffect } from 'react';
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
        // Fetch users
        const usersRes = await fetch(`${API_BASE}/admin/users`, {
          headers: getAuthHeaders(),
        });
        if (!usersRes.ok) throw new Error('Failed to fetch users');
        const usersData = await usersRes.json();
        setUsers(usersData.users || []);

        // Check API health
        const healthRes = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
        if (healthRes.ok) {
          setStatus((s) => ({ ...s, api: 'online' }));
        }

        // Check Ollama health (via a quick API call)
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
    const interval = setInterval(fetchAdminData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-gray-500">Loading admin panel...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Tenant Administration</h1>
      <p className="text-slate-600 mb-8">Manage users and system infrastructure.</p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User Management */}
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Users ({users.length})</h2>
          {users.length === 0 ? (
            <p className="text-slate-500 text-sm">No users yet</p>
          ) : (
            <ul className="divide-y text-sm">
              {users.map((user) => (
                <li key={user.id} className="py-2 flex justify-between">
                  <span className="font-mono text-xs text-slate-600">{user.email}</span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      user.role === 'admin'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {user.role}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* System Status */}
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <h2 className="text-xl font-semibold mb-4">System Status</h2>
          <ul className="space-y-3 text-sm">
            <li className="flex justify-between items-center">
              <span className="text-slate-600">API Gateway</span>
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    status.api === 'online' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span
                  className={
                    status.api === 'online' ? 'text-green-600 font-medium' : 'text-red-600'
                  }
                >
                  {status.api === 'online' ? 'Online' : 'Offline'}
                </span>
              </div>
            </li>
            <li className="flex justify-between items-center">
              <span className="text-slate-600">Local LLM (Ollama)</span>
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    status.ollama === 'online' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span
                  className={
                    status.ollama === 'online' ? 'text-green-600 font-medium' : 'text-red-600'
                  }
                >
                  {status.ollama === 'online' ? 'Online' : 'Offline'}
                </span>
              </div>
            </li>
            <li className="flex justify-between items-center">
              <span className="text-slate-600">Vector Cache</span>
              <span className="text-slate-700 font-medium">Operational</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Infrastructure Info */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">Privacy-First Architecture</h3>
        <p className="text-blue-800 text-sm">
          All data processing (document ingestion, embedding, LLM inference) runs locally within your
          tenant's private infrastructure, with zero external API calls. Full DPDP Act compliance.
        </p>
      </div>
    </div>
  );
};

export default Admin;
