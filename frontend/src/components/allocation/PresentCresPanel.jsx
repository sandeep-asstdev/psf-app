/**
 * ============================================================================
 * FILE PURPOSE: Present CRE Roster & Attendance Slide-out Panel.
 * Shows the CRE Admin which CREs are currently Present or Absent/On Leave today,
 * their active pending call workloads, and provides toggle buttons to manually mark attendance.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches present CRE list from `GET /api/v1/allocation/present-cres`.
 * - Provides toggle buttons to override attendance to 'Present' or 'On Leave'.
 * - Provides 'Allocate Now' button to immediately distribute unallocated calls.
 * - Provides 'Rebalance' button to re-equalize calls when a CRE joins mid-shift.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: CRE shows 'Absent' even though they are working
 *   -> Cause: CRE has not logged in today or was marked absent.
 *   -> What should you do: Click the 'Mark Present' toggle button in this panel to manually include them in call distribution.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import { 
  Users, CheckCircle2, XCircle, Clock, AlertCircle, RefreshCw, 
  ArrowRightLeft, ShieldCheck, UserCheck, UserX, Calendar, Play, Zap
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function PresentCresPanel({ onAttendanceChanged }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({ total_eligible: 0, total_present: 0, total_absent: 0, cres: [] });
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  
  // Rebalance modal state
  const [showRebalanceModal, setShowRebalanceModal] = useState(false);
  const [rebalancePreview, setRebalancePreview] = useState(null);
  const [rebalancing, setRebalancing] = useState(false);

  // Allocate Now modal state
  const [showAllocateNowModal, setShowAllocateNowModal] = useState(false);
  const [allocateNowPreview, setAllocateNowPreview] = useState(null);
  const [allocatingNow, setAllocatingNow] = useState(false);

  // Load present CREs
  const loadPresentCres = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/allocation/present-cres?attendance_date=${selectedDate}`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to fetch CRE presence data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPresentCres();
  }, [selectedDate]);

  // Handle manual attendance override
  const handleSetOverride = async (userId, status) => {
    try {
      await api.put('/allocation/attendance-override', {
        user_id: userId,
        attendance_date: selectedDate,
        status: status,
        reason: `Manually marked ${status} by CRE Admin`,
      });
      toast.success(`CRE attendance updated to ${status}`);
      await loadPresentCres();
      if (onAttendanceChanged) onAttendanceChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update attendance override');
    }
  };

  // Preview rebalance
  const handleOpenRebalance = async () => {
    try {
      setRebalancing(true);
      const res = await api.post('/allocation/rebalance/preview');
      setRebalancePreview(res.data);
      setShowRebalanceModal(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate rebalance preview');
    } finally {
      setRebalancing(false);
    }
  };

  // Confirm rebalance
  const handleConfirmRebalance = async () => {
    try {
      setRebalancing(true);
      const res = await api.post('/allocation/rebalance/confirm');
      toast.success(`Successfully rebalanced ${res.data.allocated_items} untouched calls!`);
      setShowRebalanceModal(false);
      await loadPresentCres();
      if (onAttendanceChanged) onAttendanceChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to execute call rebalance');
    } finally {
      setRebalancing(false);
    }
  };

  // Preview Allocate Now
  const handleOpenAllocateNow = async () => {
    try {
      setAllocatingNow(true);
      const res = await api.post('/allocation/allocate-now/preview');
      setAllocateNowPreview(res.data);
      setShowAllocateNowModal(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate allocation preview');
    } finally {
      setAllocatingNow(false);
    }
  };

  // Confirm Allocate Now
  const handleConfirmAllocateNow = async () => {
    try {
      setAllocatingNow(true);
      const res = await api.post('/allocation/allocate-now/confirm');
      toast.success(`Successfully allocated ${res.data.allocated_items} calls among present CREs!`);
      setShowAllocateNowModal(false);
      await loadPresentCres();
      if (onAttendanceChanged) onAttendanceChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to execute call allocation');
    } finally {
      setAllocatingNow(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Active Callers & Allocation Pool
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-800">
              {data.total_present} Available / {data.total_absent} Away
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time caller availability. Automatic DMS call import divides calls equally among currently present CREs.
          </p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          />
          <button
            onClick={loadPresentCres}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="Refresh Presence"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleOpenAllocateNow}
            disabled={data.total_present === 0 || allocatingNow}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
            title="Allocate all unallocated pool calls immediately to present CREs"
          >
            <Zap className="h-3.5 w-3.5" />
            Allocate Now
          </button>
          <button
            onClick={handleOpenRebalance}
            disabled={data.total_present === 0 || rebalancing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <ArrowRightLeft className="h-3.5 w-3.5" />
            Rebalance Calls
          </button>
        </div>
      </div>

      {/* CRE List Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-medium">
              <th className="pb-2.5">CRE Name & Contact</th>
              <th className="pb-2.5">Role & Scopes</th>
              <th className="pb-2.5">Presence Status</th>
              <th className="pb-2.5">Pending Calls</th>
              <th className="pb-2.5 text-right">Quick Override</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {data.cres.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-6 text-center text-slate-400">
                  No eligible callers found in this dealership.
                </td>
              </tr>
            ) : (
              data.cres.map((cre) => (
                <tr key={cre.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                  <td className="py-3">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{cre.full_name}</div>
                    <div className="text-[11px] text-slate-400">{cre.email}</div>
                  </td>
                  <td className="py-3">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      {cre.role_name}
                    </span>
                    {cre.assigned_branches?.length > 0 && (
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {cre.assigned_branches.join(', ')}
                      </div>
                    )}
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-1.5">
                      {cre.is_present ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="h-3 w-3" />
                          Present
                        </span>
                      ) : cre.attendance_status === 'ON_LEAVE' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-400 border border-purple-200 dark:border-purple-800">
                          <Clock className="h-3 w-3" />
                          On Leave
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          <XCircle className="h-3 w-3" />
                          Absent
                        </span>
                      )}

                      {cre.has_override && (
                        <span 
                          className="text-[10px] text-amber-600 dark:text-amber-400 font-medium cursor-help"
                          title={cre.override_reason || 'Manual Admin Override'}
                        >
                          (Manual)
                        </span>
                      )}
                    </div>
                    {cre.has_active_login && (
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Logged in: {new Date(cre.login_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    )}
                  </td>
                  <td className="py-3">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                      {cre.current_pending} calls
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <div className="inline-flex items-center gap-1">
                      <button
                        onClick={() => handleSetOverride(cre.user_id, 'PRESENT')}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition ${
                          cre.is_present 
                            ? 'bg-emerald-600 text-white' 
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 hover:text-emerald-700'
                        }`}
                        title="Mark Present"
                      >
                        Present
                      </button>
                      <button
                        onClick={() => handleSetOverride(cre.user_id, 'ABSENT')}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition ${
                          !cre.is_present && cre.attendance_status === 'ABSENT'
                            ? 'bg-red-600 text-white' 
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-red-50 dark:hover:bg-red-950/40 hover:text-red-700'
                        }`}
                        title="Mark Absent"
                      >
                        Absent
                      </button>
                      <button
                        onClick={() => handleSetOverride(cre.user_id, 'ON_LEAVE')}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition ${
                          cre.attendance_status === 'ON_LEAVE'
                            ? 'bg-purple-600 text-white' 
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-purple-50 dark:hover:bg-purple-950/40 hover:text-purple-700'
                        }`}
                        title="Mark On Leave"
                      >
                        Leave
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Rebalance Modal */}
      {showRebalanceModal && rebalancePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Rebalance Calls Preview
                </h3>
              </div>
              <button
                onClick={() => setShowRebalanceModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-lg text-xs text-blue-800 dark:text-blue-300 flex items-start gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5 text-blue-600" />
              <div>
                <strong>Safety Guarantee:</strong> Only untouched calls (0 attempts, status PENDING) will be rebalanced. Calls already attempted or in progress will never be moved.
              </div>
            </div>

            <div className="text-xs text-slate-600 dark:text-slate-300">
              Total untouched movable calls: <strong className="text-blue-600">{rebalancePreview.total_movable_calls}</strong> across <strong>{rebalancePreview.present_cre_count}</strong> present CREs.
            </div>

            <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden max-h-60 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold">
                  <tr>
                    <th className="py-2 px-3">CRE Name</th>
                    <th className="py-2 px-3 text-center">Current</th>
                    <th className="py-2 px-3 text-center">Proposed</th>
                    <th className="py-2 px-3 text-right">Net Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {rebalancePreview.items.map((item) => (
                    <tr key={item.user_id}>
                      <td className="py-2 px-3 font-medium text-slate-800 dark:text-slate-200">{item.full_name}</td>
                      <td className="py-2 px-3 text-center text-slate-600 dark:text-slate-400">{item.current_pending}</td>
                      <td className="py-2 px-3 text-center font-bold text-blue-600">{item.proposed_pending}</td>
                      <td className="py-2 px-3 text-right">
                        <span className={`font-semibold ${item.net_change > 0 ? 'text-emerald-600' : item.net_change < 0 ? 'text-amber-600' : 'text-slate-400'}`}>
                          {item.net_change > 0 ? `+${item.net_change}` : item.net_change}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowRebalanceModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRebalance}
                disabled={rebalancing}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition disabled:opacity-50"
              >
                {rebalancing ? 'Rebalancing...' : 'Confirm Rebalance'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Allocate Now Modal */}
      {showAllocateNowModal && allocateNowPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 max-w-lg w-full shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Allocate Unallocated Calls Now
                </h3>
              </div>
              <button
                onClick={() => setShowAllocateNowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              Immediately distribute all pending unallocated calls among currently present CREs following the active dealer allocation strategy ({allocateNowPreview.strategy}).
            </p>

            <div className="text-xs text-slate-600 dark:text-slate-300">
              Total unallocated calls to divide: <strong className="text-emerald-600">{allocateNowPreview.total_unallocated_calls}</strong> across <strong>{allocateNowPreview.present_cre_count}</strong> present CREs.
            </div>

            <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden max-h-60 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold">
                  <tr>
                    <th className="py-2 px-3">CRE Name</th>
                    <th className="py-2 px-3 text-center">Current Pending</th>
                    <th className="py-2 px-3 text-center">New Allocation</th>
                    <th className="py-2 px-3 text-right">New Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {allocateNowPreview.items.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-slate-400">
                        {allocateNowPreview.message || 'No items to allocate.'}
                      </td>
                    </tr>
                  ) : (
                    allocateNowPreview.items.map((item) => (
                      <tr key={item.user_id}>
                        <td className="py-2 px-3 font-medium text-slate-800 dark:text-slate-200">{item.full_name}</td>
                        <td className="py-2 px-3 text-center text-slate-600 dark:text-slate-400">{item.current_pending}</td>
                        <td className="py-2 px-3 text-center font-bold text-emerald-600">+{item.allocated_in_this_run}</td>
                        <td className="py-2 px-3 text-right font-bold text-slate-900 dark:text-slate-100">
                          {item.new_total_pending}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAllocateNowModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAllocateNow}
                disabled={allocatingNow || allocateNowPreview.total_unallocated_calls === 0 || allocateNowPreview.present_cre_count === 0}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
              >
                {allocatingNow ? 'Allocating...' : 'Confirm Allocation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

