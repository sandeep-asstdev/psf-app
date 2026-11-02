import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PhoneCall,
  HeartHandshake,
  AlertOctagon,
  BarChart3,
  Users,
  Settings,
  UploadCloud,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

const MODULE_TILES = [
  {
    title: 'PSF Dashboard',
    desc: 'Conduct post-service follow-up calls, complete brand questionnaires & calculate CSAT/NPS.',
    icon: PhoneCall,
    to: '/psf',
    badge: '14 Pending',
    badgeColor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    stat: '92% Connect Rate',
  },
  {
    title: 'Happiness Calling',
    desc: '15-day & 30-day post-delivery satisfaction checks to build long-term retention.',
    icon: HeartHandshake,
    to: '/happiness',
    badge: '6 Calls Due',
    badgeColor: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    stat: '4.8 Avg CSAT',
  },
  {
    title: 'Complaints Management',
    desc: 'Escalate customer dissatisfaction, track workshop corrective action & SLA timers.',
    icon: AlertOctagon,
    to: '/complaints',
    badge: '3 Open',
    badgeColor: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
    stat: '100% Reconfirmed',
  },
  {
    title: 'Reports & Analytics',
    desc: 'CSAT / NPS trends, CRE productivity, complaint turnaround time & advisor scorecards.',
    icon: BarChart3,
    to: '/reports',
    badge: 'Realtime',
    badgeColor: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    stat: 'Exports Ready',
  },
  {
    title: 'DMS Data Import',
    desc: 'Upload daily job cards from DMS via Excel/CSV, auto-map columns & distribute queues.',
    icon: UploadCloud,
    to: '/import',
    badge: 'Batch Ready',
    badgeColor: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    stat: 'Auto-Allocation',
  },
  {
    title: 'User Management',
    desc: 'Manage CREs, Service Advisors, Brand & Branch Managers with role-based scoping.',
    icon: Users,
    to: '/users',
    badge: 'Role Scoped',
    badgeColor: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    stat: '12 Active Staff',
  },
];

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* Welcome Greeting Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-blue-600 to-indigo-700 p-6 sm:p-8 text-white shadow-card">
        <div className="relative z-10 max-w-3xl space-y-2">
          <div className="inline-flex items-center space-x-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Shift Active · Shift duration: 2h 45m</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Good Afternoon, Priya Sharma 👋
          </h1>
          <p className="text-sm text-blue-100 leading-relaxed max-w-2xl">
            Welcome to the <strong>PSF Dealership Follow-up Platform</strong>. You have <strong>14 job cards</strong> queued for post-service calling today across Central Workshop (Hyundai & MG).
          </p>
        </div>

        {/* Decorative background circle */}
        <div className="absolute -right-12 -bottom-12 h-64 w-64 rounded-full bg-white/5 blur-2xl pointer-events-none" />
      </div>

      {/* KPI Snapshot Pills */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-border bg-background-surface p-4 shadow-subtle">
          <div className="flex items-center justify-between text-xs text-foreground-subtle">
            <span>Today's Target</span>
            <Clock className="h-4 w-4 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">35 Calls</div>
          <div className="mt-1 flex items-center text-xs text-status-success font-medium">
            <TrendingUp className="mr-1 h-3.5 w-3.5" />
            <span>21 completed (60%)</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-background-surface p-4 shadow-subtle">
          <div className="flex items-center justify-between text-xs text-foreground-subtle">
            <span>Connect Rate</span>
            <PhoneCall className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">88.5%</div>
          <div className="mt-1 text-xs text-foreground-subtle">19 / 21 connected</div>
        </div>

        <div className="rounded-xl border border-border bg-background-surface p-4 shadow-subtle">
          <div className="flex items-center justify-between text-xs text-foreground-subtle">
            <span>NPS (This Month)</span>
            <CheckCircle2 className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">+74</div>
          <div className="mt-1 text-xs text-foreground-subtle">Target: +70 (Exceeded)</div>
        </div>

        <div className="rounded-xl border border-border bg-background-surface p-4 shadow-subtle">
          <div className="flex items-center justify-between text-xs text-foreground-subtle">
            <span>Pending Complaints</span>
            <AlertOctagon className="h-4 w-4 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-status-danger">3 Tickets</div>
          <div className="mt-1 text-xs text-foreground-subtle">0 SLA breached</div>
        </div>
      </div>

      {/* Primary Workstation Modules */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Core Workspaces</h2>
          <span className="text-xs text-foreground-subtle">Select a module to begin work</span>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {MODULE_TILES.map((tile) => {
            const Icon = tile.icon;
            return (
              <div
                key={tile.title}
                onClick={() => navigate(tile.to)}
                className="group relative flex cursor-pointer flex-col justify-between rounded-xl border border-border bg-background-card p-5 shadow-subtle transition-all duration-200 hover:-translate-y-0.5 hover:border-accent hover:shadow-card"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background-hover text-accent transition-colors group-hover:bg-accent group-hover:text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${tile.badgeColor}`}>
                      {tile.badge}
                    </span>
                  </div>

                  <h3 className="mt-4 text-base font-semibold text-foreground group-hover:text-accent transition-colors">
                    {tile.title}
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-foreground-muted">
                    {tile.desc}
                  </p>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-border/60 pt-3 text-xs">
                  <span className="font-medium text-foreground-subtle">{tile.stat}</span>
                  <div className="flex items-center font-medium text-accent group-hover:translate-x-1 transition-transform">
                    <span>Open Module</span>
                    <ArrowRight className="ml-1 h-3.5 w-3.5" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

