import { create } from 'zustand';

const API_BASE = 'http://localhost:8000/api/v1';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  userEmail: string | null;
  tenantId: string | null;
  userId: string | null;
  error: string | null;
  isLoading: boolean;
  requiresPasswordChange: boolean;
  pendingEmail: string | null;
  pendingCurrentPassword: string | null;
  login: (email: string, password: string) => Promise<void>;
  changePassword: (email: string, currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

const parseJwtPayload = (token: string | null) => {
  if (!token) return { tenantId: null, userId: null };
  try {
    const parts = token.split('.');
    if (parts.length === 3) {
      const payload = JSON.parse(atob(parts[1]));
      return {
        tenantId: payload.tenant_id || null,
        userId: payload.sub ? String(payload.sub) : null,
      };
    }
  } catch {
    // ignore
  }
  return { tenantId: null, userId: null };
};

const initialToken = localStorage.getItem('localmind_token');
const initialMeta = parseJwtPayload(initialToken);

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  isAuthenticated: !!initialToken,
  userEmail: localStorage.getItem('localmind_email'),
  tenantId: initialMeta.tenantId,
  userId: initialMeta.userId,
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
      const meta = parseJwtPayload(data.access_token);
      set({
        token: data.access_token,
        isAuthenticated: true,
        userEmail: email,
        tenantId: meta.tenantId,
        userId: meta.userId,
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
      const meta = parseJwtPayload(data.access_token);
      set({
        token: data.access_token,
        isAuthenticated: true,
        userEmail: email,
        tenantId: meta.tenantId,
        userId: meta.userId,
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
    // Clear auth credentials and any active session keys
    const currentToken = localStorage.getItem('localmind_token');
    const { tenantId, userId } = parseJwtPayload(currentToken);
    if (tenantId && userId) {
      localStorage.removeItem(`localmind_chat_${tenantId}_${userId}`);
    }
    localStorage.removeItem('localmind_chat_messages_v1');
    localStorage.removeItem('localmind_token');
    localStorage.removeItem('localmind_email');
    set({
      token: null,
      isAuthenticated: false,
      userEmail: null,
      tenantId: null,
      userId: null,
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
