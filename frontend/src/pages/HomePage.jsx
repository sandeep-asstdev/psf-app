/**
 * ============================================================================
 * FILE PURPOSE: Dealership PSF Home Landing Page.
 * This is the first screen all dealership users see upon login. It displays their shift greeting,
 * high-level calling KPI cards (Pending Calls, Contacted, Connect Rate, Open Complaints),
 * and an immediate Calling Queue Line Items table with one-click calling and WhatsApp triggers.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches dashboard KPI counters from `GET /api/v1/psf/dashboard`.
 * - Fetches pending calling queue items from `GET /api/v1/psf/queues?status=PENDING`.
 * - Enforces role scoping: CRE callers only see their assigned customers; Admins see dealership-wide calls.
 * - Provides one-click telephone (`tel:`) and WhatsApp chat links.
 * - Provides quick navigation buttons to Data Import and Full PSF Calling Workspace.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: KPI cards show 0 and table shows 'Loading calling queue...' permanently
 *   -> Cause: Backend API server is unreachable, deadlocked, or JWT session expired.
 *   -> What should you do: Open browser DevTools Network tab. If requests are timing out, check `docker ps` and restart `psf_api` with `docker restart psf_api`.
 * - Error: Table says 'No pending calls found in your queue'
 *   -> Cause: For a CRE caller, no customers have been allocated to your account yet today.
 *   -> What should you do: Ask the CRE Admin to import today's DMS job cards or click 'Allocate Now' in Shift Attendance.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
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
  UserCheck,
  Building2,
  Phone,
  MessageSquare,
} from 'lucide-react';
import api from '../services/api';
import { useAuthStore } from '../store/authStore';

export default function HomePage() {
  const navigate = useNavigate();
  const { user, can } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [recentQueues, setRecentQueues] = useState([]);
  const [loading, setLoading] = useState(true);

  const isSuperAdmin = user?.is_super_admin || user?.role_name === 'SUPER_ADMIN';
  const isCreAdmin = user?.role_name === 'CRE_ADMIN' || user?.role_name === 'DEALER_ADMIN';
  const showAdminViews = isSuperAdmin || isCreAdmin || can('call.allocate');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, queuesRes] = await Promise.all([
        api.get('/psf/dashboard'),
        api.get('/psf/queues?status=ACTIVE&limit=10'),
      ]);
      setStats(statsRes.data);
      setRecentQueues(queuesRes.data.items || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getTimeGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const formatDisplayDate = (d) => {
    if (!d) return '—';
    try {
      const parts = String(d).split('T')[0].split('-');
      if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
      return d;
    } catch {
      return d;
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Welcome Greeting Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 p-6 sm:p-7 text-white shadow-card">
        <div className="relative z-10 max-w-3xl space-y-2">
          <div className="inline-flex items-center space-x-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Role: {user?.role_name || 'Staff User'} • Shift Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            {getTimeGreeting()}, {user?.full_name || 'Team'} 👋
          </h1>
          <p className="text-sm text-blue-100 leading-relaxed max-w-2xl">
            {showAdminViews ? (
              <span>
                You have <strong>{stats?.total_pending ?? 0} pending customer calls</strong> across your dealership workshops today.
              </span>
            ) : (
              <span>
                You have <strong>{stats?.total_pending ?? 0} assigned customer calls</strong> waiting in your calling queue today.
              </span>
            )}
          </p>
        </div>

        {/* Decorative background glow */}
        <div className="absolute -right-12 -bottom-12 h-64 w-64 rounded-full bg-white/5 blur-2xl pointer-events-none" />
      </div>

      {/* 2. KPI Snapshot Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Pending Calls</span>
            <Clock className="h-4 w-4 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
            {stats?.total_pending ?? 0}
          </div>
          <div className="mt-1 text-xs text-blue-600 font-medium">Due today</div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Total Contacted</span>
            <PhoneCall className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-emerald-600 dark:text-emerald-400">
            {stats?.total_contacted ?? 0}
          </div>
          <div className="mt-1 text-xs text-emerald-600 font-medium">Completed surveys</div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Connect Rate</span>
            <TrendingUp className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-indigo-600 dark:text-indigo-400">
            {stats?.connect_rate_pct ?? 0}%
          </div>
          <div className="mt-1 text-xs text-indigo-600 font-medium">Contact ratio</div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Open Complaints</span>
            <AlertOctagon className="h-4 w-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-amber-600 dark:text-amber-400">
            {stats?.open_complaints_count ?? 0}
          </div>
          <div className="mt-1 text-xs text-amber-600 font-medium">Requires resolution</div>
        </div>
      </div>

      {/* Ather Energy TNPS Calls Widget (Only visible when Ather TNPS is present) */}
      {stats?.tnps_calls_by_branch?.length > 0 && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/20 dark:to-teal-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-200/60 dark:border-emerald-800/60 mb-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-200">
                Ather Energy TNPS Follow-up Calls (By Workshop Branch)
              </h3>
            </div>
            <button
              type="button"
              onClick={() => navigate('/psf')}
              className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:underline flex items-center gap-1"
            >
              <span>View In PSF Workspace</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {stats.tnps_calls_by_branch.map((b) => (
              <div
                key={b.branch_id}
                onClick={() => navigate('/psf')}
                className="cursor-pointer bg-white dark:bg-slate-900 p-3 rounded-lg border border-emerald-100 dark:border-emerald-900/50 hover:border-emerald-500 transition shadow-xs"
              >
                <div className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  {b.branch_name}
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">Pending:</span>
                  <span className="font-bold text-blue-600 dark:text-blue-400 font-mono">
                    {b.pending_count}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">Contacted:</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                    {b.contacted_count}
                  </span>
                </div>
                <div className="mt-1 pt-1.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">Total TNPS:</span>
                  <span className="font-semibold text-slate-700 dark:text-slate-300 font-mono">
                    {b.total_calls}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. ASSIGNED CALLING QUEUE LINE ITEMS TABLE (No repetitive cards!) */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <PhoneCall className="h-4 w-4 text-blue-600" />
              <span>{showAdminViews ? 'Active Calling Queue Line Items' : 'My Immediate Calling Queue'}</span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold font-mono">
                {stats?.total_pending ?? 0} pending
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any customer row or the Call button to open the calling console and record sentiment.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {showAdminViews && (
              <button
                type="button"
                onClick={() => navigate('/import')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition shadow-xs"
              >
                <UploadCloud className="h-3.5 w-3.5 text-blue-600" />
                <span>Import DMS</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => navigate('/psf')}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition shadow-xs"
            >
              <span>View Full Line Items Table</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-slate-500">Loading calling queue...</div>
        ) : recentQueues.length === 0 ? (
          <div className="py-16 text-center text-xs text-slate-400">
            No pending calls found in your queue.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 whitespace-nowrap">
                <tr>
                  <th className="py-2.5 px-3">Job Card No</th>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Customer Name</th>
                  <th className="py-2.5 px-3">Branch</th>
                  <th className="py-2.5 px-3">Brand</th>
                  <th className="py-2.5 px-3">Reg No</th>
                  <th className="py-2.5 px-3">Model</th>
                  <th className="py-2.5 px-3">Service Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Followed By</th>
                  <th className="py-2.5 px-3">Advisor</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                {recentQueues.map((q) => (
                  <tr
                    key={q.id}
                    onClick={() => navigate('/psf')}
                    className="hover:bg-blue-50/50 dark:hover:bg-slate-800/60 transition cursor-pointer"
                  >
                    <td className="py-2.5 px-3 font-mono font-semibold text-blue-600 dark:text-blue-400">
                      {q.job_card_no}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                      {formatDisplayDate(q.job_card_date)}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                      <div className="flex items-center gap-1.5">
                        <span>{q.customer_name}</span>
                        {q.customer_phone_raw && (
                          <div className="flex items-center gap-1 ml-1" onClick={(e) => e.stopPropagation()}>
                            <a
                              href={`tel:${q.customer_phone_raw}`}
                              className="text-emerald-600 hover:text-emerald-700 p-0.5"
                              title={`Call ${q.customer_phone_masked}`}
                            >
                              <Phone className="h-3 w-3" />
                            </a>
                            <a
                              href={`https://wa.me/91${q.customer_phone_raw}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-green-600 hover:text-green-700 p-0.5"
                              title="WhatsApp Chat"
                            >
                              <MessageSquare className="h-3 w-3" />
                            </a>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">{q.branch_name}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold text-white shadow-xs"
                        style={{ backgroundColor: q.brand_color || '#2563EB' }}
                      >
                        {q.brand_code || q.brand_name}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-semibold">{q.vehicle_reg_no}</td>
                    <td className="py-2.5 px-3 font-medium">{q.vehicle_model}</td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">{q.service_type || 'Paid Service'}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          q.last_call_status === 'Connected' || q.status === 'CONTACTED' || q.status === 'CONNECTED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                            : q.last_call_status === 'Not Connected' || q.status === 'NOT_CONTACTED'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                            : q.last_call_status === 'Callback Requested' || q.status === 'CALLBACK_REQUESTED'
                            ? 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300'
                            : q.status === 'COMPLAINT_REGISTERED'
                            ? 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                        }`}
                      >
                        {q.last_call_status || (q.status === 'PENDING' ? 'Pending' : q.status.replace(/_/g, ' '))}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                      {q.assigned_to_name ? (
                        <span className="inline-flex items-center gap-1">
                          <UserCheck className="h-3 w-3 text-blue-600" />
                          <span>{q.assigned_to_name}</span>
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">{q.service_advisor || '—'}</td>
                    <td className="py-2.5 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => navigate('/psf')}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-[11px] transition shadow-xs"
                      >
                        <PhoneCall className="h-3 w-3" />
                        <span>Call</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. Minimal Workspace Shortcuts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div
          onClick={() => navigate('/psf')}
          className="cursor-pointer rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm hover:border-blue-500 transition group flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition">
              <PhoneCall className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition">
                PSF Calling Workspace
              </div>
              <div className="text-[11px] text-slate-500">Conduct customer surveys & VOC</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition" />
        </div>

        {showAdminViews && (
          <div
            onClick={() => navigate('/import')}
            className="cursor-pointer rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm hover:border-blue-500 transition group flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 group-hover:bg-sky-600 group-hover:text-white transition">
                <UploadCloud className="h-5 w-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition">
                  DMS Data Import
                </div>
                <div className="text-[11px] text-slate-500">Upload & equal split calls</div>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition" />
          </div>
        )}

        <div
          onClick={() => navigate('/complaints')}
          className="cursor-pointer rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm hover:border-blue-500 transition group flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 group-hover:bg-amber-600 group-hover:text-white transition">
              <AlertOctagon className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition">
                Complaints Management
              </div>
              <div className="text-[11px] text-slate-500">SLA tracking & resolution</div>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition" />
        </div>
      </div>
    </div>
  );
}
