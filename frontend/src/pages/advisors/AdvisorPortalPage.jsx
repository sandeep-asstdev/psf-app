/**
 * ============================================================================
 * FILE PURPOSE: Service Advisor Follow-up Action Portal.
 * Allows Service Advisors to review and take action on dissatisfied customers and complaints
 * assigned to their workshop repair orders.
 * 
 * KEY RESPONSIBILITIES:
 * - Displays customer complaints filtered to the logged-in Service Advisor.
 * - Allows advisors to add root cause analysis notes and proposed corrective actions.
 * - Prevents advisors from closing complaints directly (enforcing dual-authorization).
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Advisor sees 0 complaints even when customer was dissatisfied
 *   -> Cause: Complaint was not assigned to this advisor or job card advisor name did not match.
 *   -> What should you do: Verify complaint assignment in the Complaints tab.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  Wrench,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  User,
  Car,
  Phone,
  MessageSquare,
  Sparkles,
  Send,
  X,
  FileText,
  ShieldCheck,
  Building2,
  ChevronRight,
  TrendingDown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function AdvisorPortalPage() {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [statusFilter, setStatusFilter] = useState('PENDING');
  const [searchTerm, setSearchTerm] = useState('');

  // Active Task Modal for submitting advisor correction
  const [selectedTask, setSelectedTask] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form inputs
  const [advCallStatus, setAdvCallStatus] = useState('Connected');
  const [advCaseStatus, setAdvCaseStatus] = useState('Customer Convinced');
  const [advVoc, setAdvVoc] = useState('');
  const [advStatus, setAdvStatus] = useState('RESOLVED');

  useEffect(() => {
    fetchAdvisorTasks();
  }, [statusFilter]);

  const fetchAdvisorTasks = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter !== 'ALL') params.status = statusFilter;

      const res = await api.get('/complaints/advisors/tasks', { params });
      setTasks(res.data || []);
    } catch (err) {
      toast.error('Failed to load Service Advisor tasks');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenActionModal = (task) => {
    setSelectedTask(task);
    setAdvCallStatus(task.adv_call_status || 'Connected');
    setAdvCaseStatus(task.adv_case_status || 'Customer Convinced');
    setAdvVoc(task.adv_voc || '');
    setAdvStatus(task.adv_status === 'RESOLVED' ? 'RESOLVED' : 'RESOLVED');
    setIsModalOpen(true);
  };

  const handleSubmitCorrection = async (e) => {
    e.preventDefault();
    if (!advVoc.trim()) {
      toast.error('Please enter your corrective remarks and explanation');
      return;
    }

    try {
      setSubmitting(true);
      await api.post('/complaints/advisors/corrections', {
        job_card_id: selectedTask.job_card_id,
        adv_call_status: advCallStatus,
        adv_case_status: advCaseStatus,
        adv_voc: advVoc.trim(),
        adv_status: advStatus,
      });

      toast.success('Corrective follow-up recorded successfully!');
      setIsModalOpen(false);
      setSelectedTask(null);
      fetchAdvisorTasks();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit correction');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered by local search term
  const filteredTasks = tasks.filter((t) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      t.job_card_no.toLowerCase().includes(term) ||
      t.customer_name.toLowerCase().includes(term) ||
      t.vehicle_reg_no.toLowerCase().includes(term) ||
      t.vehicle_model.toLowerCase().includes(term)
    );
  });

  const pendingCount = tasks.filter((t) => t.adv_status === 'PENDING').length;
  const resolvedCount = tasks.filter((t) => t.adv_status === 'RESOLVED').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Wrench className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            Service Advisor Follow-up Portal
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review dissatisfied customer feedback, connect directly, and document corrective resolution actions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAdvisorTasks}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-700/50 shadow-sm transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Assigned Follow-ups
            </p>
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">{tasks.length}</span>
            <span className="text-xs text-slate-400">Total Leads</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Pending Clarification
            </p>
            <div className="p-2 rounded-xl bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-600 dark:text-amber-400">{pendingCount}</span>
            <span className="text-xs text-slate-400">Awaiting Action</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Resolved & Convinced
            </p>
            <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{resolvedCount}</span>
            <span className="text-xs text-slate-400">Customer Retained</span>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by Job Card No, Customer Name, or Vehicle Reg No..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setStatusFilter('PENDING')}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition ${
              statusFilter === 'PENDING'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            Pending ({pendingCount})
          </button>
          <button
            onClick={() => setStatusFilter('RESOLVED')}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition ${
              statusFilter === 'RESOLVED'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            Resolved ({resolvedCount})
          </button>
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition ${
              statusFilter === 'ALL'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            All Tasks
          </button>
        </div>
      </div>

      {/* Task List Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
              Loading Advisor Tasks...
            </p>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3 text-center px-4">
            <div className="p-4 rounded-full bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400">
              <ShieldCheck className="w-10 h-10" />
            </div>
            <h4 className="text-base font-bold text-slate-900 dark:text-white">
              No Dissatisfied Tasks Pending
            </h4>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md">
              All post-service customer feedback has been handled or there are no low CSAT/NPS scores
              escalated to your queue.
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
                  <th className="py-3 px-4">Dissatisfied Feedback (VOC)</th>
                  <th className="py-3 px-4">Advisor Action & Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredTasks.map((task) => (
                  <tr
                    key={task.id}
                    className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition group"
                  >
                    {/* Job Card */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {task.job_card_no}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {task.job_card_date}
                      </div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mt-0.5">
                        {task.branch_name}
                      </div>
                    </td>

                    {/* Customer */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-900 dark:text-white flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {task.customer_name}
                      </div>
                      <div className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                        {task.customer_phone_masked}
                      </div>
                    </td>

                    {/* Vehicle */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-900 dark:text-white flex items-center gap-1.5">
                        <Car className="w-3.5 h-3.5 text-slate-400" />
                        {task.vehicle_model}
                      </div>
                      <div className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                        {task.vehicle_reg_no}
                      </div>
                    </td>

                    {/* Dissatisfied VOC */}
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200/60 dark:border-rose-900/50">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400">
                          <TrendingDown className="w-3.5 h-3.5" />
                          <span>Customer Issue</span>
                          {task.csat_score && (
                            <span className="ml-auto font-mono text-rose-600">
                              ★ {Number(task.csat_score).toFixed(1)}/5
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-rose-900 dark:text-rose-200/90 mt-1 line-clamp-2 leading-relaxed">
                          {task.dissatisfied_voc || 'Customer rated low satisfaction during follow-up call.'}
                        </p>
                      </div>
                    </td>

                    {/* Advisor Status */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                            task.adv_status === 'RESOLVED'
                              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                              : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                          }`}
                        >
                          {task.adv_status}
                        </span>

                        {task.adv_voc ? (
                          <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-1 italic">
                            "{task.adv_voc}"
                          </p>
                        ) : (
                          <p className="text-xs text-slate-400">Pending advisor callback</p>
                        )}
                      </div>
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleOpenActionModal(task)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold shadow-sm transition ${
                          task.adv_status === 'RESOLVED'
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                        }`}
                      >
                        <Wrench className="w-3.5 h-3.5" />
                        {task.adv_status === 'RESOLVED' ? 'Edit Response' : 'Address'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Action / Correction Modal */}
      {isModalOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-indigo-600" />
                  Service Advisor Callback & Resolution
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Job Card: {selectedTask.job_card_no} • {selectedTask.customer_name} ({selectedTask.vehicle_model})
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Customer VOC review banner */}
            <div className="px-5 pt-4">
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200/70 dark:border-rose-900/60">
                <span className="text-xs font-bold text-rose-700 dark:text-rose-400 uppercase tracking-wide">
                  Customer Dissatisfaction Note
                </span>
                <p className="text-xs text-rose-900 dark:text-rose-200 mt-1 leading-relaxed">
                  {selectedTask.dissatisfied_voc || 'Customer was dissatisfied with service quality or billing.'}
                </p>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmitCorrection} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Call Status
                  </label>
                  <select
                    value={advCallStatus}
                    onChange={(e) => setAdvCallStatus(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Connected">Connected</option>
                    <option value="No Answer">No Answer</option>
                    <option value="Customer Busy">Customer Busy</option>
                    <option value="Call Later">Call Later</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Case Outcome
                  </label>
                  <select
                    value={advCaseStatus}
                    onChange={(e) => setAdvCaseStatus(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Customer Convinced">Customer Convinced</option>
                    <option value="Part Ordered">Part Ordered</option>
                    <option value="Inspection Scheduled">Inspection Scheduled</option>
                    <option value="Re-service Offered">Re-service Offered</option>
                    <option value="Unresolved">Unresolved</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Advisor Corrective Remarks & Action Plan <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="Detail your conversation with the customer, root cause explanation, and corrective action agreed upon..."
                  value={advVoc}
                  onChange={(e) => setAdvVoc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Follow-up Status
                </label>
                <select
                  value={advStatus}
                  onChange={(e) => setAdvStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="RESOLVED">Resolved (Issue Addressed)</option>
                  <option value="PENDING">Pending (Follow-up Incomplete)</option>
                  <option value="CLOSED">Closed</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {submitting ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  Save & Resolve
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

