import React from 'react';
import { Sun, Moon, Search, Bell, Menu, Shield } from 'lucide-react';
import { useThemeStore } from '../../store/themeStore';

export default function Header({ onToggleSidebar }) {
  const { resolvedTheme, toggleTheme } = useThemeStore();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border bg-background-surface px-4 shadow-subtle transition-colors lg:px-6">
      {/* Left: Mobile Menu & Branding */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleSidebar}
          className="rounded-lg p-2 text-foreground-muted hover:bg-background-hover hover:text-foreground lg:hidden focus:outline-none"
          aria-label="Toggle Navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center space-x-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground font-bold shadow-subtle">
            PSF
          </div>
          <div className="hidden sm:block">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">Post Service Follow-up</h1>
            <p className="text-xs text-foreground-subtle">Dealership CRM & Survey Suite</p>
          </div>
        </div>
      </div>

      {/* Middle: Global Search */}
      <div className="hidden md:flex flex-1 max-w-md mx-6">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-subtle" />
          <input
            type="text"
            placeholder="Search Job Card, Customer, VIN, Reg No..."
            className="w-full rounded-lg border border-border bg-background-base py-1.5 pl-9 pr-4 text-sm text-foreground placeholder:text-foreground-subtle focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>
      </div>

      {/* Right: Actions, Theme Toggle, Profile */}
      <div className="flex items-center space-x-2 sm:space-x-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={resolvedTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className="rounded-lg p-2 text-foreground-muted hover:bg-background-hover hover:text-foreground transition-colors"
        >
          {resolvedTheme === 'dark' ? (
            <Sun className="h-5 w-5 text-amber-400" />
          ) : (
            <Moon className="h-5 w-5 text-slate-600" />
          )}
        </button>

        {/* Notifications */}
        <button
          title="Notifications"
          className="relative rounded-lg p-2 text-foreground-muted hover:bg-background-hover hover:text-foreground transition-colors"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-accent animate-pulse" />
        </button>

        {/* User Mini Profile */}
        <div className="flex items-center space-x-3 border-l border-border pl-3 sm:pl-4">
          <div className="h-8 w-8 rounded-full bg-accent-subtle flex items-center justify-center text-accent font-semibold text-xs border border-accent/20">
            CRE
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-medium text-foreground">Priya Sharma</div>
            <div className="text-[10px] text-foreground-subtle">Central Workshop · Hyundai</div>
          </div>
        </div>
      </div>
    </header>
  );
}

