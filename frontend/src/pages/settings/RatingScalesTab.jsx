/**
 * ============================================================================
 * FILE PURPOSE: OEM Rating Scales & Satisfaction Bands Settings Tab.
 * Configures brand-specific rating scales (e.g. Hyundai 1-10 NPS, Tata 1-5 Star)
 * and defines score thresholds for Delight, Satisfied, and Dissatisfied classifications.
 * 
 * KEY RESPONSIBILITIES:
 * - Displays rating bands configured for each OEM brand.
 * - Allows adjusting minimum score thresholds for Delight and Dissatisfied.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Rating bands missing for a brand
 *   -> Cause: Brand has not been configured with rating scale rules.
 *   -> What should you do: Run the database seed script to restore default manufacturer rating bands.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Sparkles,
  Star,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Edit,
  ShieldAlert,
  Info,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

const CASE_STATUS_OPTIONS = [
  'Delight',
  'Satisfied',
  'Non-Delight',
  'Dissatisfied',
];

export default function RatingScalesTab() {
  const [loading, setLoading] = useState(true);
  const [scales, setScales] = useState([]);
  const [togglingBandId, setTogglingBandId] = useState(null);

  // Quick edit modal
  const [editingBand, setEditingBand] = useState(null);
  const [targetScaleId, setTargetScaleId] = useState(null);
  const [editLabel, setEditLabel] = useState('');
  const [editCaseStatus, setEditCaseStatus] = useState('Satisfied');
  const [editIsDelight, setEditIsDelight] = useState(false);
  const [editIsTrigger, setEditIsTrigger] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    fetchRatingScales();
  }, []);

  const fetchRatingScales = async () => {
    try {
      setLoading(true);
      const res = await api.get('/masters/rating-scales');
      setScales(res.data || []);
    } catch (err) {
      toast.error('Failed to load rating scales: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Toggle Complaint Trigger
  const handleToggleComplaintTrigger = async (scaleId, band) => {
    const nextVal = !band.is_complaint_trigger;
    const bandId = band.id;

    // Optimistic UI update
    setTogglingBandId(bandId);
    setScales((prevScales) =>
      prevScales.map((s) => {
        if (s.id !== scaleId) return s;
        return {
          ...s,
          bands: s.bands.map((b) =>
            b.id === bandId ? { ...b, is_complaint_trigger: nextVal } : b
          ),
        };
      })
    );

    try {
      await api.put(`/masters/rating-scales/${scaleId}/bands/${bandId}`, {
        is_complaint_trigger: nextVal,
      });
      toast.success(
        `Band [${band.min_score}-${band.max_score}] complaint trigger ${
          nextVal ? 'ENABLED' : 'DISABLED'
        }`
      );
    } catch (err) {
      toast.error('Failed to update band: ' + (err.response?.data?.detail || err.message));
      // Revert on failure
      fetchRatingScales();
    } finally {
      setTogglingBandId(null);
    }
  };

  const handleOpenEdit = (scaleId, band) => {
    setTargetScaleId(scaleId);
    setEditingBand(band);
    setEditLabel(band.label);
    setEditCaseStatus(band.derived_case_status);
    setEditIsDelight(band.is_delight);
    setEditIsTrigger(band.is_complaint_trigger);
  };

  const handleSaveBandEdit = async (e) => {
    e.preventDefault();
    if (!editingBand || !targetScaleId) return;

    try {
      setSavingEdit(true);
      const res = await api.put(
        `/masters/rating-scales/${targetScaleId}/bands/${editingBand.id}`,
        {
          label: editLabel.trim(),
          derived_case_status: editCaseStatus,
          is_delight: editIsDelight,
          is_complaint_trigger: editIsTrigger,
        }
      );

      toast.success('Rating band rules updated successfully');
      setEditingBand(null);
      setTargetScaleId(null);
      fetchRatingScales();
    } catch (err) {
      toast.error('Update failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSavingEdit(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <Sliders className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Brand Rating Scales & Automated Sentiment Bands
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Define how raw ratings (from WhatsApp or CRE phone calls) derive Case Status, classify Customer Delight, and trigger automated Complaint tickets per OEM.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchRatingScales}
          title="Refresh"
          className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* HIGHLIGHT BANNER: Hyundai Rating 9 Trigger */}
      <div className="rounded-xl border border-blue-200 dark:border-blue-800/80 bg-blue-50/70 dark:bg-blue-950/40 p-4 text-xs shadow-sm space-y-2">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 shrink-0">
            <Info className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <span className="font-bold text-blue-900 dark:text-blue-200 text-sm">
              Hyundai SOP Complaint Trigger Rule: Rating 9 vs. Rating 10
            </span>
            <p className="text-blue-800 dark:text-blue-300/90 leading-relaxed">
              In real Hyundai dealer operations, customer score <strong>10</strong> denotes pure <strong>Delight</strong>. Any score <strong>&le; 9</strong> triggers an automated complaint ticket with category <code>WATSAPP RATING &le;9</code> to allow the service team to investigate why the experience was not a 10.
            </p>
            <p className="text-blue-700 dark:text-blue-400 text-[11px] font-medium">
              💡 You can configure or toggle this complaint trigger for score 9 (or any band) using the interactive switches below.
            </p>
          </div>
        </div>
      </div>

      {/* Scales List */}
      {loading ? (
        <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
          <span className="text-xs">Loading brand rating scales...</span>
        </div>
      ) : scales.length === 0 ? (
        <div className="py-16 text-center text-slate-400 space-y-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
          <Sliders className="h-10 w-10 mx-auto text-slate-300 dark:text-slate-600" />
          <p className="text-sm font-semibold">No rating scales configured</p>
          <p className="text-xs">Please run initial seed scripts to generate default OEM scales.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {scales.map((scale) => {
            const isHyundai = (scale.brand_name || scale.name).toLowerCase().includes('hyundai');
            return (
              <div
                key={scale.id}
                className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden"
              >
                {/* Scale Header */}
                <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-9 w-9 rounded-lg flex items-center justify-center font-bold text-sm ${
                        isHyundai
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-700 text-white'
                      }`}
                    >
                      {scale.max_rating}★
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        {scale.name}
                        {isHyundai && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                            OEM Standard
                          </span>
                        )}
                      </h3>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Brand: <strong>{scale.brand_name || 'Generic'}</strong> • Scale: 1 to {scale.max_rating} Stars
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400">
                    {scale.bands.length} sentiment bands configured
                  </div>
                </div>

                {/* Bands Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-800/20 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">
                        <th className="py-3 px-4">Score Range</th>
                        <th className="py-3 px-4">Label</th>
                        <th className="py-3 px-4">Derived Case Status</th>
                        <th className="py-3 px-4 text-center">Delight Classification</th>
                        <th className="py-3 px-4">Auto-Complaint Trigger</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                      {scale.bands.map((band) => {
                        const isScore9Hyundai =
                          isHyundai && band.min_score === 9 && band.max_score === 9;
                        return (
                          <tr
                            key={band.id}
                            className={`hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition ${
                              isScore9Hyundai
                                ? 'bg-amber-50/30 dark:bg-amber-950/20 font-medium'
                                : ''
                            }`}
                          >
                            {/* Score range */}
                            <td className="py-3 px-4">
                              <span className="font-mono text-sm font-bold text-slate-800 dark:text-slate-100 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                {band.min_score === band.max_score
                                  ? `${band.min_score} ★`
                                  : `${band.min_score} – ${band.max_score} ★`}
                              </span>
                            </td>

                            {/* Label */}
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-slate-800 dark:text-slate-200">
                                  {band.label}
                                </span>
                                {isScore9Hyundai && (
                                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                    Special SOP Band
                                  </span>
                                )}
                              </div>
                            </td>

                            {/* Case status badge */}
                            <td className="py-3 px-4">
                              <span
                                className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                                  band.derived_case_status === 'Delight'
                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                                    : band.derived_case_status === 'Satisfied'
                                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                                    : band.derived_case_status === 'Non-Delight'
                                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                                    : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                                }`}
                              >
                                {band.derived_case_status}
                              </span>
                            </td>

                            {/* Delight */}
                            <td className="py-3 px-4 text-center">
                              {band.is_delight ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                                  Delight
                                </span>
                              ) : (
                                <span className="text-slate-400 text-[11px]">—</span>
                              )}
                            </td>

                            {/* Complaint Trigger Interactive Switch */}
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  disabled={togglingBandId === band.id}
                                  onClick={() =>
                                    handleToggleComplaintTrigger(scale.id, band)
                                  }
                                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                                    band.is_complaint_trigger
                                      ? 'bg-red-600'
                                      : 'bg-slate-300 dark:bg-slate-700'
                                  }`}
                                  title={`Click to ${
                                    band.is_complaint_trigger ? 'disable' : 'enable'
                                  } complaint trigger`}
                                >
                                  <span
                                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                      band.is_complaint_trigger
                                        ? 'translate-x-4'
                                        : 'translate-x-0'
                                    }`}
                                  />
                                </button>

                                <span
                                  className={`text-[11px] font-medium ${
                                    band.is_complaint_trigger
                                      ? 'text-red-700 dark:text-red-300 font-semibold'
                                      : 'text-slate-500 dark:text-slate-400'
                                  }`}
                                >
                                  {band.is_complaint_trigger
                                    ? '🚨 Creates Complaint Ticket'
                                    : 'No Complaint'}
                                </span>
                              </div>
                            </td>

                            {/* Actions */}
                            <td className="py-3 px-4 text-right">
                              <button
                                type="button"
                                onClick={() => handleOpenEdit(scale.id, band)}
                                className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                                title="Edit Band Rules"
                              >
                                <Edit className="h-4 w-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* QUICK EDIT BAND MODAL */}
      {editingBand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Sliders className="h-5 w-5 text-blue-600" />
                Configure Rating Band [{editingBand.min_score} – {editingBand.max_score} ★]
              </h3>
              <button
                type="button"
                onClick={() => setEditingBand(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveBandEdit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Band Label *
                </label>
                <input
                  type="text"
                  value={editLabel}
                  onChange={(e) => setEditLabel(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Derived Case Status *
                </label>
                <select
                  value={editCaseStatus}
                  onChange={(e) => setEditCaseStatus(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                >
                  {CASE_STATUS_OPTIONS.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={editIsDelight}
                    onChange={(e) => setEditIsDelight(e.target.checked)}
                    className="rounded text-blue-600 focus:ring-blue-500"
                  />
                  <span>Counts as Customer Delight (NPS Promoter)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={editIsTrigger}
                    onChange={(e) => setEditIsTrigger(e.target.checked)}
                    className="rounded text-red-600 focus:ring-red-500"
                  />
                  <span>Automatically open Complaint ticket on this score</span>
                </label>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingBand(null)}
                  className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEdit}
                  className="px-5 py-2 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 transition shadow-sm"
                >
                  {savingEdit ? 'Saving...' : 'Save Band Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

