/**
 * ============================================================================
 * FILE PURPOSE: Active Users & System Audit Logs Dashboard.
 * Replaces attendance feature with real-time app usage tracking and audit logs:
 * 1. Who is using the app right now (Active online users & sessions).
 * 2. Login & session activity history.
 * 3. Chronological system audit trail.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  Users,
  ShieldCheck,
  Download,
  RefreshCw,
  UserCheck,
  Smartphone,
  Laptop,
  CheckCircle2,
  Clock,
  Activity,
  FileText,
  Search,
  Filter,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function UserActivityPage() {
  const [activeTab, setActiveTab] = useState('active_users'); // 'active_users' | 'sessions' | 'audit_logs'
  const [activeUsers, setActiveUsers] = useState([]);
  const [sessionLogs, setSessionLogs] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const currentUser = useAuthStore((state) => state.user);

  useEffect(() => {
    fetchAllActivity();
  }, []);

  const fetchAllActivity = async () => {
    setLoading(true);
    try {
      const [activeRes, sessionRes, auditRes] = await Promise.all([
        api.get('/auth/active-users'),
        api.get('/auth/login-logs?limit=50'),
        api.get('/admin/audit-logs?limit=50'),
      ]);
      setActiveUsers(activeRes.data || []);
      setSessionLogs(sessionRes.data || []);
      setAuditLogs(auditRes.data || []);
    } catch (err) {
      console.error('Failed to load user activity & audit logs:', err);
      toast.error('Failed to load activity logs');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (activeTab === 'audit_logs') {
      if (!auditLogs.length) return;
      const headers = ['Action', 'Entity Type', 'Entity ID', 'User', 'Reason', 'Timestamp'];
      const rows = auditLogs.map((a) => [
        a.action || 'N/A',
        a.entity_type || 'N/A',
        a.entity_id || 'N/A',
        a.user_name || 'System',
        `"${(a.reason || '').replace(/"/g, '""')}"`,
        a.created_at ? format(new Date(a.created_at), 'yyyy-MM-dd HH:mm:ss') : '',
      ]);
      const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
      downloadCSV(csvContent, `Audit_Logs_${format(new Date(), 'yyyy-MM-dd')}.csv`);
    } else {
      if (!sessionLogs.length) return;
      const headers = ['User', 'Role', 'Login Time', 'Logout Time', 'Duration (Min)', 'Status', 'IP Address', 'Device'];
      const rows = sessionLogs.map((l) => [
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
      downloadCSV(csvContent, `App_User_Sessions_${format(new Date(), 'yyyy-MM-dd')}.csv`);
    }
  };

  const downloadCSV = (content, filename) => {
    const encodedUri = encodeURI(content);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filters
  const filteredActiveUsers = activeUsers.filter(
    (u) =>
      u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.role_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredSessionLogs = sessionLogs.filter(
    (l) =>
      l.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.role_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.ip_address?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredAuditLogs = auditLogs.filter(
    (a) =>
      a.action?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.entity_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.reason?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            <span>App Usage & Audit Logs</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time tracking of active staff using the app, session records, and system audit trail.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={fetchAllActivity}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportCSV}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 transition shadow-xs"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* 2. Quick Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div
          onClick={() => setActiveTab('active_users')}
          className={`cursor-pointer rounded-xl border p-4 shadow-xs transition ${
            activeTab === 'active_users'
              ? 'border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20 ring-2 ring-emerald-500/30'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Users Online Now
            </span>
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {activeUsers.length}
            </span>
            <span className="text-xs text-slate-500">active in dealership</span>
          </div>
        </div>

        <div
          onClick={() => setActiveTab('sessions')}
          className={`cursor-pointer rounded-xl border p-4 shadow-xs transition ${
            activeTab === 'sessions'
              ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20 ring-2 ring-blue-500/30'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              App User Sessions
            </span>
            <Activity className="h-4 w-4 text-blue-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-blue-600 dark:text-blue-400">
              {sessionLogs.length}
            </span>
            <span className="text-xs text-slate-500">recent sessions logged</span>
          </div>
        </div>

        <div
          onClick={() => setActiveTab('audit_logs')}
          className={`cursor-pointer rounded-xl border p-4 shadow-xs transition ${
            activeTab === 'audit_logs'
              ? 'border-purple-500 bg-purple-50/40 dark:bg-purple-950/20 ring-2 ring-purple-500/30'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Audit Trail Events
            </span>
            <ShieldCheck className="h-4 w-4 text-purple-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-purple-600 dark:text-purple-400">
              {auditLogs.length}
            </span>
            <span className="text-xs text-slate-500">actions audited</span>
          </div>
        </div>
      </div>

      {/* 3. Tab Switcher & Search Bar */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-3 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setActiveTab('active_users')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'active_users'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Who is using the app ({activeUsers.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sessions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'sessions'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            User Login Sessions ({sessionLogs.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('audit_logs')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'audit_logs'
                ? 'bg-purple-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            System Audit Trail ({auditLogs.length})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search by user, role, action..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
          />
        </div>
      </div>

      {/* 4. Tab Content */}

      {/* TAB 1: WHO IS USING THE APP (ACTIVE USERS) */}
      {activeTab === 'active_users' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {loading ? (
              <div className="col-span-full py-16 text-center text-xs text-slate-400">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-blue-500" />
                <span>Checking active user sessions...</span>
              </div>
            ) : filteredActiveUsers.length === 0 ? (
              <div className="col-span-full py-16 text-center text-xs text-slate-400">
                <Users className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                <p className="font-semibold text-slate-600 dark:text-slate-300">No active users match filters</p>
              </div>
            ) : (
              filteredActiveUsers.map((u) => (
                <div
                  key={u.user_id}
                  className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs relative overflow-hidden"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm">
                        {u.full_name ? u.full_name.slice(0, 2).toUpperCase() : 'US'}
                      </div>
                      <div>
                        <div className="font-bold text-slate-900 dark:text-white text-xs flex items-center gap-1.5">
                          <span>{u.full_name}</span>
                          {u.is_current_user && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300 font-semibold">
                              You
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">{u.email}</div>
                      </div>
                    </div>

                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span>Online Now</span>
                    </span>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Role:</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">{u.role_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Logged In:</span>
                      <span className="font-mono text-slate-700 dark:text-slate-300">
                        {u.login_at ? format(new Date(u.login_at), 'hh:mm a') : 'Now'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Active For:</span>
                      <span className="font-mono text-slate-700 dark:text-slate-300">
                        {u.duration_minutes ? `${u.duration_minutes} min` : 'Just started'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">IP / Device:</span>
                      <span className="font-mono text-slate-500 truncate block">
                        {u.ip_address || '127.0.0.1'}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: USER LOGIN SESSIONS */}
      {activeTab === 'sessions' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Login Time</th>
                  <th className="py-3 px-4">Logout Time</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">IP Address</th>
                  <th className="py-3 px-4">Device</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-blue-500" />
                      <span>Loading user sessions...</span>
                    </td>
                  </tr>
                ) : filteredSessionLogs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400">
                      No user session logs match filters
                    </td>
                  </tr>
                ) : (
                  filteredSessionLogs.map((l) => (
                    <tr key={l.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">
                        {l.user_name || 'Staff Member'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {l.role_name || 'USER'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        {l.login_at ? format(new Date(l.login_at), 'dd MMM yyyy, hh:mm a') : '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        {l.logout_at ? (
                          format(new Date(l.logout_at), 'dd MMM yyyy, hh:mm a')
                        ) : (
                          <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span>Active Now</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {l.duration_seconds
                          ? `${Math.round(l.duration_seconds / 60)} min`
                          : l.logout_at
                          ? '< 1 min'
                          : 'Ongoing'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            !l.logout_at || l.status === 'SUCCESS' || l.status === 'ACTIVE'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {!l.logout_at ? 'Active' : 'Completed'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500">{l.ip_address || '—'}</td>
                      <td className="py-3 px-4 text-slate-500 truncate max-w-xs">{l.device_info || 'Browser'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SYSTEM AUDIT LOGS */}
      {activeTab === 'audit_logs' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Performed By</th>
                  <th className="py-3 px-4">Reason / Notes</th>
                  <th className="py-3 px-4">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-purple-500" />
                      <span>Loading audit logs...</span>
                    </td>
                  </tr>
                ) : filteredAuditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      <ShieldCheck className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                      <p className="font-semibold text-slate-600 dark:text-slate-300">No audit records found</p>
                      <p className="text-[11px] text-slate-400 mt-1">Actions such as supervisor edits and config changes will appear here.</p>
                    </td>
                  </tr>
                ) : (
                  filteredAuditLogs.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-purple-600 dark:text-purple-400">
                        {a.action}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-slate-900 dark:text-white">{a.entity_type}</span>
                        {a.entity_id && (
                          <div className="text-[10px] font-mono text-slate-400">{String(a.entity_id).slice(0, 8)}...</div>
                        )}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">
                        {a.user_name || 'System / Admin'}
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400 max-w-sm">
                        {a.reason || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500">
                        {a.created_at ? format(new Date(a.created_at), 'dd MMM yyyy, hh:mm a') : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

