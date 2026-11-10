import React, { useState, useEffect } from 'react';
import { Plus, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';
import { useAuthStore } from '../../../store/authStore';

export default function UsersTab({ isSuperAdmin }) {
  const { user, impersonate } = useAuthStore();
  const [usersList, setUsersList] = useState([]);
  const [roles, setRoles] = useState([]);
  const [userModal, setUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    email: '',
    full_name: '',
    password: 'Welcome@123',
    role_id: '',
    employee_id: '',
    phone: '',
    scopes: [],
  });
  const [resetPwdModal, setResetPwdModal] = useState(false);
  const [targetUserForPwd, setTargetUserForPwd] = useState(null);
  const [newPwdInput, setNewPwdInput] = useState('NewSecret@123');

  const [impersonateModal, setImpersonateModal] = useState(false);
  const [targetUserToImpersonate, setTargetUserToImpersonate] = useState(null);
  const [impersonateReason, setImpersonateReason] = useState('Super Admin workspace simulation & troubleshooting');

  const loadUsersAndRoles = async () => {
    try {
      const [uRes, mRes] = await Promise.all([
        api.get('/users?page_size=50'),
        api.get('/admin/matrix'),
      ]);
      setUsersList(uRes.data.items || []);
      setRoles(mRes.data?.roles || []);
      if (mRes.data?.roles?.length > 0 && !userForm.role_id) {
        setUserForm((prev) => ({ ...prev, role_id: mRes.data.roles[0].id }));
      }
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadUsersAndRoles();
  }, []);

  const handleSaveUser = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await api.put(`/users/${editingUser.id}`, {
          full_name: userForm.full_name,
          role_id: userForm.role_id,
          phone: userForm.phone || null,
          employee_id: userForm.employee_id || null,
        });
        toast.success(`User '${userForm.full_name}' updated.`);
      } else {
        await api.post('/users', {
          email: userForm.email.toLowerCase().trim(),
          full_name: userForm.full_name,
          password: userForm.password,
          role_id: userForm.role_id || roles[0]?.id,
          employee_id: userForm.employee_id || null,
          phone: userForm.phone || null,
        });
        toast.success(`User '${userForm.email}' created successfully.`);
      }
      setUserModal(false);
      setEditingUser(null);
      setUserForm({ email: '', full_name: '', password: 'Welcome@123', role_id: '', employee_id: '', phone: '', scopes: [] });
      loadUsersAndRoles();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save user');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!targetUserForPwd) return;
    try {
      await api.post(`/users/${targetUserForPwd.id}/reset-password`, {
        new_password: newPwdInput,
      });
      toast.success(`Password reset successfully for ${targetUserForPwd.email}`);
      setResetPwdModal(false);
      setTargetUserForPwd(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleDeactivateUser = async (u) => {
    if (u.id === user?.id) {
      toast.error('Lockout protection: You cannot deactivate your own account.');
      return;
    }
    if (!confirm(`Are you sure you want to deactivate user '${u.email}'?`)) return;
    try {
      await api.delete(`/users/${u.id}`);
      toast.success(`User '${u.email}' deactivated.`);
      loadUsersAndRoles();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate user');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-foreground">User Management & "View As User" Simulation</h2>
          <span className="text-xs text-foreground-subtle">{usersList.length} Accounts registered</span>
        </div>
        <button
          onClick={() => {
            setEditingUser(null);
            setUserForm({ email: '', full_name: '', password: 'Welcome@123', role_id: roles[0]?.id || '', employee_id: '', phone: '', scopes: [] });
            setUserModal(true);
          }}
          className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Add User</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-background-surface shadow-subtle">
        <table className="w-full text-left text-xs">
          <thead className="bg-background-base text-foreground font-semibold border-b border-border">
            <tr>
              <th className="py-3 px-4">Name & Email</th>
              <th className="py-3 px-3">Role</th>
              <th className="py-3 px-3">Scopes</th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {usersList.map((u) => (
              <tr key={u.id} className="hover:bg-background-hover/50 transition-colors">
                <td className="py-2.5 px-4">
                  <div className="font-semibold text-foreground">{u.full_name}</div>
                  <div className="text-foreground-subtle text-[11px]">{u.email}</div>
                </td>
                <td className="py-2.5 px-3">
                  <span className="rounded bg-accent-subtle px-2 py-0.5 text-[11px] font-semibold text-accent font-mono">
                    {u.role_name}
                  </span>
                </td>
                <td className="py-2.5 px-3 text-foreground-subtle">
                  {u.scopes_count > 0 ? `${u.scopes_count} Scopes` : 'Tenant-wide'}
                </td>
                <td className="py-2.5 px-3">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    u.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-rose-100 text-rose-700'
                  }`}>
                    {u.is_active ? 'Active' : 'Deactivated'}
                  </span>
                </td>
                <td className="py-2.5 px-4 text-right space-x-2">
                  <button
                    onClick={() => {
                      setTargetUserForPwd(u);
                      setResetPwdModal(true);
                    }}
                    className="text-foreground-muted hover:text-accent font-medium text-[11px]"
                  >
                    Reset Pwd
                  </button>
                  {u.id !== user?.id && (
                    <button
                      onClick={() => handleDeactivateUser(u)}
                      className="text-status-danger hover:underline font-medium text-[11px]"
                    >
                      Deactivate
                    </button>
                  )}
                  {isSuperAdmin && u.id !== user?.id && (
                    <button
                      onClick={() => {
                        setTargetUserToImpersonate(u);
                        setImpersonateModal(true);
                      }}
                      className="inline-flex items-center space-x-1 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 px-2.5 py-1 text-xs font-semibold hover:bg-amber-500/20 transition-colors border border-amber-500/30"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span>View as User</span>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add / Edit User Modal */}
      {userModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">{editingUser ? 'Edit User' : 'Create New Personnel Account'}</h3>
            <form onSubmit={handleSaveUser} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  disabled={!!editingUser}
                  placeholder="employee@apexauto.com"
                  value={userForm.email}
                  onChange={(e) => setUserForm((prev) => ({ ...prev, email: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe"
                  value={userForm.full_name}
                  onChange={(e) => setUserForm((prev) => ({ ...prev, full_name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              {!editingUser && (
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Default Password</label>
                  <input
                    type="password"
                    required
                    value={userForm.password}
                    onChange={(e) => setUserForm((prev) => ({ ...prev, password: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Role Assignment</label>
                <select
                  value={userForm.role_id}
                  onChange={(e) => setUserForm((prev) => ({ ...prev, role_id: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>{r.name} ({r.level})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Employee ID</label>
                  <input
                    type="text"
                    placeholder="EMP-100"
                    value={userForm.employee_id}
                    onChange={(e) => setUserForm((prev) => ({ ...prev, employee_id: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+91 98765 00000"
                    value={userForm.phone}
                    onChange={(e) => setUserForm((prev) => ({ ...prev, phone: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setUserModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  {editingUser ? 'Update Account' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetPwdModal && targetUserForPwd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Reset Password for {targetUserForPwd.full_name}</h3>
            <form onSubmit={handleResetPassword} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">New Password</label>
                <input
                  type="text"
                  required
                  value={newPwdInput}
                  onChange={(e) => setNewPwdInput(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResetPwdModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  Confirm Reset
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Impersonation Modal */}
      {impersonateModal && targetUserToImpersonate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-amber-300 dark:border-amber-800 bg-background-surface p-6 shadow-xl space-y-4">
            <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400 font-bold text-sm">
              <Eye className="h-5 w-5" />
              <span>Simulate User: {targetUserToImpersonate.full_name}</span>
            </div>
            <p className="text-xs text-foreground-subtle">
              You will view the PSF suite exactly through the eyes and permissions of <strong>{targetUserToImpersonate.email}</strong> ({targetUserToImpersonate.role_name}).
            </p>
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">Mandatory Simulation Reason</label>
              <input
                type="text"
                required
                value={impersonateReason}
                onChange={(e) => setImpersonateReason(e.target.value)}
                className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
              />
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setImpersonateModal(false)}
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setImpersonateModal(false);
                  const ok = await impersonate(targetUserToImpersonate.id, impersonateReason);
                  if (ok) window.location.href = '/';
                }}
                className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-700 shadow-subtle"
              >
                Start Simulation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
