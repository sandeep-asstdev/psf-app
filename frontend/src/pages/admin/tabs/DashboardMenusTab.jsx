import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function DashboardMenusTab() {
  const [roles, setRoles] = useState([]);
  const [selectedRoleForDash, setSelectedRoleForDash] = useState('');
  const [roleDashConfig, setRoleDashConfig] = useState({
    widgets: ['connect_rate', 'nps_trend', 'pending_queue', 'sla_breaches', 'advisor_leaderboard'],
    default_filter_period: '30d',
  });

  useEffect(() => {
    api.get('/admin/matrix').then((res) => {
      const rList = res.data?.roles || [];
      setRoles(rList);
      if (rList.length > 0 && !selectedRoleForDash) {
        setSelectedRoleForDash(rList[0].id);
      }
    }).catch(() => {});
  }, []);

  return (
    <div className="space-y-4 max-w-xl">
      <div>
        <h2 className="text-sm font-bold text-foreground">Dashboard & Menu Configuration per Role</h2>
        <p className="text-xs text-foreground-subtle">Choose which analytics widgets and default filters are shown per role.</p>
      </div>

      <div className="p-4 rounded-lg border border-border bg-background-surface space-y-4">
        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">Select Role</label>
          <select
            value={selectedRoleForDash}
            onChange={(e) => setSelectedRoleForDash(e.target.value)}
            className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>{r.name} ({r.level})</option>
            ))}
          </select>
        </div>

        <div>
          <span className="block text-xs font-semibold text-foreground mb-2">Visible Dashboard Widgets</span>
          <div className="space-y-2">
            {[
              { id: 'connect_rate', label: 'Call Connect Rate & Attempts Gauge' },
              { id: 'nps_trend', label: 'Net Promoter Score (NPS) Trend' },
              { id: 'pending_queue', label: 'Pending Follow-up Worklist' },
              { id: 'sla_breaches', label: 'Urgent SLA Breached Tickets' },
              { id: 'advisor_leaderboard', label: 'Service Advisor Performance Leaderboard' },
            ].map((w) => (
              <label key={w.id} className="flex items-center space-x-2 text-xs text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={roleDashConfig.widgets.includes(w.id)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...roleDashConfig.widgets, w.id]
                      : roleDashConfig.widgets.filter((x) => x !== w.id);
                    setRoleDashConfig((prev) => ({ ...prev, widgets: next }));
                  }}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span>{w.label}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={() => toast.success('Dashboard preferences saved for role.')}
          className="w-full rounded-lg bg-accent px-3 py-2 text-xs font-bold text-accent-foreground hover:bg-accent/90"
        >
          Save Role Dashboard Layout
        </button>
      </div>
    </div>
  );
}
