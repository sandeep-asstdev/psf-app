/**
 * ============================================================================
 * FILE PURPOSE: Shift Attendance & Daily Login Logs Page.
 * Displays the chronological history of daily login and logout timestamps for dealership personnel,
 * showing shift start, shift end, duration, IP address, and attendance status.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches login attendance logs from `GET /api/v1/auth/attendance/logs`.
 * - Displays shift status (Active / Completed) and active shift duration.
 * - Allows CRE Admin to see who punched in today and is eligible for call allocation.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Shift shows 'Active' from 2 days ago
 *   -> Cause: User forgot to click 'End Shift / Log Out' at the end of their shift.
 *   -> What should you do: Click 'End Shift & Log Out' in the bottom left sidebar, or let the automatic end-of-day cleanup run.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { Clock, ShieldCheck, Download, RefreshCw, UserCheck, Smartphone, Laptop, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function AttendanceLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const user = useAuthStore((state) => state.user);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.get('/auth/login-logs?limit=50');
      setLogs(res.data);
    } catch (err) {
      toast.error('Failed to load attendance logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleExportCSV = () => {
    if (!logs.length) return;
    const headers = ['User', 'Role', 'Login Time', 'Logout Time', 'Duration (Min)', 'Status', 'IP Address', 'Device'];
    const rows = logs.map((l) => [
      l.user_name || 'N/A',
      l.role_name || 'N/A',
      l.login_at ? format(new Date(l.login_at), 'yyyy-MM-dd HH:mm:ss') : '',
      l.logout_at ? format(new Date(l.logout_at), 'yyyy-MM-dd HH:mm:ss') : 'Active Session',
      l.duration_seconds ? Math.round(l.duration_seconds / 60) : 'Ongoing',
      l.status,
      l.ip_address || '',
      l.device_info || '',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Attendance_Logs_${format(new Date(), 'yyyy-MM-dd')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Top Bar Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center space-x-2">
            <Clock className="h-6 w-6 text-accent" />
            <span>Attendance & Shift Logs</span>
          </h1>
          <p className="text-xs text-foreground-muted mt-0.5">
            Audit records of staff login sessions, active shifts, IP addresses, and shift duration.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-border bg-background-surface px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-background-hover transition-colors shadow-subtle"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportCSV}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-hover transition-colors shadow-subtle"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Current Active Shift Banner */}
      {user?.active_shift_login && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50/80 p-4 text-emerald-950 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300 shadow-subtle flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="h-3 w-3 rounded-full bg-emerald-500 animate-ping" />
            <div>
              <div className="text-xs font-bold uppercase tracking-wider">Active Shift In Progress</div>
              <div className="text-sm font-semibold">
                Checked in at {format(new Date(user.active_shift_login), 'hh:mm a · dd MMM yyyy')}
              </div>
            </div>
          </div>
          <div className="inline-flex items-center space-x-2 rounded-lg bg-emerald-600/10 px-3 py-1 text-xs font-semibold">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Logged in as {user.full_name} ({user.role_name})</span>
          </div>
        </div>
      )}

      {/* Attendance Logs Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-background-surface shadow-subtle">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-background-base text-foreground-muted font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Login Time (Shift Start)</th>
                <th className="py-3 px-4">Logout Time (Shift End)</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">IP / Device</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-foreground-muted">
                    <RefreshCw className="mx-auto h-6 w-6 animate-spin text-accent mb-2" />
                    <span>Loading attendance logs...</span>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-foreground-muted">
                    No login logs recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const durationMin = log.duration_seconds ? Math.round(log.duration_seconds / 60) : null;
                  const isOngoing = !log.logout_at;

                  return (
                    <tr key={log.id} className="hover:bg-background-hover/50 transition-colors">
                      <td className="py-3 px-4 font-semibold text-foreground">
                        {log.user_name || 'System User'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="rounded-md bg-accent-subtle px-2 py-0.5 text-[10px] font-semibold text-accent dark:bg-slate-800 dark:text-sky-300">
                          {log.role_name || 'CRE'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-foreground font-medium">
                        {log.login_at ? format(new Date(log.login_at), 'dd MMM yyyy, hh:mm:ss a') : '-'}
                      </td>
                      <td className="py-3 px-4 text-foreground-muted">
                        {log.logout_at ? (
                          format(new Date(log.logout_at), 'dd MMM yyyy, hh:mm:ss a')
                        ) : (
                          <span className="inline-flex items-center space-x-1 font-semibold text-emerald-600 dark:text-emerald-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span>Active Now</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-medium text-foreground">
                        {isOngoing ? (
                          <span className="text-foreground-subtle italic">In Progress</span>
                        ) : (
                          <span>{durationMin} mins</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-foreground-muted">
                        <div className="font-mono text-[11px]">{log.ip_address || 'Local Host'}</div>
                        <div className="text-[10px] text-foreground-subtle">{log.device_info || 'Web Browser'}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            isOngoing
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                              : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

