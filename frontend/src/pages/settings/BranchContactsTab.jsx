/**
 * ============================================================================
 * FILE PURPOSE: Branch Contacts & Escalation Matrix Settings Tab.
 * Allows configuring contact phone numbers, emails, and escalation managers for each workshop branch.
 * 
 * KEY RESPONSIBILITIES:
 * - Lists workshop branches with phone, email, and manager contact details.
 * - Allows updating branch escalation contact points for unresolved complaints.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Changes not saving
 *   -> Cause: User lacks `settings.manage` permission.
 *   -> What should you do: Ensure you are logged in as Super Admin or Dealer Admin.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  PhoneCall,
  User,
  Building2,
  Mail,
  Bell,
  Plus,
  Trash2,
  Edit,
  AlertTriangle,
  CheckCircle,
  Search,
  RefreshCw,
  Phone,
  ShieldAlert,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

const AVAILABLE_ROLES = [
  { value: 'SERVICE_MANAGER', label: 'Service Manager (SM)' },
  { value: 'CRE_LEAD', label: 'CRE Team Lead / Manager' },
  { value: 'SERVICE_ADVISOR', label: 'Service Advisor (SA)' },
  { value: 'BRANCH_HEAD', label: 'General / Branch Manager' },
];

const NOTIFICATION_OPTIONS = [
  { value: 'complaint', label: 'Complaint Escalations (Instant)' },
  { value: 'low_rating', label: 'Low Rating Alert (Rating <= 8 or 9)' },
  { value: 'daily_summary', label: 'Daily Workshop Summary' },
];

export default function BranchContactsTab({ branches = [], brands = [] }) {
  const [loading, setLoading] = useState(true);
  const [contacts, setContacts] = useState([]);
  const [missingBranches, setMissingBranches] = useState([]);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [roleFilter, setRoleFilter] = useState('ALL');

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingContact, setEditingContact] = useState(null);
  const [formBranchId, setFormBranchId] = useState('');
  const [formRole, setFormRole] = useState('SERVICE_MANAGER');
  const [formName, setFormName] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formNotifyOn, setFormNotifyOn] = useState(['complaint', 'low_rating']);
  const [formIsActive, setFormIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async () => {
    try {
      setLoading(true);
      const res = await api.get('/masters/branch-contacts');
      setContacts(res.data.items || []);
      setMissingBranches(res.data.missing_branches || []);
    } catch (err) {
      toast.error('Failed to load branch contacts: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = (presetBranchId = '') => {
    setEditingContact(null);
    setFormBranchId(presetBranchId || (branches.length > 0 ? branches[0].id : ''));
    setFormRole('SERVICE_MANAGER');
    setFormName('');
    setFormPhone('');
    setFormEmail('');
    setFormNotifyOn(['complaint', 'low_rating']);
    setFormIsActive(true);
    setShowModal(true);
  };

  const handleOpenEdit = (contact) => {
    setEditingContact(contact);
    setFormBranchId(contact.branch_id);
    setFormRole(contact.role);
    setFormName(contact.name);
    setFormPhone(contact.phone || '');
    setFormEmail(contact.email || '');
    setFormNotifyOn(
      contact.notify_on
        ? contact.notify_on.split(',').map((s) => s.trim()).filter(Boolean)
        : ['complaint', 'low_rating']
    );
    setFormIsActive(contact.is_active);
    setShowModal(true);
  };

  const handleToggleNotify = (val) => {
    setFormNotifyOn((prev) =>
      prev.includes(val) ? prev.filter((item) => item !== val) : [...prev, val]
    );
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formBranchId) {
      toast.error('Please select a branch');
      return;
    }
    if (!formName.trim()) {
      toast.error('Contact person name is required');
      return;
    }
    if (!formPhone.trim() || formPhone.trim().length < 10) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        branch_id: formBranchId,
        role: formRole,
        name: formName.trim(),
        phone: formPhone.trim(),
        email: formEmail.trim() || null,
        notify_on: formNotifyOn.join(','),
        is_active: formIsActive,
      };

      if (editingContact) {
        await api.put(`/masters/branch-contacts/${editingContact.id}`, payload);
        toast.success('Branch contact updated successfully');
      } else {
        await api.post('/masters/branch-contacts', payload);
        toast.success('Branch contact added successfully');
      }

      setShowModal(false);
      fetchContacts();
    } catch (err) {
      toast.error(
        (editingContact ? 'Update failed: ' : 'Creation failed: ') +
          (err.response?.data?.detail || err.message)
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (contact) => {
    if (!window.confirm(`Are you sure you want to remove contact ${contact.name} (${contact.role})?`)) {
      return;
    }
    try {
      await api.delete(`/masters/branch-contacts/${contact.id}`);
      toast.success('Contact deleted successfully');
      fetchContacts();
    } catch (err) {
      toast.error('Failed to delete contact: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Filtered Contacts
  const filteredContacts = useMemo(() => {
    return contacts.filter((c) => {
      if (branchFilter !== 'ALL' && c.branch_id !== branchFilter) return false;
      if (roleFilter !== 'ALL' && c.role !== roleFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const bName = (c.branch_name || '').toLowerCase();
        const cName = (c.name || '').toLowerCase();
        const cPhone = (c.phone || '').toLowerCase();
        const dms = (c.dms_code || '').toLowerCase();
        if (!bName.includes(q) && !cName.includes(q) && !cPhone.includes(q) && !dms.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [contacts, branchFilter, roleFilter, searchQuery]);

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Action */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <PhoneCall className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Branch Escalation & Service Manager Contacts
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Configure Service Managers and workshop heads to automatically receive WhatsApp & SMS alerts upon complaint registration or low customer rating.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchContacts}
            title="Refresh List"
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            type="button"
            onClick={() => handleOpenAdd()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 px-4 py-2 text-xs font-semibold text-white shadow-sm transition"
          >
            <Plus className="h-4 w-4" />
            Add Contact
          </button>
        </div>
      </div>

      {/* WARNING BANNER: Missing Branch Contacts */}
      {missingBranches.length > 0 && (
        <div className="rounded-xl border border-amber-300 dark:border-amber-800/80 bg-amber-50/80 dark:bg-amber-950/40 p-4 text-xs shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <div>
                <span className="font-bold text-amber-900 dark:text-amber-200">
                  Missing Service Contacts Warning: {missingBranches.length} Active Branches Have No Contact Number
                </span>
                <p className="text-amber-800 dark:text-amber-300/90 text-[11px] mt-0.5">
                  Complaints registered for these workshops cannot be automatically escalated via WhatsApp/SMS to local Service Managers. Click any branch below to configure its manager:
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5 pt-1">
                {missingBranches.map((br) => (
                  <button
                    key={br.branch_id}
                    type="button"
                    onClick={() => handleOpenAdd(br.branch_id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-300 font-medium text-[11px] hover:border-amber-400 hover:shadow-xs transition"
                    title={`Click to add contact for ${br.name}`}
                  >
                    <span>{br.name}</span>
                    {br.dms_code && (
                      <span className="text-[10px] text-amber-600 dark:text-amber-400">
                        ({br.dms_code})
                      </span>
                    )}
                    <Plus className="h-3 w-3 text-blue-600" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm text-xs">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          {/* Search */}
          <div className="relative min-w-[200px] flex-1 max-w-xs">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search branch, name, DMS code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Branch Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Branch:</span>
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-white"
            >
              <option value="ALL">All Branches ({contacts.length})</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} {b.dms_code ? `(${b.dms_code})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Role Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-white"
            >
              <option value="ALL">All Roles</option>
              {AVAILABLE_ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="text-slate-400 text-xs">
          Showing <strong>{filteredContacts.length}</strong> of <strong>{contacts.length}</strong> contacts
        </div>
      </div>

      {/* Contacts Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            <span className="text-xs">Loading branch contacts...</span>
          </div>
        ) : filteredContacts.length === 0 ? (
          <div className="py-16 text-center text-slate-400 space-y-2">
            <User className="h-10 w-10 mx-auto text-slate-300 dark:text-slate-600" />
            <p className="text-sm font-semibold">No branch contacts found</p>
            <p className="text-xs">Try adjusting your filters or click "Add Contact" to register one.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Branch / Workshop</th>
                  <th className="py-3 px-4">Contact Person & Role</th>
                  <th className="py-3 px-4">Phone (Encrypted)</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Alert Triggers</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {filteredContacts.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition"
                  >
                    {/* Branch */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {c.branch_name || 'Unassigned'}
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                        {c.dms_code && (
                          <span className="px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[10px]">
                            DMS: {c.dms_code}
                          </span>
                        )}
                        {c.branch_code && <span>• {c.branch_code}</span>}
                      </div>
                    </td>

                    {/* Person & Role */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-800 dark:text-slate-200">
                        {c.name}
                      </div>
                      <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        {c.role.replace(/_/g, ' ')}
                      </span>
                    </td>

                    {/* Phone */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300 font-mono">
                        <Phone className="h-3.5 w-3.5 text-slate-400" />
                        <span>{c.phone_masked || c.phone || 'N/A'}</span>
                      </div>
                    </td>

                    {/* Email */}
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {c.email ? (
                        <div className="flex items-center gap-1">
                          <Mail className="h-3 w-3 text-slate-400" />
                          <span>{c.email}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>

                    {/* Notify on */}
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {(c.notify_on || 'complaint,low_rating').split(',').map((tag) => {
                          const cleanTag = tag.trim();
                          if (!cleanTag) return null;
                          return (
                            <span
                              key={cleanTag}
                              className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            >
                              {cleanTag === 'complaint'
                                ? '🚨 Complaints'
                                : cleanTag === 'low_rating'
                                ? '⚠️ Low Rating'
                                : '📋 Daily Digest'}
                            </span>
                          );
                        })}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          c.is_active
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                        }`}
                      >
                        {c.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(c)}
                          title="Edit Contact"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(c)}
                          title="Delete Contact"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-red-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ADD / EDIT CONTACT MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <PhoneCall className="h-5 w-5 text-blue-600" />
                {editingContact ? 'Edit Branch Contact' : 'Add New Branch Contact'}
              </h3>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4 text-xs">
              {/* Branch */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Workshop Branch *
                </label>
                <select
                  value={formBranchId}
                  onChange={(e) => setFormBranchId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                  required
                >
                  <option value="">Select Branch...</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} {b.dms_code ? `[DMS: ${b.dms_code}]` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* Role & Name */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Role *
                  </label>
                  <select
                    value={formRole}
                    onChange={(e) => setFormRole(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                    required
                  >
                    {AVAILABLE_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Contact Person Name *
                  </label>
                  <input
                    type="text"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Ramesh Patil"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                    required
                  />
                </div>
              </div>

              {/* Phone & Email */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Phone Number (10 digits) *
                  </label>
                  <input
                    type="text"
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                    placeholder="9880012345"
                    maxLength={15}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 font-mono text-slate-900 dark:text-white"
                    required
                  />
                  <span className="text-[10px] text-slate-400">Stored with AES-128 encryption</span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Email Address (Optional)
                  </label>
                  <input
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder="sm.hubli@dealership.com"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Notification Triggers */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Automated Alert Triggers (WhatsApp / SMS)
                </label>
                <div className="space-y-1.5 rounded-lg border border-slate-200 dark:border-slate-800 p-3 bg-slate-50/50 dark:bg-slate-800/30">
                  {NOTIFICATION_OPTIONS.map((opt) => (
                    <label
                      key={opt.value}
                      className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300"
                    >
                      <input
                        type="checkbox"
                        checked={formNotifyOn.includes(opt.value)}
                        onChange={() => handleToggleNotify(opt.value)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Active Toggle */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="contactIsActiveChk"
                  checked={formIsActive}
                  onChange={(e) => setFormIsActive(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="contactIsActiveChk" className="font-semibold text-slate-700 dark:text-slate-300">
                  Active (Receive alerts)
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 transition shadow-sm"
                >
                  {submitting ? 'Saving...' : editingContact ? 'Update Contact' : 'Save Contact'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

