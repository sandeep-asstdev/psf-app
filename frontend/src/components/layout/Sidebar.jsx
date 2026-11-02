import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  PhoneCall,
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
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { formatDistanceToNow } from 'date-fns';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/psf', label: 'PSF Dashboard', icon: PhoneCall, badge: '14' },
  { to: '/happiness', label: 'Happiness Calling', icon: HeartHandshake, badge: '6' },
  { to: '/complaints', label: 'Complaints', icon: AlertOctagon, badge: '3' },
  { to: '/advisor', label: 'Advisor Followup', icon: Wrench },
  { to: '/attendance', label: 'Shift Attendance', icon: Clock },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
  { to: '/import', label: 'Data Import', icon: UploadCloud },
  { to: '/users', label: 'User Management', icon: Users },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuthStore();
  const [elapsedTime, setElapsedTime] = useState('');

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
          {NAV_ITEMS.map((item) => {
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

        {/* Bottom Section: Attendance Log / Logout */}
        <div className="border-t border-border p-3 space-y-2">
          <div className="rounded-lg bg-background-base p-2 text-xs">
            <div className="flex items-center justify-between text-foreground-subtle mb-0.5">
              <span>Shift Active:</span>
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <div className="font-semibold text-foreground">
              {elapsedTime ? `${elapsedTime} active` : 'Active'}
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center space-x-2 rounded-lg px-3 py-2 text-xs font-semibold text-status-danger hover:bg-status-danger/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>End Shift & Log Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
