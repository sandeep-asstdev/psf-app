/**
 * ============================================================================
 * FILE PURPOSE: Interactive Call Console & Customer Dossier Dialer Modal.
 * The primary caller interface: opens when a CRE clicks 'Call' on a line item.
 * Displays complete customer vehicle snapshot, repair invoice details, brand-specific survey questions,
 * sentiment selectors (Delight, Satisfied, Dissatisfied), VOC notes, and one-click complaint escalation.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches full customer dossier from `GET /api/v1/psf/console/{queue_id}`.
 * - Renders dynamic OEM survey questions (Hyundai 4-Q, Tata 7-Q, MG 5-Q).
 * - Allows setting call outcome (Connected, Not Connected, Busy, Callback Requested).
 * - Submits call log to `POST /api/v1/psf/calls/submit`.
 * - Supports 'Save & Next' to immediately advance to the next assigned customer without closing the dialer.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Submit button disabled
 *   -> Cause: Mandatory call outcome (e.g. Connected / Not Connected) or survey rating was not selected.
 *   -> What should you do: Select a call status outcome button before submitting.
 * - Error: Call submission fails with error toast
 *   -> Cause: Validation error on the submission payload.
 *   -> What should you do: Inspect DevTools network tab to see which field was missing or invalid.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  X,
  Phone,
  MessageSquare,
  Clock,
  Car,
  User,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Eye,
  EyeOff,
  Star,
  Sparkles,
  History,
  Send,
  ArrowRight,
  Play,
  Pause,
  RotateCcw,
  ShieldAlert,
  Copy,
  Save,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export function formatIndianCurrency(val) {
  if (val === null || val === undefined || isNaN(val)) return '₹ 0';
  return `₹ ${Number(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export function formatIndianDate(dateStr) {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return dateStr;
  }
}

export default function CallConsoleModal({ queueId, isOpen, onClose, onQueueUpdated }) {
  const [loading, setLoading] = useState(true);
  const [consoleData, setConsoleData] = useState(null);
  const [currentQueueId, setCurrentQueueId] = useState(queueId);

  // Phone reveal toggle
  const [showFullPhone, setShowFullPhone] = useState(false);

  // Call timer state
  const [callDuration, setCallDuration] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(true);

  // Call Disposition
  const [callStatus, setCallStatus] = useState('Connected');
  const [caseStatus, setCaseStatus] = useState('Satisfied');
  const [vocText, setVocText] = useState('');

  // Dynamic Questionnaire Answers
  const [surveyAnswers, setSurveyAnswers] = useState({});

  // Complaint Escalation
  const [hasComplaint, setHasComplaint] = useState(false);
  const [complaintSeverity, setComplaintSeverity] = useState('HIGH');
  const [complaintDesc, setComplaintDesc] = useState('');
  const [complaintCategories, setComplaintCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState('');

  // Callback / Reminder
  const [callbackAt, setCallbackAt] = useState('');
  const [callbackNote, setCallbackNote] = useState('');

  // Draft restoration
  const [isDraftRestored, setIsDraftRestored] = useState(false);

  // Submitting state
  const [submitting, setSubmitting] = useState(false);

  // Sync currentQueueId when prop changes
  useEffect(() => {
    if (queueId) setCurrentQueueId(queueId);
  }, [queueId]);

  // Load console details when currentQueueId changes
  useEffect(() => {
    if (isOpen && currentQueueId) {
      loadConsoleDetails(currentQueueId);
      setCallDuration(0);
      setIsTimerRunning(true);
      setShowFullPhone(false);
      setHasComplaint(false);
      setComplaintDesc('');
      setVocText('');
      setCallbackAt('');
      setCallStatus('Connected');
      setCaseStatus('Satisfied');
      setIsDraftRestored(false);
    }
  }, [isOpen, currentQueueId]);

  // Timer interval
  useEffect(() => {
    let interval = null;
    if (isTimerRunning && isOpen) {
      interval = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isTimerRunning, isOpen]);

  // Auto-save draft to localStorage
  useEffect(() => {
    if (!isOpen || !currentQueueId || loading) return;
    const draft = {
      surveyAnswers,
      vocText,
      callStatus,
      caseStatus,
      hasComplaint,
      complaintDesc,
      complaintSeverity,
      selectedCategoryId,
      callbackAt,
      callbackNote,
      updatedAt: Date.now(),
    };
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(`psf_call_draft_${currentQueueId}`, JSON.stringify(draft));
      } catch (e) {
        // quota or private mode fallback
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [
    isOpen,
    currentQueueId,
    loading,
    surveyAnswers,
    vocText,
    callStatus,
    caseStatus,
    hasComplaint,
    complaintDesc,
    complaintSeverity,
    selectedCategoryId,
    callbackAt,
    callbackNote,
  ]);

  // Keyboard shortcuts (Ctrl+Enter / Alt+S: Save & Next, Alt+P: Timer, Esc: Close)
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (((e.ctrlKey || e.metaKey) && e.key === 'Enter') || (e.altKey && (e.key === 's' || e.key === 'S' || e.key === 'n' || e.key === 'N'))) {
        e.preventDefault();
        handleSubmitCall(true);
      } else if (e.altKey && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault();
        setIsTimerRunning((prev) => !prev);
      } else if (e.key === 'Escape' && !submitting) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, submitting, consoleData, callStatus, caseStatus, vocText, surveyAnswers, hasComplaint, complaintDesc]);

  const loadConsoleDetails = async (qId) => {
    try {
      setLoading(true);
      const [consoleRes, catRes] = await Promise.all([
        api.get(`/psf/console/${qId}`),
        api.get('/masters/complaint-categories'),
      ]);

      setConsoleData(consoleRes.data);
      setComplaintCategories(catRes.data);
      if (catRes.data.length > 0) {
        setSelectedCategoryId(catRes.data[0].id);
      }

      // Initialize questionnaire answers with defaults
      const initial = {};
      (consoleRes.data.questionnaire?.questions || []).forEach((q) => {
        if (q.type === 'rating_5') initial[q.key] = 5;
        else if (q.type === 'nps_10') initial[q.key] = 10;
        else if (['yes_no', 'yes_no_na'].includes(q.type)) initial[q.key] = 'yes';
        else initial[q.key] = '';
      });

      // Restore from draft if available
      try {
        const savedDraft = localStorage.getItem(`psf_call_draft_${qId}`);
        if (savedDraft) {
          const parsed = JSON.parse(savedDraft);
          if (parsed.surveyAnswers && Object.keys(parsed.surveyAnswers).length > 0) {
            setSurveyAnswers({ ...initial, ...parsed.surveyAnswers });
          } else {
            setSurveyAnswers(initial);
          }
          if (parsed.vocText) setVocText(parsed.vocText);
          if (parsed.callStatus) setCallStatus(parsed.callStatus);
          if (parsed.caseStatus) setCaseStatus(parsed.caseStatus);
          if (parsed.hasComplaint !== undefined) setHasComplaint(parsed.hasComplaint);
          if (parsed.complaintDesc) setComplaintDesc(parsed.complaintDesc);
          if (parsed.callbackAt) setCallbackAt(parsed.callbackAt);
          if (parsed.callbackNote) setCallbackNote(parsed.callbackNote);
          setIsDraftRestored(true);
        } else {
          setSurveyAnswers(initial);
        }
      } catch {
        setSurveyAnswers(initial);
      }
    } catch (err) {
      toast.error('Failed to load call console details: ' + (err.response?.data?.detail || err.message));
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleDiscardDraft = () => {
    try {
      localStorage.removeItem(`psf_call_draft_${currentQueueId}`);
    } catch {}
    setIsDraftRestored(false);
    const initial = {};
    (consoleData?.questionnaire?.questions || []).forEach((q) => {
      if (q.type === 'rating_5') initial[q.key] = 5;
      else if (q.type === 'nps_10') initial[q.key] = 10;
      else if (['yes_no', 'yes_no_na'].includes(q.type)) initial[q.key] = 'yes';
      else initial[q.key] = '';
    });
    setSurveyAnswers(initial);
    setVocText('');
    setHasComplaint(false);
    setComplaintDesc('');
    toast.success('Draft discarded');
  };

  const setQuickCallback = (hours) => {
    const d = new Date();
    d.setTime(d.getTime() + hours * 3600 * 1000);
    const pad = (n) => String(n).padStart(2, '0');
    setCallbackAt(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
  };

  const setCallbackNextDay = (hour) => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(hour, 0, 0, 0);
    const pad = (n) => String(n).padStart(2, '0');
    setCallbackAt(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
  };

  // Format timer MM:SS
  const formattedDuration = useMemo(() => {
    const mins = Math.floor(callDuration / 60);
    const secs = callDuration % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, [callDuration]);

  // Conditional question visibility logic
  const isQuestionVisible = (q) => {
    if (!q.show_if || !q.show_if.field) return true;
    const condVal = surveyAnswers[q.show_if.field];
    const targetVal = q.show_if.value;
    const op = q.show_if.operator || '==';

    if (condVal === undefined || condVal === null || condVal === '') return false;

    if (op === '<=') return Number(condVal) <= Number(targetVal);
    if (op === '>=') return Number(condVal) >= Number(targetVal);
    if (op === '<') return Number(condVal) < Number(targetVal);
    if (op === '>') return Number(condVal) > Number(targetVal);
    if (op === '!=') return String(condVal) !== String(targetVal);
    return String(condVal).toLowerCase() === String(targetVal).toLowerCase();
  };

  // Real-time calculated CSAT & NPS
  const liveScores = useMemo(() => {
    if (!consoleData?.questionnaire?.questions) return { csat: null, nps: null, npsCat: null };

    let totalWeightedScore = 0;
    let totalWeight = 0;
    let npsRating = null;

    consoleData.questionnaire.questions.forEach((q) => {
      if (!isQuestionVisible(q)) return;
      const val = surveyAnswers[q.key];
      if (val === undefined || val === null || val === '') return;

      const weight = parseFloat(q.weight) || 1.0;

      if (q.type === 'nps_10') {
        const score = parseInt(val, 10);
        if (!isNaN(score)) {
          npsRating = score;
          totalWeightedScore += score * 10 * weight;
          totalWeight += weight;
        }
      } else if (q.type === 'rating_5') {
        const score = parseInt(val, 10);
        if (!isNaN(score)) {
          totalWeightedScore += score * 20 * weight;
          totalWeight += weight;
        }
      } else if (['yes_no', 'yes_no_na'].includes(q.type)) {
        if (String(val).toLowerCase() === 'yes') {
          totalWeightedScore += 100 * weight;
          totalWeight += weight;
        }
      }
    });

    const csat = totalWeight > 0 ? (totalWeightedScore / totalWeight).toFixed(0) : null;
    let npsCat = null;
    if (npsRating !== null) {
      if (npsRating >= 9) npsCat = 'PROMOTER';
      else if (npsRating >= 7) npsCat = 'PASSIVE';
      else npsCat = 'DETRACTOR';
    }

    return { csat, nps: npsRating, npsCat };
  }, [consoleData, surveyAnswers]);

  // Handle Form Submission
  const handleSubmitCall = async (saveAndNext = false) => {
    if (!callStatus) {
      toast.error('Please select call status');
      return;
    }

    if (hasComplaint && !complaintDesc.trim()) {
      toast.error('Please enter complaint details or description');
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        followup_queue_id: currentQueueId,
        call_status: callStatus,
        case_status: caseStatus,
        duration_seconds: callDuration,
        voc: vocText.trim() || null,
        survey_answers: callStatus === 'Connected' ? surveyAnswers : null,
        has_complaint: hasComplaint,
        complaint_category_id: hasComplaint ? selectedCategoryId : null,
        complaint_severity: hasComplaint ? complaintSeverity : null,
        complaint_description: hasComplaint ? complaintDesc.trim() : null,
        callback_at: (callStatus === 'Callback Requested' || caseStatus === 'Follow-up Required')
          ? (callbackAt ? new Date(callbackAt).toISOString() : new Date(Date.now() + 24 * 3600 * 1000).toISOString())
          : null,
        callback_note: callbackNote.trim() || null,
      };

      const res = await api.post('/psf/calls/submit', payload);

      try {
        localStorage.removeItem(`psf_call_draft_${currentQueueId}`);
      } catch {}

      if (res.data.complaint_ticket_no) {
        toast.success(`Complaint registered: Ticket ${res.data.complaint_ticket_no}`, { icon: '🚨' });
      } else {
        toast.success('Call feedback recorded successfully!');
      }

      if (onQueueUpdated) onQueueUpdated();

      if (saveAndNext && res.data.next_queue_id) {
        toast('Loading next customer in queue...', { icon: '⏩' });
        setCurrentQueueId(res.data.next_queue_id);
      } else {
        onClose();
      }
    } catch (err) {
      toast.error('Failed to save call: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const cust = consoleData?.customer;
  const veh = consoleData?.vehicle;
  const jc = consoleData?.job_card;
  const qList = consoleData?.questionnaire?.questions || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-2 sm:p-4">
      <div className="relative w-full max-w-7xl h-[94vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
        {/* TOP STATUS BAR */}
        <div className="h-14 border-b border-slate-200 dark:border-slate-800 px-5 flex items-center justify-between bg-slate-50 dark:bg-slate-900 shrink-0">
          <div className="flex items-center gap-3">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: jc?.brand_color || '#2563EB' }}
            ></span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900 dark:text-white">
                {jc?.brand_name} PSF Console
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 font-semibold uppercase">
                {consoleData?.queue?.queue_type || 'PSF'}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                RO: {jc?.job_card_no}
              </span>
            </div>
            {isDraftRestored && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-800 text-[11px] font-semibold text-amber-800 dark:text-amber-300">
                <Save className="h-3 w-3 text-amber-600" />
                <span>Draft auto-restored</span>
                <button
                  type="button"
                  onClick={handleDiscardDraft}
                  className="ml-1 text-red-600 hover:underline"
                >
                  Discard
                </button>
              </div>
            )}
          </div>

          {/* Center Call Timer */}
          <div className="flex items-center gap-3 bg-white dark:bg-slate-800 px-4 py-1.5 rounded-full border border-slate-200 dark:border-slate-700 shadow-sm">
            <Clock className={`h-4 w-4 ${isTimerRunning ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
            <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">
              {formattedDuration}
            </span>
            <button
              type="button"
              onClick={() => setIsTimerRunning(!isTimerRunning)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              title={isTimerRunning ? 'Pause Timer (Alt+P)' : 'Resume Timer (Alt+P)'}
            >
              {isTimerRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 text-emerald-500" />}
            </button>
            <button
              type="button"
              onClick={() => setCallDuration(0)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              title="Reset Timer"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          </div>

          {/* Right Action & Close */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">
              Attempt: <strong>{(consoleData?.queue?.attempts || 0) + 1}</strong> of 3
            </span>
            <button
              onClick={onClose}
              title="Close (Esc)"
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* MAIN BODY: SPLIT 2-COLUMN LAYOUT */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
          {/* ========================================================
              LEFT COLUMN: CUSTOMER & VEHICLE DOSSIER (40% / 5 cols)
              ======================================================== */}
          <div className="lg:col-span-5 border-r border-slate-200 dark:border-slate-800 p-5 overflow-y-auto space-y-4 bg-slate-50/50 dark:bg-slate-900/50">
            {loading ? (
              <div className="py-20 text-center text-xs text-slate-500">
                Loading customer profile...
              </div>
            ) : (
              <>
                {/* 1. Customer Card with One-Click Call */}
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center font-bold text-sm">
                        {cust?.name ? cust.name.slice(0, 2).toUpperCase() : 'CU'}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          {cust?.name}
                          {cust?.dnd && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-100 text-red-700 font-bold">
                              DND
                            </span>
                          )}
                        </h3>
                        <p className="text-xs text-slate-400">{cust?.city || 'Workshop City'}</p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => setShowFullPhone(!showFullPhone)}
                      className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                      title={showFullPhone ? 'Hide Number' : 'Reveal Contact Number'}
                    >
                      {showFullPhone ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4 text-blue-600" />}
                    </button>
                  </div>

                  {/* Phone Number Display & Quick Actions */}
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2">
                      <div className="font-mono text-xs font-semibold text-slate-900 dark:text-white">
                        {showFullPhone ? cust?.phone_raw : cust?.phone_masked}
                      </div>
                      {cust?.phone_raw && (
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard?.writeText(cust.phone_raw);
                            toast.success(`Copied: ${cust.phone_raw}`);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                          title="Copy phone number"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {cust?.phone_raw && (
                        <a
                          href={`tel:${cust.phone_raw}`}
                          onClick={() => {
                            setIsTimerRunning(true);
                            navigator.clipboard?.writeText(cust.phone_raw);
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition"
                          title="Click to Call (+ Copy)"
                        >
                          <Phone className="h-3 w-3" />
                          Call
                        </a>
                      )}
                      {cust?.phone_raw && (
                        <a
                          href={`https://wa.me/91${cust.phone_raw}?text=Dear%20${encodeURIComponent(cust.name || 'Customer')},%20greetings%20from%20${encodeURIComponent(jc?.brand_name || 'dealership')}.`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-green-600 hover:bg-green-700 text-white text-xs font-semibold shadow-sm transition"
                          title="Open WhatsApp Greeting"
                        >
                          <MessageSquare className="h-3 w-3" />
                          WhatsApp
                        </a>
                      )}
                    </div>
                  </div>

                  {cust?.alt_phone_raw && (
                    <div className="text-xs text-slate-400 flex items-center justify-between">
                      <span>Alt Phone: <span className="font-mono text-slate-600 dark:text-slate-300">{cust.alt_phone_raw}</span></span>
                      <a
                        href={`tel:${cust.alt_phone_raw}`}
                        className="text-[11px] text-blue-600 hover:underline font-semibold"
                      >
                        Call Alt
                      </a>
                    </div>
                  )}
                </div>

                {/* 2. Vehicle & Service Card */}
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                    <div className="flex items-center gap-2">
                      <Car className="h-4 w-4 text-blue-600" />
                      <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                        {veh?.model}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                      {veh?.reg_no}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-slate-400">VIN:</span>
                      <div className="font-mono text-[11px] text-slate-700 dark:text-slate-300 truncate">
                        {veh?.vin}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">Total Invoice:</span>
                      <div className="font-bold text-blue-600 text-sm">
                        {formatIndianCurrency(jc?.total_amount)}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">Advisor:</span>
                      <div className="font-medium text-slate-800 dark:text-slate-200">
                        {jc?.service_advisor}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">RO Date:</span>
                      <div className="font-medium text-slate-800 dark:text-slate-200">
                        {formatIndianDate(jc?.job_card_date)}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">Technician:</span>
                      <div className="font-medium text-slate-800 dark:text-slate-200">
                        {jc?.technician || 'General Tech'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400">Service Type:</span>
                      <div className="text-slate-700 dark:text-slate-300 font-medium">
                        {jc?.service_type}
                      </div>
                    </div>
                    <div className="col-span-2">
                      <span className="text-slate-400">Workshop Branch:</span>
                      <div className="text-slate-700 dark:text-slate-300 font-medium">
                        {jc?.branch_name}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Previous Call History Timeline */}
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5 text-blue-600" />
                    Previous Call History ({(consoleData?.call_history || []).length})
                  </h4>

                  {(consoleData?.call_history || []).length === 0 ? (
                    <div className="py-3 text-center text-xs text-slate-400">
                      No previous calls recorded for this job card. First call attempt.
                    </div>
                  ) : (
                    <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1">
                      {consoleData.call_history.map((hist) => (
                        <div
                          key={hist.id}
                          className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-1"
                        >
                          <div className="flex justify-between items-center">
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {hist.call_status} ({hist.duration_seconds}s)
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {formatIndianDate(hist.called_at)}
                            </span>
                          </div>
                          {hist.voc && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 italic">
                              "{hist.voc}"
                            </p>
                          )}
                          <div className="text-[10px] text-slate-400">
                            Caller: {hist.called_by}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* ========================================================
              RIGHT COLUMN: DYNAMIC SCRIPT & ACTIONS (60% / 7 cols)
              ======================================================== */}
          <div className="lg:col-span-7 p-5 overflow-y-auto space-y-5 bg-white dark:bg-slate-900">
            {/* Disposition Controls Bar */}
            <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              <div>
                <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">
                  Call Connect Status *
                </label>
                <select
                  value={callStatus}
                  onChange={(e) => {
                    const newStatus = e.target.value;
                    setCallStatus(newStatus);
                    if (['Not Connected', 'Busy', 'Switched Off', 'Wrong Number'].includes(newStatus)) {
                      setCaseStatus('No Response');
                    } else if (newStatus === 'Callback Requested') {
                      setCaseStatus('Follow-up Required');
                      if (!callbackAt) {
                        const d = new Date();
                        d.setDate(d.getDate() + 1);
                        d.setHours(10, 0, 0, 0);
                        const pad = (n) => String(n).padStart(2, '0');
                        setCallbackAt(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
                      }
                    } else if (newStatus === 'Connected' && caseStatus === 'No Response') {
                      setCaseStatus('Satisfied');
                    }
                  }}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-900 dark:text-white"
                >
                  <option value="Connected">Connected (Customer Spoke)</option>
                  <option value="Not Connected">Not Connected / Ringing</option>
                  <option value="Busy">Line Busy</option>
                  <option value="Switched Off">Switched Off / Out of Reach</option>
                  <option value="Wrong Number">Wrong Number</option>
                  <option value="Callback Requested">Callback Requested</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">
                  Overall Case Disposition
                </label>
                <select
                  value={caseStatus}
                  onChange={(e) => setCaseStatus(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-900 dark:text-white"
                >
                  <option value="Satisfied">Satisfied (Positive Experience)</option>
                  <option value="Delight">Delight (Exceeded Expectations)</option>
                  <option value="No Response">No Response / Unreachable</option>
                  <option value="Follow-up Required">Follow-up Required / Callback</option>
                  <option value="Dissatisfied">Dissatisfied / Concern</option>
                  <option value="Complaint Registered">Complaint Registered</option>
                  <option value="Closed">Closed</option>
                </select>
              </div>
            </div>

            {/* Callback Datetime Picker if Callback Requested */}
            {callStatus === 'Callback Requested' && (
              <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                    <Calendar className="h-4 w-4" />
                    Schedule Customer Callback Reminder
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setQuickCallback(2)}
                      className="px-2 py-0.5 rounded bg-amber-100 hover:bg-amber-200 dark:bg-amber-800/40 text-[10px] font-semibold text-amber-900 dark:text-amber-200 transition"
                    >
                      +2 Hours
                    </button>
                    <button
                      type="button"
                      onClick={() => setCallbackNextDay(10)}
                      className="px-2 py-0.5 rounded bg-amber-100 hover:bg-amber-200 dark:bg-amber-800/40 text-[10px] font-semibold text-amber-900 dark:text-amber-200 transition"
                    >
                      Tmrw 10 AM
                    </button>
                    <button
                      type="button"
                      onClick={() => setCallbackNextDay(15)}
                      className="px-2 py-0.5 rounded bg-amber-100 hover:bg-amber-200 dark:bg-amber-800/40 text-[10px] font-semibold text-amber-900 dark:text-amber-200 transition"
                    >
                      Tmrw 3 PM
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-amber-700 dark:text-amber-300 mb-0.5">
                      Callback Date & Time *
                    </label>
                    <input
                      type="datetime-local"
                      value={callbackAt}
                      onChange={(e) => setCallbackAt(e.target.value)}
                      className="w-full rounded border border-amber-300 dark:border-amber-700 bg-white dark:bg-slate-800 p-1.5 text-xs text-slate-900 dark:text-white"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-amber-700 dark:text-amber-300 mb-0.5">
                      Callback Note
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Call after 4 PM when customer is free"
                      value={callbackNote}
                      onChange={(e) => setCallbackNote(e.target.value)}
                      className="w-full rounded border border-amber-300 dark:border-amber-700 bg-white dark:bg-slate-800 p-1.5 text-xs text-slate-900 dark:text-white"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* DYNAMIC QUESTIONNAIRE SECTION (Only if Connected) */}
            {callStatus === 'Connected' && (
              <div className="space-y-4">
                <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-blue-600" />
                    Dynamic Calling Questionnaire ({qList.length} questions)
                  </h3>

                  {/* Live CSAT & NPS Badges */}
                  <div className="flex items-center gap-2">
                    {liveScores.csat !== null && (
                      <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                        CSAT: {liveScores.csat}%
                      </span>
                    )}
                    {liveScores.npsCat && (
                      <span
                        className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                          liveScores.npsCat === 'PROMOTER'
                            ? 'bg-emerald-100 text-emerald-800'
                            : liveScores.npsCat === 'PASSIVE'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {liveScores.npsCat} ({liveScores.nps})
                      </span>
                    )}
                  </div>
                </div>

                {/* Render Questions */}
                <div className="space-y-4 max-h-[42vh] overflow-y-auto pr-2">
                  {qList.map((q, idx) => {
                    if (!isQuestionVisible(q)) return null;

                    return (
                      <div
                        key={q.id}
                        className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 space-y-2 hover:border-blue-400 transition"
                      >
                        <div className="flex justify-between items-start">
                          <label className="text-xs font-semibold text-slate-900 dark:text-white leading-relaxed">
                            <span className="text-slate-400 mr-1.5">{idx + 1}.</span>
                            {q.label}
                            {q.is_required && <span className="text-red-500 ml-1 font-bold">*</span>}
                          </label>
                          <span className="text-[10px] text-slate-400 uppercase font-medium">
                            {q.section}
                          </span>
                        </div>

                        {/* Question Inputs */}
                        {/* 1. 5-STAR RATING */}
                        {q.type === 'rating_5' && (
                          <div className="flex items-center gap-2 pt-1">
                            {[1, 2, 3, 4, 5].map((val) => {
                              const isSelected = surveyAnswers[q.key] === val;
                              return (
                                <button
                                  key={val}
                                  type="button"
                                  onClick={() =>
                                    setSurveyAnswers((prev) => ({ ...prev, [q.key]: val }))
                                  }
                                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                                    isSelected
                                      ? 'bg-amber-500 text-white border-amber-600 shadow-sm'
                                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'
                                  }`}
                                >
                                  <Star className={`h-3.5 w-3.5 ${isSelected ? 'fill-white' : ''}`} />
                                  <span>{val}</span>
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {/* 2. 0-10 NPS SCALE */}
                        {q.type === 'nps_10' && (
                          <div className="space-y-1 pt-1">
                            <div className="flex flex-wrap gap-1.5">
                              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((val) => {
                                const isSelected = surveyAnswers[q.key] === val;
                                const isDetractor = val <= 6;
                                const isPassive = val === 7 || val === 8;
                                const isPromoter = val >= 9;

                                return (
                                  <button
                                    key={val}
                                    type="button"
                                    onClick={() =>
                                      setSurveyAnswers((prev) => ({ ...prev, [q.key]: val }))
                                    }
                                    className={`w-7 h-7 rounded text-xs font-bold border transition ${
                                      isSelected
                                        ? isPromoter
                                          ? 'bg-emerald-600 text-white border-emerald-700 ring-2 ring-emerald-400'
                                          : isPassive
                                          ? 'bg-amber-500 text-white border-amber-600 ring-2 ring-amber-400'
                                          : 'bg-red-600 text-white border-red-700 ring-2 ring-red-400'
                                        : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'
                                    }`}
                                  >
                                    {val}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* 3. YES / NO / NA */}
                        {['yes_no', 'yes_no_na'].includes(q.type) && (
                          <div className="flex items-center gap-2 pt-1">
                            {['yes', 'no', ...(q.type === 'yes_no_na' ? ['na'] : [])].map((choice) => {
                              const isSelected = surveyAnswers[q.key] === choice;
                              return (
                                <button
                                  key={choice}
                                  type="button"
                                  onClick={() =>
                                    setSurveyAnswers((prev) => ({ ...prev, [q.key]: choice }))
                                  }
                                  className={`px-3.5 py-1 rounded-lg text-xs font-semibold uppercase border transition ${
                                    isSelected
                                      ? choice === 'yes'
                                        ? 'bg-emerald-600 text-white border-emerald-700'
                                        : choice === 'no'
                                        ? 'bg-red-600 text-white border-red-700'
                                        : 'bg-slate-600 text-white border-slate-700'
                                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'
                                  }`}
                                >
                                  {choice === 'na' ? 'N/A' : choice}
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {/* 4. TEXT / REMARKS */}
                        {['text', 'textarea'].includes(q.type) && (
                          <textarea
                            rows={2}
                            value={surveyAnswers[q.key] || ''}
                            onChange={(e) =>
                              setSurveyAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))
                            }
                            placeholder="Customer remarks..."
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Voice of Customer (VOC) */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-800 dark:text-slate-200">
                Voice of Customer (VOC Remarks)
              </label>
              <textarea
                rows={2}
                value={vocText}
                onChange={(e) => setVocText(e.target.value)}
                placeholder="Enter customer exact feedback, praise, or concerns expressed during the call..."
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-xs text-slate-900 dark:text-white"
              />
            </div>

            {/* COMPLAINT REGISTRATION TOGGLE */}
            <div className="p-3.5 rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/20 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="hasComplaintChk"
                    checked={hasComplaint}
                    onChange={(e) => setHasComplaint(e.target.checked)}
                    className="h-4 w-4 rounded text-red-600 focus:ring-red-500"
                  />
                  <label htmlFor="hasComplaintChk" className="text-xs font-bold text-red-900 dark:text-red-300 cursor-pointer">
                    Escalate & Register Formal Customer Complaint
                  </label>
                </div>
                {hasComplaint && (
                  <span className="text-[10px] uppercase font-bold text-red-600 bg-red-100 dark:bg-red-900/60 px-2 py-0.5 rounded">
                    SLA Timer Triggers Automatically
                  </span>
                )}
              </div>

              {hasComplaint && (
                <div className="space-y-3 pt-2 border-t border-red-200 dark:border-red-900/40">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-red-900 dark:text-red-300 mb-1">
                        Complaint Category *
                      </label>
                      <select
                        value={selectedCategoryId}
                        onChange={(e) => setSelectedCategoryId(e.target.value)}
                        className="w-full rounded-lg border border-red-300 dark:border-red-800 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                      >
                        {complaintCategories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} ({c.default_sla_hours}h SLA)
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-red-900 dark:text-red-300 mb-1">
                        Severity *
                      </label>
                      <select
                        value={complaintSeverity}
                        onChange={(e) => setComplaintSeverity(e.target.value)}
                        className="w-full rounded-lg border border-red-300 dark:border-red-800 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white font-semibold"
                      >
                        <option value="HIGH">HIGH (Urgent Resolution)</option>
                        <option value="MEDIUM">MEDIUM (Standard SLA)</option>
                        <option value="LOW">LOW (Observation / Minor)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-red-900 dark:text-red-300 mb-1">
                      Issue Description / Workmanship Defect *
                    </label>
                    <textarea
                      rows={2}
                      value={complaintDesc}
                      onChange={(e) => setComplaintDesc(e.target.value)}
                      placeholder="Specify the exact issue reported (e.g. A/C cooling inadequate after repair, bill amount higher than estimate)..."
                      className="w-full rounded-lg border border-red-300 dark:border-red-800 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                      required
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM ACTION BAR */}
        <div className="h-16 border-t border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between bg-slate-50 dark:bg-slate-900 shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="font-semibold text-slate-500">Shortcuts:</span>
            <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 font-bold">Ctrl+Enter</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 font-bold">Alt+S</kbd> Save & Next
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 font-bold">Alt+P</kbd> Timer
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 font-bold">Esc</kbd> Close
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 hover:bg-slate-200 transition"
            >
              Cancel / Close
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSubmitCall(false)}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-white hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 transition"
            >
              {submitting ? 'Saving...' : 'Save & Close'}
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSubmitCall(true)}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold bg-blue-600 text-white hover:bg-blue-700 shadow-md transition disabled:opacity-50"
            >
              {submitting ? (
                'Saving...'
              ) : (
                <>
                  Save & Next Customer
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

