/**
 * ============================================================================
 * FILE PURPOSE: Customer Complaints, Escalations & SLA Management Page.
 * Tracks customer dissatisfaction issues generated from follow-up calls.
 * Enables dealership managers to assign tickets, track resolution deadlines, and log corrective actions.
 * 
 * KEY RESPONSIBILITIES:
 * - Lists customer complaints with status filters (OPEN, IN_PROGRESS, RESOLVED, CLOSED).
 * - Highlights SLA breached complaints with flashing warning badges.
 * - Allows managers to reassign complaints to Service Advisors or Service Managers.
 * - Provides action modal to record resolution remarks and customer compensation notes.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Resolution button is disabled or fails with HTTP 403
 *   -> Cause: Logged in user does not have `complaint.close` permission.
 *   -> What should you do: Only CRE Admin, Dealer Admin, or Super Admin can mark complaints RESOLVED / CLOSED.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Building2,
  ChevronRight,
  User,
  Phone,
  FileText,
  Calendar,
  History,
  Send,
  X,
  MessageSquare,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function ComplaintManagementPage() {
  const [loading, setLoading] = useState(true);
  const [complaintsError, setComplaintsError] = useState(null);
  const [complaints, setComplaints] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [slaBreachedFilter, setSlaBreachedFilter] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Masters
  const [branches, setBranches] = useState([]);
  const [users, setUsers] = useState([]);

  // Active Ticket Drawer / Modal
  const [selectedComplaintId, setSelectedComplaintId] = useState(null);
  const [activeComplaintDetail, setActiveComplaintDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Status Change Form State
  const [newStatus, setNewStatus] = useState('IN_PROGRESS');
  const [assigneeId, setAssigneeId] = useState('');
  const [statusRemarks, setStatusRemarks] = useState('');
  const [resolutionRemarks, setResolutionRemarks] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Reconfirmation Call Form State
  const [reconfCallStatus, setReconfCallStatus] = useState('Connected');
  const [reconfStatus, setReconfStatus] = useState('SATISFIED_CLOSED');
  const [reconfFeedback, setReconfFeedback] = useState('');
  const [submittingReconf, setSubmittingReconf] = useState(false);

  useEffect(() => {
    fetchMasters();
  }, []);

  useEffect(() => {
    fetchComplaints();
  }, [statusFilter, severityFilter, branchFilter, slaBreachedFilter]);

  const fetchMasters = async () => {
    try {
      const [branchesRes, usersRes] = await Promise.all([
        api.get('/masters/branches'),
        api.get('/users?limit=100'),
      ]);
      setBranches(branchesRes.data);
      setUsers(usersRes.data.items || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchComplaints = async () => {
    try {
      setLoading(true);
      setComplaintsError(null);
      const params = {
        limit: 50,
      };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (severityFilter !== 'ALL') params.severity = severityFilter;
      if (branchFilter !== 'ALL') params.branch_id = branchFilter;
      if (slaBreachedFilter) params.is_sla_breached = true;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const res = await api.get('/complaints', { params });
      setComplaints(res.data.items || []);
      setTotalCount(res.data.total || 0);
    } catch (err) {
      setComplaintsError(err.response?.data?.detail || 'Failed to load complaints');
      toast.error('Failed to load complaints');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchComplaints();
  };

  // Open Ticket Detail Drawer
  const handleOpenTicket = async (id) => {
    try {
      setSelectedComplaintId(id);
      setDetailLoading(true);
      const res = await api.get(`/complaints/${id}`);
      setActiveComplaintDetail(res.data);
      setNewStatus(res.data.status);
      setAssigneeId(res.data.assigned_to_id || '');
      setStatusRemarks('');
      setResolutionRemarks(res.data.resolution_remarks || '');
    } catch (err) {
      toast.error('Failed to load complaint details');
    } finally {
      setDetailLoading(false);
    }
  };

  // Submit Status Update
  const handleUpdateStatus = async (e) => {
    e.preventDefault();
    try {
      setUpdatingStatus(true);
      const res = await api.put(`/complaints/${selectedComplaintId}/status`, {
        status: newStatus,
        assigned_to_id: assigneeId || null,
        remarks: statusRemarks.trim() || null,
        resolution_remarks: newStatus === 'RESOLVED' ? resolutionRemarks.trim() : null,
      });

      toast.success(`Complaint status updated to ${newStatus}`);
      setActiveComplaintDetail(res.data);
      await fetchComplaints();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Submit Post-Resolution Reconfirmation Call
  const handleReconfirmationSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmittingReconf(true);
      const res = await api.post('/complaints/reconfirmations', {
        complaint_id: selectedComplaintId,
        call_status: reconfCallStatus,
        status: reconfStatus,
        customer_feedback: reconfFeedback.trim() || null,
        closure_verified: reconfStatus === 'SATISFIED_CLOSED',
      });

      if (reconfStatus === 'SATISFIED_CLOSED') {
        toast.success('Customer verified satisfaction! Complaint CLOSED permanently.', { icon: '🎉' });
      } else {
        toast.error('Customer dissatisfied. Complaint ticket REOPENED with priority SLA!', { icon: '🚨' });
      }

      const refreshed = await api.get(`/complaints/${selectedComplaintId}`);
      setActiveComplaintDetail(refreshed.data);
      await fetchComplaints();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit reconfirmation');
    } finally {
      setSubmittingReconf(false);
    }
  };

  // KPI Metrics Calculation
  const metrics = useMemo(() => {
    const total = complaints.length;
    const openCount = complaints.filter((c) => ['OPEN', 'ASSIGNED', 'IN_PROGRESS', 'REOPENED'].includes(c.status)).length;
    const resolvedCount = complaints.filter((c) => ['RESOLVED', 'RECONFIRMATION_PENDING'].includes(c.status)).length;
    const closedCount = complaints.filter((c) => c.status === 'CLOSED').length;
    const breachedCount = complaints.filter((c) => c.is_sla_breached).length;

    return { total, openCount, resolvedCount, closedCount, breachedCount };
  }, [complaints]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            Complaint Management & SLA Resolution Portal
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            End-to-end customer dissatisfaction lifecycle: Investigation, Resolution, Escalations & Post-Resolution Reconfirmations.
          </p>
        </div>

        <button
          onClick={fetchComplaints}
          className="p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition self-start md:self-auto"
          title="Refresh Data"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* 1. KPI COUNTER CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Tickets */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-1">
          <div className="text-xs font-medium text-slate-500">Active Complaints</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white">{totalCount}</div>
          <div className="text-[11px] text-slate-400">Total registered tickets</div>
        </div>

        {/* Open & In Progress */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-1">
          <div className="text-xs font-medium text-amber-600 dark:text-amber-400 flex items-center justify-between">
            <span>In Investigation</span>
            <Clock className="h-4 w-4" />
          </div>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{metrics.openCount}</div>
          <div className="text-[11px] text-slate-400">Under workshop review</div>
        </div>

        {/* Resolved / Reconfirmation Pending */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-1">
          <div className="text-xs font-medium text-blue-600 dark:text-blue-400 flex items-center justify-between">
            <span>Awaiting Reconfirmation</span>
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{metrics.resolvedCount}</div>
          <div className="text-[11px] text-slate-400">Resolution calling queued</div>
        </div>

        {/* Closed & Satisfied */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-1">
          <div className="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
            <span>Closed & Satisfied</span>
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{metrics.closedCount}</div>
          <div className="text-[11px] text-slate-400">Customer verified</div>
        </div>

        {/* SLA Breached */}
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 shadow-sm space-y-1 col-span-2 lg:col-span-1">
          <div className="text-xs font-bold text-red-600 dark:text-red-400 flex items-center justify-between">
            <span>SLA Breached</span>
            <ShieldAlert className="h-4 w-4 text-red-600" />
          </div>
          <div className="text-2xl font-extrabold text-red-600 dark:text-red-400">{metrics.breachedCount}</div>
          <div className="text-[11px] text-red-500 font-medium">Exceeded turnaround time</div>
        </div>
      </div>

      {/* 2. FILTER TOOLBAR */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row gap-3 justify-between items-stretch md:items-center">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search Ticket No (CMP-...), Customer Name, RO No..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Branch Filter */}
          <select
            value={branchFilter}
            onChange={(e) => setBranchFilter(e.target.value)}
            className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
          >
            <option value="ALL">All Workshop Branches</option>
            {branches.map((br) => (
              <option key={br.id} value={br.id}>
                {br.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open (New)</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved (Pending Reconf)</option>
            <option value="CLOSED">Closed & Satisfied</option>
            <option value="REOPENED">Reopened</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
          >
            <option value="ALL">All Severities</option>
            <option value="HIGH">HIGH Severity</option>
            <option value="MEDIUM">MEDIUM Severity</option>
            <option value="LOW">LOW Severity</option>
          </select>

          {/* SLA Breached Toggle Pill */}
          <button
            type="button"
            onClick={() => setSlaBreachedFilter(!slaBreachedFilter)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              slaBreachedFilter
                ? 'bg-red-600 text-white border-red-700 shadow-sm'
                : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'
            }`}
          >
            SLA Breached Only
          </button>
        </div>
      </div>

      {/* 3. COMPLAINTS LIST TABLE */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            Customer Dissatisfaction Tickets ({totalCount})
          </h2>
        </div>

        {complaintsError ? (
          <div className="py-16 text-center space-y-3">
            <div className="inline-flex p-3 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <p className="text-xs text-red-600 dark:text-red-400 font-semibold">{complaintsError}</p>
            <button
              type="button"
              onClick={fetchComplaints}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 text-white text-xs font-semibold hover:bg-red-700 shadow-sm transition"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : loading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse flex items-center px-4 gap-4">
                <div className="h-3.5 w-28 bg-slate-200 dark:bg-slate-700 rounded" />
                <div className="h-3.5 w-24 bg-slate-200 dark:bg-slate-700 rounded" />
                <div className="h-3.5 w-32 bg-slate-200 dark:bg-slate-700 rounded" />
                <div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-700 rounded ml-auto" />
              </div>
            ))}
          </div>
        ) : complaints.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="inline-flex p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400">
              <CheckCircle2 className="h-6 w-6 text-emerald-500" />
            </div>
            <p className="text-xs text-slate-500 font-medium">No complaints found matching the active filters.</p>
            {(statusFilter !== 'ALL' || severityFilter !== 'ALL' || branchFilter !== 'ALL' || slaBreachedFilter || searchTerm) && (
              <button
                type="button"
                onClick={() => {
                  setStatusFilter('ALL');
                  setSeverityFilter('ALL');
                  setBranchFilter('ALL');
                  setSlaBreachedFilter(false);
                  setSearchTerm('');
                }}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 transition"
              >
                <X className="h-3.5 w-3.5" />
                <span>Reset Filters</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-3">Customer Name</th>
                  <th className="py-3 px-3">Reg No</th>
                  <th className="py-3 px-3">Ticket / Job Card</th>
                  <th className="py-3 px-3">Category & Severity</th>
                  <th className="py-3 px-3">SLA Countdown</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Assigned Owner</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {complaints.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition cursor-pointer"
                    onClick={() => handleOpenTicket(c.id)}
                  >
                    {/* 1. Customer Name */}
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900 dark:text-white text-xs">
                        {c.customer_name || 'Customer'}
                      </div>
                      <div className="font-mono text-[11px] text-slate-400">
                        {c.customer_phone_masked}
                      </div>
                    </td>

                    {/* 2. Reg No of Vehicle */}
                    <td className="py-3 px-3">
                      <div className="font-mono font-semibold text-slate-900 dark:text-white">
                        {c.vehicle_reg_no || 'N/A'}
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                        <span>{c.vehicle_model}</span>
                        <span>•</span>
                        <span>{c.brand_code}</span>
                      </div>
                    </td>

                    {/* 3. Ticket & Job Card No */}
                    <td className="py-3 px-3">
                      <div className="font-mono font-bold text-red-600 dark:text-red-400">
                        {c.complaint_no}
                      </div>
                      <div className="font-mono text-[11px] text-slate-400">
                        RO: {c.job_card_no}
                      </div>
                    </td>

                    {/* 4. Category & Severity */}
                    <td className="py-3 px-3">
                      <div className="font-medium text-slate-900 dark:text-white">
                        {c.category_name}
                      </div>
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          c.severity === 'HIGH'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                            : c.severity === 'MEDIUM'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                        }`}
                      >
                        {c.severity}
                      </span>
                    </td>

                    {/* SLA Countdown Timer */}
                    <td className="py-3 px-3">
                      {c.status === 'CLOSED' ? (
                        <span className="text-slate-400 font-medium">Resolved</span>
                      ) : c.is_sla_breached ? (
                        <div className="flex items-center gap-1 text-red-600 font-bold">
                          <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                          <span>BREACHED ({Math.abs(c.hours_remaining)}h ago)</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-emerald-600 font-medium">
                          <Clock className="h-3.5 w-3.5 shrink-0" />
                          <span>{c.hours_remaining}h left</span>
                        </div>
                      )}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-3">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${
                          c.status === 'RESOLVED'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                            : c.status === 'CLOSED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : c.status === 'REOPENED'
                            ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>

                    {/* Assigned Owner */}
                    <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                      {c.assigned_to_name}
                    </td>

                    {/* Action */}
                    <td className="py-3 px-3 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenTicket(c.id);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 text-white font-semibold text-xs shadow-sm transition"
                      >
                        Manage
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. TICKET MANAGEMENT & TIMELINE MODAL */}
      {selectedComplaintId && activeComplaintDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 sm:p-5">
          <div className="relative w-full max-w-5xl h-[92vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="h-14 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between bg-slate-50 dark:bg-slate-900 shrink-0">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm font-bold text-red-600 dark:text-red-400">
                  {activeComplaintDetail.complaint_no}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-200 dark:bg-slate-800">
                  {activeComplaintDetail.category_name}
                </span>
                <span className="text-xs text-slate-400">
                  RO: {activeComplaintDetail.job_card_no}
                </span>
              </div>

              <button
                onClick={() => setSelectedComplaintId(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Split Content */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
              {/* Left: Ticket Dossier & Timeline (7 cols) */}
              <div className="lg:col-span-7 border-r border-slate-200 dark:border-slate-800 p-5 overflow-y-auto space-y-5">
                {/* Issue Description */}
                <div className="p-4 rounded-xl bg-red-50/50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/40 space-y-1.5">
                  <div className="text-xs font-bold text-red-800 dark:text-red-300">
                    Reported Customer Defect / Issue:
                  </div>
                  <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                    "{activeComplaintDetail.description}"
                  </p>
                </div>

                {/* Customer & Vehicle Snapshot */}
                <div className="grid grid-cols-2 gap-3 text-xs p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div>
                    <span className="text-slate-400">Customer Name:</span>
                    <div className="font-semibold text-slate-900 dark:text-white">
                      {activeComplaintDetail.customer_name}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400">Customer Phone:</span>
                    <div className="font-mono text-slate-900 dark:text-white">
                      {activeComplaintDetail.customer_phone_masked}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400">Vehicle:</span>
                    <div className="font-semibold text-slate-900 dark:text-white">
                      {activeComplaintDetail.vehicle_model} ({activeComplaintDetail.vehicle_reg_no})
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400">Workshop Branch:</span>
                    <div className="text-slate-700 dark:text-slate-300">
                      {activeComplaintDetail.branch_name}
                    </div>
                  </div>
                </div>

                {/* Resolution Remarks if already logged */}
                {activeComplaintDetail.resolution_remarks && (
                  <div className="p-3.5 rounded-xl bg-blue-50/60 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-xs space-y-1">
                    <span className="font-bold text-blue-800 dark:text-blue-300">
                      Resolution Remarks Submitted:
                    </span>
                    <p className="text-slate-800 dark:text-slate-200">
                      {activeComplaintDetail.resolution_remarks}
                    </p>
                  </div>
                )}

                {/* Audit Trail & Event Timeline */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5 text-blue-600" />
                    Investigation & Audit Timeline ({activeComplaintDetail.events.length})
                  </h4>

                  <div className="space-y-3 border-l-2 border-slate-200 dark:border-slate-700 ml-2 pl-4">
                    {activeComplaintDetail.events.map((ev) => (
                      <div key={ev.id} className="relative space-y-0.5 text-xs">
                        <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-600 border-2 border-white dark:border-slate-900"></span>
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {ev.event_type} {ev.to_status ? `→ ${ev.to_status}` : ''}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {new Date(ev.created_at).toLocaleString()}
                          </span>
                        </div>
                        {ev.remarks && (
                          <p className="text-slate-600 dark:text-slate-300 text-[11px] italic">
                            "{ev.remarks}"
                          </p>
                        )}
                        <div className="text-[10px] text-slate-400">By: {ev.performed_by_name}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right: Actions & Post-Resolution Reconfirmation (5 cols) */}
              <div className="lg:col-span-5 p-5 overflow-y-auto space-y-6 bg-white dark:bg-slate-900">
                {/* 1. Status Transition Form */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Update Ticket Lifecycle Status
                  </h3>

                  <form onSubmit={handleUpdateStatus} className="space-y-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Select New Status *
                      </label>
                      <select
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white font-semibold"
                      >
                        <option value="IN_PROGRESS">IN PROGRESS (Work Underway)</option>
                        <option value="RESOLVED">RESOLVED (Job Fixed - Triggers Reconf Call)</option>
                        <option value="CLOSED">CLOSED (Formally Closed)</option>
                        <option value="REOPENED">REOPENED (Customer Dissatisfied)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Assign Ticket Owner
                      </label>
                      <select
                        value={assigneeId}
                        onChange={(e) => setAssigneeId(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                      >
                        <option value="">-- Unassigned --</option>
                        {users.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.full_name} ({u.role?.name || 'Staff'})
                          </option>
                        ))}
                      </select>
                    </div>

                    {newStatus === 'RESOLVED' && (
                      <div>
                        <label className="block text-[11px] font-semibold text-blue-600 dark:text-blue-400 mb-1">
                          Corrective Action / Resolution Remarks *
                        </label>
                        <textarea
                          rows={2}
                          value={resolutionRemarks}
                          onChange={(e) => setResolutionRemarks(e.target.value)}
                          placeholder="Explain how the issue was fixed (e.g. Brake pad replaced, advisor apologized)..."
                          className="w-full rounded-lg border border-blue-300 dark:border-blue-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                          required
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Timeline Note / Internal Remarks
                      </label>
                      <input
                        type="text"
                        value={statusRemarks}
                        onChange={(e) => setStatusRemarks(e.target.value)}
                        placeholder="Internal communication or update..."
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={updatingStatus}
                      className="w-full py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
                    >
                      {updatingStatus ? 'Updating...' : 'Save Lifecycle Status'}
                    </button>
                  </form>
                </div>

                {/* 2. Post-Resolution Reconfirmation Call Form */}
                <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 space-y-4">
                  <div className="space-y-1">
                    <h3 className="text-xs font-bold text-blue-900 dark:text-blue-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Phone className="h-3.5 w-3.5" />
                      Post-Resolution Reconfirmation Call
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Call customer to verify vehicle satisfaction post-resolution before formal closure.
                    </p>
                  </div>

                  <form onSubmit={handleReconfirmationSubmit} className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] font-semibold text-slate-700 dark:text-slate-300 mb-0.5">
                          Call Connect *
                        </label>
                        <select
                          value={reconfCallStatus}
                          onChange={(e) => setReconfCallStatus(e.target.value)}
                          className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs"
                        >
                          <option value="Connected">Connected</option>
                          <option value="Not Connected">Not Connected</option>
                          <option value="Busy">Busy</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] font-semibold text-slate-700 dark:text-slate-300 mb-0.5">
                          Customer Verdict *
                        </label>
                        <select
                          value={reconfStatus}
                          onChange={(e) => setReconfStatus(e.target.value)}
                          className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs font-bold text-slate-900 dark:text-white"
                        >
                          <option value="SATISFIED_CLOSED">Satisfied (Close Ticket)</option>
                          <option value="UNSATISFIED_REOPENED">Unsatisfied (Reopen Ticket)</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-slate-700 dark:text-slate-300 mb-0.5">
                        Customer Voice / Reconfirmation Feedback
                      </label>
                      <textarea
                        rows={2}
                        value={reconfFeedback}
                        onChange={(e) => setReconfFeedback(e.target.value)}
                        placeholder="Customer verbatim remarks during reconfirmation call..."
                        className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={submittingReconf}
                      className={`w-full py-2 rounded-lg text-xs font-bold text-white transition ${
                        reconfStatus === 'SATISFIED_CLOSED'
                          ? 'bg-emerald-600 hover:bg-emerald-700'
                          : 'bg-red-600 hover:bg-red-700'
                      }`}
                    >
                      {submittingReconf
                        ? 'Submitting...'
                        : reconfStatus === 'SATISFIED_CLOSED'
                        ? 'Confirm Satisfaction & Close Ticket'
                        : 'Reopen Complaint Ticket'}
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

