import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import { Sun, Moon, ShieldCheck, Lock, Mail, ArrowRight, UserCheck, Clock } from 'lucide-react';

const DEMO_ACCOUNTS = [
  { role: 'CRE (Caller)', email: 'priya.cre@apexauto.com', name: 'Priya Sharma (Hyundai Central)' },
  { role: 'Dealer Admin', email: 'dealer.admin@apexauto.com', name: 'Vikram Malhotra (Apex Auto)' },
  { role: 'Service Advisor', email: 'rajesh.adv@apexauto.com', name: 'Rajesh Kumar (Central Hub)' },
  { role: 'Super Admin', email: 'admin@apexauto.com', name: 'Sandeep Sharma (Platform Owner)' },
];

export default function LoginPage() {
  const [email, setEmail] = useState('priya.cre@apexauto.com');
  const [password, setPassword] = useState('Priya@12345');
  const { login, isLoading } = useAuthStore();
  const { resolvedTheme, toggleTheme } = useThemeStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(email, password);
    if (success) {
      navigate('/');
    }
  };

  const handleSelectDemo = (demoEmail, demoRole) => {
    setEmail(demoEmail);
    if (demoEmail.includes('priya')) setPassword('Priya@12345');
    else if (demoEmail.includes('admin@')) setPassword('Admin@12345');
    else if (demoEmail.includes('dealer')) setPassword('Dealer@12345');
    else if (demoEmail.includes('rajesh')) setPassword('Advisor@12345');
    else setPassword('Welcome@123');
  };

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-background p-4 sm:p-6 lg:p-8">
      {/* Top right Theme Toggle */}
      <div className="absolute top-4 right-4">
        <button
          onClick={toggleTheme}
          className="rounded-xl border border-border bg-background-surface p-2.5 text-foreground-muted hover:bg-background-hover hover:text-foreground shadow-subtle transition-colors"
        >
          {resolvedTheme === 'dark' ? <Sun className="h-5 w-5 text-amber-400" /> : <Moon className="h-5 w-5 text-slate-600" />}
        </button>
      </div>

      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground font-black text-xl shadow-card">
            PSF
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            PSF Dealership Platform
          </h1>
          <p className="text-xs text-foreground-muted">
            Post Service Follow-up & Customer Retention Suite
          </p>
        </div>

        {/* Shift Attendance Notice */}
        <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-3.5 text-xs text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-300 shadow-subtle flex items-start space-x-2.5">
          <Clock className="h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div>
            <span className="font-semibold">Attendance Log Active:</span> Signing in automatically starts your CRE/Advisor caller shift and tracks session duration.
          </div>
        </div>

        {/* Login Card */}
        <div className="rounded-2xl border border-border bg-background-surface p-6 sm:p-8 shadow-card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-subtle" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@dealership.com"
                  className="w-full rounded-lg border border-border bg-background-base py-2.5 pl-9 pr-3 text-sm text-foreground focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-subtle" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-border bg-background-base py-2.5 pl-9 pr-3 text-sm text-foreground focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-2 flex w-full items-center justify-center space-x-2 rounded-lg bg-accent py-2.5 px-4 text-sm font-semibold text-white hover:bg-accent-hover shadow-subtle transition-colors disabled:opacity-50"
            >
              <span>{isLoading ? 'Authenticating...' : 'Sign In & Start Shift'}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Quick Demo Switcher */}
          <div className="mt-6 border-t border-border pt-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-foreground-subtle block mb-2.5 text-center">
              Quick Role Switch (Demo)
            </span>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((d) => (
                <button
                  key={d.role}
                  type="button"
                  onClick={() => handleSelectDemo(d.email, d.role)}
                  className={`rounded-lg border p-2 text-left text-xs transition-colors ${
                    email === d.email
                      ? 'border-accent bg-accent-subtle text-accent font-medium dark:bg-slate-800'
                      : 'border-border bg-background-base text-foreground-muted hover:border-accent/40'
                  }`}
                >
                  <div className="font-semibold text-foreground text-[11px]">{d.role}</div>
                  <div className="text-[10px] text-foreground-subtle truncate">{d.name}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Security watermark */}
        <div className="flex items-center justify-center space-x-2 text-xs text-foreground-subtle">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>AES-256 PII Encrypted · Multi-Tenant Isolated</span>
        </div>
      </div>
    </div>
  );
}
