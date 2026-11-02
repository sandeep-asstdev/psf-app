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

