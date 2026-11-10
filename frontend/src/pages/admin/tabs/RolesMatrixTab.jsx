import React, { useState, useEffect, useMemo } from 'react';
import { Key, Plus, Copy, Trash2, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function RolesMatrixTab({ isSuperAdmin }) {
  const [loading, setLoading] = useState(false);
  const [matrixData, setMatrixData] = useState({ roles: [], catalogue: [], permissions: [] });
  const [matrixChanges, setMatrixChanges] = useState({});
  const [newRoleModal, setNewRoleModal] = useState(false);
  const [cloneRoleModal, setCloneRoleModal] = useState(false);
  const [selectedRoleToClone, setSelectedRoleToClone] = useState(null);
  const [newRoleForm, setNewRoleForm] = useState({ name: '', description: '', level: 'L3' });
  const [cloneRoleForm, setCloneRoleForm] = useState({ new_name: '', description: '' });

  const loadMatrix = async () => {
    try {
      setLoading(true);
      const res = await api.get('/admin/matrix');
      setMatrixData(res.data);
      const initialMap = {};
      res.data.roles.forEach((r) => {
        initialMap[r.id] = {};
      });
      res.data.permissions.forEach((p) => {
        if (!initialMap[p.role_id]) initialMap[p.role_id] = {};
        initialMap[p.role_id][p.permission] = p.data_scope;
      });
      setMatrixChanges(initialMap);
    } catch (err) {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMatrix();
  }, []);

  const groupedCatalogue = useMemo(() => {
    const groups = {};
    (matrixData.catalogue || []).forEach((item) => {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    });
    return groups;
  }, [matrixData.catalogue]);

  const handleScopeToggle = (roleId, permKey, currentScope) => {
    setMatrixChanges((prev) => {
      const roleMap = { ...(prev[roleId] || {}) };
      if (!currentScope) {
        roleMap[permKey] = 'ALL';
      } else {
        const cycle = ['ALL', 'DEALERSHIP', 'ASSIGNED_BRANCHES', 'OWN', null];
        const nextIdx = (cycle.indexOf(currentScope) + 1) % cycle.length;
        const nextVal = cycle[nextIdx];
        if (nextVal) {
          roleMap[permKey] = nextVal;
        } else {
          delete roleMap[permKey];
        }
      }
      return { ...prev, [roleId]: roleMap };
    });
  };

  const handleSaveMatrixRole = async (roleId, roleName) => {
    const rolePerms = matrixChanges[roleId] || {};
    const payloadItems = Object.entries(rolePerms).map(([permission, data_scope]) => ({
      permission,
      data_scope,
    }));

    try {
      await api.put(`/admin/roles/${roleId}/permissions`, {
        permissions: payloadItems,
        reason: `Updated dynamic permission matrix for role ${roleName}`,
      });
      toast.success(`Updated matrix for '${roleName}' & invalidated Redis cache.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update permissions');
    }
  };

  const handleCreateRole = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/roles', {
        name: newRoleForm.name.toUpperCase().replace(/\s+/g, '_'),
        description: newRoleForm.description,
        level: newRoleForm.level,
        permissions: [],
      });
      toast.success(`Role '${newRoleForm.name}' created successfully`);
      setNewRoleModal(false);
      setNewRoleForm({ name: '', description: '', level: 'L3' });
      loadMatrix();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create role');
    }
  };

  const handleCloneRole = async (e) => {
    e.preventDefault();
    if (!selectedRoleToClone) return;
    try {
      await api.post(`/admin/roles/${selectedRoleToClone.id}/clone`, {
        new_name: cloneRoleForm.new_name.toUpperCase().replace(/\s+/g, '_'),
        description: cloneRoleForm.description,
      });
      toast.success(`Role cloned into '${cloneRoleForm.new_name}'`);
      setCloneRoleModal(false);
      setCloneRoleForm({ new_name: '', description: '' });
      loadMatrix();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to clone role');
    }
  };

  const handleDeleteRole = async (role) => {
    if (role.is_system || role.name === 'SUPER_ADMIN') {
      toast.error('System core roles cannot be deleted');
      return;
    }
    if (!confirm(`Are you sure you want to delete role '${role.name}'?`)) return;
    try {
      await api.delete(`/admin/roles/${role.id}`);
      toast.success(`Role '${role.name}' deleted.`);
      loadMatrix();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete role');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-foreground-subtle bg-background-base p-3 rounded-lg border border-border">
        <div>
          <span className="font-semibold text-foreground">Matrix Legend: </span>
          <span className="inline-block px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-mono text-[10px] mr-1.5 font-bold">ALL / DEALERSHIP</span>
          <span className="inline-block px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 font-mono text-[10px] mr-1.5 font-bold">ASSIGNED_BRANCHES</span>
          <span className="inline-block px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 font-mono text-[10px] mr-1.5 font-bold">OWN</span>
          <span>Click any badge to cycle scopes or toggle permission. Click the floppy icon to persist & invalidate Redis cache.</span>
        </div>
        <button
          onClick={() => setNewRoleModal(true)}
          className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors shrink-0 ml-4"
        >
          <Plus className="h-4 w-4" />
          <span>Add Role</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
        <table className="w-full text-left text-xs">
          <thead className="bg-background-base text-foreground font-semibold border-b border-border">
            <tr>
              <th className="py-3 px-4 min-w-[260px]">Resource Action Key</th>
              {matrixData.roles.map((r) => (
                <th key={r.id} className="py-3 px-3 text-center min-w-[150px] border-l border-border">
                  <div className="font-bold">{r.name}</div>
                  <div className="text-[10px] font-normal text-foreground-subtle">
                    {r.level} {r.is_system ? '· System' : ''}
                  </div>
                  <div className="mt-1 flex items-center justify-center space-x-1">
                    <button
                      onClick={() => handleSaveMatrixRole(r.id, r.name)}
                      title="Save & Invalidate Cache"
                      className="p-1 rounded hover:bg-background-hover text-emerald-600 dark:text-emerald-400 font-bold"
                    >
                      <Save className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedRoleToClone(r);
                        setCloneRoleForm({ new_name: `${r.name}_COPY`, description: `Cloned from ${r.name}` });
                        setCloneRoleModal(true);
                      }}
                      title="Clone Role"
                      className="p-1 rounded hover:bg-background-hover text-foreground-muted"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    {!r.is_system && r.name !== 'SUPER_ADMIN' && (
                      <button
                        onClick={() => handleDeleteRole(r)}
                        title="Delete Role"
                        className="p-1 rounded hover:bg-background-hover text-status-danger"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Object.entries(groupedCatalogue).map(([category, items]) => (
              <React.Fragment key={category}>
                <tr className="bg-background-base/60">
                  <td colSpan={matrixData.roles.length + 1} className="py-2 px-4 font-bold text-foreground text-xs uppercase tracking-wider bg-background-base/80">
                    {category}
                  </td>
                </tr>
                {items.map((item) => (
                  <tr key={item.key} className="hover:bg-background-hover/50 transition-colors">
                    <td className="py-2.5 px-4">
                      <div className="font-mono text-xs font-semibold text-accent">{item.key}</div>
                      <div className="text-foreground text-[11px] font-medium">{item.label}</div>
                      <div className="text-foreground-subtle text-[10px]">{item.description}</div>
                    </td>
                    {matrixData.roles.map((r) => {
                      const assignedScope = (matrixChanges[r.id] || {})[item.key];
                      const isSuper = r.name === 'SUPER_ADMIN';

                      return (
                        <td key={r.id} className="py-2.5 px-3 text-center border-l border-border">
                          {isSuper ? (
                            <span className="inline-block px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 font-mono text-[10px] font-bold">
                              ALL (L1)
                            </span>
                          ) : (
                            <button
                              onClick={() => handleScopeToggle(r.id, item.key, assignedScope)}
                              className={`px-2 py-1 rounded text-[10px] font-mono font-semibold transition-all ${
                                assignedScope === 'ALL' || assignedScope === 'DEALERSHIP'
                                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                                  : assignedScope === 'ASSIGNED_BRANCHES'
                                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300 border border-amber-300 dark:border-amber-700'
                                  : assignedScope === 'OWN'
                                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300 border border-purple-300 dark:border-purple-700'
                                  : 'bg-background-base text-foreground-subtle border border-dashed border-border hover:border-foreground-muted'
                              }`}
                            >
                              {assignedScope || '—'}
                            </button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Role Modal */}
      {newRoleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Add New Custom Role</h3>
            <form onSubmit={handleCreateRole} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Role Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. WORKSHOP_AUDITOR"
                  value={newRoleForm.name}
                  onChange={(e) => setNewRoleForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Hierarchy Level</label>
                <select
                  value={newRoleForm.level}
                  onChange={(e) => setNewRoleForm((prev) => ({ ...prev, level: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                >
                  <option value="L2">L2 CRE Admin (Dealership-wide)</option>
                  <option value="L3">L3 Branch Level (Scoped)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Role responsibilities and purpose"
                  value={newRoleForm.description}
                  onChange={(e) => setNewRoleForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setNewRoleModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  Create Role
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Clone Role Modal */}
      {cloneRoleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Clone Role '{selectedRoleToClone?.name}'</h3>
            <form onSubmit={handleCloneRole} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">New Role Name</label>
                <input
                  type="text"
                  required
                  value={cloneRoleForm.new_name}
                  onChange={(e) => setCloneRoleForm((prev) => ({ ...prev, new_name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Description</label>
                <input
                  type="text"
                  value={cloneRoleForm.description}
                  onChange={(e) => setCloneRoleForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCloneRoleModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  Clone Role
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

