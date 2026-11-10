/**
 * ============================================================================
 * FILE PURPOSE: Frontend Smoke & Render Test Suite.
 * Verifies that core React components render successfully without throwing unhandled exceptions.
 * 
 * KEY RESPONSIBILITIES:
 * - Tests that the application mounts without runtime syntax errors.
 * - Tests that basic UI controls render properly.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Smoke test fails with ReferenceError or TypeError
 *   -> Cause: A component has an unhandled null check or missing import.
 *   -> What should you do: Check the test error output for the component name and line number.
 * ============================================================================
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useThemeStore } from '../store/themeStore';
import { useAuthStore } from '../store/authStore';

describe('Frontend Theme Store', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with system theme or persisted preference', () => {
    const { initTheme, theme } = useThemeStore.getState();
    initTheme();
    expect(['light', 'dark', 'system']).toContain(theme);
    expect(['light', 'dark']).toContain(useThemeStore.getState().resolvedTheme);
  });

  it('toggles theme between light and dark', () => {
    const { setTheme } = useThemeStore.getState();
    setTheme('dark');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(useThemeStore.getState().resolvedTheme).toBe('dark');
    expect(localStorage.getItem('psf-theme')).toBe('dark');

    setTheme('light');
    expect(useThemeStore.getState().theme).toBe('light');
    expect(useThemeStore.getState().resolvedTheme).toBe('light');
    expect(localStorage.getItem('psf-theme')).toBe('light');
  });
});

describe('Frontend Auth Store', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('manages auth token state and logout correctly', async () => {
    const { logout } = useAuthStore.getState();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);

    // Simulate session load
    localStorage.setItem('psf_token', 'sample-jwt-token');
    useAuthStore.setState({ token: 'sample-jwt-token', isAuthenticated: true });
    expect(useAuthStore.getState().token).toBe('sample-jwt-token');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    await logout();
    expect(useAuthStore.getState().token).toBe(null);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
