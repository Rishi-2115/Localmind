import { create } from 'zustand';

const API_BASE = 'http://localhost:8000/api/v1';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  userEmail: string | null;
  error: string | null;
  isLoading: boolean;
  requiresPasswordChange: boolean;
  pendingEmail: string | null;
  pendingCurrentPassword: string | null;
  login: (email: string, password: string) => Promise<void>;
  changePassword: (email: string, currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('localmind_token'),
  isAuthenticated: !!localStorage.getItem('localmind_token'),
  userEmail: localStorage.getItem('localmind_email'),
  error: null,
  isLoading: false,
  requiresPasswordChange: false,
  pendingEmail: null,
  pendingCurrentPassword: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 form expects "username"
      formData.append('password', password);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      if (!res.ok) {
        const detail = await res.json();
        const errObj = detail.detail;
        if (res.status === 403 && (errObj?.code === 'PASSWORD_CHANGE_REQUIRED' || (typeof errObj === 'string' && errObj.includes('Password change required')))) {
          set({
            requiresPasswordChange: true,
            pendingEmail: email,
            pendingCurrentPassword: password,
            isLoading: false,
            error: 'Initial password change required by security policy (min 12 characters).',
          });
          return;
        }
        throw new Error(typeof errObj === 'string' ? errObj : (errObj?.message || 'Login failed'));
      }

      const data = await res.json();
      localStorage.setItem('localmind_token', data.access_token);
      localStorage.setItem('localmind_email', email);
      set({
        token: data.access_token,
        isAuthenticated: true,
        userEmail: email,
        isLoading: false,
        requiresPasswordChange: false,
        pendingEmail: null,
        pendingCurrentPassword: null,
      });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  changePassword: async (email: string, currentPassword: string, newPassword: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || 'Password change failed');
      }

      const data = await res.json();
      localStorage.setItem('localmind_token', data.access_token);
      localStorage.setItem('localmind_email', email);
      set({
        token: data.access_token,
        isAuthenticated: true,
        userEmail: email,
        isLoading: false,
        requiresPasswordChange: false,
        pendingEmail: null,
        pendingCurrentPassword: null,
        error: null,
      });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('localmind_token');
    localStorage.removeItem('localmind_email');
    set({
      token: null,
      isAuthenticated: false,
      userEmail: null,
      requiresPasswordChange: false,
      pendingEmail: null,
      pendingCurrentPassword: null,
    });
  },
}));

export const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('localmind_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export { API_BASE };
