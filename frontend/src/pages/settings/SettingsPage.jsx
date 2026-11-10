/**
 * ============================================================================
 * FILE PURPOSE: Dealership Settings Container Page.
 * Houses tabbed configuration panels for Allocation Rules, Branch Contacts, and OEM Rating Scales.
 * 
 * KEY RESPONSIBILITIES:
 * - Switches between Allocation Rules, Branch Contacts, and Rating Scales tabs.
 * - Restricts tab access according to user permissions.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Allocation Rules tab is missing
 *   -> Cause: CRE Admin (L2) is not permitted to edit allocation rules (Super Admin L1 only).
 *   -> What should you do: Log in as Super Admin (`admin@apexauto.com`) to edit allocation rules.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Sliders,
  FileQuestion,
  Building2,
  AlertTriangle,
  Palette,
  Plus,
  Copy,
  Trash2,
  Eye,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Star,
  RefreshCw,
  Sparkles,
  Save,
  MessageSquare,
  PhoneCall,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import BranchContactsTab from './BranchContactsTab';
import RatingScalesTab from './RatingScalesTab';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('questionnaires');
  const [loading, setLoading] = useState(true);

  // Data states
  const [questionnaires, setQuestionnaires] = useState([]);
  const [brands, setBrands] = useState([]);
  const [branches, setBranches] = useState([]);
  const [complaintCategories, setComplaintCategories] = useState([]);
  const [settings, setSettings] = useState(null);

  // Filters & selection
  const [selectedBrandFilter, setSelectedBrandFilter] = useState('ALL');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState('ALL');
  const [expandedQId, setExpandedQId] = useState(null);
  const [activeQuestionnaireDetail, setActiveQuestionnaireDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Modals & form state
  const [showCreateQModal, setShowCreateQModal] = useState(false);
  const [showAddQuestionModal, setShowAddQuestionModal] = useState(false);
  const [targetQForQuestion, setTargetQForQuestion] = useState(null);

  // Create Questionnaire Form
  const [newQBrandId, setNewQBrandId] = useState('');
  const [newQType, setNewQType] = useState('PSF');
  const [newQTitle, setNewQTitle] = useState('');
  const [createQSubmitting, setCreateQSubmitting] = useState(false);

  // Add Question Form
  const [newQKey, setNewQKey] = useState('');
  const [newQLabel, setNewQLabel] = useState('');
  const [newQFieldType, setNewQFieldType] = useState('rating_5');
  const [newQSection, setNewQSection] = useState('General');
  const [newQWeight, setNewQWeight] = useState('1.0');
  const [newQRequired, setNewQRequired] = useState(false);
  const [newQOptions, setNewQOptions] = useState('');
  const [newQShowIfField, setNewQShowIfField] = useState('');
  const [newQShowIfOperator, setNewQShowIfOperator] = useState('<=');
  const [newQShowIfValue, setNewQShowIfValue] = useState('');
  const [addQuestionSubmitting, setAddQuestionSubmitting] = useState(false);

  // Interactive Previewer State
  const [previewQId, setPreviewQId] = useState('');
  const [previewQuestionnaire, setPreviewQuestionnaire] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewAnswers, setPreviewAnswers] = useState({});

  // Fetch initial master data
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [qRes, brandsRes, branchesRes, catRes, setRes] = await Promise.all([
        api.get('/questionnaires'),
        api.get('/masters/brands'),
        api.get('/masters/branches'),
        api.get('/masters/complaint-categories'),
        api.get('/masters/settings'),
      ]);

      setQuestionnaires(qRes.data);
      setBrands(brandsRes.data);
      setBranches(branchesRes.data);
      setComplaintCategories(catRes.data);
      setSettings(setRes.data);

      if (brandsRes.data.length > 0) {
        setNewQBrandId(brandsRes.data[0].id);
      }
      if (qRes.data.length > 0) {
        setPreviewQId(qRes.data[0].id);
      }
    } catch (err) {
      toast.error('Failed to load configuration masters: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const reloadQuestionnaires = async () => {
    try {
      const res = await api.get('/questionnaires');
      setQuestionnaires(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  // Check if selected brand for new questionnaire is Hyundai
  const selectedNewBrand = useMemo(() => {
    return brands.find((b) => b.id === newQBrandId);
  }, [brands, newQBrandId]);

  const isSelectedBrandHyundai = useMemo(() => {
    if (!selectedNewBrand) return false;
    return (
      selectedNewBrand.name.toUpperCase().includes('HYUNDAI') ||
      ['HYUN', 'HYUNDAI'].includes(selectedNewBrand.code.toUpperCase())
    );
  }, [selectedNewBrand]);

  // Load questionnaire detail for expansion
  const toggleExpand = async (qId) => {
    if (expandedQId === qId) {
      setExpandedQId(null);
      setActiveQuestionnaireDetail(null);
      return;
    }

    try {
      setDetailLoading(true);
      setExpandedQId(qId);
      const res = await api.get(`/questionnaires/${qId}`);
      setActiveQuestionnaireDetail(res.data);
    } catch (err) {
      toast.error('Failed to load questionnaire details: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDetailLoading(false);
    }
  };

  // Load questionnaire for Interactive Previewer
  useEffect(() => {
    if (!previewQId) return;
    loadPreviewQuestionnaire(previewQId);
  }, [previewQId]);

  const loadPreviewQuestionnaire = async (id) => {
    try {
      setPreviewLoading(true);
      const res = await api.get(`/questionnaires/${id}`);
      setPreviewQuestionnaire(res.data);
      // Reset preview answers
      const initial = {};
      (res.data.questions || []).forEach((q) => {
        if (q.type === 'rating_5') initial[q.key] = 5;
        else if (q.type === 'nps_10') initial[q.key] = 10;
        else if (q.type === 'yes_no' || q.type === 'yes_no_na') initial[q.key] = 'yes';
        else initial[q.key] = '';
      });
      setPreviewAnswers(initial);
    } catch (err) {
      toast.error('Failed to load questionnaire for preview: ' + (err.response?.data?.detail || err.message));
    } finally {
      setPreviewLoading(false);
    }
  };

  // Handle Create Questionnaire
  const handleCreateQuestionnaire = async (e) => {
    e.preventDefault();
    if (!newQBrandId) {
      toast.error('Please select a brand');
      return;
    }
    if (!newQTitle.trim()) {
      toast.error('Please enter a title');
      return;
    }

    // OEM Compliance Rule Check: Happiness Calling is strictly for Hyundai
    if (newQType === 'HAPPINESS' && !isSelectedBrandHyundai) {
      toast.error('OEM Compliance Error: Happiness Calling is strictly exclusive to Hyundai brands.');
      return;
    }

    try {
      setCreateQSubmitting(true);
      await api.post('/questionnaires', {
        brand_id: newQBrandId,
        type: newQType,
        title: newQTitle.trim(),
        is_active: true,
      });

      toast.success('Questionnaire template created successfully!');
      setShowCreateQModal(false);
      setNewQTitle('');
      await reloadQuestionnaires();
    } catch (err) {
      toast.error('Failed to create questionnaire: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreateQSubmitting(false);
    }
  };

  // Handle Clone / Version increment
  const handleCloneVersion = async (qId, title, version) => {
    const confirmed = window.confirm(`Clone "${title}" into Version ${version + 1}?`);
    if (!confirmed) return;

    try {
      const res = await api.post(`/questionnaires/${qId}/clone`);
      toast.success(`Created version ${res.data.version} successfully!`);
      await reloadQuestionnaires();
      setExpandedQId(res.data.id);
      setActiveQuestionnaireDetail(res.data);
    } catch (err) {
      toast.error('Failed to clone questionnaire: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Handle Add Question
  const handleOpenAddQuestion = (q) => {
    setTargetQForQuestion(q);
    setNewQKey('');
    setNewQLabel('');
    setNewQFieldType('rating_5');
    setNewQSection('General');
    setNewQWeight('1.0');
    setNewQRequired(false);
    setNewQOptions('');
    setNewQShowIfField('');
    setNewQShowIfOperator('<=');
    setNewQShowIfValue('');
    setShowAddQuestionModal(true);
  };

  const handleSaveQuestion = async (e) => {
    e.preventDefault();
    if (!newQKey.trim() || !newQLabel.trim()) {
      toast.error('Key and Label are required');
      return;
    }

    let parsedOptions = null;
    if (['single_select', 'multi_select'].includes(newQFieldType) && newQOptions.trim()) {
      parsedOptions = newQOptions
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((opt) => ({ label: opt, value: opt.toLowerCase().replace(/\s+/g, '_') }));
    }

    let showIfObj = null;
    if (newQShowIfField.trim() && newQShowIfValue.trim()) {
      showIfObj = {
        field: newQShowIfField.trim(),
        operator: newQShowIfOperator,
        value: isNaN(newQShowIfValue) ? newQShowIfValue.trim() : Number(newQShowIfValue),
      };
    }

    try {
      setAddQuestionSubmitting(true);
      await api.post(`/questionnaires/${targetQForQuestion.id}/questions`, {
        key: newQKey.trim(),
        label: newQLabel.trim(),
        type: newQFieldType,
        section: newQSection.trim() || 'General',
        weight: parseFloat(newQWeight) || 1.0,
        is_required: newQRequired,
        options: parsedOptions,
        show_if: showIfObj,
      });

      toast.success('Question added successfully!');
      setShowAddQuestionModal(false);
      // Refresh current expanded detail
      const res = await api.get(`/questionnaires/${targetQForQuestion.id}`);
      setActiveQuestionnaireDetail(res.data);
      await reloadQuestionnaires();
      if (previewQId === targetQForQuestion.id) {
        loadPreviewQuestionnaire(targetQForQuestion.id);
      }
    } catch (err) {
      toast.error('Failed to add question: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAddQuestionSubmitting(false);
    }
  };

  const handleDeleteQuestion = async (qId, questionId, label) => {
    if (!window.confirm(`Delete question "${label}"?`)) return;
    try {
      await api.delete(`/questionnaires/${qId}/questions/${questionId}`);
      toast.success('Question removed');
      const res = await api.get(`/questionnaires/${qId}`);
      setActiveQuestionnaireDetail(res.data);
      await reloadQuestionnaires();
      if (previewQId === qId) {
        loadPreviewQuestionnaire(qId);
      }
    } catch (err) {
      toast.error('Failed to delete question: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Filtered questionnaires
  const filteredQuestionnaires = useMemo(() => {
    return questionnaires.filter((q) => {
      if (selectedBrandFilter !== 'ALL' && q.brand_id !== selectedBrandFilter) return false;
      if (selectedTypeFilter !== 'ALL' && q.type !== selectedTypeFilter) return false;
      return true;
    });
  }, [questionnaires, selectedBrandFilter, selectedTypeFilter]);

  // Previewer Conditional Evaluation
  const isQuestionVisible = (q) => {
    if (!q.show_if || !q.show_if.field) return true;
    const condVal = previewAnswers[q.show_if.field];
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

  // Previewer Real-time CSAT and NPS calculation
  const previewScores = useMemo(() => {
    if (!previewQuestionnaire || !previewQuestionnaire.questions) {
      return { csat: null, nps: null, npsCategory: null };
    }

    let totalWeightedScore = 0;
    let totalWeight = 0;
    let npsRating = null;

    previewQuestionnaire.questions.forEach((q) => {
      if (!isQuestionVisible(q)) return;
      const val = previewAnswers[q.key];
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
        } else if (String(val).toLowerCase() === 'no') {
          totalWeightedScore += 0;
          totalWeight += weight;
        }
      }
    });

    const csat = totalWeight > 0 ? (totalWeightedScore / totalWeight).toFixed(1) : null;
    let npsCategory = null;
    if (npsRating !== null) {
      if (npsRating >= 9) npsCategory = 'PROMOTER';
      else if (npsRating >= 7) npsCategory = 'PASSIVE';
      else npsCategory = 'DETRACTOR';
    }

    return { csat, nps: npsRating, npsCategory };
  }, [previewQuestionnaire, previewAnswers]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-600" />
          <span>Loading dealership configuration & questionnaire templates...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Title & OEM Rule Alert Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sliders className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            Dealership Settings & Dynamic Questionnaires
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Configure multi-brand survey engines, OEM SLAs, workshop branches, and white-label branding.
          </p>
        </div>

        {/* Hyundai Exclusivity Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300 text-xs font-medium">
          <ShieldAlert className="h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400" />
          <span>OEM Rule: <strong>Happiness Calling</strong> is strictly exclusive to Hyundai brands</span>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="flex space-x-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab('questionnaires')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'questionnaires'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <FileQuestion className="h-4 w-4" />
            Dynamic Questionnaire Builder
            <span className="ml-1 px-2 py-0.5 rounded-full text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              {questionnaires.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('previewer')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'previewer'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Eye className="h-4 w-4" />
            Interactive Questionnaire Previewer
            <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
              Live Test
            </span>
          </button>

          <button
            onClick={() => setActiveTab('brands')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'brands'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Building2 className="h-4 w-4" />
            Brands & Workshops ({brands.length} Brands / {branches.length} Branches)
          </button>

          <button
            onClick={() => setActiveTab('complaints')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'complaints'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            Complaint Categories & SLAs
          </button>

          <button
            onClick={() => setActiveTab('branch_contacts')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'branch_contacts'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <PhoneCall className="h-4 w-4" />
            Branch Contacts
          </button>

          <button
            onClick={() => setActiveTab('rating_scales')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'rating_scales'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Sliders className="h-4 w-4" />
            Rating Scales & Bands
          </button>

          <button
            onClick={() => setActiveTab('branding')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === 'branding'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Palette className="h-4 w-4" />
            White-Label & Templates
          </button>
        </nav>
      </div>

      {/* TAB 1: QUESTIONNAIRE BUILDER */}
      {activeTab === 'questionnaires' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Filter Brand
                </label>
                <select
                  value={selectedBrandFilter}
                  onChange={(e) => setSelectedBrandFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                >
                  <option value="ALL">All Brands ({brands.length})</option>
                  {brands.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Filter Type
                </label>
                <select
                  value={selectedTypeFilter}
                  onChange={(e) => setSelectedTypeFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                >
                  <option value="ALL">All Survey Types</option>
                  <option value="PSF">PSF (Follow-up)</option>
                  <option value="TNPS">TNPS</option>
                  <option value="HAPPINESS">Happiness Calling (Hyundai Only)</option>
                  <option value="RECONFIRMATION">Reconfirmation</option>
                </select>
              </div>
            </div>

            <button
              onClick={() => setShowCreateQModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition"
            >
              <Plus className="h-4 w-4" />
              New Questionnaire Template
            </button>
          </div>

          {/* Questionnaire Cards */}
          <div className="grid grid-cols-1 gap-4">
            {filteredQuestionnaires.map((q) => {
              const isExpanded = expandedQId === q.id;
              const isHyundai = q.brand_name?.toUpperCase().includes('HYUNDAI');

              return (
                <div
                  key={q.id}
                  className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden"
                >
                  {/* Card Header */}
                  <div className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            q.type === 'HAPPINESS'
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300'
                              : q.type === 'PSF'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                              : q.type === 'TNPS'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                              : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                          }`}
                        >
                          {q.type}
                        </span>

                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                          {q.brand_name}
                        </span>

                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                          v{q.version}
                        </span>

                        {q.type === 'HAPPINESS' && (
                          <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                            • Hyundai OEM Exclusive
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                        {q.title}
                      </h3>

                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Contains {q.questions_count} structured questions • JSONB responses mapped with auto CSAT/NPS
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => {
                          setPreviewQId(q.id);
                          setActiveTab('previewer');
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Preview & Test
                      </button>

                      <button
                        onClick={() => handleCloneVersion(q.id, q.title, q.version)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 hover:bg-slate-200 transition"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        New Version (v{q.version + 1})
                      </button>

                      <button
                        onClick={() => handleOpenAddQuestion(q)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 transition"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        Add Question
                      </button>

                      <button
                        onClick={() => toggleExpand(q.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200 hover:bg-slate-300 transition"
                      >
                        {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                        {isExpanded ? 'Hide Questions' : `View Questions (${q.questions_count})`}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Questions Table */}
                  {isExpanded && (
                    <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-4 sm:p-5">
                      {detailLoading ? (
                        <div className="py-6 text-center text-xs text-slate-500">
                          <RefreshCw className="h-4 w-4 animate-spin inline mr-2" />
                          Loading questions list...
                        </div>
                      ) : activeQuestionnaireDetail?.questions?.length === 0 ? (
                        <div className="py-6 text-center text-xs text-slate-500">
                          No questions added to this questionnaire yet. Click "Add Question" above.
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-left text-xs">
                            <thead className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase tracking-wider font-semibold">
                              <tr>
                                <th className="py-2.5 px-3">#</th>
                                <th className="py-2.5 px-3">Section</th>
                                <th className="py-2.5 px-3">Question Label</th>
                                <th className="py-2.5 px-3">Field Key</th>
                                <th className="py-2.5 px-3">Type</th>
                                <th className="py-2.5 px-3">Condition (show_if)</th>
                                <th className="py-2.5 px-3">Weight</th>
                                <th className="py-2.5 px-3 text-right">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                              {activeQuestionnaireDetail?.questions?.map((question, idx) => (
                                <tr key={question.id} className="hover:bg-slate-100/60 dark:hover:bg-slate-800/60">
                                  <td className="py-2.5 px-3 font-mono text-slate-400">{idx + 1}</td>
                                  <td className="py-2.5 px-3 font-medium text-blue-600 dark:text-blue-400">
                                    {question.section}
                                  </td>
                                  <td className="py-2.5 px-3 max-w-sm font-medium text-slate-900 dark:text-white">
                                    {question.label}
                                    {question.is_required && (
                                      <span className="text-red-500 ml-1 font-bold">*</span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px]">
                                    {question.key}
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-slate-200 dark:bg-slate-800">
                                      {question.type}
                                    </span>
                                  </td>
                                  <td className="py-2.5 px-3 text-[11px] text-amber-600 dark:text-amber-400 font-mono">
                                    {question.show_if ? (
                                      <span>
                                        if {question.show_if.field} {question.show_if.operator} {String(question.show_if.value)}
                                      </span>
                                    ) : (
                                      <span className="text-slate-400 font-sans">Always</span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3 font-mono">{question.weight}</td>
                                  <td className="py-2.5 px-3 text-right">
                                    <button
                                      onClick={() => handleDeleteQuestion(q.id, question.id, question.label)}
                                      className="p-1 rounded text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition"
                                      title="Delete Question"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: INTERACTIVE QUESTIONNAIRE PREVIEWER */}
      {activeTab === 'previewer' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Survey Simulator (Left 2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-amber-500" />
                    Caller Console Interactive Simulator
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Test questionnaire layout, star ratings, NPS button scales, and conditional triggers in real-time.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-500 whitespace-nowrap">Switch Survey:</label>
                  <select
                    value={previewQId}
                    onChange={(e) => setPreviewQId(e.target.value)}
                    className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white"
                  >
                    {questionnaires.map((q) => (
                      <option key={q.id} value={q.id}>
                        [{q.brand_name}] {q.type} - {q.title} (v{q.version})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {previewLoading ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  <RefreshCw className="h-5 w-5 animate-spin inline mr-2 text-blue-600" />
                  Loading interactive questionnaire...
                </div>
              ) : !previewQuestionnaire ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  Select a questionnaire above to launch preview.
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Campaign Header */}
                  <div className="p-4 rounded-lg bg-blue-50/70 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 flex justify-between items-center">
                    <div>
                      <div className="text-xs font-semibold text-blue-800 dark:text-blue-300">
                        {previewQuestionnaire.brand_name} • {previewQuestionnaire.type} Campaign
                      </div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white">
                        {previewQuestionnaire.title}
                      </div>
                    </div>
                    {previewQuestionnaire.type === 'HAPPINESS' && (
                      <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 text-xs font-semibold">
                        Hyundai Exclusive
                      </span>
                    )}
                  </div>

                  {/* Questions Grouped by Section */}
                  {Object.entries(
                    (previewQuestionnaire.questions || []).reduce((acc, q) => {
                      const sec = q.section || 'General';
                      if (!acc[sec]) acc[sec] = [];
                      acc[sec].push(q);
                      return acc;
                    }, {})
                  ).map(([sectionTitle, secQuestions]) => {
                    const visibleSecQuestions = secQuestions.filter(isQuestionVisible);
                    if (visibleSecQuestions.length === 0) return null;

                    return (
                      <div key={sectionTitle} className="space-y-4">
                        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                          <span className="h-2 w-2 rounded-full bg-blue-600"></span>
                          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                            {sectionTitle}
                          </h3>
                        </div>

                        <div className="space-y-4 pl-3">
                          {visibleSecQuestions.map((q, idx) => (
                            <div
                              key={q.id}
                              className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2.5 transition hover:border-blue-400"
                            >
                              <div className="flex justify-between items-start">
                                <label className="text-xs font-medium text-slate-900 dark:text-white leading-relaxed">
                                  <span className="font-bold text-slate-400 mr-1.5">{idx + 1}.</span>
                                  {q.label}
                                  {q.is_required && <span className="text-red-500 ml-1 font-bold">*</span>}
                                </label>

                                {q.show_if && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 shrink-0">
                                    Conditional Trigger
                                  </span>
                                )}
                              </div>

                              {/* Input Renderers based on Question Type */}
                              {/* 1. 5-STAR RATING */}
                              {q.type === 'rating_5' && (
                                <div className="flex items-center gap-2 pt-1">
                                  {[1, 2, 3, 4, 5].map((val) => {
                                    const isSelected = previewAnswers[q.key] === val;
                                    return (
                                      <button
                                        key={val}
                                        type="button"
                                        onClick={() =>
                                          setPreviewAnswers((prev) => ({ ...prev, [q.key]: val }))
                                        }
                                        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                                          isSelected
                                            ? 'bg-amber-500 text-white border-amber-600 shadow-sm'
                                            : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-amber-50 dark:hover:bg-amber-900/20'
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
                                <div className="space-y-1.5 pt-1">
                                  <div className="flex flex-wrap gap-1.5">
                                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((val) => {
                                      const isSelected = previewAnswers[q.key] === val;
                                      const isDetractor = val <= 6;
                                      const isPassive = val === 7 || val === 8;
                                      const isPromoter = val >= 9;

                                      return (
                                        <button
                                          key={val}
                                          type="button"
                                          onClick={() =>
                                            setPreviewAnswers((prev) => ({ ...prev, [q.key]: val }))
                                          }
                                          className={`w-8 h-8 rounded-lg text-xs font-bold border transition ${
                                            isSelected
                                              ? isPromoter
                                                ? 'bg-emerald-600 text-white border-emerald-700 ring-2 ring-emerald-400'
                                                : isPassive
                                                ? 'bg-amber-500 text-white border-amber-600 ring-2 ring-amber-400'
                                                : 'bg-red-600 text-white border-red-700 ring-2 ring-red-400'
                                              : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200'
                                          }`}
                                        >
                                          {val}
                                        </button>
                                      );
                                    })}
                                  </div>
                                  <div className="flex justify-between text-[10px] text-slate-400 px-1">
                                    <span className="text-red-500">0 - Detractor</span>
                                    <span className="text-amber-500">7-8 - Passive</span>
                                    <span className="text-emerald-500">9-10 - Promoter</span>
                                  </div>
                                </div>
                              )}

                              {/* 3. YES / NO / NA */}
                              {['yes_no', 'yes_no_na'].includes(q.type) && (
                                <div className="flex items-center gap-2 pt-1">
                                  {['yes', 'no', ...(q.type === 'yes_no_na' ? ['na'] : [])].map((choice) => {
                                    const isSelected = previewAnswers[q.key] === choice;
                                    return (
                                      <button
                                        key={choice}
                                        type="button"
                                        onClick={() =>
                                          setPreviewAnswers((prev) => ({ ...prev, [q.key]: choice }))
                                        }
                                        className={`px-4 py-1.5 rounded-lg text-xs font-semibold uppercase border transition ${
                                          isSelected
                                            ? choice === 'yes'
                                              ? 'bg-emerald-600 text-white border-emerald-700'
                                              : choice === 'no'
                                              ? 'bg-red-600 text-white border-red-700'
                                              : 'bg-slate-600 text-white border-slate-700'
                                            : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200'
                                        }`}
                                      >
                                        {choice === 'na' ? 'N/A' : choice}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}

                              {/* 4. TEXT / VOC */}
                              {['text', 'textarea'].includes(q.type) && (
                                <textarea
                                  rows={2}
                                  value={previewAnswers[q.key] || ''}
                                  onChange={(e) =>
                                    setPreviewAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))
                                  }
                                  placeholder="Record Voice of Customer (VOC)..."
                                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                                />
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Real-time Score Engine Preview (Right 1 col) */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4 sticky top-6">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-600" />
                Real-Time Score Engine
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Shows auto-aggregation calculation executed during live CRE calls.
              </p>

              {/* CSAT Metric Card */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Calculated CSAT (0 - 100%)
                </div>
                <div className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">
                  {previewScores.csat !== null ? `${previewScores.csat}%` : 'N/A'}
                </div>
                <div className="text-[11px] text-slate-400">
                  Weighted aggregate of all active rating & compliance questions
                </div>
              </div>

              {/* NPS Metric Card */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Net Promoter Score (NPS)
                </div>
                <div className="flex items-center justify-between">
                  <div className="text-3xl font-extrabold text-slate-900 dark:text-white">
                    {previewScores.nps !== null ? previewScores.nps : 'N/A'}
                  </div>
                  {previewScores.npsCategory && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold ${
                        previewScores.npsCategory === 'PROMOTER'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                          : previewScores.npsCategory === 'PASSIVE'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                      }`}
                    >
                      {previewScores.npsCategory}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400">
                  Categorized per OEM standards: Promoters (9-10), Passives (7-8), Detractors (0-6)
                </div>
              </div>

              {/* JSONB Payload Preview */}
              <div className="space-y-1 pt-2">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  JSONB Storage Snapshot (answers):
                </div>
                <pre className="p-2.5 rounded-lg bg-slate-950 text-emerald-400 font-mono text-[10px] max-h-48 overflow-y-auto">
                  {JSON.stringify(previewAnswers, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: BRANDS & WORKSHOP BRANCHES */}
      {activeTab === 'brands' && (
        <div className="space-y-6">
          {/* Brands Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {brands.map((b) => (
              <div
                key={b.id}
                className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-4 h-4 rounded-full border border-slate-300"
                      style={{ backgroundColor: b.primary_color || '#2563EB' }}
                    ></div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">{b.name}</h3>
                  </div>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {b.code}
                  </span>
                </div>

                <div className="text-xs text-slate-500 space-y-1">
                  <div>Workshop Branches: <strong>{b.branches_count} locations</strong></div>
                  <div>OEM Brand Color: <span className="font-mono">{b.primary_color}</span></div>
                </div>

                {/* Hyundai Special Badge */}
                {b.has_happiness_calling ? (
                  <div className="pt-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                      <CheckCircle className="h-3.5 w-3.5" />
                      Happiness Calling Enabled (15/30-Day Survey)
                    </span>
                  </div>
                ) : (
                  <div className="pt-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs text-slate-400 bg-slate-50 dark:bg-slate-800">
                      Standard PSF & TNPS Only
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Workshop Branches Table */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Workshop Branches ({branches.length})
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Dealer service centers mapped to DMS job card imports and caller queues.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Branch Name</th>
                    <th className="py-2.5 px-3">Code</th>
                    <th className="py-2.5 px-3">OEM Brand</th>
                    <th className="py-2.5 px-3">Location / City</th>
                    <th className="py-2.5 px-3">Support Phone</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                  {branches.map((br) => (
                    <tr key={br.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                        {br.name}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">{br.code}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                          {br.brand_name || 'Mapped Brand'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{br.city || 'Gurgaon'}, {br.state || 'Haryana'}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">{br.phone || '+91 9811002233'}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                          ACTIVE
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: COMPLAINT CATEGORIES & SLAS */}
      {activeTab === 'complaints' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Complaint Categories & Turnaround Time (TAT / SLA)
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Configurable resolution targets and auto-escalation thresholds for dissatisfied customers.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Category Name</th>
                  <th className="py-2.5 px-3">OEM Brand</th>
                  <th className="py-2.5 px-3">Default Severity</th>
                  <th className="py-2.5 px-3">SLA Resolution Target</th>
                  <th className="py-2.5 px-3">Auto-Escalation Interval</th>
                  <th className="py-2.5 px-3">Reconfirmation Window</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {complaintCategories.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400">
                      Standard categories: Service Quality (24h), Billing & Estimates (24h), Staff Behavior (12h), Parts Unavailability (48h), Pick-up Delay (12h).
                    </td>
                  </tr>
                ) : (
                  complaintCategories.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">{c.name}</td>
                      <td className="py-2.5 px-3">{c.brand_name || 'All Brands'}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
                          {c.severity || 'HIGH'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono font-bold text-blue-600">{c.sla_hours || 24} Hours</td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">Every 4 Hours</td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">24 Hours post-resolution</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB: BRANCH CONTACTS */}
      {activeTab === 'branch_contacts' && (
        <BranchContactsTab branches={branches} brands={brands} />
      )}

      {/* TAB: RATING SCALES & BANDS */}
      {activeTab === 'rating_scales' && (
        <RatingScalesTab />
      )}

      {/* TAB 5: WHITE-LABEL BRANDING & TEMPLATES */}
      {activeTab === 'branding' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Tenant White-Label */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Palette className="h-4 w-4 text-blue-600" />
              Tenant White-Label Branding
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Dealership Group Name
                </label>
                <input
                  type="text"
                  defaultValue={settings?.theme?.dealer_name || 'Apex Automotive Group'}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Primary Theme Accent Color
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    defaultValue={settings?.theme?.primary_color || '#2563EB'}
                    className="h-9 w-14 rounded cursor-pointer border border-slate-300 dark:border-slate-700"
                  />
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                    {settings?.theme?.primary_color || '#2563EB'}
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => toast.success('Branding preferences saved successfully')}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition"
                >
                  <Save className="h-4 w-4" />
                  Save Branding Changes
                </button>
              </div>
            </div>
          </div>

          {/* SMS / WhatsApp Notification Templates */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-emerald-600" />
              SMS & WhatsApp Communication Templates
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Post-Service Feedback Link Template (SMS)
                </label>
                <textarea
                  rows={2}
                  defaultValue={settings?.templates?.sms_satisfaction}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                />
                <span className="text-[10px] text-slate-400">Available: &#123;&#123;customer_name&#125;&#125;, &#123;&#123;job_card_no&#125;&#125;, &#123;&#123;feedback_link&#125;&#125;</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Complaint Ticket Acknowledgement (WhatsApp)
                </label>
                <textarea
                  rows={2}
                  defaultValue={settings?.templates?.whatsapp_complaint_opened}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-xs text-slate-900 dark:text-white"
                />
                <span className="text-[10px] text-slate-400">Available: &#123;&#123;ticket_no&#125;&#125;, &#123;&#123;customer_name&#125;&#125;, &#123;&#123;service_manager&#125;&#125;</span>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => toast.success('Templates updated')}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700 transition"
                >
                  <Save className="h-4 w-4" />
                  Save Templates
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: CREATE QUESTIONNAIRE TEMPLATE */}
      {showCreateQModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 p-6 shadow-xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Create New Questionnaire Template
            </h3>

            <form onSubmit={handleCreateQuestionnaire} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  OEM Brand *
                </label>
                <select
                  value={newQBrandId}
                  onChange={(e) => setNewQBrandId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                >
                  {brands.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Survey Queue Type *
                </label>
                <select
                  value={newQType}
                  onChange={(e) => setNewQType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                >
                  <option value="PSF">PSF (Post Service Follow-up)</option>
                  <option value="TNPS">TNPS (Net Promoter Score)</option>
                  <option value="HAPPINESS">Happiness Calling (15/30 Day - Hyundai Only)</option>
                  <option value="RECONFIRMATION">Post-Complaint Reconfirmation</option>
                </select>
              </div>

              {/* Real-time OEM validation notice */}
              {newQType === 'HAPPINESS' && !isSelectedBrandHyundai && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>
                    <strong>OEM Restriction:</strong> Happiness Calling questionnaires are strictly exclusive to Hyundai brands. Please switch the brand to Hyundai to proceed.
                  </span>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Questionnaire Title *
                </label>
                <input
                  type="text"
                  value={newQTitle}
                  onChange={(e) => setNewQTitle(e.target.value)}
                  placeholder="e.g. Hyundai 2026 PSF Quality Audit"
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateQModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createQSubmitting || (newQType === 'HAPPINESS' && !isSelectedBrandHyundai)}
                  className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {createQSubmitting ? 'Creating...' : 'Create Questionnaire'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD QUESTION */}
      {showAddQuestionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 p-6 shadow-xl border border-slate-200 dark:border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Add Question to "{targetQForQuestion?.title}"
            </h3>

            <form onSubmit={handleSaveQuestion} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Unique Field Key *
                  </label>
                  <input
                    type="text"
                    value={newQKey}
                    onChange={(e) => setNewQKey(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                    placeholder="e.g. hygiene_rating"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-mono text-slate-900 dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    UI Section *
                  </label>
                  <input
                    type="text"
                    value={newQSection}
                    onChange={(e) => setNewQSection(e.target.value)}
                    placeholder="e.g. Work Quality"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Question Label (Script for Caller) *
                </label>
                <textarea
                  rows={2}
                  value={newQLabel}
                  onChange={(e) => setNewQLabel(e.target.value)}
                  placeholder="e.g. How satisfied were you with the explanation of charges by the advisor?"
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-xs text-slate-900 dark:text-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Question Input Type *
                  </label>
                  <select
                    value={newQFieldType}
                    onChange={(e) => setNewQFieldType(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                  >
                    <option value="rating_5">5-Star Rating (1 to 5)</option>
                    <option value="nps_10">NPS Scale (0 to 10)</option>
                    <option value="yes_no">Yes / No</option>
                    <option value="yes_no_na">Yes / No / Not Applicable</option>
                    <option value="single_select">Single Select Options</option>
                    <option value="text">Free Text / Customer VOC</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Score Weight (0.1 to 5.0)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={newQWeight}
                    onChange={(e) => setNewQWeight(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Conditional Show If Logic Builder */}
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                  Conditional Display Logic (Optional show_if)
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <input
                      type="text"
                      placeholder="Depends on key (e.g. hyundai_work_quality)"
                      value={newQShowIfField}
                      onChange={(e) => setNewQShowIfField(e.target.value)}
                      className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-[11px]"
                    />
                  </div>
                  <div>
                    <select
                      value={newQShowIfOperator}
                      onChange={(e) => setNewQShowIfOperator(e.target.value)}
                      className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-[11px]"
                    >
                      <option value="<=">&le; (Less than or equal)</option>
                      <option value="==">== (Equals)</option>
                      <option value=">=">&ge; (Greater than or equal)</option>
                      <option value="!=">!= (Not equal)</option>
                    </select>
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Value (e.g. 3)"
                      value={newQShowIfValue}
                      onChange={(e) => setNewQShowIfValue(e.target.value)}
                      className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-[11px]"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isRequiredChk"
                  checked={newQRequired}
                  onChange={(e) => setNewQRequired(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="isRequiredChk" className="text-xs text-slate-700 dark:text-slate-300">
                  Mandatory answer required during call submission
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddQuestionModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addQuestionSubmitting}
                  className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {addQuestionSubmitting ? 'Saving...' : 'Save Question'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

