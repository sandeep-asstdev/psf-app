import React, { useState, useEffect } from 'react';
import { RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function AuditHistoryTab() {
  const [auditLogs, setAuditLogs] = useState([]);
  const [configHistories, setConfigHistories] = useState([]);

  const loadAuditAndHistory = async () => {
    try {
      const [audRes, cfgRes] = await Promise.all([
        api.get('/admin/audit-logs?limit=50'),
        api.get('/admin/config-history?limit=30'),
      ]);
      setAuditLogs(audRes.data);
      setConfigHistories(cfgRes.data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadAuditAndHistory();
  }, []);

  const handleRollbackConfig = async (historyId) => {
    const reason = prompt('Please enter mandatory reason for config rollback:');
    if (!reason || reason.trim().length < 5) {
      toast.error('Rollback aborted: mandatory reason required.');
      return;
    }
    try {
      const res = await api.post(`/admin/config-history/${historyId}/rollback`, { reason });
      toast.success(res.data.message || 'Config rolled back successfully.');
      loadAuditAndHistory();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to rollback config');
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-foreground">Configuration Change History & 1-Click Rollback</h2>
          <span className="text-xs text-foreground-subtle">{configHistories.length} revisions</span>
        </div>
        <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
          <table className="w-full text-left text-xs">
            <thead className="bg-background-base text-foreground font-semibold border-b border-border">
              <tr>
                <th className="py-2.5 px-4">Config Type</th>
                <th className="py-2.5 px-3">Revision</th>
                <th className="py-2.5 px-3">Changed By</th>
                <th className="py-2.5 px-4">Reason</th>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-4 text-right">Rollback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {configHistories.map((cfg) => (
                <tr key={cfg.id} className="hover:bg-background-hover/50">
                  <td className="py-2 px-4 font-mono font-semibold text-accent">{cfg.config_type}</td>
                  <td className="py-2 px-3 font-mono">v{cfg.version}</td>
                  <td className="py-2 px-3">{cfg.changed_by_name}</td>
                  <td className="py-2 px-4 text-foreground-muted">{cfg.reason}</td>
                  <td className="py-2 px-3 text-foreground-subtle text-[11px]">
                    {new Date(cfg.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 px-4 text-right">
                    <button
                      onClick={() => handleRollbackConfig(cfg.id)}
                      className="inline-flex items-center space-x-1 rounded bg-rose-500/10 text-status-danger px-2 py-0.5 text-xs font-semibold hover:bg-rose-500/20"
                    >
                      <RotateCcw className="h-3 w-3" />
                      <span>Rollback</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-foreground">System Audit Trail</h2>
          <span className="text-xs text-foreground-subtle">{auditLogs.length} events logged</span>
        </div>
        <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle max-h-80 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-background-base text-foreground font-semibold border-b border-border sticky top-0">
              <tr>
                <th className="py-2.5 px-4">Action</th>
                <th className="py-2.5 px-3">Entity</th>
                <th className="py-2.5 px-3">User</th>
                <th className="py-2.5 px-4">Reason / Notes</th>
                <th className="py-2.5 px-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {auditLogs.map((a) => (
                <tr key={a.id} className="hover:bg-background-hover/50">
                  <td className="py-2 px-4 font-mono font-bold text-accent">{a.action}</td>
                  <td className="py-2 px-3">{a.entity_type} {a.entity_id ? `(${a.entity_id.slice(0, 8)})` : ''}</td>
                  <td className="py-2 px-3">{a.user_name || 'System'}</td>
                  <td className="py-2 px-4 text-foreground-muted">{a.reason || '—'}</td>
                  <td className="py-2 px-3 text-foreground-subtle text-[11px]">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

