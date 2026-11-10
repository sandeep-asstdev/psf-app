/**
 * ============================================================================
 * FILE PURPOSE: OEM 24-Hour Happiness Calling Queue Page.
 * Dedicated calling queue for immediate next-day post-service follow-up (24-hour happiness check),
 * ensuring customer satisfaction before the official OEM survey period.
 * 
 * KEY RESPONSIBILITIES:
 * - Filters calling queue to `queue_type=HAPPINESS`.
 * - Allows CREs to make quick satisfaction verification calls.
 * - Immediately escalates any customer dissatisfaction into an urgent complaint ticket.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Queue is empty
 *   -> Cause: No job cards have been imported for the Happiness queue or all have been completed.
 *   -> What should you do: Check the main PSF Dashboard to see if calling line items are in the PSF queue instead.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  HeartHandshake,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  Building2,
  Phone,
  MessageSquare,
  Sparkles,
  ChevronRight,
  ShieldCheck,
  User,
  Calendar,
  Car,
  Play,
  Award,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import CallConsoleModal from '../../components/calling/CallConsoleModal';

export default function HappinessCallingPage() {
  const [loading, setLoading] = useState(true);
  const [queues, setQueues] = useState([]);
  const [totalQueues, setTotalQueues] = useState(0);

  // Filters
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Masters
  const [branches, setBranches] = useState([]);

  // Active Calling Console Modal
  const [selectedQueueId, setSelectedQueueId] = useState(null);
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);

  useEffect(() => {
    fetchBranches();
  }, []);

  useEffect(() => {
    fetchHappinessQueues();
  }, [branchFilter, statusFilter]);

  const fetchBranches = async () => {
    try {
      const res = await api.get('/masters/branches');
      setBranches(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHappinessQueues = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 50,
      };
      if (branchFilter !== 'ALL') params.branch_id = branchFilter;
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const res = await api.get('/complaints/happiness/queues', { params });
      setQueues(res.data.items || []);
      setTotalQueues(res.data.total || 0);
    } catch (err) {
      toast.error('Failed to load Happiness Calling records');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchHappinessQueues();
  };

  const openConsole = (queueId) => {
    setSelectedQueueId(queueId);
    setIsConsoleOpen(true);
  };

  const handleQueueUpdated = () => {
    fetchHappinessQueues();
  };

  // Metrics summary
  const pendingCount = queues.filter((q) => ['PENDING', 'NOT_CONTACTED', 'CALLBACK_REQUESTED'].includes(q.status)).length;
  const contactedCount = queues.filter((q) => ['CONTACTED', 'SATISFIED'].includes(q.status)).length;
  const complaintCount = queues.filter((q) => q.status === 'COMPLAINT_REGISTERED').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Hyundai OEM Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900 via-indigo-900 to-sky-950 p-6 sm:p-8 text-white shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-blue-500/20 px-3 py-1 text-xs font-semibold text-blue-200 border border-blue-400/30">
              <Award className="w-3.5 h-3.5 text-blue-300" />
              OEM Exclusive Campaign • Hyundai Motor India SOP
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight flex items-center gap-3">
              <HeartHandshake className="w-8 h-8 text-sky-400" />
              15 / 30-Day Happiness Calling
            </h1>
            <p className="text-sm text-blue-100/90 max-w-2xl leading-relaxed">
              Post-delivery vehicle running quality check and long-term customer satisfaction campaign.
              Strictly exclusive to Hyundai customers to ensure Zero-Defect ownership experience.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={fetchHappinessQueues}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm font-semibold transition border border-white/10 shadow-sm backdrop-blur"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh Queue
            </button>
          </div>
        </div>

        {/* Ambient background decoration */}
        <div className="absolute -right-12 -bottom-16 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-40 top-0 w-48 h-48 bg-sky-400/10 rounded-full blur-2xl pointer-events-none" />
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Happiness Leads
            </p>
            <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
              <HeartHandshake className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">{totalQueues}</span>
            <span className="text-xs font-medium text-slate-400">Hyundai Jobs</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Pending Calling
            </p>
            <div className="p-2 rounded-xl bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-600 dark:text-amber-400">{pendingCount}</span>
            <span className="text-xs font-medium text-slate-400">Awaiting CRE</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Contacted & Satisfied
            </p>
            <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{contactedCount}</span>
            <span className="text-xs font-medium text-slate-400">Happy Owners</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Issues Flagged
            </p>
            <div className="p-2 rounded-xl bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-600 dark:text-rose-400">{complaintCount}</span>
            <span className="text-xs font-medium text-slate-400">Escalated</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Job Card No, Customer Name, Vehicle Reg No, or Model..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            >
              <option value="ALL">All Branches</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="CONTACTED">Contacted</option>
              <option value="SATISFIED">Satisfied</option>
              <option value="COMPLAINT_REGISTERED">Complaint</option>
              <option value="CLOSED">Closed</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition shadow-sm"
            >
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Happiness Queue Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HeartHandshake className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Hyundai Happiness Calling Queue
            </h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
              {queues.length} records
            </span>
          </div>
          <span className="text-xs font-medium text-slate-400">
            Filtered by Hyundai Motor India campaign rules
          </span>
        </div>

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
              Loading Happiness Queue...
            </p>
          </div>
        ) : queues.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3 text-center px-4">
            <div className="p-4 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
              <ShieldCheck className="w-10 h-10" />
            </div>
            <h4 className="text-base font-bold text-slate-900 dark:text-white">
              No Happiness Leads Found
            </h4>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md">
              There are currently no active 15 or 30-day Happiness Calling tasks matching your filters.
              New records are automatically created upon DMS job card completion for Hyundai vehicles.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Job Card</th>
                  <th className="py-3 px-4">Customer & Contact</th>
                  <th className="py-3 px-4">Vehicle</th>
                  <th className="py-3 px-4">Branch & Advisor</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Status & Attempts</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {queues.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition group"
                  >
                    {/* Job Card */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {item.job_card_no}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {item.job_card_date}
                      </div>
                      {item.total_amount > 0 && (
                        <div className="text-xs font-mono font-medium text-emerald-600 dark:text-emerald-400 mt-0.5">
                          ₹{Number(item.total_amount).toLocaleString('en-IN')}
                        </div>
                      )}
                    </td>

                    {/* Customer */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-900 dark:text-white flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {item.customer_name}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                          {item.customer_phone_masked}
                        </span>
                        {item.customer_phone_raw && (
                          <div className="flex items-center gap-1.5 opacity-80 group-hover:opacity-100 transition">
                            <a
                              href={`tel:${item.customer_phone_raw}`}
                              title="Click to Call"
                              className="p-1 rounded-md bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 transition"
                            >
                              <Phone className="w-3 h-3" />
                            </a>
                            <a
                              href={`https://wa.me/${item.customer_phone_raw.replace(/[^0-9]/g, '')}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Message on WhatsApp"
                              className="p-1 rounded-md bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:hover:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 transition"
                            >
                              <MessageSquare className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Vehicle */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-900 dark:text-white flex items-center gap-1.5">
                        <Car className="w-3.5 h-3.5 text-slate-400" />
                        {item.vehicle_model}
                      </div>
                      <div className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                        {item.vehicle_reg_no}
                      </div>
                    </td>

                    {/* Branch & Advisor */}
                    <td className="py-3.5 px-4">
                      <div className="text-slate-900 dark:text-white font-medium">
                        {item.branch_name}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        SA: {item.service_advisor || 'Unassigned'}
                      </div>
                    </td>

                    {/* Due Date */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{item.due_at ? new Date(item.due_at).toLocaleDateString() : 'N/A'}</span>
                      </div>
                    </td>

                    {/* Status & Attempts */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                            item.status === 'CONTACTED' || item.status === 'SATISFIED'
                              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                              : item.status === 'COMPLAINT_REGISTERED'
                              ? 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
                              : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                          }`}
                        >
                          {item.status}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {item.attempts} {item.attempts === 1 ? 'call' : 'calls'}
                        </span>
                      </div>
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => openConsole(item.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition group-hover:scale-105"
                      >
                        <Play className="w-3.5 h-3.5" />
                        Call
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dedicated Call Console Modal with Hyundai Questionnaire */}
      {isConsoleOpen && selectedQueueId && (
        <CallConsoleModal
          queueId={selectedQueueId}
          isOpen={isConsoleOpen}
          onClose={() => setIsConsoleOpen(false)}
          onQueueUpdated={handleQueueUpdated}
        />
      )}
    </div>
  );
}

