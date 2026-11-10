import React, { useState, useEffect } from 'react';
import { Plus, Edit, ArrowUp, ArrowDown, Check, X, Shield, History, RefreshCw, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function ProgramsTab() {
  const [programs, setPrograms] = useState([]);
  const [brands, setBrands] = useState([]);
  const [questionnaires, setQuestionnaires] = useState([]);
  const [ratingScales, setRatingScales] = useState([]);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [loading, setLoading] = useState(false);

  // Modals & form state
  const [programModal, setProgramModal] = useState(false);
  const [editingProgram, setEditingProgram] = useState(null);
  const [programForm, setProgramForm] = useState({
    brand_id: '',
    code: '',
    label: '',
    enabled: true,
    trigger: 'ON_IMPORT',
    trigger_days: 0,
    channel: 'PHONE',
    questionnaire_id: '',
    rating_scale_id: '',
    max_attempts: 3,
    retry_gap_hours: 24,
    sla_hours: 48,
    sort_order: 0,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [pRes, bRes, qRes, rRes] = await Promise.all([
        api.get(`/config/programs${selectedBrandId ? `?brand_id=${selectedBrandId}` : ''}`),
        api.get('/masters/brands'),
        api.get('/questionnaires'),
        api.get('/masters/rating-scales'),
      ]);
      setPrograms(pRes.data);
      setBrands(bRes.data);
      setQuestionnaires(qRes.data);
      setRatingScales(rRes.data);
    } catch (err) {
      toast.error('Failed to load programs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBrandId]);

  const handleSaveProgram = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        brand_id: programForm.brand_id || null,
        code: programForm.code.toUpperCase().trim(),
        label: programForm.label.trim(),
        enabled: programForm.enabled,
        trigger: programForm.trigger.startsWith('AFTER_DAYS')
          ? `AFTER_DAYS(${programForm.trigger_days || 15})`
          : programForm.trigger,
        channel: programForm.channel,
        questionnaire_id: programForm.questionnaire_id || null,
        rating_scale_id: programForm.rating_scale_id || null,
        max_attempts: parseInt(programForm.max_attempts, 10) || 3,
        retry_gap_hours: parseInt(programForm.retry_gap_hours, 10) || 24,
        sla_hours: parseInt(programForm.sla_hours, 10) || 48,
        sort_order: parseInt(programForm.sort_order, 10) || 0,
      };

      if (editingProgram) {
        await api.put(`/config/programs/${editingProgram.id}`, payload);
        toast.success(`Program '${payload.label}' updated.`);
      } else {
        await api.post('/config/programs', payload);
        toast.success(`Program '${payload.label}' created.`);
      }

      setProgramModal(false);
      setEditingProgram(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save program');
    }
  };

  const handleToggleEnable = async (prog) => {
    try {
      await api.put(`/config/programs/${prog.id}`, { enabled: !prog.enabled });
      toast.success(`Program '${prog.label}' ${!prog.enabled ? 'enabled' : 'disabled'}.`);
      loadData();
    } catch (err) {
      toast.error('Failed to toggle program status');
    }
  };

  const handleMoveOrder = async (index, direction) => {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= programs.length) return;

    const updated = [...programs];
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;

    const orderedIds = updated.map((p, idx) => ({ id: p.id, sort_order: idx }));

    try {
      await api.put('/config/programs/reorder', { orders: orderedIds });
      toast.success('Program sort order updated.');
      loadData();
    } catch (err) {
      toast.error('Failed to update sort order');
    }
  };

  const handlePublishConfig = async () => {
    const note = prompt('Enter change summary note for this published revision (optional):') || '';
    try {
      await api.post('/config/publish', {
        config_type: 'PROGRAMS',
        scope: selectedBrandId ? 'BRAND' : 'DEALERSHIP',
        scope_id: selectedBrandId || null,
        note,
      });
      toast.success('Programs published and active! Redis cache invalidated.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish program config');
    }
  };

  const handleRollback = async () => {
    const reason = prompt('Mandatory reason for rollback:');
    if (!reason || reason.trim().length < 5) {
      toast.error('Rollback cancelled: reason is mandatory (min 5 chars).');
      return;
    }
    try {
      await api.post('/config/rollback', {
        config_type: 'PROGRAMS',
        scope: selectedBrandId ? 'BRAND' : 'DEALERSHIP',
        scope_id: selectedBrandId || null,
        reason,
      });
      toast.success('Configuration rolled back successfully.');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to rollback config');
    }
  };

  return (
    <div className="space-y-4">
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-background-surface p-4 rounded-lg border border-border">
        <div>
          <h2 className="text-sm font-bold text-foreground">Follow-Up Programs & Campaign Orchestration</h2>
          <p className="text-xs text-foreground-subtle">
            Configure automated follow-up programs per brand (PSF, Ather TNPS, Happiness Calling) without hard-coded survey logic.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={selectedBrandId}
            onChange={(e) => setSelectedBrandId(e.target.value)}
            className="rounded-lg border border-border bg-background-base px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="">All Brands / Default</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
            ))}
          </select>

          <button
            onClick={() => {
              setEditingProgram(null);
              setProgramForm({
                brand_id: selectedBrandId,
                code: '',
                label: '',
                enabled: true,
                trigger: 'ON_IMPORT',
                trigger_days: 0,
                channel: 'PHONE',
                questionnaire_id: questionnaires[0]?.id || '',
                rating_scale_id: ratingScales[0]?.id || '',
                max_attempts: 3,
                retry_gap_hours: 24,
                sla_hours: 48,
                sort_order: programs.length,
              });
              setProgramModal(true);
            }}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Add Program</span>
          </button>

          <button
            onClick={handlePublishConfig}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 shadow-subtle transition-colors"
            title="Publish revision & invalidate cache"
          >
            <Send className="h-3.5 w-3.5" />
            <span>Publish</span>
          </button>

          <button
            onClick={handleRollback}
            className="inline-flex items-center space-x-1 rounded-lg border border-border bg-background-base px-2.5 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
            title="Rollback to previous revision"
          >
            <History className="h-3.5 w-3.5" />
            <span>Rollback</span>
          </button>
        </div>
      </div>

      {/* Program List */}
      <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
        <table className="w-full text-left text-xs">
          <thead className="bg-background-base text-foreground font-semibold border-b border-border">
            <tr>
              <th className="py-2.5 px-3 w-16 text-center">Order</th>
              <th className="py-2.5 px-3">Program Code / Label</th>
              <th className="py-2.5 px-3">Brand Scope</th>
              <th className="py-2.5 px-3">Trigger Event</th>
              <th className="py-2.5 px-3">Channel</th>
              <th className="py-2.5 px-3">Attempts / SLA</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {programs.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-foreground-subtle">
                  No programs configured. Click "Add Program" or publish default pack.
                </td>
              </tr>
            ) : (
              programs.map((prog, idx) => (
                <tr key={prog.id} className="hover:bg-background-hover/50 transition-colors">
                  <td className="py-2.5 px-3 text-center">
                    <div className="flex items-center justify-center space-x-1">
                      <button
                        disabled={idx === 0}
                        onClick={() => handleMoveOrder(idx, -1)}
                        className="p-0.5 rounded hover:bg-background-base disabled:opacity-20"
                      >
                        <ArrowUp className="h-3 w-3" />
                      </button>
                      <span className="font-mono text-xs">{idx + 1}</span>
                      <button
                        disabled={idx === programs.length - 1}
                        onClick={() => handleMoveOrder(idx, 1)}
                        className="p-0.5 rounded hover:bg-background-base disabled:opacity-20"
                      >
                        <ArrowDown className="h-3 w-3" />
                      </button>
                    </div>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="font-mono font-bold text-accent">{prog.code}</div>
                    <div className="text-foreground text-[11px] font-semibold">{prog.label}</div>
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="rounded bg-background-base px-2 py-0.5 text-[11px] font-semibold text-foreground border border-border">
                      {prog.brand_name || 'Dealership Default'}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-foreground-subtle">
                    {prog.trigger}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold font-mono bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                      {prog.channel}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-foreground-subtle text-[11px]">
                    Max {prog.max_attempts} calls · Gap {prog.retry_gap_hours}h · SLA {prog.sla_hours}h
                  </td>
                  <td className="py-2.5 px-3">
                    <button
                      onClick={() => handleToggleEnable(prog)}
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold transition-colors ${
                        prog.enabled
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                      }`}
                    >
                      {prog.enabled ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                      <span>{prog.enabled ? 'Enabled' : 'Disabled'}</span>
                    </button>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => {
                        setEditingProgram(prog);
                        setProgramForm({
                          brand_id: prog.brand_id || '',
                          code: prog.code,
                          label: prog.label,
                          enabled: prog.enabled,
                          trigger: prog.trigger.startsWith('AFTER_DAYS') ? 'AFTER_DAYS' : prog.trigger,
                          trigger_days: prog.trigger.includes('(') ? parseInt(prog.trigger.match(/\d+/)?.[0] || '15', 10) : 0,
                          channel: prog.channel,
                          questionnaire_id: prog.questionnaire_id || '',
                          rating_scale_id: prog.rating_scale_id || '',
                          max_attempts: prog.max_attempts,
                          retry_gap_hours: prog.retry_gap_hours,
                          sla_hours: prog.sla_hours,
                          sort_order: prog.sort_order,
                        });
                        setProgramModal(true);
                      }}
                      className="p-1 rounded text-foreground-muted hover:text-accent hover:bg-background-hover"
                      title="Edit Program"
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Program Modal */}
      {programModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">
              {editingProgram ? 'Edit Follow-up Program' : 'Create Follow-up Program'}
            </h3>
            <form onSubmit={handleSaveProgram} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">OEM Brand Scope</label>
                  <select
                    value={programForm.brand_id}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, brand_id: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    <option value="">Dealership Default (All Brands)</option>
                    {brands.map((b) => (
                      <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Program Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. PSF, TNPS, HAPPINESS"
                    value={programForm.code}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Program Label (UI Name)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Post Service Follow-up (PSF), Ather Energy TNPS"
                  value={programForm.label}
                  onChange={(e) => setProgramForm((prev) => ({ ...prev, label: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Trigger Event</label>
                  <select
                    value={programForm.trigger}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, trigger: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    <option value="ON_IMPORT">ON_IMPORT (Immediate Day 1)</option>
                    <option value="AFTER_DAYS">AFTER_DAYS (Scheduled Delay)</option>
                    <option value="AFTER_COMPLAINT_CLOSURE">AFTER_COMPLAINT_CLOSURE (Reconfirmation)</option>
                  </select>
                </div>
                {programForm.trigger === 'AFTER_DAYS' && (
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">Delay (Days)</label>
                    <input
                      type="number"
                      min="1"
                      max="90"
                      value={programForm.trigger_days}
                      onChange={(e) => setProgramForm((prev) => ({ ...prev, trigger_days: parseInt(e.target.value, 10) }))}
                      className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                    />
                  </div>
                )}
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Delivery Channel</label>
                  <select
                    value={programForm.channel}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, channel: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    <option value="PHONE">PHONE (CRE Dialing)</option>
                    <option value="WHATSAPP">WHATSAPP (Automated Bot / Link)</option>
                    <option value="BOTH">BOTH (Multichannel)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Linked Questionnaire</label>
                  <select
                    value={programForm.questionnaire_id}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, questionnaire_id: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    <option value="">Default Questionnaire</option>
                    {questionnaires.map((q) => (
                      <option key={q.id} value={q.id}>{q.title} (v{q.version})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Linked Rating Scale</label>
                  <select
                    value={programForm.rating_scale_id}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, rating_scale_id: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    <option value="">Default Scale</option>
                    {ratingScales.map((s) => (
                      <option key={s.id} value={s.id}>{s.name} (Max {s.max_rating})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Max Attempts</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={programForm.max_attempts}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, max_attempts: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Retry Gap (Hours)</label>
                  <input
                    type="number"
                    min="1"
                    max="168"
                    value={programForm.retry_gap_hours}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, retry_gap_hours: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">SLA (Hours)</label>
                  <input
                    type="number"
                    min="1"
                    max="720"
                    value={programForm.sla_hours}
                    onChange={(e) => setProgramForm((prev) => ({ ...prev, sla_hours: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              </div>

              <label className="flex items-center space-x-2 text-xs text-foreground cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={programForm.enabled}
                  onChange={(e) => setProgramForm((prev) => ({ ...prev, enabled: e.target.checked }))}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span className="font-semibold">Program is Active & Auto-Creates Queues</span>
              </label>

              <div className="flex justify-end space-x-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setProgramModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  {editingProgram ? 'Update Program' : 'Create Program'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
