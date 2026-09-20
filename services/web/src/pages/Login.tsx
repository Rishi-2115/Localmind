import React, { useState } from 'react';
import { Hexagon, Lock, ShieldCheck, ArrowRight } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const Login: React.FC = () => {
  const [email, setEmail] = useState('admin@localmind.in');
  const [password, setPassword] = useState('localmind_admin_2027');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    login,
    changePassword,
    error,
    isLoading,
    requiresPasswordChange,
    pendingEmail,
    pendingCurrentPassword,
  } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    await login(email, password);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (newPassword.length < 12) {
      setLocalError('Password must be at least 12 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setLocalError('New passwords do not match.');
      return;
    }
    await changePassword(
      pendingEmail || email,
      pendingCurrentPassword || password,
      newPassword
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0B1120] relative overflow-hidden px-4 selection:bg-blue-500/30">
      
      {/* Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none opacity-60 animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[100px] pointer-events-none opacity-60" />

      <div className="w-full max-w-[420px] p-8 md:p-10 bg-[#0F172A]/80 backdrop-blur-2xl rounded-[2rem] border border-slate-700/50 shadow-2xl relative z-10 animate-slide-up">
        <div className="text-center mb-8">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-[0_0_30px_rgba(59,130,246,0.3)] mb-5 ring-1 ring-white/10">
            <Hexagon size={32} className="text-white fill-white/20" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">LocalMind</h1>
          <p className="text-slate-400 text-sm font-medium">Privacy-First Legal AI Copilot</p>
        </div>

        {requiresPasswordChange ? (
          <form onSubmit={handleChangePassword} className="space-y-5 animate-fade-in">
            <div className="bg-amber-500/10 border border-amber-500/20 text-amber-300 px-4 py-3 rounded-xl flex items-start space-x-3">
              <Lock size={18} className="flex-shrink-0 mt-0.5 text-amber-400" />
              <p className="text-xs leading-relaxed font-medium">
                <strong className="text-amber-200">Security Rotation:</strong> Initial password update required. Must be at least 12 characters.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[13px] font-semibold text-slate-300 mb-1.5 uppercase tracking-wide">New Password</label>
                <input
                  id="new-password-input"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#1E293B]/60 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-medium"
                  placeholder="At least 12 characters"
                  minLength={12}
                  required
                />
              </div>

              <div>
                <label className="block text-[13px] font-semibold text-slate-300 mb-1.5 uppercase tracking-wide">Confirm Password</label>
                <input
                  id="confirm-password-input"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#1E293B]/60 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-medium"
                  placeholder="Re-enter password"
                  minLength={12}
                  required
                />
              </div>
            </div>

            {(localError || error) && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-300 px-4 py-3 rounded-xl text-sm font-medium animate-fade-in">
                {localError || error}
              </div>
            )}

            <button
              id="submit-new-password-btn"
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] hover:shadow-[0_0_25px_rgba(16,185,129,0.3)] flex items-center justify-center space-x-2"
            >
              <span>{isLoading ? 'Updating...' : 'Set Password'}</span>
              {!isLoading && <ArrowRight size={16} />}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              <div>
                <label className="block text-[13px] font-semibold text-slate-300 mb-1.5 uppercase tracking-wide">Email</label>
                <input
                  id="login-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-[#1E293B]/60 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-medium"
                  placeholder="you@lawfirm.in"
                  required
                />
              </div>
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-[13px] font-semibold text-slate-300 uppercase tracking-wide">Password</label>
                </div>
                <input
                  id="login-password-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-[#1E293B]/60 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-medium"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-300 px-4 py-3 rounded-xl text-sm font-medium animate-fade-in">
                {error}
              </div>
            )}

            <button
              id="login-submit-btn"
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_25px_rgba(59,130,246,0.4)] flex items-center justify-center space-x-2"
            >
              <span>{isLoading ? 'Authenticating...' : 'Sign In'}</span>
              {!isLoading && <ArrowRight size={16} />}
            </button>
          </form>
        )}

        <div className="mt-8 pt-6 border-t border-slate-800/60 flex items-center justify-center space-x-2 text-slate-500">
          <ShieldCheck size={14} className="text-emerald-500/70" />
          <p className="text-[11px] font-medium tracking-wide uppercase">DPDP Act Compliant Infrastructure</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
