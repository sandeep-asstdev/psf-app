import { create } from 'zustand';
import api from '../services/api';
import toast from 'react-hot-toast';

export const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('psf_user') || 'null'),
  token: localStorage.getItem('psf_token') || null,
  isAuthenticated: !!localStorage.getItem('psf_token'),
  isLoading: false,

  login: async (email, password, deviceInfo = 'Web Browser') => {
    set({ isLoading: true });
    try {
      const res = await api.post('/auth/login', {
        email,
        password,
        device_info: deviceInfo,
      });

      const { access_token, user_id, email: userEmail, full_name, role, tenant_id, tenant_name, permissions } = res.data;

      localStorage.setItem('psf_token', access_token);
      
      // Fetch complete user profile with active shift and scopes
      const meRes = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      const userData = meRes.data;
      localStorage.setItem('psf_user', JSON.stringify(userData));

      set({
        user: userData,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
      });

      toast.success(`Welcome back, ${full_name}! Shift started.`);
      return true;
    } catch (err) {
      set({ isLoading: false });
      const msg = err.response?.data?.detail || 'Invalid email or password';
      toast.error(msg);
      return false;
    }
  },

  logout: async () => {
    try {
      const res = await api.post('/auth/logout');
      const min = res.data?.shift_duration_minutes || 0;
      toast.success(`Logged out successfully. Shift duration: ${min} minutes.`);
    } catch (err) {
      // ignore
    } finally {
      localStorage.removeItem('psf_token');
      localStorage.removeItem('psf_user');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
      });
      window.location.href = '/login';
    }
  },

  fetchProfile: async () => {
    const token = get().token;
    if (!token) return;

    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isAuthenticated: true });
      localStorage.setItem('psf_user', JSON.stringify(res.data));
    } catch (err) {
      if (err.response?.status === 401) {
        get().logout();
      }
    }
  },
}));
