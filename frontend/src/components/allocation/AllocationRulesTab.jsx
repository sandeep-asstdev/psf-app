/**
 * ============================================================================
 * FILE PURPOSE: Allocation Strategy & Rules Configuration Component.
 * Allows Super Admins to configure how DMS job card follow-ups are distributed:
 * strategy (Equal Present CRE, Round Robin, By Branch), sticky customer grouping, and logout policies.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches current allocation rules from `GET /api/v1/allocation/rules`.
 * - Saves updated rules to `PUT /api/v1/allocation/rules`.
 * - Restricted to Super Admin (L1) only.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Save button fails with HTTP 403 Forbidden
 *   -> Cause: Logged in user is not a Super Admin.
 *   -> What should you do: CRE Admin (L2) cannot edit allocation rules; log in as `admin@apexauto.com`.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import { 
  SplitSquareVertical, Sliders, ShieldCheck, Undo2, Users, 
  Layers, PhoneCall, RefreshCw, Save, Info, AlertTriangle
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function AllocationRulesTab() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [rules, setRules] = useState({
    strategy: 'EQUAL_PRESENT_CRE',
    pool_mode: 'CRE_POOL',
    sticky_customers: true,
    balance_total_pending: false,
    logout_policy: 'KEEP',
    undo_window_minutes: 15,
    weights: {},
  });

  const loadRules = async () => {
    try {
      setLoading(true);
      const res = await api.get('/allocation/rules');
      setRules(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load allocation configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const res = await api.put('/allocation/rules', rules);
      setRules(res.data);
      toast.success('Call allocation rules successfully updated!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save allocation rules');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <div className="flex items-center gap-2">
          <SplitSquareVertical className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Automatic Call Allocation Engine
          </h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Configure how new DMS job cards are automatically divided among active, present CREs upon import.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Core Strategy Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <Sliders className="h-4 w-4 text-blue-500" />
            1. Allocation Strategy & Distribution Mode
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Distribution Strategy
              </label>
              <select
                value={rules.strategy}
                onChange={(e) => setRules({ ...rules, strategy: e.target.value })}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="EQUAL_PRESENT_CRE">EQUAL_PRESENT_CRE (Default: Equal split ±1 with rotating cursor)</option>
                <option value="ROUND_ROBIN">ROUND_ROBIN (Standard single round-robin)</option>
                <option value="BY_BRANCH">BY_BRANCH (Strictly assign to branch-allocated CREs)</option>
                <option value="MANUAL">MANUAL (Leave in unallocated pool for manual assignment)</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-1">
                Equal split guarantees caller workloads differ by at most 1, rotating the remainder cursor across batch imports.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Pool Scoping Mode
              </label>
              <select
                value={rules.pool_mode}
                onChange={(e) => setRules({ ...rules, pool_mode: e.target.value })}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="CRE_POOL">CRE_POOL (Central team handles calls across all branches)</option>
                <option value="BRANCH_ONLY">BRANCH_ONLY (Only callers explicitly assigned to branch receive calls)</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-1">
                Controls whether callers without branch restrictions receive job cards from any dealership branch.
              </p>
            </div>
          </div>
        </div>

        {/* Workload & Customer Grouping */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <Users className="h-4 w-4 text-emerald-500" />
            2. Customer Continuity & Workload Balancing
          </h3>

          <div className="space-y-3">
            <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 cursor-pointer">
              <input
                type="checkbox"
                checked={rules.sticky_customers}
                onChange={(e) => setRules({ ...rules, sticky_customers: e.target.checked })}
                className="mt-0.5 rounded text-blue-600 focus:ring-blue-500 h-4 w-4"
              />
              <div>
                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Sticky Customers (Recommended)
                </span>
                <p className="text-[11px] text-slate-400">
                  Multiple job cards for the same customer phone in the same batch are bundled and allocated to the same CRE so the customer only receives one call.
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 cursor-pointer">
              <input
                type="checkbox"
                checked={rules.balance_total_pending}
                onChange={(e) => setRules({ ...rules, balance_total_pending: e.target.checked })}
                className="mt-0.5 rounded text-blue-600 focus:ring-blue-500 h-4 w-4"
              />
              <div>
                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Balance Total Pending Workload
                </span>
                <p className="text-[11px] text-slate-400">
                  When enabled, caller distribution accounts for existing pending queues, assigning more new calls to callers with fewer outstanding calls. Off divides only the new batch.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Shift Logout & Safety Controls */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-purple-500" />
            3. Caller Shift Logout Policy & Rollback Window
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                CRE Logout Policy for Pending Calls
              </label>
              <select
                value={rules.logout_policy}
                onChange={(e) => setRules({ ...rules, logout_policy: e.target.value })}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="KEEP">KEEP (Calls remain assigned to caller for their next shift)</option>
                <option value="RETURN_TO_POOL">RETURN_TO_POOL (Untouched calls returned to unallocated pool)</option>
                <option value="REDISTRIBUTE_EQUALLY">REDISTRIBUTE_EQUALLY (Untouched calls redistributed to other active CREs)</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-1">
                Governs untouched calls when a caller clocks out for the day.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Undo Safety Window (Minutes)
              </label>
              <input
                type="number"
                min="1"
                max="120"
                value={rules.undo_window_minutes}
                onChange={(e) => setRules({ ...rules, undo_window_minutes: parseInt(e.target.value) || 15 })}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Time limit allowed for CRE Admin to 1-click rollback an allocation run if no call attempts were made.
              </p>
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={loadRules}
            disabled={loading || saving}
            className="px-4 py-2 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
          >
            Reset
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save Allocation Rules'}
          </button>
        </div>
      </form>
    </div>
  );
}

