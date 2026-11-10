import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function CustomFieldsTab() {
  const [customFields, setCustomFields] = useState([]);
  const [selectedEntityForCustomField, setSelectedEntityForCustomField] = useState('JOB_CARD');
  const [customFieldModal, setCustomFieldModal] = useState(false);
  const [newCustomField, setNewCustomField] = useState({
    entity_name: 'JOB_CARD',
    brand_id: '',
    field_name: '',
    field_label: '',
    field_type: 'TEXT',
    is_required: false,
    default_value: '',
  });

  const loadCustomFields = async () => {
    try {
      const res = await api.get(`/admin/custom-fields?entity_name=${selectedEntityForCustomField}`);
      setCustomFields(res.data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadCustomFields();
  }, [selectedEntityForCustomField]);

  const handleAddCustomField = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/custom-fields', {
        entity_name: newCustomField.entity_name,
        brand_id: newCustomField.brand_id || null,
        field_name: newCustomField.field_name.trim().toLowerCase().replace(/\s+/g, '_'),
        field_label: newCustomField.field_label.trim(),
        field_type: newCustomField.field_type,
        is_required: newCustomField.is_required,
        default_value: newCustomField.default_value || null,
      });
      toast.success(`Custom field '${newCustomField.field_label}' created.`);
      setCustomFieldModal(false);
      setNewCustomField({ entity_name: selectedEntityForCustomField, brand_id: '', field_name: '', field_label: '', field_type: 'TEXT', is_required: false, default_value: '' });
      loadCustomFields();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add custom field');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <h2 className="text-sm font-bold text-foreground">Dynamic Custom Fields (JSONB)</h2>
          <select
            value={selectedEntityForCustomField}
            onChange={(e) => setSelectedEntityForCustomField(e.target.value)}
            className="rounded-lg border border-border bg-background-base px-2.5 py-1 text-xs text-foreground"
          >
            <option value="JOB_CARD">Job Cards (JSONB)</option>
            <option value="CALL">Call Attempts (JSONB)</option>
            <option value="COMPLAINT">Complaints (JSONB)</option>
          </select>
        </div>
        <button
          onClick={() => setCustomFieldModal(true)}
          className="flex items-center space-x-1.5 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Add Custom Field</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
        <table className="w-full text-left text-xs">
          <thead className="bg-background-base text-foreground font-semibold border-b border-border">
            <tr>
              <th className="py-2.5 px-4">Field Key</th>
              <th className="py-2.5 px-3">Label</th>
              <th className="py-2.5 px-3">Data Type</th>
              <th className="py-2.5 px-3">Required</th>
              <th className="py-2.5 px-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {customFields.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-4 text-center text-foreground-subtle">
                  No custom fields defined for {selectedEntityForCustomField}. Add field definitions to extend forms.
                </td>
              </tr>
            ) : (
              customFields.map((f) => (
                <tr key={f.id} className="hover:bg-background-hover/50">
                  <td className="py-2 px-4 font-mono font-semibold text-accent">{f.field_name}</td>
                  <td className="py-2 px-3 text-foreground">{f.field_label}</td>
                  <td className="py-2 px-3 font-mono text-foreground-subtle">{f.field_type}</td>
                  <td className="py-2 px-3">{f.is_required ? 'Yes' : 'No'}</td>
                  <td className="py-2 px-3">
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">Active</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {customFieldModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Add Custom Field to {selectedEntityForCustomField}</h3>
            <form onSubmit={handleAddCustomField} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Field JSON Key</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. extended_warranty_no"
                  value={newCustomField.field_name}
                  onChange={(e) => setNewCustomField((prev) => ({ ...prev, field_name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Field Display Label</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Extended Warranty Policy Number"
                  value={newCustomField.field_label}
                  onChange={(e) => setNewCustomField((prev) => ({ ...prev, field_label: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Data Type</label>
                <select
                  value={newCustomField.field_type}
                  onChange={(e) => setNewCustomField((prev) => ({ ...prev, field_type: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                >
                  <option value="TEXT">Text String</option>
                  <option value="NUMBER">Numeric Value</option>
                  <option value="BOOLEAN">Boolean Toggle</option>
                  <option value="DATE">Calendar Date</option>
                  <option value="DROPDOWN">Dropdown List</option>
                </select>
              </div>
              <label className="flex items-center space-x-2 text-xs text-foreground cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={newCustomField.is_required}
                  onChange={(e) => setNewCustomField((prev) => ({ ...prev, is_required: e.target.checked }))}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span>Mandatory Required Field</span>
              </label>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCustomFieldModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  Create Field
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
