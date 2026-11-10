import React, { useState, useEffect } from 'react';
import { Tag, Plus, Check, X } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function KpiTagsTab() {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    tag: '',
    label: '',
    description: '',
    is_active: true,
  });

  const loadTags = async () => {
    try {
      setLoading(true);
      const res = await api.get('/config/kpi-tags');
      setTags(res.data);
    } catch (err) {
      toast.error('Failed to load KPI tags');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTags();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      await api.post('/config/kpi-tags', {
        tag: form.tag.toUpperCase().trim().replace(/\s+/g, '_'),
        label: form.label.trim(),
        description: form.description?.trim() || null,
        is_active: form.is_active,
      });
      toast.success(`KPI Tag '${form.label}' created.`);
      setModalOpen(false);
      setForm({ tag: '', label: '', description: '', is_active: true });
      loadTags();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create KPI tag');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-background-surface p-4 rounded-lg border border-border">
        <div>
          <h2 className="text-sm font-bold text-foreground">Operational KPI Tags & Survey Categories</h2>
          <p className="text-xs text-foreground-subtle">
            Manage tags (Service Quality, Timeliness, Washing, Billing, Advisor Behavior) attached to questions for normalized analytics.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors shrink-0"
        >
          <Plus className="h-4 w-4" />
          <span>Add KPI Tag</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
        <table className="w-full text-left text-xs">
          <thead className="bg-background-base text-foreground font-semibold border-b border-border">
            <tr>
              <th className="py-2.5 px-4">Tag Code</th>
              <th className="py-2.5 px-3">Display Label</th>
              <th className="py-2.5 px-3">Description</th>
              <th className="py-2.5 px-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {tags.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-foreground-subtle">
                  No KPI tags configured.
                </td>
              </tr>
            ) : (
              tags.map((t) => (
                <tr key={t.id} className="hover:bg-background-hover/50 transition-colors">
                  <td className="py-2.5 px-4">
                    <span className="font-mono text-xs font-bold text-accent px-2 py-0.5 rounded bg-accent-subtle">
                      {t.tag}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-foreground">{t.label}</td>
                  <td className="py-2.5 px-3 text-foreground-subtle text-[11px]">{t.description || '—'}</td>
                  <td className="py-2.5 px-3">
                    <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      t.is_active ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {t.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Add New KPI Tag</h3>
            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Tag Key (Uppercase Snake Case)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. BILLING_TRANSPARENCY"
                  value={form.tag}
                  onChange={(e) => setForm((prev) => ({ ...prev, tag: e.target.value.toUpperCase() }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Display Label</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Billing Transparency & Cost"
                  value={form.label}
                  onChange={(e) => setForm((prev) => ({ ...prev, label: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Explains what this KPI measures across survey questions"
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base p-2 text-xs text-foreground"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  Create Tag
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

