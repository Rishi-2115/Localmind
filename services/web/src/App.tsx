import { useState } from 'react';
import { MessageSquare, UploadCloud, ShieldCheck, Settings, LogOut, Hexagon } from 'lucide-react';
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

  const navItems = [
    { id: 'chat', label: 'Copilot Chat', icon: MessageSquare },
    { id: 'upload', label: 'Documents & Ingest', icon: UploadCloud },
    { id: 'audit', label: 'Audit Trail', icon: ShieldCheck },
    { id: 'admin', label: 'Admin & Tenant', icon: Settings },
  ] as const;

  return (
    <div className="flex h-screen bg-[#0B1120] font-sans text-slate-100 selection:bg-blue-500/30">
      {/* Sidebar */}
      <div className="w-64 bg-[#0F172A]/90 backdrop-blur-xl border-r border-slate-800/60 flex flex-col justify-between shadow-2xl relative z-10">
        <div>
          <div className="p-6 border-b border-slate-800/60">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/25 ring-1 ring-white/10">
                <Hexagon size={20} className="fill-white/10" />
              </div>
              <div>
                <h1 className="text-[17px] font-bold text-white tracking-tight leading-tight">LocalMind</h1>
                <p className="text-[11px] text-blue-400 font-medium tracking-wide uppercase">Legal Copilot</p>
              </div>
            </div>
          </div>

          <nav className="p-4 space-y-1.5">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                id={`nav-${id}-btn`}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                  activeTab === id
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'
                }`}
              >
                <Icon size={18} className={activeTab === id ? 'text-blue-500' : 'text-slate-500 group-hover:text-slate-400 transition-colors'} />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* User profile & logout */}
        <div className="p-4 border-t border-slate-800/60 bg-slate-900/50 backdrop-blur-md">
          <div className="flex items-center justify-between mb-3 px-1">
            <div className="overflow-hidden">
              <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-0.5">Signed in as</p>
              <p className="text-xs font-medium text-slate-300 truncate pr-2">{userEmail || 'admin@localmind.in'}</p>
            </div>
            <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-sm shadow-indigo-500/10">
              ADMIN
            </span>
          </div>
          <button
            id="logout-btn"
            onClick={logout}
            className="w-full flex items-center justify-center space-x-2 py-2 px-3 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 hover:border-rose-500/30 rounded-xl transition-all font-medium text-center shadow-sm shadow-rose-500/5"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative bg-[#0B1120]">
        {/* Subtle background glow */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none opacity-50" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none opacity-50" />
        
        <div className="relative h-full z-10 animate-fade-in">
          {activeTab === 'chat' && <Chat />}
          {activeTab === 'upload' && <Upload />}
          {activeTab === 'audit' && <Audit />}
          {activeTab === 'admin' && <Admin />}
        </div>
      </main>
    </div>
  );
}

export default App;
