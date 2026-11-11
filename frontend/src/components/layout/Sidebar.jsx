/**
 * ============================================================================
 * FILE PURPOSE: Left Navigation Sidebar with Permission Filtering.
 * Renders the primary navigation menu links, filtering each link based on the user's role permissions,
 * and displays the real-time active shift timer in the footer.
 * 
 * KEY RESPONSIBILITIES:
 * - Filters menu items according to user permissions (`can`, `canAny`).
 * - Highlights the active navigation route.
 * - Displays active shift elapsed timer (e.g. 'Shift Active: 2 hours active').
 * - Provides End Shift & Log Out button at the bottom.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: A menu link (e.g. Enterprise Admin) is missing for a user
 *   -> Cause: The user's role lacks the required permission for that menu item.
 *   -> What should you do: This is by design (RBAC). Super Admin has access to all links; CRE only sees calling screens.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  PhoneCall,
  Zap,
  HeartHandshake,
  AlertOctagon,
  Wrench,
  BarChart3,
  UploadCloud,
  Users,
  Settings,
  LogOut,
  Clock,
  X,
  ShieldCheck,
  Building2,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { formatDistanceToNow } from 'date-fns';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/psf', label: 'PSF Dashboard', icon: PhoneCall, badge: '14', permission: 'call.view' },
  { to: '/tnps', label: 'TNPS Dashboard', icon: Zap, badge: 'Ather', permission: 'call.view' },
  { to: '/happiness', label: 'Happiness Calling', icon: HeartHandshake, badge: '6', permission: 'call.view' },
  { to: '/complaints', label: 'Complaints', icon: AlertOctagon, badge: '3', permission: 'complaint.view' },
  { to: '/advisor', label: 'Advisor Followup', icon: Wrench, permission: 'advisor.action' },
  { to: '/activity', label: 'App Usage & Audit', icon: ShieldCheck },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3, permission: 'report.view' },
  { to: '/import', label: 'Data Import', icon: UploadCloud, permission: 'jobcard.import' },
  { to: '/users', label: 'User Management', icon: Users, permissions: ['user.create', 'user.edit'] },
  { to: '/admin-console', label: 'Enterprise Admin', icon: ShieldCheck, permissions: ['role.manage', 'permission.manage', 'brand.manage', 'data.correct'] },
  { to: '/admin-console?tab=tenants', label: 'Tenants & Dealerships', icon: Building2, permissions: ['role.manage', 'permission.manage', 'brand.manage', 'data.correct'] },
  { to: '/settings', label: 'Settings', icon: Settings, permissions: ['brand.manage', 'settings.manage', 'config.view'] },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout, can, canAny } = useAuthStore();
  const [elapsedTime, setElapsedTime] = useState('');

  const visibleNavItems = NAV_ITEMS.filter((item) => {
    if (user?.is_super_admin) return true;
    if (item.permission) return can(item.permission);
    if (item.permissions) return canAny(...item.permissions);
    return true;
  });

  useEffect(() => {
    if (!user?.active_shift_login) {
      setElapsedTime('Shift Not Started');
      return;
    }

    const updateTimer = () => {
      try {
        const distance = formatDistanceToNow(new Date(user.active_shift_login), { addSuffix: false });
        setElapsedTime(distance);
      } catch (e) {
        setElapsedTime('Active');
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000);
    return () => clearInterval(interval);
  }, [user?.active_shift_login]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-background-surface transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Mobile Header Close */}
        <div className="flex h-16 items-center justify-between border-b border-border px-4 lg:hidden">
          <span className="font-semibold text-foreground">Menu Navigation</span>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-foreground-muted hover:bg-background-hover"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => onClose()}
                className={({ isActive }) =>
                  `flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent text-accent-foreground shadow-subtle'
                      : 'text-foreground-muted hover:bg-background-hover hover:text-foreground'
                  }`
                }
              >
                <div className="flex items-center space-x-3">
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="rounded-full bg-accent-subtle px-2 py-0.5 text-xs font-semibold text-accent dark:bg-slate-800 dark:text-sky-300">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Section: User Session / Sign Out */}
        <div className="border-t border-border p-3 space-y-2">
          <div className="flex items-center justify-between text-xs px-2 py-1 text-foreground-muted">
            <span className="truncate max-w-[150px] font-medium">{user?.full_name || user?.email}</span>
            <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">{user?.role_name}</span>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center space-x-2 rounded-lg px-3 py-2 text-xs font-semibold text-status-danger hover:bg-status-danger/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
