import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  Users,
  UserPlus,
  Search,
  KeyRound,
  Edit2,
  CheckCircle,
  XCircle,
  Shield,
  RefreshCw,
  Building2,
  Car,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function UserManagementPage() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [resetModalUser, setResetModalUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');

  // Form state
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: 'Welcome@123',
    phone: '',
    employee_id: '',
    role_id: '',
  });

  const currentUser = useAuthStore((state) => state.user);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, rolesRes] = await Promise.all([
        api.get(`/users?search=${encodeURIComponent(search)}`),
        api.get('/auth/roles'),
      ]);
      setUsers(usersRes.data.items || []);
      setRoles(rolesRes.data || []);
      if (rolesRes.data.length > 0 && !form.role_id) {
        setForm((prev) => ({ ...prev, role_id: rolesRes.data[0].id }));
      }
    } catch (err) {
      toast.error('Failed to load user directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [search]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.post('/users', form);
      toast.success(`User '${form.full_name}' created successfully`);
      setIsModalOpen(false);
      setForm({
        full_name: '',
        email: '',
        password: 'Welcome@123',
        phone: '',
        employee_id: '',
        role_id: roles[0]?.id || '',
      });
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create user';
      toast.error(msg);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetModalUser || !newPassword) return;

    try {
      await api.post(`/users/${resetModalUser.id}/reset-password`, {
        new_password: newPassword,
      });
      toast.success(`Password reset for ${resetModalUser.email}`);
      setResetModalUser(null);
      setNewPassword('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleToggleActive = async (user) => {
    try {
      await api.put(`/users/${user.id}`, {
        is_active: !user.is_active,
      });
      toast.success(`User account ${!user.is_active ? 'activated' : 'deactivated'}`);
      fetchData();
    } catch (err) {
      toast.error('Failed to update status');
    }
  };

  const filteredUsers = users.filter((u) => {
    if (roleFilter && u.role_id !== roleFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center space-x-2">
            <Users className="h-6 w-6 text-accent" />
            <span>Dealership User Management</span>
          </h1>
          <p className="text-xs text-foreground-muted mt-0.5">
            Manage CREs, Service Advisors, and Managers. Configure role permissions and workshop scopes.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center space-x-1.5 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-white hover:bg-accent-hover transition-colors shadow-subtle"
        >
          <UserPlus className="h-4 w-4" />
          <span>Add New Staff</span>
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-border bg-background-surface p-3 shadow-subtle">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground-subtle" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email or employee ID..."
            className="w-full rounded-lg border border-border bg-background-base py-1.5 pl-8 pr-3 text-xs text-foreground focus:border-border-focus focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-border bg-background-base py-1.5 px-3 text-xs text-foreground focus:border-border-focus focus:outline-none"
          >
            <option value="">All Roles</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          <button
            onClick={fetchData}
            title="Refresh list"
            className="rounded-lg border border-border bg-background-surface p-2 text-foreground-muted hover:bg-background-hover transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-background-surface shadow-subtle">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-background-base text-foreground-muted font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Staff Member</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Contact (Encrypted PII)</th>
                <th className="py-3 px-4">Scopes</th>
                <th className="py-3 px-4">Last Login</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-foreground-muted">
                    <RefreshCw className="mx-auto h-6 w-6 animate-spin text-accent mb-2" />
                    <span>Loading users...</span>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-foreground-muted">
                    No users found matching your search.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-background-hover/50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground">{u.full_name}</div>
                      <div className="text-[11px] text-foreground-muted">{u.email}</div>
                      {u.employee_id && (
                        <span className="font-mono text-[10px] text-foreground-subtle">
                          ID: {u.employee_id}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="rounded-md bg-accent-subtle px-2 py-0.5 text-[11px] font-semibold text-accent dark:bg-slate-800 dark:text-sky-300">
                        {u.role_name}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-foreground font-mono text-[11px]">
                      {u.phone || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="rounded-full bg-background-base px-2 py-0.5 text-[10px] text-foreground-muted font-medium border border-border">
                        {u.scopes_count > 0 ? `${u.scopes_count} Branch/Brand` : 'Global Dealer'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-foreground-muted">
                      {u.last_login_at
                        ? format(new Date(u.last_login_at), 'dd MMM yyyy, hh:mm a')
                        : 'Never logged in'}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={`inline-flex items-center space-x-1 rounded-full px-2 py-0.5 text-[10px] font-semibold transition-colors ${
                          u.is_active
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 hover:bg-rose-100 hover:text-rose-700'
                            : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 hover:bg-emerald-100 hover:text-emerald-700'
                        }`}
                      >
                        {u.is_active ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                        <span>{u.is_active ? 'Active' : 'Inactive'}</span>
                      </button>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setResetModalUser(u)}
                        title="Reset User Password"
                        className="rounded-lg p-1.5 text-foreground-muted hover:bg-background-hover hover:text-foreground transition-colors"
                      >
                        <KeyRound className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Create User */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-border bg-background-surface p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-bold text-foreground text-sm">Add New Staff Member</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1 text-foreground-muted hover:bg-background-hover"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-foreground mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="e.g. Rahul Verma"
                  className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                />
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="rahul@apexauto.com"
                  className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                />
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Initial Password</label>
                <input
                  type="password"
                  required
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium text-foreground mb-1">Phone Number</label>
                  <input
                    type="text"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="+91 98..."
                    className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                  />
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Employee ID</label>
                  <input
                    type="text"
                    value={form.employee_id}
                    onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
                    placeholder="EMP-102"
                    className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Assigned Role</label>
                <select
                  value={form.role_id}
                  onChange={(e) => setForm({ ...form, role_id: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} - {r.description}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-foreground-muted hover:bg-background-hover font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-4 py-1.5 text-white font-semibold hover:bg-accent-hover"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Reset Password */}
      {resetModalUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-background-surface p-5 shadow-card space-y-3">
            <h3 className="font-bold text-foreground text-sm">Reset Password</h3>
            <p className="text-xs text-foreground-muted">
              Enter a new password for <strong>{resetModalUser.email}</strong>.
            </p>
            <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password (min 6 chars)"
                className="w-full rounded-lg border border-border bg-background-base p-2 text-foreground focus:outline-none focus:border-border-focus"
              />
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setResetModalUser(null)}
                  className="rounded-lg border border-border px-3 py-1.5 text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-white font-semibold hover:bg-accent-hover"
                >
                  Confirm Reset
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
