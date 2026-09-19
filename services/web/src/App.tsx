import { useState } from 'react';
import Chat from './pages/Chat';
import Upload from './pages/Upload';
import Audit from './pages/Audit';
import Admin from './pages/Admin';
import Login from './pages/Login';
import { useAuthStore } from './store/authStore';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'audit' | 'admin'>('chat');
  const { isAuthenticated, userEmail, logout } = useAuthStore();

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div className="flex h-screen bg-slate-900 font-sans text-slate-100">
      {/* Sidebar */}
      <div className="w-64 bg-slate-950/80 backdrop-blur border-r border-slate-800/80 flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-slate-800/80">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
                LM
              </div>
              <div>
                <h1 className="text-lg font-bold text-white tracking-tight">LocalMind</h1>
                <p className="text-[11px] text-blue-400 font-medium">Legal Copilot (DPDP)</p>
              </div>
            </div>
          </div>

          <nav className="p-4 space-y-1.5">
            <button
              id="nav-chat-btn"
              onClick={() => setActiveTab('chat')}
              className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              💬 Copilot Chat
            </button>
            <button
              id="nav-docs-btn"
              onClick={() => setActiveTab('upload')}
              className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              📄 Documents & Ingest
            </button>
            <button
              id="nav-audit-btn"
              onClick={() => setActiveTab('audit')}
              className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'audit'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              🛡️ Audit Trail
            </button>
            <button
              id="nav-admin-btn"
              onClick={() => setActiveTab('admin')}
              className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'admin'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              ⚙️ Admin & Tenant
            </button>
          </nav>
        </div>

        {/* User profile & logout */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center justify-between mb-2">
            <div className="overflow-hidden">
              <p className="text-xs text-slate-400 truncate">Signed in as</p>
              <p className="text-xs font-semibold text-slate-200 truncate">{userEmail || 'admin@localmind.in'}</p>
            </div>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Admin
            </span>
          </div>
          <button
            id="logout-btn"
            onClick={logout}
            className="w-full mt-2 py-1.5 px-3 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 rounded-md transition font-medium text-center"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto bg-slate-900">
        {activeTab === 'chat' && <Chat />}
        {activeTab === 'upload' && <Upload />}
        {activeTab === 'audit' && <Audit />}
        {activeTab === 'admin' && <Admin />}
      </main>
    </div>
  );
}

export default App;
