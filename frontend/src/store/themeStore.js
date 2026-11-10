/**
 * ============================================================================
 * FILE PURPOSE: Zustand Theme Management Store (Light / Dark Mode).
 * Stores the user's color scheme preference in localStorage and toggles the `dark` class
 * on the root HTML document element.
 * 
 * KEY RESPONSIBILITIES:
 * - Toggles between 'light' and 'dark' display modes.
 * - Persists user theme choice in browser localStorage.
 * - Applies or removes the `dark` class on the HTML `document.documentElement`.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Dark mode styles not applying to a component
 *   -> Cause: Component missing Tailwind dark mode classes (e.g. `dark:bg-slate-900`).
 *   -> What should you do: Add explicit `dark:` prefix variants to the component's JSX className.
 * ============================================================================
 */
import { create } from 'zustand';

export const useThemeStore = create((set, get) => ({
  theme: 'system', // 'light' | 'dark' | 'system'
  resolvedTheme: 'light',

  initTheme: () => {
    const saved = localStorage.getItem('psf-theme') || 'system';
    get().setTheme(saved);

    // Watch system changes if set to system
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (get().theme === 'system') {
          const newResolved = e.matches ? 'dark' : 'light';
          get().applyThemeClass(newResolved);
          set({ resolvedTheme: newResolved });
        }
      });
    }
  },

  setTheme: (newTheme) => {
    localStorage.setItem('psf-theme', newTheme);
    let resolved = newTheme;

    if (newTheme === 'system') {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      resolved = prefersDark ? 'dark' : 'light';
    }

    get().applyThemeClass(resolved);
    set({ theme: newTheme, resolvedTheme: resolved });
  },

  applyThemeClass: (resolved) => {
    const root = document.documentElement;
    if (resolved === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  },

  toggleTheme: () => {
    const current = get().resolvedTheme;
    const next = current === 'dark' ? 'light' : 'dark';
    get().setTheme(next);
  },
}));

