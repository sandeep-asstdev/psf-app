import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function DataCorrectionTab() {
  const [correctionForm, setCorrectionForm] = useState({
    entity_type: 'JOB_CARD',
    entity_id: '',
    field_updates: '{\n  "status": "COMPLETED"\n}',
    reason: '',
  });

  const handleExecuteDataCorrection = async (e) => {
    e.preventDefault();
    if (!correctionForm.reason || correctionForm.reason.trim().length < 5) {
      toast.error('Mandatory audit justification reason (min 5 chars) is required.');
      return;
    }
    try {
      let parsedUpdates;
      try {
        parsedUpdates = JSON.parse(correctionForm.field_updates);
      } catch (err) {
        toast.error('Invalid JSON in field updates');
        return;
      }

      const res = await api.post('/admin/data-correction', {
        entity_type: correctionForm.entity_type,
        entity_id: correctionForm.entity_id.trim(),
        field_updates: parsedUpdates,
        reason: correctionForm.reason.trim(),
      });
      toast.success(res.data.message || 'Record corrected and audited successfully!');
      setCorrectionForm((prev) => ({ ...prev, field_updates: '{}', reason: '' }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Data correction failed');
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="p-4 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200 text-xs">
        <div className="flex items-center space-x-2 font-bold mb-1">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <span>Super Admin Emergency Data Correction</span>
        </div>
        Direct record modification bypasses standard workflow restrictions. Every execution strictly logs the previous values, new values, user IP, and mandatory logged justification reason.
      </div>

      <form onSubmit={handleExecuteDataCorrection} className="space-y-4 p-5 rounded-lg border border-border bg-background-surface shadow-subtle">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">Entity Type</label>
            <select
              value={correctionForm.entity_type}
              onChange={(e) => setCorrectionForm((prev) => ({ ...prev, entity_type: e.target.value }))}
              className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
            >
              <option value="JOB_CARD">Job Card</option>
              <option value="CALL">Call Attempt</option>
              <option value="COMPLAINT">Complaint Ticket</option>
              <option value="CUSTOMER">Customer Profile</option>
              <option value="USER">User Account</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">Target Entity UUID</label>
            <input
              type="text"
              required
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              value={correctionForm.entity_id}
              onChange={(e) => setCorrectionForm((prev) => ({ ...prev, entity_id: e.target.value }))}
              className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">Field Updates (JSON Object)</label>
          <textarea
            rows={4}
            required
            value={correctionForm.field_updates}
            onChange={(e) => setCorrectionForm((prev) => ({ ...prev, field_updates: e.target.value }))}
            className="w-full rounded-lg border border-border bg-background-base p-2.5 text-xs text-foreground font-mono"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">
            Mandatory Audit Justification Reason <span className="text-status-danger">*</span>
          </label>
          <input
            type="text"
            required
            placeholder="e.g. Correcting customer phone per signed authorization request from branch manager"
            value={correctionForm.reason}
            onChange={(e) => setCorrectionForm((prev) => ({ ...prev, reason: e.target.value }))}
            className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
          />
        </div>

        <button
          type="submit"
          className="w-full rounded-lg bg-status-danger px-4 py-2 text-xs font-bold text-white hover:bg-status-danger/90 shadow-subtle transition-colors"
        >
          Apply Audited Correction
        </button>
      </form>
    </div>
  );
}
