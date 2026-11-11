/**
 * ============================================================================
 * FILE PURPOSE: Main PSF Calling Workspace & Line Items Spreadsheet.
 * The primary operational dashboard for dealership customer follow-up calls.
 * Renders the complete Line Items Spreadsheet Table matching manufacturer DMS format,
 * enforces CRE role scoping, provides search/filters, and launches the Call Console dialer.
 * 
 * KEY RESPONSIBILITIES:
 * - Displays top KPI cards (Due Calls Today, Contacted, Connect Rate %, Open Complaints).
 * - Renders full Line Items table: Job Card No, Date, Customer Name (Call/WhatsApp), Branch, Brand Logo, VIN, Reg No, Model, Service Type, Status, VOC, Followed By (CRE), Service Advisor, Technician.
 * - Enforces CRE role scoping: CRE callers only see their assigned line items.
 * - Allows Admins to filter by Branch, Queue Type, Status, and Assigned CRE.
 * - Provides Bulk Reassignment bar allowing Admins to reassign selected line items.
 * - Opens the CallConsoleModal dialer when a row or 'Call' button is clicked.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Infinite spinner saying 'Loading line items...'
 *   -> Cause: Backend API server was reloading or timed out.
 *   -> What should you do: Refresh the browser page (`F5`). If issue persists, check `docker logs --tail 20 psf_api`.
 * - Error: CRE user sees 'No line items found'
 *   -> Cause: No calls have been allocated to this specific CRE yet.
 *   -> What should you do: Ask the CRE Admin to import a DMS file or use 'Allocate Now' in Shift Attendance.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  PhoneCall,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Filter,
  Search,
  RefreshCw,
  Users,
  Building2,
  Calendar,
  Phone,
  MessageSquare,
  Sparkles,
  ChevronRight,
  TrendingUp,
  UserCheck,
  ShieldAlert,
  Play,
  History,
  X,
  ExternalLink,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import CallConsoleModal from '../../components/calling/CallConsoleModal';
import CallAttemptHistoryModal from '../../components/calling/CallAttemptHistoryModal';
import PresentCresPanel from '../../components/allocation/PresentCresPanel';

export default function PsfDashboardPage() {
  const navigate = useNavigate();
  const { user, can } = useAuthStore();
  const isSuperAdmin = user?.is_super_admin || user?.role_name === 'SUPER_ADMIN' || user?.level === 'L1';
  const isCreAdmin = user?.role_name === 'CRE_ADMIN' || user?.role_name === 'DEALER_ADMIN';
  const canAllocate = isSuperAdmin || isCreAdmin || can('call.allocate');

  const [showPresencePanel, setShowPresencePanel] = useState(false);
  const [statsLoading, setStatsLoading] = useState(true);
  const [queuesLoading, setQueuesLoading] = useState(true);

  // High-level dashboard stats
  const [stats, setStats] = useState(null);

  // Queue table state
  const [queues, setQueues] = useState([]);
  const [totalQueues, setTotalQueues] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);

  // Masters
  const [brands, setBrands] = useState([]);
  const [branches, setBranches] = useState([]);
  const [creUsers, setCreUsers] = useState([]);

  // Filters
  const [selectedBrand, setSelectedBrand] = useState('ALL');
  const [selectedBranch, setSelectedBranch] = useState('ALL');
  const [selectedQueueType, setSelectedQueueType] = useState('PSF');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedCre, setSelectedCre] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Multi-select & Bulk Allocation
  const [selectedQueueIds, setSelectedQueueIds] = useState([]);
  const [bulkTargetUserId, setBulkTargetUserId] = useState('');
  const [bulkAssigning, setBulkAssigning] = useState(false);

  // Active Call Console Modal state
  const [activeConsoleQueueId, setActiveConsoleQueueId] = useState(null);
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [historyModalData, setHistoryModalData] = useState(null);

  useEffect(() => {
    fetchMasters();
  }, []);

  useEffect(() => {
    fetchDashboardStats();
    fetchQueues();
  }, [selectedBrand, selectedBranch, selectedQueueType, selectedStatus, selectedCre, page, pageSize]);

  const fetchMasters = async () => {
    try {
      const [brandsRes, branchesRes, usersRes] = await Promise.all([
        api.get('/masters/brands'),
        api.get('/masters/branches'),
        api.get('/users?limit=100'),
      ]);
      setBrands(brandsRes.data || []);
      setBranches(branchesRes.data || []);
      // Filter CRE / staff callers
      setCreUsers(usersRes.data.items || []);
    } catch (err) {
      console.error('Failed to load masters:', err);
    }
  };

  const fetchDashboardStats = async () => {
    try {
      setStatsLoading(true);
      const params = {};
      if (selectedBrand !== 'ALL') params.brand_id = selectedBrand;
      if (selectedBranch !== 'ALL') params.branch_id = selectedBranch;
      if (selectedCre !== 'ALL') params.cre_id = selectedCre;

      const res = await api.get('/psf/dashboard', { params });
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchQueues = async () => {
    try {
      setQueuesLoading(true);
      const params = {
        queue_type: selectedQueueType,
        status: selectedStatus,
        skip: page * pageSize,
        limit: pageSize,
      };
      if (selectedBrand !== 'ALL') params.brand_id = selectedBrand;
      if (selectedBranch !== 'ALL') params.branch_id = selectedBranch;
      if (selectedCre !== 'ALL') params.assigned_to_id = selectedCre;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const res = await api.get('/psf/queues', { params });
      setQueues(res.data.items || []);
      setTotalQueues(res.data.total || 0);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load calling queue records');
    } finally {
      setQueuesLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    fetchQueues();
  };

  const toggleSelectAll = () => {
    if (selectedQueueIds.length === queues.length) {
      setSelectedQueueIds([]);
    } else {
      setSelectedQueueIds(queues.map((q) => q.id));
    }
  };

  const toggleSelectQueue = (id) => {
    if (selectedQueueIds.includes(id)) {
      setSelectedQueueIds(selectedQueueIds.filter((item) => item !== id));
    } else {
      setSelectedQueueIds([...selectedQueueIds, id]);
    }
  };

  const handleBulkAssign = async () => {
    if (!bulkTargetUserId) {
      toast.error('Please select a CRE to assign calls to');
      return;
    }
    try {
      setBulkAssigning(true);
      await api.post('/psf/queues/bulk-assign', {
        queue_ids: selectedQueueIds,
        assigned_to_id: bulkTargetUserId,
      });
      toast.success(`Assigned ${selectedQueueIds.length} calls successfully`);
      setSelectedQueueIds([]);
      setBulkTargetUserId('');
      fetchQueues();
      fetchDashboardStats();
    } catch (err) {
      toast.error('Failed to bulk assign calls');
    } finally {
      setBulkAssigning(false);
    }
  };

  const handleOpenConsole = (queueId) => {
    setActiveConsoleQueueId(queueId);
    setIsConsoleOpen(true);
  };

  const handleQueueUpdated = () => {
    fetchQueues();
    fetchDashboardStats();
  };

  const formatDisplayDate = (d) => {
    if (!d) return '—';
    try {
      const parts = String(d).split('T')[0].split('-');
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return d;
    } catch {
      return d;
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '—';
    try {
      const dt = new Date(ts);
      if (isNaN(dt.getTime())) return ts;
      return dt.toLocaleString('en-IN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. TOP HEADER & ATTENDANCE ACTION */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <PhoneCall className="h-5 w-5 text-blue-600" />
            <span>PSF Follow-up Calling</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {canAllocate ? (
              <span>Dealership Post-Service Customer Follow-up & Survey Records (All Line Items)</span>
            ) : (
              <span>My Assigned Customer Calling Queue • {user?.full_name || 'CRE'}</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canAllocate && (
            <button
              type="button"
              onClick={() => setShowPresencePanel(!showPresencePanel)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm ${
                showPresencePanel
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Shift Attendance & CRE Pool</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              fetchDashboardStats();
              fetchQueues();
            }}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
            title="Refresh Data"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Slide-over / Collapsible CRE Presence & Attendance Panel (For Admins) */}
      {showPresencePanel && canAllocate && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-blue-200 dark:border-blue-900/50 p-4 shadow-sm relative">
          <button
            type="button"
            onClick={() => setShowPresencePanel(false)}
            className="absolute top-3 right-3 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400"
          >
            <X className="h-4 w-4" />
          </button>
          <PresentCresPanel
            onAttendanceChanged={() => {
              fetchDashboardStats();
              fetchQueues();
            }}
          />
        </div>
      )}

      {/* 2. COMPACT KPI SNAPSHOT (4 Minimal Cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Due Calls Today</div>
            <div className="text-xl font-black text-slate-900 dark:text-white mt-0.5">
              {stats?.total_pending ?? 0}
            </div>
          </div>
          <div className="h-9 w-9 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 flex items-center justify-center">
            <Clock className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Reached / Contacted</div>
            <div className="text-xl font-black text-emerald-600 dark:text-emerald-400 mt-0.5">
              {stats?.total_contacted ?? 0}
            </div>
          </div>
          <div className="h-9 w-9 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Connect Rate</div>
            <div className="text-xl font-black text-blue-600 dark:text-blue-400 mt-0.5">
              {stats?.connect_rate_pct ?? 0}%
            </div>
          </div>
          <div className="h-9 w-9 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 flex items-center justify-center">
            <TrendingUp className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Open Complaints</div>
            <div className="text-xl font-black text-amber-600 dark:text-amber-400 mt-0.5">
              {stats?.open_complaints_count ?? 0}
            </div>
          </div>
          <div className="h-9 w-9 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 flex items-center justify-center">
            <AlertTriangle className="h-4 w-4" />
          </div>
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
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => navigate('/tnps')}
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold flex items-center gap-1 shadow-xs transition"
              >
                <span>Open Dedicated TNPS Dashboard</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedQueueType('TNPS');
                  setPage(0);
                }}
                className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:underline flex items-center gap-1"
              >
                <span>Filter Table Below</span>
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {stats.tnps_calls_by_branch.map((b) => (
              <div
                key={b.branch_id}
                onClick={() => {
                  setSelectedBranch(b.branch_id);
                  setSelectedQueueType('TNPS');
                  setPage(0);
                }}
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

      {/* 3. MINIMAL FILTERS & SEARCH BAR */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-3 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-2.5 items-stretch md:items-center justify-between">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search Job Card, Customer, VIN, Reg No..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-4 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:bg-white dark:focus:bg-slate-900 transition"
            />
          </form>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Branch Filter */}
            <select
              value={selectedBranch}
              onChange={(e) => {
                setSelectedBranch(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-white"
            >
              <option value="ALL">All Branches</option>
              {branches.map((br) => (
                <option key={br.id} value={br.id}>
                  {br.name}
                </option>
              ))}
            </select>

            {/* Queue Type Filter */}
            <select
              value={selectedQueueType}
              onChange={(e) => {
                setSelectedQueueType(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400"
            >
              <option value="PSF">Queue: PSF</option>
              <option value="HAPPINESS">Queue: Happiness</option>
              <option value="TNPS">Queue: TNPS</option>
              <option value="ALL">Queue: All</option>
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-white font-medium"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">All Active Calls (Pending / Retry / Callback)</option>
              <option value="PENDING">Pending (Untouched)</option>
              <option value="CALLBACK_REQUESTED">Callback Requested</option>
              <option value="NOT_CONTACTED">Not Contacted (Retry)</option>
              <option value="CONTACTED">Contacted (Completed)</option>
              <option value="COMPLAINT_REGISTERED">Complaint Registered</option>
            </select>

            {/* Assigned CRE Filter (Visible only to Admins) */}
            {canAllocate && (
              <select
                value={selectedCre}
                onChange={(e) => {
                  setSelectedCre(e.target.value);
                  setPage(0);
                }}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-white font-medium"
              >
                <option value="ALL">All Assigned CREs</option>
                {creUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    CRE: {u.full_name}
                  </option>
                ))}
              </select>
            )}

            {/* Page Size */}
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-xs text-slate-600 dark:text-slate-400 font-mono"
            >
              <option value="25">25 / page</option>
              <option value="50">50 / page</option>
              <option value="100">100 / page</option>
            </select>
          </div>
        </div>

        {/* BULK REASSIGNMENT BAR (For Admins) */}
        {selectedQueueIds.length > 0 && canAllocate && (
          <div className="flex items-center justify-between p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-xs">
            <span className="font-semibold text-blue-900 dark:text-blue-300">
              {selectedQueueIds.length} line items selected
            </span>

            <div className="flex items-center gap-2">
              <select
                value={bulkTargetUserId}
                onChange={(e) => setBulkTargetUserId(e.target.value)}
                className="rounded border border-blue-300 dark:border-blue-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs"
              >
                <option value="">-- Reassign To CRE --</option>
                {creUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                disabled={bulkAssigning}
                onClick={handleBulkAssign}
                className="px-3 py-1 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {bulkAssigning ? 'Reassigning...' : 'Apply Reassignment'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. LINE ITEMS SPREADSHEET TABLE (Exact Match to User Reference Images) */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/30">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
              Calling Line Items
            </span>
            <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              {totalQueues} items
            </span>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            Showing {queues.length > 0 ? page * pageSize + 1 : 0} - {Math.min((page + 1) * pageSize, totalQueues)} of {totalQueues}
          </div>
        </div>

        {queuesLoading ? (
          <div className="py-24 text-center text-xs text-slate-500">
            <RefreshCw className="h-5 w-5 animate-spin inline mr-2 text-blue-600" />
            Loading line items...
          </div>
        ) : queues.length === 0 ? (
          <div className="py-24 text-center text-xs text-slate-400">
            No line items found. Upload DMS data to distribute calling line items.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs border-collapse">
              <thead className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 whitespace-nowrap">
                <tr>
                  {canAllocate && (
                    <th className="py-2.5 px-2.5 w-8 text-center">
                      <input
                        type="checkbox"
                        checked={selectedQueueIds.length === queues.length && queues.length > 0}
                        onChange={toggleSelectAll}
                        className="rounded text-blue-600"
                      />
                    </th>
                  )}
                  <th className="py-2.5 px-3">Job Card No</th>
                  <th className="py-2.5 px-3">Job Card Date</th>
                  <th className="py-2.5 px-3">Customer Name</th>
                  <th className="py-2.5 px-3">Branch</th>
                  <th className="py-2.5 px-3">Brand Logo</th>
                  <th className="py-2.5 px-3">Vin No</th>
                  <th className="py-2.5 px-3">Reg No</th>
                  <th className="py-2.5 px-3">Model</th>
                  <th className="py-2.5 px-3">Service Type</th>
                  <th className="py-2.5 px-3">Call Status</th>
                  <th className="py-2.5 px-3">Case Status</th>
                  <th className="py-2.5 px-3">VOC</th>
                  <th className="py-2.5 px-3">Followed By</th>
                  <th className="py-2.5 px-3">Followup Timestamp</th>
                  <th className="py-2.5 px-3 text-center">Total Attempted</th>
                  <th className="py-2.5 px-3 text-center">Total Contacted</th>
                  <th className="py-2.5 px-3">Service Advisor</th>
                  <th className="py-2.5 px-3">Technician</th>
                  <th className="py-2.5 px-3 text-center sticky right-0 bg-slate-100 dark:bg-slate-800">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                {queues.map((q) => (
                  <tr
                    key={q.id}
                    onClick={() => handleOpenConsole(q.id)}
                    className="hover:bg-blue-50/50 dark:hover:bg-slate-800/60 transition cursor-pointer group"
                  >
                    {canAllocate && (
                      <td className="py-2.5 px-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedQueueIds.includes(q.id)}
                          onChange={() => toggleSelectQueue(q.id)}
                          className="rounded text-blue-600"
                        />
                      </td>
                    )}

                    {/* 1. Job Card No */}
                    <td className="py-2.5 px-3 font-mono font-semibold text-blue-600 dark:text-blue-400">
                      {q.job_card_no}
                    </td>

                    {/* 2. Job Card Date */}
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                      {formatDisplayDate(q.job_card_date)}
                    </td>

                    {/* 3. Customer Name & Direct Call/WhatsApp Links */}
                    <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate max-w-[140px] font-semibold">{q.customer_name}</span>
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

                    {/* 4. Branch */}
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                      {q.branch_name}
                    </td>

                    {/* 5. Brand Logo / Badge */}
                    <td className="py-2.5 px-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold text-white shadow-xs"
                        style={{ backgroundColor: q.brand_color || '#2563EB' }}
                      >
                        {q.brand_code || q.brand_name}
                      </span>
                    </td>

                    {/* 6. Vin No */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {q.vin_no || '—'}
                    </td>

                    {/* 7. Reg No */}
                    <td className="py-2.5 px-3 font-mono font-semibold text-slate-800 dark:text-slate-200">
                      {q.vehicle_reg_no}
                    </td>

                    {/* 8. Model */}
                    <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                      {q.vehicle_model}
                    </td>

                    {/* 9. Service Type */}
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                      {q.service_type || 'Paid Service'}
                    </td>

                    {/* 10. Call Status */}
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

                    {/* 11. Case Status */}
                    <td className="py-2.5 px-3">
                      {q.last_case_status ? (
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            q.last_case_status === 'Delight' || q.last_case_status === 'Satisfied'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
                              : q.last_case_status === 'Non-Delight' || q.last_case_status === 'Dissatisfied'
                              ? 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300'
                              : q.last_case_status === 'No Response'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                              : q.last_case_status === 'Follow-up Required' || q.last_case_status === 'Callback Requested'
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-950/50 dark:text-purple-300'
                              : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {q.last_case_status}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">—</span>
                      )}
                    </td>

                    {/* 12. VOC (Voice of Customer) */}
                    <td className="py-2.5 px-3 max-w-[180px] truncate text-[11px] text-slate-600 dark:text-slate-400" title={q.voc || ''}>
                      {q.voc || '—'}
                    </td>

                    {/* 13. Followed By (Assigned CRE) */}
                    <td className="py-2.5 px-3">
                      {q.assigned_to_name ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-slate-800 dark:text-slate-200">
                          <UserCheck className="h-3 w-3 text-blue-600 flex-shrink-0" />
                          <span className="truncate max-w-[120px]">{q.assigned_to_name}</span>
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px] italic">Unassigned</span>
                      )}
                    </td>

                    {/* 14. Followup Timestamp */}
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {formatTimestamp(q.followup_timestamp || q.last_attempt_at)}
                    </td>

                    {/* 15. Total Attempted */}
                    <td className="py-2.5 px-3 text-center font-mono font-semibold text-slate-700 dark:text-slate-300">
                      {q.attempts ?? 0}
                    </td>

                    {/* 16. Total Contacted */}
                    <td className="py-2.5 px-3 text-center font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {q.contacted_count ?? 0}
                    </td>

                    {/* 17. Service Advisor */}
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                      {q.service_advisor || '—'}
                    </td>

                    {/* 18. Technician */}
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                      {q.technician_name || '—'}
                    </td>

                    {/* 19. Action Button */}
                    <td className="py-2.5 px-3 text-center sticky right-0 bg-white dark:bg-slate-900 group-hover:bg-blue-50/50 dark:group-hover:bg-slate-800/60 shadow-xs" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => handleOpenConsole(q.id)}
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

        {/* PAGINATION CONTROLS */}
        {totalQueues > pageSize && (
          <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs bg-slate-50/50 dark:bg-slate-800/30">
            <span className="text-slate-500">
              Page {page + 1} of {Math.ceil(totalQueues / pageSize)}
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold disabled:opacity-40 hover:bg-slate-50 transition"
              >
                Previous
              </button>

              <button
                type="button"
                disabled={(page + 1) * pageSize >= totalQueues}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold disabled:opacity-40 hover:bg-slate-50 transition"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5. CALL CONSOLE MODAL */}
      {isConsoleOpen && activeConsoleQueueId && (
        <CallConsoleModal
          queueId={activeConsoleQueueId}
          isOpen={isConsoleOpen}
          onClose={() => {
            setIsConsoleOpen(false);
            setActiveConsoleQueueId(null);
          }}
          onQueueUpdated={handleQueueUpdated}
        />
      )}

      {/* 6. CALL ATTEMPT HISTORY MODAL */}
      {historyModalData && (
        <CallAttemptHistoryModal
          data={historyModalData}
          onClose={() => setHistoryModalData(null)}
        />
      )}
    </div>
  );
}
