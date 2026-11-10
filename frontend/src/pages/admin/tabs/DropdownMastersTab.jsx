import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function DropdownMastersTab() {
  const [mastersSubTab, setMastersSubTab] = useState('service_types');
  const [serviceTypes, setServiceTypes] = useState([]);
  const [caseStatuses, setCaseStatuses] = useState([]);
  const [callStatuses, setCallStatuses] = useState([]);
  const [complaintCategories, setComplaintCategories] = useState([]);

  const [serviceTypeModal, setServiceTypeModal] = useState(false);
  const [serviceTypeForm, setServiceTypeForm] = useState({ name: '', code: '', category: 'GENERAL', default_tat_hours: 24, color: '#2563EB', icon: 'Wrench' });

  const [statusModal, setStatusModal] = useState(false);
  const [statusForm, setStatusForm] = useState({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#10B981', type: 'CASE' });

  const [categoryModal, setCategoryModal] = useState(false);
  const [categoryForm, setCategoryForm] = useState({ name: '', default_sla_hours: 24, severity_level: 'MEDIUM', brand_id: '' });

  const loadDropdownMasters = async () => {
    try {
      const [stRes, csRes, clRes, catRes] = await Promise.all([
        api.get('/admin/service-types'),
        api.get('/masters/case-statuses'),
        api.get('/masters/call-statuses'),
        api.get('/masters/complaint-categories'),
      ]);
      setServiceTypes(stRes.data);
      setCaseStatuses(csRes.data);
      setCallStatuses(clRes.data);
      setComplaintCategories(catRes.data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadDropdownMasters();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex space-x-2 border-b border-border pb-2">
        {[
          { id: 'service_types', label: 'Service Types' },
          { id: 'case_statuses', label: 'Case Statuses (Sentiment)' },
          { id: 'call_statuses', label: 'Call Statuses' },
          { id: 'complaint_categories', label: 'Complaint Categories' },
        ].map((sub) => (
          <button
            key={sub.id}
            onClick={() => setMastersSubTab(sub.id)}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
              mastersSubTab === sub.id
                ? 'bg-accent text-accent-foreground shadow-sm'
                : 'bg-background-base text-foreground-muted hover:text-foreground'
            }`}
          >
            {sub.label}
          </button>
        ))}
      </div>

      {mastersSubTab === 'service_types' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-foreground-subtle">{serviceTypes.length} Service types configured</span>
            <button
              onClick={() => setServiceTypeModal(true)}
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Service Type
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {serviceTypes.map((st) => (
              <div key={st.id} className="p-3 rounded-lg border border-border bg-background-surface space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground">{st.name}</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-white" style={{ backgroundColor: st.color || '#2563EB' }}>
                    {st.code}
                  </span>
                </div>
                <div className="text-[10px] text-foreground-subtle">
                  Category: {st.category || 'GENERAL'} · TAT: {st.default_tat_hours || 24}h · Icon: {st.icon}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mastersSubTab === 'case_statuses' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-foreground-subtle">{caseStatuses.length} Case outcome statuses</span>
            <button
              onClick={() => {
                setStatusForm({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#10B981', type: 'CASE' });
                setStatusModal(true);
              }}
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Case Status
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {caseStatuses.map((cs) => (
              <div key={cs.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-surface">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cs.color || '#10B981' }} />
                    <span className="text-xs font-bold text-foreground">{cs.name}</span>
                  </div>
                  <div className="text-[10px] text-foreground-subtle">
                    Category: <span className="font-mono">{cs.category}</span> · Contacted: {cs.counts_as_contacted ? 'Yes' : 'No'} · Closes: {cs.closes_followup ? 'Yes' : 'No'} · Retry: {cs.retry_allowed ? 'Yes' : 'No'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mastersSubTab === 'call_statuses' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-foreground-subtle">{callStatuses.length} Call statuses</span>
            <button
              onClick={() => {
                setStatusForm({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#2563EB', type: 'CALL' });
                setStatusModal(true);
              }}
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Call Status
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {callStatuses.map((cls) => (
              <div key={cls.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-surface">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cls.color || '#2563EB' }} />
                    <span className="text-xs font-bold text-foreground">{cls.name}</span>
                  </div>
                  <div className="text-[10px] text-foreground-subtle">
                    Category: <span className="font-mono">{cls.category}</span> · Contacted: {cls.counts_as_contacted ? 'Yes' : 'No'} · Closes: {cls.closes_followup ? 'Yes' : 'No'} · Retry: {cls.retry_allowed ? 'Yes' : 'No'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mastersSubTab === 'complaint_categories' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-foreground-subtle">{complaintCategories.length} Categories</span>
            <button
              onClick={() => setCategoryModal(true)}
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Category
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {complaintCategories.map((cat) => (
              <div key={cat.id} className="p-3 rounded-lg border border-border bg-background-surface space-y-1">
                <div className="text-xs font-bold text-foreground">{cat.name}</div>
                <div className="text-[10px] text-foreground-subtle">
                  Severity: <span className="font-semibold text-amber-600">{cat.severity_level}</span> · Default SLA: {cat.default_sla_hours}h
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
