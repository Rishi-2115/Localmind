import { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  UploadCloud, 
  ShieldCheck, 
  Settings, 
  LogOut, 
  Hexagon, 
  Sun, 
  Moon, 
  Zap
} from 'lucide-react';
import Chat from './pages/Chat';
import Upload from './pages/Upload';
import Audit from './pages/Audit';
import Admin from './pages/Admin';
import Login from './pages/Login';
import { useAuthStore } from './store/authStore';
import { useThemeStore } from './store/themeStore';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'audit' | 'admin'>('chat');
  const { isAuthenticated, userEmail, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  useEffect(() => {
    // Sync theme class to html on boot
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  if (!isAuthenticated) {
    return <Login />;
  }

  const navItems = [
    { id: 'chat', label: 'Copilot Chat', icon: MessageSquare },
    { id: 'upload', label: 'Documents & Ingest', icon: UploadCloud },
    { id: 'audit', label: 'Compliance Audit', icon: ShieldCheck },
    { id: 'admin', label: 'Admin & Tenant', icon: Settings },
  ] as const;

  const isDark = theme === 'dark';

  return (
    <div className={`flex h-screen w-screen overflow-hidden font-sans transition-colors duration-200 ${
      isDark ? 'bg-[#030712] text-slate-100' : 'bg-[#FAFAFA] text-[#09090B]'
    }`}>
      {/* ─────────────────────────────────────────────────────────────
          SIDEBAR NAVIGATION
      ───────────────────────────────────────────────────────────── */}
      <aside className={`w-72 flex flex-col justify-between border-r shadow-2xl relative z-20 backdrop-blur-2xl transition-colors duration-200 ${
        isDark 
          ? 'bg-[#0B132B]/90 border-orange-500/15 shadow-[10px_0_30px_rgba(3,7,18,0.8)]' 
          : 'bg-white/95 border-zinc-200 shadow-[10px_0_30px_rgba(0,0,0,0.03)]'
      }`}>
        <div>
          {/* Logo & Header */}
          <div className={`p-6 border-b flex items-center justify-between ${
            isDark ? 'border-orange-500/10' : 'border-zinc-100'
          }`}>
            <div className="flex items-center space-x-3.5">
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-bold shadow-lg ring-1 transition-all ${
                isDark 
                  ? 'bg-gradient-to-br from-orange-500 to-[#FF4500] text-black shadow-orange-500/30 ring-orange-400/40' 
                  : 'bg-black text-white shadow-zinc-950/20 ring-zinc-900'
              }`}>
                <Hexagon size={22} className={isDark ? "fill-black" : "fill-white"} />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <h1 className={`text-[18px] font-black tracking-tight leading-none ${
                    isDark ? 'text-white' : 'text-black'
                  }`}>
                    LocalMind
                  </h1>
                  {isDark ? (
                    <span className="w-2 h-2 rounded-full bg-[#FF6B00] animate-ping" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-yellow-400" />
                  )}
                </div>
                <p className={`text-[10px] font-extrabold tracking-widest uppercase mt-1 ${
                  isDark ? 'text-[#FF8533]' : 'text-zinc-500'
                }`}>
                  Enterprise DPDPA Copilot
                </p>
              </div>
            </div>

            {/* Quick Theme Toggle Icon */}
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-xl border transition-all ${
                isDark 
                  ? 'bg-orange-500/10 border-orange-500/25 text-[#FF8533] hover:bg-orange-500/20' 
                  : 'bg-zinc-100 border-zinc-200 text-zinc-700 hover:bg-zinc-200'
              }`}
              title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
            >
              {isDark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="p-4 space-y-2">
            {navItems.map(({ id, label, icon: Icon }) => {
              const active = activeTab === id;
              return (
                <button
                  key={id}
                  id={`nav-${id}-btn`}
                  onClick={() => setActiveTab(id)}
                  className={`w-full flex items-center space-x-3.5 px-4 py-3 rounded-2xl text-xs font-bold transition-all duration-200 group ${
                    active
                      ? isDark
                        ? 'bg-gradient-to-r from-orange-500/20 to-orange-500/5 text-[#FF8533] border border-orange-500/40 shadow-[0_0_20px_rgba(255,107,0,0.2)]'
                        : 'bg-black text-white border border-black shadow-lg shadow-black/10'
                      : isDark
                        ? 'text-slate-400 hover:bg-[#030712]/60 hover:text-white border border-transparent'
                        : 'text-zinc-600 hover:bg-zinc-100 hover:text-black border border-transparent'
                  }`}
                >
                  <Icon 
                    size={18} 
                    className={`transition-colors duration-200 ${
                      active 
                        ? isDark ? 'text-[#FF6B00]' : 'text-yellow-400' 
                        : isDark ? 'text-slate-500 group-hover:text-slate-300' : 'text-zinc-400 group-hover:text-zinc-900'
                    }`} 
                  />
                  <span>{label}</span>
                </button>
              );
            })}
          </nav>

          {/* System Mode Pill Banner */}
          <div className="px-5 py-2">
            <div className={`p-3.5 rounded-2xl border text-xs flex items-center space-x-3 ${
              isDark 
                ? 'bg-[#030712]/80 border-orange-500/20 text-slate-300' 
                : 'bg-zinc-50 border-zinc-200 text-zinc-700'
            }`}>
              <div className={`p-1.5 rounded-lg ${isDark ? 'bg-orange-500/20 text-[#FF6B00]' : 'bg-yellow-400/20 text-yellow-600'}`}>
                <Zap size={14} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-[11px] leading-tight">100% Air-Gapped</p>
                <p className="text-[10px] text-slate-400 opacity-80 truncate">Zero Egress • DPDP Act</p>
              </div>
            </div>
          </div>
        </div>

        {/* User profile, Theme switcher bar & logout */}
        <div className={`p-4 border-t ${
          isDark 
            ? 'border-orange-500/10 bg-[#030712]/90' 
            : 'border-zinc-200 bg-zinc-50/80'
        }`}>
          {/* User info */}
          <div className="flex items-center justify-between mb-3 px-1">
            <div className="overflow-hidden">
              <p className="text-[9px] uppercase tracking-wider font-extrabold text-slate-400">Authenticated Fiduciary</p>
              <p className={`text-xs font-semibold truncate pr-2 ${isDark ? 'text-white' : 'text-black'}`}>
                {userEmail || 'admin@localmind.in'}
              </p>
            </div>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black border tracking-wider ${
              isDark 
                ? 'bg-orange-500/15 text-[#FF8533] border-orange-500/30' 
                : 'bg-black text-white border-black'
            }`}>
              ADMIN
            </span>
          </div>

          {/* Bottom Controls */}
          <div className="grid grid-cols-2 gap-2 mt-2">
            <button
              onClick={toggleTheme}
              className={`flex items-center justify-center space-x-1.5 py-2 px-3 rounded-xl text-xs font-bold border transition-all ${
                isDark 
                  ? 'bg-slate-900 border-slate-700 text-slate-200 hover:border-orange-500/40 hover:text-[#FF8533]' 
                  : 'bg-white border-zinc-200 text-zinc-800 hover:border-black'
              }`}
            >
              {isDark ? <Sun size={13} className="text-yellow-400" /> : <Moon size={13} />}
              <span>{isDark ? 'Light' : 'Dark'}</span>
            </button>

            <button
              id="logout-btn"
              onClick={logout}
              className={`flex items-center justify-center space-x-1.5 py-2 px-3 rounded-xl text-xs font-bold border transition-all ${
                isDark 
                  ? 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20' 
                  : 'bg-rose-50 border-rose-200 text-rose-600 hover:bg-rose-100'
              }`}
            >
              <LogOut size={13} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* ─────────────────────────────────────────────────────────────
          MAIN CONTENT WORKSPACE
      ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden relative flex flex-col">
        {/* Futuristic Background Atmospheric Accents */}
        {isDark ? (
          <>
            <div className="absolute top-0 right-1/4 w-[600px] h-[600px] bg-blue-900/20 rounded-full blur-[140px] pointer-events-none" />
            <div className="absolute bottom-0 left-1/3 w-[500px] h-[500px] bg-[#FF6B00]/10 rounded-full blur-[140px] pointer-events-none" />
          </>
        ) : (
          <>
            <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-yellow-400/5 rounded-full blur-[120px] pointer-events-none" />
          </>
        )}

        <div className="relative h-full w-full z-10 flex-1 overflow-hidden">
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
