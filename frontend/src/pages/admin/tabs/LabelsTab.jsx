/**
 * ============================================================================
 * FILE PURPOSE: Custom Terminology & Labels Admin Configuration Tab.
 * Allows dealerships to customize terminology across the entire app
 * (e.g. rename CRE to "Calling Specialist", Job Card to "RO", Complaint to "Concern").
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import { Tag, Save, RotateCcw, CheckCircle, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';
import { useLabelStore, DEFAULT_SYSTEM_LABELS } from '../../../store/labelStore';

const LABEL_DESCRIPTIONS = {
  CRE: 'The tele-caller / representative making post-service follow-up calls.',
  DELIGHT: 'Highest rating band label displayed on dashboards and feedback cards.',
  TNPS: 'Brand-specific follow-up survey name (e.g., Ather TNPS, Hyundai PSF).',
  JOB_CARD: 'Service repair order / job card record identifier.',
  COMPLAINT: 'Customer escalation, grievance, or dissatisfaction ticket.',
  CUSTOMER: 'Vehicle owner or representative receiving follow-up calls.',
  ADVISOR: 'Workshop service advisor responsible for vehicle service.',
  BRANCH: 'Workshop or dealership service location.',
  BRAND: 'Automotive brand / OEM manufacturer.',
  SURVEY: 'Follow-up questionnaire administered to customers.',
};

export default function LabelsTab() {
  const { labels, fetchLabels, updateLabels } = useLabelStore();
  const [formValues, setFormValues] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchLabels();
  }, [fetchLabels]);

  useEffect(() => {
    setFormValues(labels || {});
  }, [labels]);

  const handleChange = (key, val) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await updateLabels(formValues);
      if (res.success) {
        toast.success('Custom terminology saved successfully!');
      } else {
        toast.error('Failed to save label overrides.');
      }
    } catch (err) {
      toast.error('Error saving labels: ' + (err.message || 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async (key) => {
    try {
      await api.delete(`/config/labels/${key}`);
      const defVal = DEFAULT_SYSTEM_LABELS[key] || key;
      setFormValues((prev) => ({
        ...prev,
        [key]: defVal,
      }));
      await fetchLabels();
      toast.success(`Reset ${key} to default: "${defVal}"`);
    } catch (err) {
      toast.error('Failed to reset label');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Tag className="w-5 h-5 text-indigo-600" />
            Custom Terminology &amp; Labels
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Customize platform vocabulary to match your dealership or OEM standard terms.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg shadow-sm transition"
        >
          {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Label Overrides
        </button>
      </div>

      {/* Form List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 grid grid-cols-12 text-xs font-semibold text-slate-600 uppercase tracking-wider">
          <div className="col-span-3">System Term Key</div>
          <div className="col-span-5">Custom Display Label</div>
          <div className="col-span-3">Default Value</div>
          <div className="col-span-1 text-right">Reset</div>
        </div>

        <div className="divide-y divide-slate-100">
          {Object.keys(DEFAULT_SYSTEM_LABELS).map((key) => {
            const defaultVal = DEFAULT_SYSTEM_LABELS[key];
            const currentVal = formValues[key] || '';
            const isModified = currentVal && currentVal !== defaultVal;

            return (
              <div key={key} className="p-4 grid grid-cols-12 items-center gap-4 hover:bg-slate-50/50 transition">
                <div className="col-span-3">
                  <div className="font-mono text-sm font-semibold text-slate-800 flex items-center gap-2">
                    {key}
                    {isModified && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800">
                        Modified
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {LABEL_DESCRIPTIONS[key] || 'Platform vocabulary term'}
                  </div>
                </div>

                <div className="col-span-5">
                  <input
                    type="text"
                    value={currentVal}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={defaultVal}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>

                <div className="col-span-3 text-sm text-slate-500 font-medium">
                  {defaultVal}
                </div>

                <div className="col-span-1 text-right">
                  {isModified && (
                    <button
                      type="button"
                      onClick={() => handleReset(key)}
                      title="Reset to default"
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50 transition"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
