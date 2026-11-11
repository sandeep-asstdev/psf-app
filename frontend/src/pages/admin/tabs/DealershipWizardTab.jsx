/**
 * ============================================================================
 * FILE PURPOSE: Multi-Tenant Dealership Management & Onboarding Tab.
 * STRICTLY RESTRICTED TO: Super Admin (L1).
 * 
 * KEY CAPABILITIES:
 * 1. View all registered dealership tenants with real-time stats (brands, branches, users).
 * 2. Dedicated "Create New Tenant" option with both:
 *    - All-in-One Fast Form (single-screen direct tenant creation)
 *    - 4-Step Guided Wizard (Dealership -> Brand/Branch -> Admin User -> Review)
 * 3. OEM Configuration Packs (Hyundai, Tata, MG, Ather, Blank) Management.
 * 4. Export & Import full dealership configurations as validated JSON.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  Building2,
  Package,
  Sparkles,
  Download,
  Upload,
  CheckCircle2,
  Users,
  Layers,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Search,
  PlusCircle,
  ExternalLink,
  Store,
  Check,
  Sliders,
  FileText,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';
import { useAuthStore, isUserSuperAdmin } from '../../../store/authStore';

export default function DealershipWizardTab({ createTrigger = 0 }) {
  const { user } = useAuthStore();
  const isSuperAdmin = isUserSuperAdmin(user);

  // Sub-tabs: 'list' | 'create' | 'packs'
  const [subView, setSubView] = useState('list');
  // Creation Mode inside 'create': 'single' | 'wizard'
  const [formMode, setFormMode] = useState('single');

  // Tenant List State
  const [tenants, setTenants] = useState([]);
  const [tenantsLoading, setTenantsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Packs State
  const [packs, setPacks] = useState([]);
  const [packsLoading, setPacksLoading] = useState(true);
  const [selectedPack, setSelectedPack] = useState('BLANK');
  const [isCloning, setIsCloning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // Wizard / Create Form State
  const [wizardStep, setWizardStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTenantResult, setCreatedTenantResult] = useState(null);
  const [wizardData, setWizardData] = useState({
    name: '',
    slug: '',
    brand_name: 'Custom Brand',
    brand_code: 'CUSTOM',
    branch_name: 'Main Workshop',
    branch_code: 'MAIN-01',
    admin_name: '',
    admin_email: '',
    admin_password: '',
    pack_code: 'BLANK',
  });

  // Import State
  const [importJsonText, setImportJsonText] = useState('');
  const [validationResult, setValidationResult] = useState(null);

  useEffect(() => {
    if (isSuperAdmin) {
      fetchTenants();
      fetchPacks();
    }
  }, [isSuperAdmin]);

  useEffect(() => {
    if (createTrigger > 0) {
      setSubView('create');
      resetWizard();
    }
  }, [createTrigger]);

  const fetchTenants = async () => {
    try {
      setTenantsLoading(true);
      let res;
      try {
        res = await api.get('/admin/tenants');
      } catch (e) {
        res = await api.get('/config/tenants');
      }
      setTenants(res.data || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load dealership tenants');
    } finally {
      setTenantsLoading(false);
    }
  };

  const fetchPacks = async () => {
    try {
      setPacksLoading(true);
      const res = await api.get('/config/packs');
      setPacks(res.data || []);
    } catch (err) {
      toast.error('Failed to load configuration packs');
    } finally {
      setPacksLoading(false);
    }
  };

  const handleNameChange = (e) => {
    const val = e.target.value;
    const autoSlug = val
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    setWizardData((prev) => ({
      ...prev,
      name: val,
      slug: prev.slug === '' || prev.slug === prev.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') ? autoSlug : prev.slug,
    }));
  };

  const handleClonePack = async () => {
    if (!window.confirm(`Are you sure you want to clone the '${selectedPack}' pack into the active dealership? Existing matching items will be updated.`)) {
      return;
    }
    setIsCloning(true);
    try {
      const res = await api.post('/config/packs/clone', { pack_code: selectedPack });
      toast.success(res.data.message || `Successfully cloned ${selectedPack} pack!`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to clone pack');
    } finally {
      setIsCloning(false);
    }
  };

  const handleExportConfig = async () => {
    setIsExporting(true);
    try {
      const res = await api.get('/config/dealership/export');
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(res.data, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `dealership-config-${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      toast.success('Configuration exported successfully!');
    } catch (err) {
      toast.error('Failed to export configuration');
    } finally {
      setIsExporting(false);
    }
  };

  const handleValidateImport = async () => {
    try {
      const parsed = JSON.parse(importJsonText);
      const res = await api.post('/config/dealership/import', { config: parsed, validate_only: true });
      setValidationResult({ valid: true, message: res.data.message });
      toast.success('Configuration JSON schema is valid!');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setValidationResult({ valid: false, message: msg });
      toast.error('Validation failed: ' + msg);
    }
  };

  const handleExecuteImport = async () => {
    setIsImporting(true);
    try {
      const parsed = JSON.parse(importJsonText);
      const res = await api.post('/config/dealership/import', { config: parsed, validate_only: false });
      toast.success(res.data.message || 'Configuration successfully imported!');
      setImportJsonText('');
      setValidationResult(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to import configuration');
    } finally {
      setIsImporting(false);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      let res;
      try {
        res = await api.post('/admin/tenants', wizardData);
      } catch (e1) {
        res = await api.post('/config/dealerships/wizard', wizardData);
      }
      toast.success(res.data.message || 'Dealership tenant created successfully!');
      setCreatedTenantResult(res.data);
      fetchTenants();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create dealership tenant');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetWizard = () => {
    setWizardStep(1);
    setCreatedTenantResult(null);
    setWizardData({
      name: '',
      slug: '',
      brand_name: 'Custom Brand',
      brand_code: 'CUSTOM',
      branch_name: 'Main Workshop',
      branch_code: 'MAIN-01',
      admin_name: '',
      admin_email: '',
      admin_password: '',
      pack_code: 'BLANK',
    });
  };

  // If not super admin, strictly deny access
  if (!isSuperAdmin) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center max-w-xl mx-auto my-12">
        <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-red-900">Access Restricted</h3>
        <p className="text-sm text-red-700 mt-2">
          Only Super Administrators (L1) have permission to create new dealership tenants or manage multi-tenant platform configurations.
        </p>
      </div>
    );
  }

  const filteredTenants = tenants.filter(
    (t) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.slug.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Top Banner & Sub-View Switcher */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold text-slate-900">
              Dealership Tenant Management
            </h2>
            <span className="bg-blue-100 text-blue-800 text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Super Admin Only
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Create, configure, and isolate multi-brand dealership tenants. Deploy pre-built OEM config packs and manage tenant databases.
          </p>
        </div>

        {/* View Switcher Controls */}
        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg">
          <button
            type="button"
            id="tab-all-tenants"
            onClick={() => setSubView('list')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
              subView === 'list'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Tenants ({tenants.length})
          </button>
          <button
            type="button"
            id="tab-create-tenant-wizard"
            onClick={() => {
              setSubView('create');
              if (createdTenantResult) resetWizard();
            }}
            className={`px-3.5 py-1.5 rounded-md text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              subView === 'create'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm'
            }`}
          >
            <PlusCircle className="w-4 h-4" />
            + Create New Tenant
          </button>
          <button
            type="button"
            id="tab-oem-packs"
            onClick={() => setSubView('packs')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
              subView === 'packs'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            OEM Packs &amp; JSON
          </button>
        </div>
      </div>

      {/* SUB-VIEW 1: TENANTS LIST */}
      {subView === 'list' && (
        <div className="space-y-4">
          {/* Header Action Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search tenants by name or slug..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={fetchTenants}
                disabled={tenantsLoading}
                className="px-3 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${tenantsLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                type="button"
                id="btn-list-create-tenant"
                onClick={() => {
                  setSubView('create');
                  resetWizard();
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm cursor-pointer"
              >
                <PlusCircle className="w-4 h-4" />
                + Create New Tenant
              </button>
            </div>
          </div>

          {/* Tenants Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Dealership Tenant</th>
                  <th className="py-3 px-4">Slug Identifier</th>
                  <th className="py-3 px-4 text-center">OEM Brands</th>
                  <th className="py-3 px-4 text-center">Workshop Branches</th>
                  <th className="py-3 px-4 text-center">Users</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tenantsLoading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-600" />
                      Loading platform tenants...
                    </td>
                  </tr>
                ) : filteredTenants.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500 space-y-3">
                      <Store className="w-8 h-8 text-slate-300 mx-auto" />
                      <p>No dealership tenants found.</p>
                      <button
                        type="button"
                        onClick={() => {
                          setSubView('create');
                          resetWizard();
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold inline-flex items-center gap-1.5 shadow-sm cursor-pointer"
                      >
                        <PlusCircle className="w-4 h-4" />
                        + Create First Tenant
                      </button>
                    </td>
                  </tr>
                ) : (
                  filteredTenants.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-white text-xs shadow-sm shrink-0"
                            style={{ backgroundColor: t.primary_color || '#2563EB' }}
                          >
                            {t.name.charAt(0)}
                          </div>
                          <div>
                            <span className="font-bold text-slate-900 block">{t.name}</span>
                            <span className="text-[10px] font-mono text-slate-400">{t.id.slice(0, 8)}...</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <code className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px] font-mono font-medium">
                          {t.slug}
                        </code>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-semibold text-slate-800">{t.brands_count}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-semibold text-slate-800">{t.branches_count}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-semibold text-slate-800">{t.users_count}</span>
                      </td>
                      <td className="py-3 px-4">
                        {t.is_active ? (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px] font-bold">
                            Active
                          </span>
                        ) : (
                          <span className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full text-[10px] font-bold">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {t.created_at ? new Date(t.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CREATE NEW TENANT */}
      {subView === 'create' && (
        <div className="max-w-3xl mx-auto space-y-4">
          {createdTenantResult ? (
            /* Creation Success Card */
            <div className="bg-white rounded-xl border border-emerald-200 shadow-md p-8 text-center space-y-5">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto text-emerald-600">
                <Check className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900">Dealership Tenant Created Successfully!</h3>
                <p className="text-sm text-slate-600 mt-1">
                  The new tenant has been provisioned, isolated in the database, and initialized with OEM configurations.
                </p>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 text-left text-xs font-mono border border-slate-200 space-y-2 max-w-lg mx-auto">
                <div className="flex justify-between">
                  <span className="text-slate-500">Tenant ID:</span>
                  <span className="font-bold text-slate-800">{createdTenantResult.tenant_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Config Pack Cloned:</span>
                  <span className="font-bold text-indigo-600">{createdTenantResult.pack_cloned}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Initial Admin User:</span>
                  <span className="font-bold text-emerald-700">{wizardData.admin_email}</span>
                </div>
              </div>

              <div className="flex justify-center gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setSubView('list')}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
                >
                  View All Tenants
                </button>
                <button
                  type="button"
                  onClick={resetWizard}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer"
                >
                  + Create Another Tenant
                </button>
              </div>
            </div>
          ) : (
            /* Create Tenant Card */
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              {/* Header with Mode Switcher */}
              <div className="bg-slate-50 border-b border-slate-200 p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div>
                  <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                    <Store className="w-5 h-5 text-blue-600" />
                    Create New Dealership Tenant
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Provision a brand-new multi-tenant dealership with initial brand, branch, administrator, and OEM pack.
                  </p>
                </div>

                <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 text-xs">
                  <button
                    type="button"
                    onClick={() => setFormMode('single')}
                    className={`px-2.5 py-1 rounded font-semibold transition cursor-pointer ${
                      formMode === 'single' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Direct Form
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormMode('wizard')}
                    className={`px-2.5 py-1 rounded font-semibold transition cursor-pointer ${
                      formMode === 'wizard' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    4-Step Wizard
                  </button>
                </div>
              </div>

              {/* FORM MODE 1: DIRECT ALL-IN-ONE FORM */}
              {formMode === 'single' ? (
                <form onSubmit={handleFormSubmit} className="p-6 space-y-6">
                  {/* Section 1: Tenant Information */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-700 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                      <Building2 className="w-4 h-4" /> 1. Dealership Organization Details
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Dealership Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.name}
                          onChange={handleNameChange}
                          placeholder="e.g. Metro Mobility Motors"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Tenant URL Slug <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.slug}
                          onChange={(e) =>
                            setWizardData({
                              ...wizardData,
                              slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''),
                            })
                          }
                          placeholder="e.g. metro-mobility"
                          className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Select OEM Config Pack <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={wizardData.pack_code}
                        onChange={(e) => setWizardData({ ...wizardData, pack_code: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      >
                        {packs.map((p) => (
                          <option key={p.code} value={p.code}>
                            {p.name} ({p.code}) — {p.description || p.code}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Section 2: Brand & Branch */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-700 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                      <Store className="w-4 h-4" /> 2. Primary OEM Brand &amp; Workshop Branch
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Brand Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.brand_name}
                          onChange={(e) => setWizardData({ ...wizardData, brand_name: e.target.value })}
                          placeholder="e.g. Hyundai or Tata"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Brand Code <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.brand_code}
                          onChange={(e) => setWizardData({ ...wizardData, brand_code: e.target.value.toUpperCase() })}
                          placeholder="e.g. HYUNDAI"
                          className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Workshop Branch Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.branch_name}
                          onChange={(e) => setWizardData({ ...wizardData, branch_name: e.target.value })}
                          placeholder="e.g. Main Workshop"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Branch Code <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.branch_code}
                          onChange={(e) => setWizardData({ ...wizardData, branch_code: e.target.value.toUpperCase() })}
                          placeholder="e.g. MAIN-01"
                          className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Section 3: Admin User */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-700 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                      <Users className="w-4 h-4" /> 3. Initial Dealership Administrator Credentials
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Admin Full Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={wizardData.admin_name}
                          onChange={(e) => setWizardData({ ...wizardData, admin_name: e.target.value })}
                          placeholder="e.g. Rajesh Kumar"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Admin Email <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="email"
                          required
                          value={wizardData.admin_email}
                          onChange={(e) => setWizardData({ ...wizardData, admin_email: e.target.value })}
                          placeholder="admin@metromobility.com"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Admin Password <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="password"
                          required
                          value={wizardData.admin_password}
                          onChange={(e) => setWizardData({ ...wizardData, admin_password: e.target.value })}
                          placeholder="Min 6 characters"
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Submit Button */}
                  <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => setSubView('list')}
                      className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      id="btn-create-tenant-submit"
                      disabled={isSubmitting}
                      className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition shadow-sm cursor-pointer"
                    >
                      {isSubmitting ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" /> Provisioning Tenant...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" /> Create New Tenant Now
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                /* FORM MODE 2: 4-STEP GUIDED WIZARD */
                <div>
                  <div className="bg-slate-50/50 border-b border-slate-200 p-3">
                    <div className="grid grid-cols-4 gap-2 text-center text-xs">
                      <div
                        className={`py-1.5 rounded font-bold border transition ${
                          wizardStep === 1
                            ? 'bg-blue-600 text-white border-blue-600'
                            : wizardStep > 1
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                            : 'bg-white text-slate-400 border-slate-200'
                        }`}
                      >
                        1. Dealership
                      </div>
                      <div
                        className={`py-1.5 rounded font-bold border transition ${
                          wizardStep === 2
                            ? 'bg-blue-600 text-white border-blue-600'
                            : wizardStep > 2
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                            : 'bg-white text-slate-400 border-slate-200'
                        }`}
                      >
                        2. Brand &amp; Branch
                      </div>
                      <div
                        className={`py-1.5 rounded font-bold border transition ${
                          wizardStep === 3
                            ? 'bg-blue-600 text-white border-blue-600'
                            : wizardStep > 3
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                            : 'bg-white text-slate-400 border-slate-200'
                        }`}
                      >
                        3. Admin User
                      </div>
                      <div
                        className={`py-1.5 rounded font-bold border transition ${
                          wizardStep === 4
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-slate-400 border-slate-200'
                        }`}
                      >
                        4. Review &amp; Deploy
                      </div>
                    </div>
                  </div>

                  <form onSubmit={handleFormSubmit} className="p-6 space-y-5">
                    {wizardStep === 1 && (
                      <div className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Dealership Name <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="text"
                            required
                            value={wizardData.name}
                            onChange={handleNameChange}
                            placeholder="e.g. Metro Mobility Motors"
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Tenant URL Slug <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="text"
                            required
                            value={wizardData.slug}
                            onChange={(e) =>
                              setWizardData({
                                ...wizardData,
                                slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''),
                              })
                            }
                            placeholder="e.g. metro-mobility"
                            className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Select Config Pack <span className="text-red-500">*</span>
                          </label>
                          <select
                            value={wizardData.pack_code}
                            onChange={(e) => setWizardData({ ...wizardData, pack_code: e.target.value })}
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          >
                            {packs.map((p) => (
                              <option key={p.code} value={p.code}>
                                {p.name} ({p.code})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="pt-4 flex justify-end">
                          <button
                            type="button"
                            disabled={!wizardData.name.trim() || !wizardData.slug.trim()}
                            onClick={() => setWizardStep(2)}
                            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer"
                          >
                            Next: Brand &amp; Branch <ArrowRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}

                    {wizardStep === 2 && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              Brand Name <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              required
                              value={wizardData.brand_name}
                              onChange={(e) => setWizardData({ ...wizardData, brand_name: e.target.value })}
                              placeholder="e.g. Hyundai"
                              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              Brand Code <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              required
                              value={wizardData.brand_code}
                              onChange={(e) => setWizardData({ ...wizardData, brand_code: e.target.value.toUpperCase() })}
                              placeholder="e.g. HYUNDAI"
                              className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg"
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              Workshop Branch Name <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              required
                              value={wizardData.branch_name}
                              onChange={(e) => setWizardData({ ...wizardData, branch_name: e.target.value })}
                              placeholder="e.g. Main Workshop"
                              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              Branch Code <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              required
                              value={wizardData.branch_code}
                              onChange={(e) => setWizardData({ ...wizardData, branch_code: e.target.value.toUpperCase() })}
                              placeholder="e.g. MAIN-01"
                              className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg"
                            />
                          </div>
                        </div>
                        <div className="pt-4 flex justify-between">
                          <button
                            type="button"
                            onClick={() => setWizardStep(1)}
                            className="flex items-center gap-1.5 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 cursor-pointer"
                          >
                            <ArrowLeft className="w-3.5 h-3.5" /> Back
                          </button>
                          <button
                            type="button"
                            disabled={!wizardData.brand_name.trim() || !wizardData.branch_name.trim()}
                            onClick={() => setWizardStep(3)}
                            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer"
                          >
                            Next: Admin User <ArrowRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}

                    {wizardStep === 3 && (
                      <div className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Admin Full Name <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="text"
                            required
                            value={wizardData.admin_name}
                            onChange={(e) => setWizardData({ ...wizardData, admin_name: e.target.value })}
                            placeholder="e.g. Rajesh Kumar"
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Admin Email Address <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="email"
                            required
                            value={wizardData.admin_email}
                            onChange={(e) => setWizardData({ ...wizardData, admin_email: e.target.value })}
                            placeholder="admin@metromobility.com"
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Admin Password <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="password"
                            required
                            value={wizardData.admin_password}
                            onChange={(e) => setWizardData({ ...wizardData, admin_password: e.target.value })}
                            placeholder="At least 6 characters"
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                          />
                        </div>
                        <div className="pt-4 flex justify-between">
                          <button
                            type="button"
                            onClick={() => setWizardStep(2)}
                            className="flex items-center gap-1.5 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 cursor-pointer"
                          >
                            <ArrowLeft className="w-3.5 h-3.5" /> Back
                          </button>
                          <button
                            type="button"
                            disabled={!wizardData.admin_name.trim() || !wizardData.admin_email.trim() || wizardData.admin_password.length < 6}
                            onClick={() => setWizardStep(4)}
                            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer"
                          >
                            Next: Review &amp; Deploy <ArrowRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}

                    {wizardStep === 4 && (
                      <div className="space-y-4">
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 text-xs">
                          <div className="grid grid-cols-2 gap-2 border-b border-slate-200 pb-2">
                            <div>
                              <span className="text-slate-500 block">Dealership:</span>
                              <span className="font-bold text-slate-900">{wizardData.name}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">URL Slug:</span>
                              <span className="font-mono font-bold text-blue-600">{wizardData.slug}</span>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2 border-b border-slate-200 pb-2">
                            <div>
                              <span className="text-slate-500 block">Brand:</span>
                              <span className="font-bold text-slate-900">{wizardData.brand_name} ({wizardData.brand_code})</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">Branch:</span>
                              <span className="font-bold text-slate-900">{wizardData.branch_name} ({wizardData.branch_code})</span>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2 border-b border-slate-200 pb-2">
                            <div>
                              <span className="text-slate-500 block">Admin Account:</span>
                              <span className="font-bold text-slate-900">{wizardData.admin_name}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">Admin Email:</span>
                              <span className="font-bold text-emerald-700">{wizardData.admin_email}</span>
                            </div>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Config Pack:</span>
                            <span className="font-bold text-indigo-700">{wizardData.pack_code}</span>
                          </div>
                        </div>

                        <div className="pt-4 flex justify-between">
                          <button
                            type="button"
                            onClick={() => setWizardStep(3)}
                            className="flex items-center gap-1.5 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 cursor-pointer"
                          >
                            <ArrowLeft className="w-3.5 h-3.5" /> Back
                          </button>
                          <button
                            type="submit"
                            id="btn-wizard-submit-create-tenant"
                            disabled={isSubmitting}
                            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition shadow-sm cursor-pointer"
                          >
                            {isSubmitting ? (
                              <>
                                <RefreshCw className="w-4 h-4 animate-spin" /> Provisioning Tenant...
                              </>
                            ) : (
                              <>
                                <CheckCircle2 className="w-4 h-4" /> Create New Tenant Now
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </form>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW 3: OEM CONFIG PACKS & IMPORT/EXPORT */}
      {subView === 'packs' && (
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Package className="w-5 h-5 text-indigo-600" />
                OEM Config Packs &amp; JSON Portability
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Deploy pre-packaged OEM configurations (Hyundai, Tata, MG, Ather, Blank) or export/import versioned JSON templates.
              </p>
            </div>
            <button
              onClick={handleExportConfig}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              {isExporting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Export Active Config (JSON)
            </button>
          </div>

          {/* Available Packs Grid */}
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              Pre-Configured Packs Catalogue
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {packs.map((p) => {
                const isSelected = selectedPack === p.code;
                return (
                  <div
                    key={p.code}
                    onClick={() => setSelectedPack(p.code)}
                    className={`cursor-pointer rounded-xl p-4 border transition flex flex-col justify-between ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded">
                          {p.code}
                        </span>
                        <span className="text-[11px] text-slate-400">v{p.version}</span>
                      </div>
                      <h4 className="font-bold text-slate-900 text-sm mt-2">{p.name}</h4>
                      <p className="text-xs text-slate-500 mt-1 line-clamp-3">{p.description}</p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                      <span className="text-slate-400">Brand: {p.brand_code}</span>
                      {isSelected && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Clone Selected Pack into Current Dealership */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="text-sm font-semibold text-slate-800">
                  Apply Pack to Active Dealership: <span className="font-mono text-indigo-600">{selectedPack}</span>
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Installs programs, questionnaires, scales, outcome rules, and labels from the selected pack.
                </div>
              </div>
              <button
                onClick={handleClonePack}
                disabled={isCloning}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition cursor-pointer"
              >
                {isCloning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                Clone Into Active Dealership
              </button>
            </div>
          </div>

          {/* Config JSON Import & Validation */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Upload className="w-4 h-4 text-indigo-600" />
                Import Configuration Pack (JSON)
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Paste or inspect JSON config pack before importing into the dealership.
              </p>
            </div>

            <textarea
              rows={10}
              value={importJsonText}
              onChange={(e) => {
                setImportJsonText(e.target.value);
                setValidationResult(null);
              }}
              placeholder='Paste JSON pack here: { "pack_version": "1.0.0", "programs": [...], "questionnaires": [...], "rules": [...] }'
              className="w-full p-3 font-mono text-xs border border-slate-300 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />

            {validationResult && (
              <div
                className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 ${
                  validationResult.valid ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
                }`}
              >
                {validationResult.valid ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : null}
                {validationResult.message}
              </div>
            )}

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={handleValidateImport}
                disabled={!importJsonText.trim()}
                className="px-4 py-2 border border-slate-300 hover:bg-slate-50 disabled:opacity-50 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
              >
                Validate Schema
              </button>
              <button
                type="button"
                onClick={handleExecuteImport}
                disabled={isImporting || !importJsonText.trim()}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm cursor-pointer"
              >
                {isImporting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                Import &amp; Apply Config
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
