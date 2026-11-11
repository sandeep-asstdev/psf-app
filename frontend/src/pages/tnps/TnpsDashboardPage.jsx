/**
 * ============================================================================
 * FILE PURPOSE: Dedicated Ather Energy TNPS Dashboard & Calling Workspace.
 * Comprehensive, standalone operational dashboard exclusively for Ather Energy's
 * Post-Service Follow-up (TNPS) programme.
 * 
 * KEY RESPONSIBILITIES:
 * - Surfaces Ather-scoped KPI metrics: Total Pending, Contacted, Connect Rate.
 * - Computes and renders real-time Net Promoter Score (TNPS) meter:
 *   Promoters (9-10), Passives (7-8), Detractors (0-6), and net score.
 * - Shows Ather workshop branch breakdown with quick one-click filtering.
 * - Hosts the dedicated calling queue table strictly for queue_type="TNPS".
 * - Seamlessly integrates CallConsoleModal (with Ather Questionnaire),
 *   CallAttemptHistoryModal, and PresentCresPanel.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Zap,
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
  ShieldAlert,
  Play,
  History,
  X,
  Gauge,
  Smile,
  Meh,
  Frown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { useLabel } from '../../hooks/useLabel';
import CallConsoleModal from '../../components/calling/CallConsoleModal';
import CallAttemptHistoryModal from '../../components/calling/CallAttemptHistoryModal';
import PresentCresPanel from '../../components/allocation/PresentCresPanel';

export default function TnpsDashboardPage() {
  const { user, can } = useAuthStore();
  const { t } = useLabel();
  const isSuperAdmin = user?.is_super_admin || user?.role_name === 'SUPER_ADMIN' || user?.level === 'L1';
  const isCreAdmin = user?.role_name === 'CRE_ADMIN' || user?.role_name === 'DEALER_ADMIN';
  const canAllocate = isSuperAdmin || isCreAdmin || can('call.allocate');

  const [showPresencePanel, setShowPresencePanel] = useState(false);
  const [statsLoading, setStatsLoading] = useState(true);
  const [queuesLoading, setQueuesLoading] = useState(true);

  // Dedicated TNPS stats
  const [stats, setStats] = useState(null);

  // Calling queue state
  const [queues, setQueues] = useState([]);
  const [totalQueues, setTotalQueues] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);

  // Masters
  const [atherBranches, setAtherBranches] = useState([]);
  const [creUsers, setCreUsers] = useState([]);

  // Filters
  const [selectedBranch, setSelectedBranch] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedCre, setSelectedCre] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Bulk reassignment
  const [selectedQueueIds, setSelectedQueueIds] = useState([]);
  const [bulkTargetUserId, setBulkTargetUserId] = useState('');
  const [bulkAssigning, setBulkAssigning] = useState(false);

  // Modals
  const [activeConsoleQueueId, setActiveConsoleQueueId] = useState(null);
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [historyModalData, setHistoryModalData] = useState(null);

  useEffect(() => {
    fetchMasters();
  }, []);

  useEffect(() => {
    fetchTnpsStats();
    fetchQueues();
  }, [selectedBranch, selectedStatus, selectedCre, page, pageSize]);

  const fetchMasters = async () => {
    try {
      const [branchesRes, usersRes, brandsRes] = await Promise.all([
        api.get('/masters/branches'),
        api.get('/users?limit=100'),
        api.get('/masters/brands'),
      ]);

      const brands = brandsRes.data || [];
      const atherBrand = brands.find(
        (b) =>
          b.enable_tnps ||
          b.code?.toUpperCase() === 'ATHER' ||
          b.code?.toUpperCase() === 'ATHER_ENERGY' ||
          b.name?.toLowerCase().includes('ather')
      );

      const allBranches = branchesRes.data || [];
      if (atherBrand) {
        setAtherBranches(allBranches.filter((br) => br.brand_id === atherBrand.id));
      } else {
        setAtherBranches(allBranches.filter((br) => br.name?.toLowerCase().includes('ather')));
      }

      setCreUsers(usersRes.data.items || []);
    } catch (err) {
      console.error('Failed to load masters:', err);
    }
  };

  const fetchTnpsStats = async () => {
    try {
      setStatsLoading(true);
      const params = {};
      if (selectedBranch !== 'ALL') params.branch_id = selectedBranch;
      if (selectedCre !== 'ALL') params.cre_id = selectedCre;

      const res = await api.get('/psf/dashboard/tnps', { params });
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch TNPS dashboard stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchQueues = async () => {
    try {
      setQueuesLoading(true);
      const params = {
        queue_type: 'TNPS',
        status: selectedStatus,
        skip: page * pageSize,
        limit: pageSize,
      };
      if (selectedBranch !== 'ALL') params.branch_id = selectedBranch;
      if (selectedCre !== 'ALL') params.assigned_to_id = selectedCre;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const res = await api.get('/psf/queues', { params });
      setQueues(res.data.items || []);
      setTotalQueues(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load TNPS calling queues:', err);
      toast.error('Failed to load TNPS calling queue records');
    } finally {
      setQueuesLoading(false);
    }
  };

  const handleLaunchConsole = (queueId) => {
    setActiveConsoleQueueId(queueId);
    setIsConsoleOpen(true);
  };

  const handleConsoleClose = () => {
    setIsConsoleOpen(false);
    setActiveConsoleQueueId(null);
    fetchTnpsStats();
    fetchQueues();
  };

  const handleBulkAssign = async () => {
    if (!bulkTargetUserId) {
      toast.error('Select a team member to assign');
      return;
    }
    if (selectedQueueIds.length === 0) {
      toast.error('Select at least one calling queue item');
      return;
    }
    try {
      setBulkAssigning(true);
      await api.post('/psf/queues/bulk-assign', {
        queue_ids: selectedQueueIds,
        assigned_to_id: bulkTargetUserId,
      });
      toast.success(`Successfully assigned ${selectedQueueIds.length} calls`);
      setSelectedQueueIds([]);
      setBulkTargetUserId('');
      fetchTnpsStats();
      fetchQueues();
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Bulk assignment failed');
    } finally {
      setBulkAssigning(false);
    }
  };

  const toggleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedQueueIds(queues.map((q) => q.id));
    } else {
      setSelectedQueueIds([]);
    }
  };

  const toggleSelectOne = (id) => {
    setSelectedQueueIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const totalPages = Math.ceil(totalQueues / pageSize) || 1;

  // NPS color styling helper
  const getNpsColor = (score) => {
    if (score === null || score === undefined) return 'text-slate-400';
    if (score >= 50) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 0) return 'text-amber-600 dark:text-amber-400';
    return 'text-rose-600 dark:text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* 1. HEADER BANNER */}
      <div className="bg-gradient-to-r from-teal-900 via-emerald-900 to-slate-900 rounded-2xl p-6 text-white shadow-lg border border-teal-800/40 relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-emerald-500/10 via-transparent to-transparent pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="p-2 bg-emerald-500/20 border border-emerald-400/30 rounded-xl text-emerald-400">
                <Zap className="h-6 w-6" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold tracking-tight text-white">
                    Ather Energy {t('TNPS', 'TNPS')} Dashboard
                  </h1>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-400/20 text-emerald-300 border border-emerald-400/30">
                    Ather PSF Programme
                  </span>
                </div>
                <p className="text-xs text-emerald-100/80 mt-0.5">
                  Transactional Net Promoter Score & Post-Service Follow-up Management for Ather EV Workshop Outlets
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {canAllocate && (
              <button
                type="button"
                onClick={() => setShowPresencePanel(!showPresencePanel)}
                className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  showPresencePanel
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : 'bg-white/10 text-white hover:bg-white/20 border border-white/20'
                }`}
              >
                <Users className="h-3.5 w-3.5" />
                <span>Shift Presence & Allocation</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                fetchTnpsStats();
                fetchQueues();
                toast.success('TNPS Dashboard refreshed');
              }}
              className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${statsLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Presence panel slider */}
        {showPresencePanel && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <PresentCresPanel
              onAllocated={() => {
                fetchTnpsStats();
                fetchQueues();
              }}
            />
          </div>
        )}
      </div>

      {/* 2. TOP METRIC KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Pending */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Pending TNPS Calls
            </span>
            <span className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
              <Clock className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
              {statsLoading ? '-' : stats?.total_pending ?? 0}
            </span>
            <span className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">Due for Contact</span>
          </div>
        </div>

        {/* Total Contacted */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Contacted Riders
            </span>
            <span className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
              {statsLoading ? '-' : stats?.total_contacted ?? 0}
            </span>
            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">Completed</span>
          </div>
        </div>

        {/* Connect Rate % */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Reach / Connect Rate
            </span>
            <span className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400">
              <TrendingUp className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
              {statsLoading ? '-' : `${stats?.connect_rate_pct ?? 0}%`}
            </span>
            <span className="text-[11px] text-slate-500 font-medium">Contact Efficiency</span>
          </div>
        </div>

        {/* Net Promoter Score (TNPS Meter) */}
        <div className="bg-gradient-to-br from-white to-emerald-50/40 dark:from-slate-900 dark:to-emerald-950/20 rounded-xl border border-emerald-200/80 dark:border-emerald-800/80 p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase text-emerald-900 dark:text-emerald-200 tracking-wider flex items-center gap-1">
              <Gauge className="h-3.5 w-3.5 text-emerald-600" />
              <span>Ather Net Score</span>
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200">
              TNPS
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${getNpsColor(stats?.nps_score)}`}>
              {statsLoading
                ? '-'
                : stats?.nps_score !== null && stats?.nps_score !== undefined
                ? `${stats.nps_score > 0 ? '+' : ''}${stats.nps_score}`
                : 'N/A'}
            </span>
            <span className="text-[10px] text-slate-500">
              {stats?.nps_respondents ? `(${stats.nps_respondents} ratings)` : 'No ratings yet'}
            </span>
          </div>
          <div className="mt-2 pt-1 border-t border-emerald-100 dark:border-emerald-900/40 flex items-center justify-between text-[10px]">
            <span className="text-emerald-700 dark:text-emerald-300 flex items-center gap-0.5">
              <Smile className="h-3 w-3 inline text-emerald-500" /> {stats?.promoters_count || 0} Promoters
            </span>
            <span className="text-amber-700 dark:text-amber-300 flex items-center gap-0.5">
              <Meh className="h-3 w-3 inline text-amber-500" /> {stats?.passives_count || 0} Passives
            </span>
            <span className="text-rose-700 dark:text-rose-300 flex items-center gap-0.5">
              <Frown className="h-3 w-3 inline text-rose-500" /> {stats?.detractors_count || 0} Detractors
            </span>
          </div>
        </div>

        {/* Open Escalations / Complaints */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              {t('COMPLAINT', 'Escalations')}
            </span>
            <span className="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400">
              <ShieldAlert className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-rose-600 dark:text-rose-400">
              {statsLoading ? '-' : stats?.open_complaints_count ?? 0}
            </span>
            <span className="text-[11px] text-rose-600 dark:text-rose-400 font-medium">Ather Concerns</span>
          </div>
        </div>
      </div>

      {/* 3. ATHER WORKSHOP BRANCHES BREAKDOWN WIDGET */}
      {stats?.tnps_calls_by_branch?.length > 0 && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/20 dark:to-teal-950/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-200/60 dark:border-emerald-800/60 mb-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-200">
                Ather Energy Workshop Outlets
              </h3>
            </div>
            {selectedBranch !== 'ALL' && (
              <button
                type="button"
                onClick={() => {
                  setSelectedBranch('ALL');
                  setPage(0);
                }}
                className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:underline flex items-center gap-1"
              >
                <span>Clear Branch Filter (Show All)</span>
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {stats.tnps_calls_by_branch.map((b) => {
              const isSelected = selectedBranch === b.branch_id;
              return (
                <div
                  key={b.branch_id}
                  onClick={() => {
                    setSelectedBranch(isSelected ? 'ALL' : b.branch_id);
                    setPage(0);
                  }}
                  className={`cursor-pointer p-3 rounded-lg border transition shadow-xs ${
                    isSelected
                      ? 'bg-emerald-600 text-white border-emerald-700 ring-2 ring-emerald-500'
                      : 'bg-white dark:bg-slate-900 border-emerald-100 dark:border-emerald-900/50 hover:border-emerald-500'
                  }`}
                >
                  <div className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-900 dark:text-white'}`}>
                    {b.branch_name}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px]">
                    <span className={isSelected ? 'text-emerald-100' : 'text-slate-500'}>Pending:</span>
                    <span className={`font-bold font-mono ${isSelected ? 'text-white' : 'text-blue-600 dark:text-blue-400'}`}>
                      {b.pending_count}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px]">
                    <span className={isSelected ? 'text-emerald-100' : 'text-slate-500'}>Contacted:</span>
                    <span className={`font-bold font-mono ${isSelected ? 'text-emerald-200' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {b.contacted_count}
                    </span>
                  </div>
                  <div className={`mt-1 pt-1.5 border-t flex items-center justify-between text-[11px] ${
                    isSelected ? 'border-emerald-500 text-emerald-100' : 'border-slate-100 dark:border-slate-800 text-slate-400'
                  }`}>
                    <span>Total Calls:</span>
                    <span className={`font-semibold font-mono ${isSelected ? 'text-white' : 'text-slate-700 dark:text-slate-300'}`}>
                      {b.total_calls}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. FILTERS & SEARCH BAR */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-3 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {/* Workshop Branch */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Workshop Branch</label>
            <select
              value={selectedBranch}
              onChange={(e) => {
                setSelectedBranch(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2.5 py-1.5"
            >
              <option value="ALL">All Ather Branches</option>
              {atherBranches.map((br) => (
                <option key={br.id} value={br.id}>
                  {br.name}
                </option>
              ))}
            </select>
          </div>

          {/* Call Status */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Calling Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2.5 py-1.5"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending (Not Called)</option>
              <option value="CONTACTED">Contacted / Completed</option>
              <option value="NOT_CONTACTED">Not Contacted (Unreachable)</option>
              <option value="CALLBACK_REQUESTED">Callback Requested</option>
              <option value="IN_PROGRESS">In Progress</option>
            </select>
          </div>

          {/* Assigned CRE */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Assigned {t('CRE', 'CRE')}</label>
            <select
              value={selectedCre}
              onChange={(e) => {
                setSelectedCre(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2.5 py-1.5"
            >
              <option value="ALL">All Callers</option>
              {creUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </select>
          </div>

          {/* Live Search */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Search Calling Records</label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Reg No, Customer, Job Card..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setPage(0);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') fetchQueues();
                }}
                className="w-full pl-8 pr-2.5 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
              />
            </div>
          </div>
        </div>

        {/* Bulk Reassign Bar */}
        {canAllocate && selectedQueueIds.length > 0 && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs bg-slate-50 dark:bg-slate-800/40 p-2 rounded-lg">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              {selectedQueueIds.length} calls selected
            </span>
            <div className="flex items-center gap-2">
              <select
                value={bulkTargetUserId}
                onChange={(e) => setBulkTargetUserId(e.target.value)}
                className="text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1"
              >
                <option value="">Reassign To...</option>
                {creUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleBulkAssign}
                disabled={bulkAssigning}
                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50"
              >
                {bulkAssigning ? 'Reassigning...' : 'Confirm Reassign'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5. CALLING QUEUE TABLE */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">
              Ather TNPS Calling Queue
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
              {totalQueues} total calls
            </span>
          </div>

          <div className="text-xs text-slate-500">
            Page {page + 1} of {totalPages}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                {canAllocate && (
                  <th className="p-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedQueueIds.length === queues.length && queues.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded text-emerald-600"
                    />
                  </th>
                )}
                <th className="p-3">Job Card</th>
                <th className="p-3">Customer & Phone</th>
                <th className="p-3">Vehicle Details</th>
                <th className="p-3">Workshop Branch</th>
                <th className="p-3">Status</th>
                <th className="p-3">Assigned Caller</th>
                <th className="p-3">Attempts</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {queuesLoading ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-emerald-500" />
                    <span>Loading Ather TNPS queue records...</span>
                  </td>
                </tr>
              ) : queues.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">
                    <Zap className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    <p className="font-semibold text-slate-600 dark:text-slate-300">
                      No Ather TNPS calls match current filters
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Import an Ather DMS batch or adjust the filter criteria above.
                    </p>
                  </td>
                </tr>
              ) : (
                queues.map((q) => {
                  const isSelected = selectedQueueIds.includes(q.id);
                  const isPending = q.status === 'PENDING';
                  return (
                    <tr
                      key={q.id}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition ${
                        isSelected ? 'bg-emerald-50/40 dark:bg-emerald-950/20' : ''
                      }`}
                    >
                      {canAllocate && (
                        <td className="p-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectOne(q.id)}
                            className="rounded text-emerald-600"
                          />
                        </td>
                      )}
                      <td className="p-3 font-mono font-semibold text-slate-900 dark:text-white">
                        {q.job_card_no}
                        <div className="text-[10px] text-slate-400 font-sans">{q.job_card_date}</div>
                      </td>
                      <td className="p-3">
                        <div className="font-medium text-slate-900 dark:text-white">{q.customer_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {q.customer_phone_masked || q.customer_phone_raw}
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                          {q.vehicle_model || 'Ather 450X'}
                        </div>
                        <div className="text-[11px] font-mono text-slate-400">{q.vehicle_reg_no}</div>
                      </td>
                      <td className="p-3 text-slate-700 dark:text-slate-300">
                        {q.branch_name}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            q.status === 'PENDING'
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-200'
                              : q.status === 'CONTACTED'
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-200'
                              : q.status === 'CALLBACK_REQUESTED'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-200'
                              : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {q.status}
                        </span>
                      </td>
                      <td className="p-3 text-slate-600 dark:text-slate-300">
                        {q.assigned_to_name || (
                          <span className="text-amber-600 dark:text-amber-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-center">
                        <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[11px]">
                          {q.attempts ?? 0}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleLaunchConsole(q.id)}
                            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-[11px] font-semibold flex items-center gap-1 transition shadow-xs"
                          >
                            <Phone className="h-3 w-3" />
                            <span>Call</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => setHistoryModalData(q.id)}
                            className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded transition"
                            title="Call Attempts History"
                          >
                            <History className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination bar */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing {queues.length} of {totalQueues} records
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="font-mono">
              {page + 1} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* 6. CALL CONSOLE MODAL (Includes Ather Questionnaire) */}
      {isConsoleOpen && activeConsoleQueueId && (
        <CallConsoleModal
          queueId={activeConsoleQueueId}
          onClose={handleConsoleClose}
        />
      )}

      {/* 7. CALL ATTEMPT HISTORY MODAL */}
      {historyModalData && (
        <CallAttemptHistoryModal
          queueId={historyModalData}
          onClose={() => setHistoryModalData(null)}
        />
      )}
    </div>
  );
}
