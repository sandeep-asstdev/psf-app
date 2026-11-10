/**
 * ============================================================================
 * FILE PURPOSE: Zustand Authentication State & RBAC Permission Checking Store.
 * Maintains the currently logged-in user's profile, JWT access token, and list of permissions.
 * Provides easy permission checking helpers (`can('call.make')`, `canAny(...)`) used across all UI components.
 * 
 * KEY RESPONSIBILITIES:
 * - Stores authenticated user profile object and JWT token string in localStorage.
 * - Provides `can(permissionKey)` helper to check if the user has a specific permission.
 * - Provides `canAny(...permissionKeys)` helper for multi-permission UI checks.
 * - Handles login state hydration and logout cleanup (`logout`).
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: User permissions do not update after role change in Admin Console
 *   -> Cause: Permissions are cached in the user's active session token.
 *   -> What should you do: Log out and log back in to refresh the JWT token with the newly assigned permissions.
 * ============================================================================
 */
import { create } from 'zustand';
import api from '../services/api';
import toast from 'react-hot-toast';

export const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('psf_user') || 'null'),
  token: localStorage.getItem('psf_token') || null,
  originalToken: localStorage.getItem('psf_orig_token') || null,
  isAuthenticated: !!localStorage.getItem('psf_token'),
  isImpersonating: !!localStorage.getItem('psf_orig_token'),
  permissions: JSON.parse(localStorage.getItem('psf_permissions') || '{}'),
  fieldRules: JSON.parse(localStorage.getItem('psf_field_rules') || '{}'),
  dashboardConfig: JSON.parse(localStorage.getItem('psf_dashboard_config') || '{}'),
  isLoading: false,

  /** Check if the current user has a specific permission */
  can: (permissionKey) => {
    const { user, permissions } = get();
    if (!user) return false;
    if (user.is_super_admin || user.role_name === 'SUPER_ADMIN') return true;
    return !!permissions[permissionKey];
  },

  /** Check if the current user has any of the listed permissions */
  canAny: (...permissionKeys) => {
    const { user, permissions } = get();
    if (!user) return false;
    if (user.is_super_admin || user.role_name === 'SUPER_ADMIN') return true;
    return permissionKeys.some((k) => !!permissions[k]);
  },

  /** Check if a field is visible / editable / masked */
  getFieldRule: (fieldName) => {
    const { user, fieldRules } = get();
    if (user?.is_super_admin) return 'editable';
    return fieldRules[fieldName] || 'visible';
  },

  login: async (email, password, deviceInfo = 'Web Browser') => {
    set({ isLoading: true });
    try {
      const res = await api.post('/auth/login', {
        email,
        password,
        device_info: deviceInfo,
      });

      const { access_token, full_name } = res.data;
      localStorage.setItem('psf_token', access_token);

      // Fetch complete profile & permissions
      const [meRes, permRes] = await Promise.all([
        api.get('/auth/me', { headers: { Authorization: `Bearer ${access_token}` } }),
        api.get('/auth/me/permissions', { headers: { Authorization: `Bearer ${access_token}` } }),
      ]);

      const userData = meRes.data;
      const permData = permRes.data;

      const permsMap = permData.permissions || {};
      const fRules = permData.field_rules || {};
      const dConfig = permData.dashboard_config || {};

      localStorage.setItem('psf_user', JSON.stringify(userData));
      localStorage.setItem('psf_permissions', JSON.stringify(permsMap));
      localStorage.setItem('psf_field_rules', JSON.stringify(fRules));
      localStorage.setItem('psf_dashboard_config', JSON.stringify(dConfig));

      set({
        user: userData,
        token: access_token,
        permissions: permsMap,
        fieldRules: fRules,
        dashboardConfig: dConfig,
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
      localStorage.removeItem('psf_permissions');
      localStorage.removeItem('psf_field_rules');
      localStorage.removeItem('psf_dashboard_config');
      localStorage.removeItem('psf_orig_token');
      localStorage.removeItem('psf_orig_user');
      set({
        user: null,
        token: null,
        originalToken: null,
        permissions: {},
        fieldRules: {},
        dashboardConfig: {},
        isAuthenticated: false,
        isImpersonating: false,
      });
      window.location.href = '/login';
    }
  },

  impersonate: async (targetUserId, reason = 'Admin simulation') => {
    set({ isLoading: true });
    try {
      const currentToken = get().token;
      const currentUser = get().user;

      const res = await api.post(`/auth/impersonate/${targetUserId}?reason=${encodeURIComponent(reason)}`);
      const { access_token, user: impUser } = res.data;

      // Stash original token and user
      localStorage.setItem('psf_orig_token', currentToken);
      localStorage.setItem('psf_orig_user', JSON.stringify(currentUser));

      localStorage.setItem('psf_token', access_token);
      localStorage.setItem('psf_user', JSON.stringify(impUser));

      // Fetch impersonated permissions
      const permRes = await api.get('/auth/me/permissions', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const permsMap = permRes.data.permissions || {};
      const fRules = permRes.data.field_rules || {};
      const dConfig = permRes.data.dashboard_config || {};

      localStorage.setItem('psf_permissions', JSON.stringify(permsMap));
      localStorage.setItem('psf_field_rules', JSON.stringify(fRules));
      localStorage.setItem('psf_dashboard_config', JSON.stringify(dConfig));

      set({
        token: access_token,
        user: impUser,
        originalToken: currentToken,
        isImpersonating: true,
        permissions: permsMap,
        fieldRules: fRules,
        dashboardConfig: dConfig,
        isLoading: false,
      });

      toast.success(`Now viewing as ${impUser.full_name} (${impUser.role_name || impUser.role})`);
      return true;
    } catch (err) {
      set({ isLoading: false });
      const msg = err.response?.data?.detail || 'Impersonation failed';
      toast.error(msg);
      return false;
    }
  },

  exitImpersonation: async () => {
    const origToken = localStorage.getItem('psf_orig_token');
    const origUser = JSON.parse(localStorage.getItem('psf_orig_user') || 'null');

    if (!origToken) {
      get().logout();
      return;
    }

    localStorage.removeItem('psf_orig_token');
    localStorage.removeItem('psf_orig_user');
    localStorage.setItem('psf_token', origToken);
    localStorage.setItem('psf_user', JSON.stringify(origUser));

    // Refetch original admin permissions
    try {
      const permRes = await api.get('/auth/me/permissions', {
        headers: { Authorization: `Bearer ${origToken}` },
      });
      const permsMap = permRes.data.permissions || {};
      localStorage.setItem('psf_permissions', JSON.stringify(permsMap));

      set({
        token: origToken,
        user: origUser,
        originalToken: null,
        isImpersonating: false,
        permissions: permsMap,
      });
      toast.success('Exited simulation mode. Returned to Super Admin.');
      window.location.href = '/admin-console';
    } catch (err) {
      get().logout();
    }
  },

  fetchProfile: async () => {
    const token = get().token;
    if (!token) return;

    try {
      const [meRes, permRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/auth/me/permissions'),
      ]);

      const userData = meRes.data;
      const permsMap = permRes.data.permissions || {};
      const fRules = permRes.data.field_rules || {};
      const dConfig = permRes.data.dashboard_config || {};

      set({
        user: userData,
        permissions: permsMap,
        fieldRules: fRules,
        dashboardConfig: dConfig,
        isAuthenticated: true,
      });

      localStorage.setItem('psf_user', JSON.stringify(userData));
      localStorage.setItem('psf_permissions', JSON.stringify(permsMap));
      localStorage.setItem('psf_field_rules', JSON.stringify(fRules));
      localStorage.setItem('psf_dashboard_config', JSON.stringify(dConfig));
    } catch (err) {
      if (err.response?.status === 401) {
        get().logout();
      }
    }
  },
}));
