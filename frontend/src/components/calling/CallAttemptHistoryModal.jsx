/**
 * ============================================================================
 * FILE PURPOSE: Call Attempt History Modal Popup.
 * Displays the chronological audit trail of all previous phone call attempts made to a customer,
 * including timestamps, who called, call outcomes (Connected, Busy, Switched Off), and past VOC feedback.
 * 
 * KEY RESPONSIBILITIES:
 * - Displays past calling attempts for a specific follow-up queue item.
 * - Shows caller name, date/time, customer rating, and recorded remarks.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Modal opens empty
 *   -> Cause: No previous attempts have been made on this queue item (first attempt).
 *   -> What should you do: The modal displays 'No previous call attempts recorded' in this scenario.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  X,
  History,
  PhoneCall,
  CheckCircle,
  AlertCircle,
  Clock,
  User,
  Star,
  MessageSquare,
  FileText,
  RefreshCw,
} from 'lucide-react';
import api from '../../services/api';

export default function CallAttemptHistoryModal({
  isOpen,
  onClose,
  queueId,
  jobCardId,
  jobCardNo = '',
  customerName = '',
  vehicleRegNo = '',
}) {
  const [loading, setLoading] = useState(false);
  const [attempts, setAttempts] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && (queueId || jobCardId)) {
      fetchAttempts();
    } else {
      setAttempts([]);
      setError(null);
    }
  }, [isOpen, queueId, jobCardId]);

  const fetchAttempts = async () => {
    try {
      setLoading(true);
      setError(null);
      const url = queueId
        ? `/psf/queues/${queueId}/attempts`
        : `/psf/job-cards/${jobCardId}/attempts`;
      const res = await api.get(url);
      setAttempts(res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load attempt history');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                Call Attempt History
              </h3>
              <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {jobCardNo && (
                  <span className="font-semibold text-blue-600 dark:text-blue-400">
                    JC: {jobCardNo}
                  </span>
                )}
                {vehicleRegNo && <span>• {vehicleRegNo}</span>}
                {customerName && <span>• {customerName}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={fetchAttempts}
              title="Refresh"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
              <p className="text-sm">Loading call attempt logs...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div className="text-sm text-red-700 dark:text-red-300">{error}</div>
            </div>
          ) : attempts.length === 0 ? (
            <div className="py-12 text-center text-slate-400 space-y-2">
              <PhoneCall className="h-10 w-10 mx-auto text-slate-300 dark:text-slate-600" />
              <p className="text-sm font-medium">No call attempts recorded yet.</p>
              <p className="text-xs text-slate-400">
                Any attempted or connected calls made via the call console will be logged here.
              </p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-700">
              {attempts.map((att, idx) => {
                const isConnected = att.call_status === 'Connected';
                return (
                  <div key={att.id || idx} className="relative group">
                    {/* Timeline Node */}
                    <div
                      className={`absolute -left-[27px] top-1 h-5 w-5 rounded-full border-2 flex items-center justify-center text-[10px] font-bold ${
                        isConnected
                          ? 'border-emerald-500 bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'border-amber-500 bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                      }`}
                    >
                      {att.attempt_number || idx + 1}
                    </div>

                    {/* Attempt Card */}
                    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/60 p-4 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition">
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100 dark:border-slate-700/50">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              isConnected
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                            }`}
                          >
                            {att.call_status}
                          </span>
                          {att.case_status && (
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                              {att.case_status}
                            </span>
                          )}
                          {att.rating !== null && att.rating !== undefined && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                              <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                              {att.rating}/10
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <Clock className="h-3.5 w-3.5" />
                          <span>
                            {att.called_at
                              ? new Date(att.called_at).toLocaleString('en-IN', {
                                  day: '2-digit',
                                  month: 'short',
                                  year: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : 'N/A'}
                          </span>
                          {att.duration_seconds ? (
                            <span>({att.duration_seconds}s)</span>
                          ) : null}
                        </div>
                      </div>

                      {/* Caller info & VOC */}
                      <div className="mt-3 space-y-2 text-xs">
                        {att.called_by_name && (
                          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                            <User className="h-3.5 w-3.5 text-slate-400" />
                            <span>Caller: <strong>{att.called_by_name}</strong></span>
                          </div>
                        )}

                        {att.voc ? (
                          <div className="rounded-lg bg-slate-50 dark:bg-slate-900/70 p-3 border border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-300 flex items-start gap-2">
                            <MessageSquare className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5" />
                            <div className="space-y-0.5">
                              <span className="font-semibold text-slate-500 dark:text-slate-400 block text-[11px]">
                                Voice of Customer (VOC):
                              </span>
                              <p className="italic">{att.voc}</p>
                            </div>
                          </div>
                        ) : (
                          <p className="text-slate-400 italic">No customer feedback remarks logged.</p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 flex items-center justify-between text-xs text-slate-500">
          <span>Total attempts recorded: <strong>{attempts.length}</strong></span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-semibold transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}

