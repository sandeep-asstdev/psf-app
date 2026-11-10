/**
 * ============================================================================
 * FILE PURPOSE: Dealership Onboarding Wizard & Config Packs Management Tab.
 * Allows Super Admins to:
 * 1. Onboard new dealerships using a 4-step wizard with pre-built OEM config packs.
 * 2. Clone a pack (Hyundai, Tata, MG, Ather, Blank) into the active dealership.
 * 3. Export full dealership configuration as JSON.
 * 4. Import/validate JSON config packs.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  Package,
  Sparkles,
  Download,
  Upload,
  CheckCircle2,
  Building,
  UserPlus,
  Layers,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function DealershipWizardTab() {
  const [packs, setPacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPack, setSelectedPack] = useState('BLANK');
  const [isCloning, setIsCloning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // Wizard State
  const [wizardStep, setWizardStep] = useState(1);
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
    fetchPacks();
  }, []);

  const fetchPacks = async () => {
    try {
      setLoading(true);
      const res = await api.get('/config/packs');
      setPacks(res.data || []);
    } catch (err) {
      toast.error('Failed to load configuration packs');
    } finally {
      setLoading(false);
    }
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

  const handleWizardSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('/config/dealerships/wizard', wizardData);
      toast.success(res.data.message || 'Dealership onboarded successfully!');
      setWizardStep(1);
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
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to onboard dealership');
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Package className="w-5 h-5 text-indigo-600" />
            Config Packs &amp; Dealership Onboarding
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Deploy pre-packaged OEM configurations (Hyundai, Tata, MG, Ather, Blank) or export/import versioned JSON templates.
          </p>
        </div>
        <button
          onClick={handleExportConfig}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-sm font-medium transition"
        >
          {isExporting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Export Active Config (JSON)
        </button>
      </div>

      {/* Available Packs Grid */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-600" />
          Pre-Configured Packs Catalogue
        </h3>
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
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium shadow-sm transition"
          >
            {isCloning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Clone Into Dealership
          </button>
        </div>
      </div>

      {/* Two Column Layout: Wizard and Import/Export */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dealership Onboarding Wizard */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Building className="w-4 h-4 text-indigo-600" />
                Create Dealership Wizard
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Onboard a new dealership tenant with brand, branch, admin user, and config pack.
              </p>
            </div>
            <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
              Step {wizardStep} of 3
            </span>
          </div>

          <form onSubmit={handleWizardSubmit} className="space-y-4">
            {wizardStep === 1 && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Step 1: Dealership Details
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Dealership Name</label>
                  <input
                    type="text"
                    required
                    value={wizardData.name}
                    onChange={(e) => setWizardData({ ...wizardData, name: e.target.value })}
                    placeholder="e.g. Metro Mobility Motors"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Tenant Slug</label>
                  <input
                    type="text"
                    required
                    value={wizardData.slug}
                    onChange={(e) => setWizardData({ ...wizardData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    placeholder="e.g. metro-mobility"
                    className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Select Config Pack</label>
                  <select
                    value={wizardData.pack_code}
                    onChange={(e) => setWizardData({ ...wizardData, pack_code: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    {packs.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.name} ({p.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium"
                  >
                    Next: Brand &amp; Branch <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Step 2: Brand &amp; Branch
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Brand Name</label>
                    <input
                      type="text"
                      required
                      value={wizardData.brand_name}
                      onChange={(e) => setWizardData({ ...wizardData, brand_name: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Brand Code</label>
                    <input
                      type="text"
                      required
                      value={wizardData.brand_code}
                      onChange={(e) => setWizardData({ ...wizardData, brand_code: e.target.value.toUpperCase() })}
                      className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Workshop Branch Name</label>
                    <input
                      type="text"
                      required
                      value={wizardData.branch_name}
                      onChange={(e) => setWizardData({ ...wizardData, branch_name: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Branch Code</label>
                    <input
                      type="text"
                      required
                      value={wizardData.branch_code}
                      onChange={(e) => setWizardData({ ...wizardData, branch_code: e.target.value.toUpperCase() })}
                      className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg"
                    />
                  </div>
                </div>
                <div className="pt-2 flex justify-between">
                  <button
                    type="button"
                    onClick={() => setWizardStep(1)}
                    className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium"
                  >
                    Next: Admin User <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {wizardStep === 3 && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Step 3: Initial Admin User
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Admin Full Name</label>
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
                  <label className="block text-xs font-medium text-slate-700 mb-1">Admin Email</label>
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
                  <label className="block text-xs font-medium text-slate-700 mb-1">Password</label>
                  <input
                    type="password"
                    required
                    value={wizardData.admin_password}
                    onChange={(e) => setWizardData({ ...wizardData, admin_password: e.target.value })}
                    placeholder="Min 6 characters"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
                  />
                </div>
                <div className="pt-2 flex justify-between">
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    className="flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm"
                  >
                    Create Dealership &amp; Deploy Pack
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Config JSON Import & Validation */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-600" />
              Import Configuration Pack (JSON)
            </h3>
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
              className="px-4 py-2 border border-slate-300 hover:bg-slate-50 disabled:opacity-50 text-slate-700 rounded-lg text-xs font-semibold"
            >
              Validate Schema
            </button>
            <button
              type="button"
              onClick={handleExecuteImport}
              disabled={isImporting || !importJsonText.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm"
            >
              {isImporting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              Import &amp; Apply Config
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
