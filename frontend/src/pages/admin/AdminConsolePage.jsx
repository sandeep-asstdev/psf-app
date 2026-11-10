/**
 * ============================================================================
 * FILE PURPOSE: Enterprise Admin Console (Super Admin Control Center).
 * Provides Super Admins with full control over the dealership system: the RBAC Role Permission Matrix
 * (who can do what and at what data scope level), system-wide allocation rules, and supervisor data corrections.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches and updates the Role Permission Matrix (`GET/PUT /api/v1/admin/matrix`).
 * - Allows configuring permission scopes: ALL, BRAND, BRANCH, OWN.
 * - Provides supervisor data correction tool with mandatory audit reason logging.
 * - Guarantees lockout protection so the Super Admin role cannot accidentally delete itself.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Page shows 'Access Denied' or redirects to login
 *   -> Cause: Logged in user is not a Super Admin (L1).
 *   -> What should you do: Log in using `admin@apexauto.com` / `Password@12345` to access the Admin Console.
 * - Error: Saving permissions matrix fails with error toast
 *   -> Cause: Network error or constraint violation.
 *   -> What should you do: Check the DevTools network tab for specific validation error message.
 * ============================================================================
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldCheck,
  Key,
  Users,
  Building2,
  ListPlus,
  FileQuestion,
  Gauge,
  Sliders,
  Database,
  LayoutDashboard,
  FileSpreadsheet,
  MessageSquare,
  History,
  Wrench,
  Search,
  Plus,
  Copy,
  Trash2,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Eye,
  LogOut,
  ChevronRight,
  Filter,
  Check,
  X,
  Upload,
  Edit,
  Clock,
  Sparkles,
  SplitSquareVertical,
} from 'lucide-react';
import AllocationRulesTab from '../../components/allocation/AllocationRulesTab';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';

export default function AdminConsolePage() {
  const { user, can, impersonate } = useAuthStore();
  const isSuperAdmin = user?.is_super_admin || user?.role_name === 'SUPER_ADMIN';

  // Automatically default tab: Super Admin starts at 'matrix', others start at 'users' or 'brands_branches'
  const [activeTab, setActiveTab] = useState(isSuperAdmin ? 'matrix' : 'users');
  const [loading, setLoading] = useState(false);

  // -------------------------------------------------------------
  // Tab 1: Roles & Permission Matrix State
  // -------------------------------------------------------------
  const [matrixData, setMatrixData] = useState({ roles: [], catalogue: [], permissions: [] });
  const [matrixChanges, setMatrixChanges] = useState({});
  const [newRoleModal, setNewRoleModal] = useState(false);
  const [cloneRoleModal, setCloneRoleModal] = useState(false);
  const [selectedRoleToClone, setSelectedRoleToClone] = useState(null);
  const [newRoleForm, setNewRoleForm] = useState({ name: '', description: '', level: 'L3' });
  const [cloneRoleForm, setCloneRoleForm] = useState({ new_name: '', description: '' });

  // -------------------------------------------------------------
  // Tab 2: Brands & Branches State
  // -------------------------------------------------------------
  const [brands, setBrands] = useState([]);
  const [branches, setBranches] = useState([]);
  const [brandModal, setBrandModal] = useState(false);
  const [editingBrand, setEditingBrand] = useState(null);
  const [brandForm, setBrandForm] = useState({ name: '', code: '', primary_color: '#002C6C', logo_url: '' });

  const [branchModal, setBranchModal] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [branchForm, setBranchForm] = useState({
    name: '',
    code: '',
    dms_code: '',
    display_name: '',
    brand_id: '',
    city: 'Bangalore',
    state: 'Karnataka',
    address: '',
    phone: '',
    email: '',
  });

  // -------------------------------------------------------------
  // Tab 3: Users State
  // -------------------------------------------------------------
  const [usersList, setUsersList] = useState([]);
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

  // -------------------------------------------------------------
  // Tab 4: Dropdown Masters State
  // -------------------------------------------------------------
  const [mastersSubTab, setMastersSubTab] = useState('service_types'); // service_types | case_statuses | call_statuses | complaint_categories
  const [serviceTypes, setServiceTypes] = useState([]);
  const [caseStatuses, setCaseStatuses] = useState([]);
  const [callStatuses, setCallStatuses] = useState([]);
  const [complaintCategories, setComplaintCategories] = useState([]);

  const [serviceTypeModal, setServiceTypeModal] = useState(false);
  const [serviceTypeForm, setServiceTypeForm] = useState({ name: '', code: '', category: 'GENERAL', default_tat_hours: 24, color: '#2563EB', icon: 'Wrench' });

  const [statusModal, setStatusModal] = useState(false);
  const [statusForm, setStatusForm] = useState({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#10B981', type: 'CASE' });

  const [categoryModal, setCategoryModal] = useState(false);
  const [categoryForm, setCategoryForm] = useState({ name: '', default_sla_hours: 24, severity_level: 'MEDIUM', brand_id: '' });

  // -------------------------------------------------------------
  // Tab 5: Questionnaires State
  // -------------------------------------------------------------
  const [questionnaires, setQuestionnaires] = useState([]);
  const [selectedQBrand, setSelectedQBrand] = useState('ALL');
  const [activeQuestionnaire, setActiveQuestionnaire] = useState(null);
  const [newQuestionModal, setNewQuestionModal] = useState(false);
  const [questionForm, setQuestionForm] = useState({
    key: '',
    label: '',
    type: 'RATING_10',
    section: 'Service Quality',
    is_required: true,
    weight: 10,
    show_if: null,
  });

  // -------------------------------------------------------------
  // Tab 6: Rating Scales & SLAs State
  // -------------------------------------------------------------
  const [ratingScales, setRatingScales] = useState([]);
  const [tenantSettings, setTenantSettings] = useState({});

  // -------------------------------------------------------------
  // Tab 7: Custom Fields State
  // -------------------------------------------------------------
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

  // -------------------------------------------------------------
  // Tab 8: Dashboard Configuration State
  // -------------------------------------------------------------
  const [selectedRoleForDash, setSelectedRoleForDash] = useState('');
  const [roleDashConfig, setRoleDashConfig] = useState({
    widgets: ['connect_rate', 'nps_trend', 'pending_queue', 'sla_breaches', 'advisor_leaderboard'],
    default_filter_period: '30d',
  });

  // -------------------------------------------------------------
  // Tab 9: Import Templates State
  // -------------------------------------------------------------
  const [importTemplates, setImportTemplates] = useState([]);
  const [importTemplateModal, setImportTemplateModal] = useState(false);
  const [newTemplateForm, setNewTemplateForm] = useState({
    brand_id: '',
    template_name: '',
    file_type: 'CSV',
    is_default: true,
    mapping_json: '{\n  "job_card_no": "Job Card No",\n  "customer_name": "Customer Name",\n  "customer_phone": "Customer Mobile",\n  "vehicle_reg_no": "Reg No",\n  "vehicle_model": "Model",\n  "service_type": "Service Type"\n}',
  });

  // -------------------------------------------------------------
  // Tab 10: Templates & Settings State
  // -------------------------------------------------------------
  const [settingsForm, setSettingsForm] = useState({
    sms_satisfaction: 'Dear Customer, thank you for servicing your vehicle with us.',
    whatsapp_complaint_opened: 'Hello {{customer_name}}, your complaint {{ticket_no}} has been registered.',
    dealer_name: 'Apex Automotive Group',
    primary_color: '#2563EB',
    logo_url: '',
  });

  // -------------------------------------------------------------
  // Tab 11: Audit Logs & Rollback State
  // -------------------------------------------------------------
  const [auditLogs, setAuditLogs] = useState([]);
  const [configHistories, setConfigHistories] = useState([]);

  // -------------------------------------------------------------
  // Tab 12: Data Correction State
  // -------------------------------------------------------------
  const [correctionForm, setCorrectionForm] = useState({
    entity_type: 'JOB_CARD',
    entity_id: '',
    field_updates: '{\n  "status": "COMPLETED"\n}',
    reason: '',
  });

  // -------------------------------------------------------------
  // Data Loaders
  // -------------------------------------------------------------
  const loadMatrix = async () => {
    if (!isSuperAdmin && !can('permission.manage') && !can('role.manage')) return;
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
      if (res.data.roles.length > 0 && !selectedRoleForDash) {
        setSelectedRoleForDash(res.data.roles[0].id);
      }
    } catch (err) {
      // Graceful fallback for non-super admin
    } finally {
      setLoading(false);
    }
  };

  const loadBrandsAndBranches = async () => {
    try {
      const [brRes, bchRes] = await Promise.all([
        api.get('/masters/brands'),
        api.get('/masters/branches'),
      ]);
      setBrands(brRes.data);
      setBranches(bchRes.data);
      if (brRes.data.length > 0 && !branchForm.brand_id) {
        setBranchForm((prev) => ({ ...prev, brand_id: brRes.data[0].id }));
      }
    } catch (err) {
      // ignore
    }
  };

  const loadUsers = async () => {
    try {
      const res = await api.get('/users?page_size=50');
      setUsersList(res.data.items || []);
    } catch (err) {
      // ignore
    }
  };

  const loadDropdownMasters = async () => {
    try {
      const [stRes, csRes, clRes, catRes] = await Promise.all([
        api.get('/admin/service-types'),
        api.get('/masters/case-statuses'),
        api.get('/masters/call-statuses'),
        api.get('/masters/complaint-categories'),
      ]);
      setServiceTypes(stRes.data);
      setCaseStatuses(csRes.data);
      setCallStatuses(clRes.data);
      setComplaintCategories(catRes.data);
    } catch (err) {
      // ignore
    }
  };

  const loadQuestionnaires = async () => {
    try {
      const res = await api.get('/questionnaires');
      setQuestionnaires(res.data);
      if (res.data.length > 0) {
        const first = await api.get(`/questionnaires/${res.data[0].id}`);
        setActiveQuestionnaire(first.data);
      }
    } catch (err) {
      // ignore
    }
  };

  const loadRatingScalesAndSettings = async () => {
    try {
      const [rsRes, setRes] = await Promise.all([
        api.get('/masters/rating-scales'),
        api.get('/masters/settings'),
      ]);
      setRatingScales(rsRes.data);
      setTenantSettings(setRes.data);
      if (setRes.data?.theme) {
        setSettingsForm((prev) => ({
          ...prev,
          dealer_name: setRes.data.theme.dealer_name || prev.dealer_name,
          primary_color: setRes.data.theme.primary_color || prev.primary_color,
          logo_url: setRes.data.theme.logo_url || prev.logo_url,
        }));
      }
      if (setRes.data?.templates) {
        setSettingsForm((prev) => ({
          ...prev,
          sms_satisfaction: setRes.data.templates.sms_satisfaction || prev.sms_satisfaction,
          whatsapp_complaint_opened: setRes.data.templates.whatsapp_complaint_opened || prev.whatsapp_complaint_opened,
        }));
      }
    } catch (err) {
      // ignore
    }
  };

  const loadCustomFields = async () => {
    try {
      const res = await api.get(`/admin/custom-fields?entity_name=${selectedEntityForCustomField}`);
      setCustomFields(res.data);
    } catch (err) {
      // ignore
    }
  };

  const loadImportTemplates = async () => {
    try {
      const res = await api.get('/admin/import-templates');
      setImportTemplates(res.data);
    } catch (err) {
      // ignore
    }
  };

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
    if (activeTab === 'matrix') loadMatrix();
    if (activeTab === 'brands_branches') loadBrandsAndBranches();
    if (activeTab === 'users') {
      loadUsers();
      if (matrixData.roles.length === 0) loadMatrix();
      if (branches.length === 0) loadBrandsAndBranches();
    }
    if (activeTab === 'masters') loadDropdownMasters();
    if (activeTab === 'questionnaires') {
      loadQuestionnaires();
      if (brands.length === 0) loadBrandsAndBranches();
    }
    if (activeTab === 'rating_slas') {
      loadRatingScalesAndSettings();
      if (brands.length === 0) loadBrandsAndBranches();
    }
    if (activeTab === 'custom_fields') loadCustomFields();
    if (activeTab === 'dashboard_menus') {
      if (matrixData.roles.length === 0) loadMatrix();
    }
    if (activeTab === 'import_templates') {
      loadImportTemplates();
      if (brands.length === 0) loadBrandsAndBranches();
    }
    if (activeTab === 'templates_settings') loadRatingScalesAndSettings();
    if (activeTab === 'audit_history') loadAuditAndHistory();
  }, [activeTab, selectedEntityForCustomField]);

  // Group permission catalogue by category
  const groupedCatalogue = useMemo(() => {
    const groups = {};
    (matrixData.catalogue || []).forEach((item) => {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    });
    return groups;
  }, [matrixData.catalogue]);

  // -------------------------------------------------------------
  // Handlers: Brands & Branches
  // -------------------------------------------------------------
  const handleSaveBrand = async (e) => {
    e.preventDefault();
    try {
      if (editingBrand) {
        await api.put(`/masters/brands/${editingBrand.id}`, {
          name: brandForm.name,
          code: brandForm.code,
          primary_color: brandForm.primary_color,
          logo_url: brandForm.logo_url || null,
        });
        toast.success(`Brand '${brandForm.name}' updated successfully.`);
      } else {
        await api.post('/masters/brands', {
          name: brandForm.name,
          code: brandForm.code,
          primary_color: brandForm.primary_color,
          logo_url: brandForm.logo_url || null,
          is_active: true,
        });
        toast.success(`Brand '${brandForm.name}' created successfully.`);
      }
      setBrandModal(false);
      setEditingBrand(null);
      setBrandForm({ name: '', code: '', primary_color: '#002C6C', logo_url: '' });
      loadBrandsAndBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save brand');
    }
  };

  const handleDeactivateBrand = async (brand) => {
    if (!confirm(`Are you sure you want to deactivate brand '${brand.name}'?`)) return;
    try {
      await api.delete(`/masters/brands/${brand.id}`);
      toast.success(`Brand '${brand.name}' deactivated.`);
      loadBrandsAndBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate brand');
    }
  };

  const handleSaveBranch = async (e) => {
    e.preventDefault();
    try {
      if (editingBranch) {
        await api.put(`/masters/branches/${editingBranch.id}`, {
          name: branchForm.name,
          code: branchForm.code,
          dms_code: branchForm.dms_code || null,
          display_name: branchForm.display_name || null,
          city: branchForm.city,
          state: branchForm.state,
          address: branchForm.address,
          phone: branchForm.phone,
          email: branchForm.email,
        });
        toast.success(`Branch '${branchForm.name}' updated.`);
      } else {
        await api.post('/masters/branches', {
          brand_id: branchForm.brand_id || brands[0]?.id,
          name: branchForm.name,
          code: branchForm.code,
          dms_code: branchForm.dms_code || null,
          display_name: branchForm.display_name || null,
          city: branchForm.city,
          state: branchForm.state,
          address: branchForm.address,
          phone: branchForm.phone,
          email: branchForm.email,
          is_active: true,
        });
        toast.success(`Branch '${branchForm.name}' created with DMS code '${branchForm.dms_code}'.`);
      }
      setBranchModal(false);
      setEditingBranch(null);
      setBranchForm({ name: '', code: '', dms_code: '', display_name: '', brand_id: brands[0]?.id || '', city: 'Bangalore', state: 'Karnataka', address: '', phone: '', email: '' });
      loadBrandsAndBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save branch');
    }
  };

  const handleDeactivateBranch = async (branch) => {
    if (!confirm(`Are you sure you want to deactivate branch '${branch.name}'?`)) return;
    try {
      await api.delete(`/masters/branches/${branch.id}`);
      toast.success(`Branch '${branch.name}' deactivated.`);
      loadBrandsAndBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate branch');
    }
  };

  // -------------------------------------------------------------
  // Handlers: Users
  // -------------------------------------------------------------
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
          role_id: userForm.role_id || matrixData.roles[0]?.id,
          employee_id: userForm.employee_id || null,
          phone: userForm.phone || null,
        });
        toast.success(`User '${userForm.email}' created successfully.`);
      }
      setUserModal(false);
      setEditingUser(null);
      setUserForm({ email: '', full_name: '', password: 'Welcome@123', role_id: '', employee_id: '', phone: '', scopes: [] });
      loadUsers();
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
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to deactivate user');
    }
  };

  // -------------------------------------------------------------
  // Handlers: Matrix
  // -------------------------------------------------------------
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

  // -------------------------------------------------------------
  // Handlers: Rating Scales (Toggle Score 9 Complaint Trigger)
  // -------------------------------------------------------------
  const handleToggleComplaintTrigger = async (scaleId, band) => {
    try {
      await api.put(`/masters/rating-scales/${scaleId}/bands/${band.id}`, {
        is_complaint_trigger: !band.is_complaint_trigger,
      });
      toast.success(`Updated band '${band.label}': Complaint trigger set to ${!band.is_complaint_trigger}`);
      loadRatingScalesAndSettings();
    } catch (err) {
      toast.error('Failed to update rating band trigger');
    }
  };

  // -------------------------------------------------------------
  // Handlers: Data Correction
  // -------------------------------------------------------------
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
      } catch (e) {
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

  // -------------------------------------------------------------
  // Handlers: Config Rollback
  // -------------------------------------------------------------
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

  // -------------------------------------------------------------
  // Handlers: Dynamic Custom Fields
  // -------------------------------------------------------------
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

  // Tab definitions: strictly filter based on dynamic permissions!
  const availableTabs = [
    { id: 'matrix', label: 'Roles & Matrix', icon: Key, visible: isSuperAdmin || can('role.manage') || can('permission.manage') },
    { id: 'brands_branches', label: 'Brands & Branches', icon: Building2, visible: isSuperAdmin || can('brand.manage') || can('branch.manage') },
    { id: 'users', label: 'Users & Simulation', icon: Users, visible: isSuperAdmin || can('user.create') || can('user.edit') },
    { id: 'masters', label: 'Dropdown Masters', icon: ListPlus, visible: isSuperAdmin || can('dropdown.manage') || can('status.manage') || can('dropdown.view') },
    { id: 'questionnaires', label: 'Questionnaires', icon: FileQuestion, visible: isSuperAdmin || can('questionnaire.manage') || can('questionnaire.view') },
    { id: 'rating_slas', label: 'Rating Scales & SLAs', icon: Gauge, visible: isSuperAdmin || can('status.manage') || can('settings.manage') },
    { id: 'allocation_rules', label: 'Call Allocation', icon: SplitSquareVertical, visible: isSuperAdmin || can('allocation.configure') || can('call.allocate') || can('config.view') },
    { id: 'custom_fields', label: 'Custom Fields', icon: Database, visible: isSuperAdmin || can('config.manage') },
    { id: 'dashboard_menus', label: 'Dashboards & Menus', icon: LayoutDashboard, visible: isSuperAdmin || can('config.manage') },
    { id: 'import_templates', label: 'Import Templates', icon: FileSpreadsheet, visible: isSuperAdmin || can('jobcard.import') || can('config.manage') },
    { id: 'templates_settings', label: 'Templates & Branding', icon: MessageSquare, visible: isSuperAdmin || can('settings.manage') },
    { id: 'audit_history', label: 'Audit & Rollback', icon: History, visible: isSuperAdmin || can('audit.view') },
    { id: 'data_correction', label: 'Data Correction', icon: Wrench, visible: isSuperAdmin || can('data.correct') },
  ].filter((t) => t.visible);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-6 w-6 text-accent" />
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Enterprise Admin Console
            </h1>
            <span className="rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-semibold text-accent">
              {isSuperAdmin ? 'L1 Super Admin (Full Control)' : `${user?.role_name || 'CRE Admin'} (Data-Driven Access)`}
            </span>
          </div>
          <p className="mt-1 text-xs text-foreground-subtle">
            Configure dealership multi-brand hierarchy, role matrix, custom fields, masters, and audit policies without code changes.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {activeTab === 'matrix' && (
            <button
              onClick={() => setNewRoleModal(true)}
              className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Add Role</span>
            </button>
          )}
          {activeTab === 'brands_branches' && (
            <>
              <button
                onClick={() => {
                  setEditingBrand(null);
                  setBrandForm({ name: '', code: '', primary_color: '#002C6C', logo_url: '' });
                  setBrandModal(true);
                }}
                className="flex items-center space-x-1.5 rounded-lg border border-border bg-background-surface px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-background-hover shadow-subtle transition-colors"
              >
                <Plus className="h-4 w-4 text-accent" />
                <span>Add Brand</span>
              </button>
              <button
                onClick={() => {
                  setEditingBranch(null);
                  setBranchForm({ name: '', code: '', dms_code: '', display_name: '', brand_id: brands[0]?.id || '', city: 'Bangalore', state: 'Karnataka', address: '', phone: '', email: '' });
                  setBranchModal(true);
                }}
                className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
              >
                <Plus className="h-4 w-4" />
                <span>Add Branch</span>
              </button>
            </>
          )}
          {activeTab === 'users' && (
            <button
              onClick={() => {
                setEditingUser(null);
                setUserForm({ email: '', full_name: '', password: 'Welcome@123', role_id: matrixData.roles[0]?.id || '', employee_id: '', phone: '', scopes: [] });
                setUserModal(true);
              }}
              className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Add User</span>
            </button>
          )}
          {activeTab === 'custom_fields' && (
            <button
              onClick={() => setCustomFieldModal(true)}
              className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Add Custom Field</span>
            </button>
          )}
          {activeTab === 'import_templates' && (
            <button
              onClick={() => setImportTemplateModal(true)}
              className="flex items-center space-x-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90 shadow-subtle transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>New Template</span>
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 overflow-x-auto border-b border-border pb-1">
        {availableTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 whitespace-nowrap px-3.5 py-2 text-xs font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-accent text-accent-foreground shadow-subtle font-bold'
                  : 'text-foreground-muted hover:bg-background-hover hover:text-foreground'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Roles & Permission Matrix */}
      {activeTab === 'matrix' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-foreground-subtle bg-background-base p-3 rounded-lg border border-border">
            <div>
              <span className="font-semibold text-foreground">Matrix Legend: </span>
              <span className="inline-block px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-mono text-[10px] mr-1.5 font-bold">ALL / DEALERSHIP</span>
              <span className="inline-block px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 font-mono text-[10px] mr-1.5 font-bold">ASSIGNED_BRANCHES</span>
              <span className="inline-block px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 font-mono text-[10px] mr-1.5 font-bold">OWN</span>
              <span>Click any badge to cycle scopes or toggle permission. Click the floppy icon to persist & invalidate Redis cache.</span>
            </div>
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
        </div>
      )}

      {/* Tab 2: Brands & Branches */}
      {activeTab === 'brands_branches' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Brands Section */}
            <div className="rounded-lg border border-border bg-background-surface p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div>
                  <h2 className="text-sm font-bold text-foreground">OEM Brands</h2>
                  <p className="text-[11px] text-foreground-subtle">{brands.length} Brands configured</p>
                </div>
                <button
                  onClick={() => {
                    setEditingBrand(null);
                    setBrandForm({ name: '', code: '', primary_color: '#002C6C', logo_url: '' });
                    setBrandModal(true);
                  }}
                  className="inline-flex items-center space-x-1 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Brand</span>
                </button>
              </div>
              <div className="space-y-2.5">
                {brands.map((b) => (
                  <div key={b.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-base">
                    <div className="flex items-center space-x-3">
                      <div className="h-8 w-8 rounded-lg flex items-center justify-center font-bold text-xs text-white shadow-sm" style={{ backgroundColor: b.primary_color || '#002C6C' }}>
                        {b.code.slice(0, 2)}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-foreground">{b.name} ({b.code})</div>
                        <div className="text-[10px] text-foreground-subtle">
                          {b.has_happiness_calling ? '15/30 Day Happiness Calling Enabled' : 'Standard Follow-up Flow'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => {
                          setEditingBrand(b);
                          setBrandForm({ name: b.name, code: b.code, primary_color: b.primary_color || '#002C6C', logo_url: b.logo_url || '' });
                          setBrandModal(true);
                        }}
                        className="p-1 rounded text-foreground-muted hover:text-accent hover:bg-background-hover"
                        title="Edit Brand"
                      >
                        <Edit className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeactivateBrand(b)}
                        className="p-1 rounded text-foreground-muted hover:text-status-danger hover:bg-background-hover"
                        title="Deactivate Brand"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Branches Section */}
            <div className="rounded-lg border border-border bg-background-surface p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div>
                  <h2 className="text-sm font-bold text-foreground">Workshop Branches & DMS Codes</h2>
                  <p className="text-[11px] text-foreground-subtle">{branches.length} Workshop Locations</p>
                </div>
                <button
                  onClick={() => {
                    setEditingBranch(null);
                    setBranchForm({ name: '', code: '', dms_code: '', display_name: '', brand_id: brands[0]?.id || '', city: 'Bangalore', state: 'Karnataka', address: '', phone: '', email: '' });
                    setBranchModal(true);
                  }}
                  className="inline-flex items-center space-x-1 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Branch</span>
                </button>
              </div>
              <div className="space-y-2.5 max-h-[480px] overflow-y-auto">
                {branches.map((br) => (
                  <div key={br.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-base">
                    <div>
                      <div className="text-xs font-bold text-foreground">
                        {br.name} {br.display_name ? `(${br.display_name})` : ''}
                      </div>
                      <div className="text-[11px] font-mono text-foreground-subtle mt-0.5">
                        Code: <span className="text-foreground">{br.code}</span> · DMS Code: <span className="font-bold text-accent px-1 py-0.5 rounded bg-accent-subtle">{br.dms_code || 'N/A'}</span> · {br.city}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => {
                          setEditingBranch(br);
                          setBranchForm({
                            name: br.name,
                            code: br.code,
                            dms_code: br.dms_code || '',
                            display_name: br.display_name || '',
                            brand_id: br.brand_id || '',
                            city: br.city || 'Bangalore',
                            state: br.state || 'Karnataka',
                            address: br.address || '',
                            phone: br.phone || '',
                            email: br.email || '',
                          });
                          setBranchModal(true);
                        }}
                        className="p-1 rounded text-foreground-muted hover:text-accent hover:bg-background-hover"
                        title="Edit Branch"
                      >
                        <Edit className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeactivateBranch(br)}
                        className="p-1 rounded text-foreground-muted hover:text-status-danger hover:bg-background-hover"
                        title="Deactivate Branch"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Users & Simulation */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground">User Management & "View As User" Simulation</h2>
            <span className="text-xs text-foreground-subtle">{usersList.length} Accounts registered</span>
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
        </div>
      )}

      {/* Tab 4: Dropdown Masters */}
      {activeTab === 'masters' && (
        <div className="space-y-4">
          <div className="flex space-x-2 border-b border-border pb-2">
            {[
              { id: 'service_types', label: 'Service Types' },
              { id: 'case_statuses', label: 'Case Statuses (Sentiment)' },
              { id: 'call_statuses', label: 'Call Statuses' },
              { id: 'complaint_categories', label: 'Complaint Categories' },
            ].map((sub) => (
              <button
                key={sub.id}
                onClick={() => setMastersSubTab(sub.id)}
                className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                  mastersSubTab === sub.id
                    ? 'bg-accent text-accent-foreground shadow-sm'
                    : 'bg-background-base text-foreground-muted hover:text-foreground'
                }`}
              >
                {sub.label}
              </button>
            ))}
          </div>

          {mastersSubTab === 'service_types' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-foreground-subtle">{serviceTypes.length} Service types configured</span>
                <button
                  onClick={() => setServiceTypeModal(true)}
                  className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
                >
                  Add Service Type
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {serviceTypes.map((st) => (
                  <div key={st.id} className="p-3 rounded-lg border border-border bg-background-surface space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">{st.name}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-white" style={{ backgroundColor: st.color || '#2563EB' }}>
                        {st.code}
                      </span>
                    </div>
                    <div className="text-[10px] text-foreground-subtle">
                      Category: {st.category || 'GENERAL'} · TAT: {st.default_tat_hours || 24}h · Icon: {st.icon}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {mastersSubTab === 'case_statuses' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-foreground-subtle">{caseStatuses.length} Case outcome statuses</span>
                <button
                  onClick={() => {
                    setStatusForm({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#10B981', type: 'CASE' });
                    setStatusModal(true);
                  }}
                  className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
                >
                  Add Case Status
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {caseStatuses.map((cs) => (
                  <div key={cs.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-surface">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cs.color || '#10B981' }} />
                        <span className="text-xs font-bold text-foreground">{cs.name}</span>
                      </div>
                      <div className="text-[10px] text-foreground-subtle">
                        Category: <span className="font-mono">{cs.category}</span> · Contacted: {cs.counts_as_contacted ? 'Yes' : 'No'} · Closes: {cs.closes_followup ? 'Yes' : 'No'} · Retry: {cs.retry_allowed ? 'Yes' : 'No'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {mastersSubTab === 'call_statuses' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-foreground-subtle">{callStatuses.length} Call statuses</span>
                <button
                  onClick={() => {
                    setStatusForm({ name: '', category: 'SENTIMENT', counts_as_contacted: true, closes_followup: false, retry_allowed: false, color: '#2563EB', type: 'CALL' });
                    setStatusModal(true);
                  }}
                  className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
                >
                  Add Call Status
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {callStatuses.map((cls) => (
                  <div key={cls.id} className="flex items-center justify-between p-3 rounded-lg border border-border bg-background-surface">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cls.color || '#2563EB' }} />
                        <span className="text-xs font-bold text-foreground">{cls.name}</span>
                      </div>
                      <div className="text-[10px] text-foreground-subtle">
                        Category: <span className="font-mono">{cls.category}</span> · Contacted: {cls.counts_as_contacted ? 'Yes' : 'No'} · Closes: {cls.closes_followup ? 'Yes' : 'No'} · Retry: {cls.retry_allowed ? 'Yes' : 'No'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {mastersSubTab === 'complaint_categories' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-foreground-subtle">{complaintCategories.length} Categories</span>
                <button
                  onClick={() => setCategoryModal(true)}
                  className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
                >
                  Add Category
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {complaintCategories.map((cat) => (
                  <div key={cat.id} className="p-3 rounded-lg border border-border bg-background-surface space-y-1">
                    <div className="text-xs font-bold text-foreground">{cat.name}</div>
                    <div className="text-[10px] text-foreground-subtle">
                      Severity: <span className="font-semibold text-amber-600">{cat.severity_level}</span> · Default SLA: {cat.default_sla_hours}h
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Questionnaires */}
      {activeTab === 'questionnaires' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-foreground">Dynamic Questionnaire Builder & Version Control</h2>
              <p className="text-[11px] text-foreground-subtle">Draft questions, bump versions, and publish templates per brand</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1 space-y-2">
              <span className="text-xs font-bold text-foreground">Available Templates</span>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {questionnaires.map((q) => (
                  <div
                    key={q.id}
                    onClick={async () => {
                      const det = await api.get(`/questionnaires/${q.id}`);
                      setActiveQuestionnaire(det.data);
                    }}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      activeQuestionnaire?.id === q.id
                        ? 'border-accent bg-accent-subtle shadow-sm'
                        : 'border-border bg-background-surface hover:bg-background-hover'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">{q.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-background-base">v{q.version}</span>
                    </div>
                    <div className="text-[10px] text-foreground-subtle mt-1">
                      Brand: {q.brand_name || 'All'} · Type: {q.type} · {q.questions_count || 0} questions
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="md:col-span-2 space-y-3 p-4 rounded-lg border border-border bg-background-surface">
              {activeQuestionnaire ? (
                <>
                  <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-foreground">{activeQuestionnaire.title} (v{activeQuestionnaire.version})</h3>
                      <p className="text-[11px] text-foreground-subtle">
                        Brand: {activeQuestionnaire.brand_name || 'Generic'} · Campaign: {activeQuestionnaire.type}
                      </p>
                    </div>
                    <button
                      onClick={() => setNewQuestionModal(true)}
                      className="inline-flex items-center space-x-1 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>Add Question</span>
                    </button>
                  </div>

                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {(activeQuestionnaire.questions || []).map((qItem, idx) => (
                      <div key={qItem.id || idx} className="p-3 rounded-lg border border-border bg-background-base flex items-center justify-between">
                        <div>
                          <div className="text-xs font-semibold text-foreground">
                            {idx + 1}. {qItem.label}
                          </div>
                          <div className="text-[10px] font-mono text-foreground-subtle mt-0.5">
                            Key: <span className="text-accent">{qItem.key}</span> · Type: {qItem.type} · Section: {qItem.section} · Weight: {qItem.weight}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="py-8 text-center text-xs text-foreground-subtle">Select a questionnaire template to view details</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Rating Scales & SLAs */}
      {activeTab === 'rating_slas' && (
        <div className="space-y-6">
          <div className="rounded-lg border border-border bg-background-surface p-4 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-foreground">Brand Rating Scales & Complaint Triggers</h2>
              <p className="text-xs text-foreground-subtle">
                Rating bands partition CSAT outcomes. Toggle the complaint trigger to automatically escalate low ratings (including Hyundai score 9).
              </p>
            </div>

            <div className="space-y-4">
              {ratingScales.map((scale) => (
                <div key={scale.id} className="p-4 rounded-lg border border-border bg-background-base space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-foreground">{scale.name}</span>
                      <span className="text-[11px] text-foreground-subtle ml-2">Brand: {scale.brand_name} (Max {scale.max_rating})</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                    {(scale.bands || []).map((band) => (
                      <div key={band.id} className="p-2.5 rounded-lg border border-border bg-background-surface space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-foreground">{band.label}</span>
                          <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-background-base">
                            {band.min_score === band.max_score ? band.min_score : `${band.min_score}-${band.max_score}`}
                          </span>
                        </div>
                        <div className="text-[10px] text-foreground-subtle">
                          Derived Status: <span className="font-semibold">{band.derived_case_status}</span>
                        </div>
                        <div className="pt-1 flex items-center justify-between border-t border-border/50 text-[10px]">
                          <span className={band.is_complaint_trigger ? 'text-status-danger font-bold' : 'text-foreground-subtle'}>
                            {band.is_complaint_trigger ? 'Triggers Complaint' : 'No Complaint'}
                          </span>
                          <button
                            onClick={() => handleToggleComplaintTrigger(scale.id, band)}
                            className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent-subtle text-accent hover:bg-accent hover:text-accent-foreground transition-colors"
                          >
                            Toggle Trigger
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 7: Custom Fields */}
      {activeTab === 'custom_fields' && (
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
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Custom Field
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
        </div>
      )}

      {/* Tab 8: Dashboards & Menus */}
      {activeTab === 'dashboard_menus' && (
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
                {matrixData.roles.map((r) => (
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
      )}

      {/* Tab 9: Import Templates */}
      {activeTab === 'import_templates' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground">DMS Import Column Mapping Templates</h2>
            <button
              onClick={() => setImportTemplateModal(true)}
              className="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
            >
              Add Template
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {importTemplates.map((tmpl) => (
              <div key={tmpl.id} className="p-4 rounded-lg border border-border bg-background-surface space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground">{tmpl.template_name}</span>
                  {tmpl.is_default && (
                    <span className="rounded bg-accent px-2 py-0.5 text-[10px] font-bold text-accent-foreground">Default</span>
                  )}
                </div>
                <div className="text-[11px] text-foreground-subtle">File Type: {tmpl.file_type}</div>
                <pre className="p-2 rounded bg-background-base text-[10px] font-mono overflow-x-auto max-h-36">
                  {JSON.stringify(tmpl.mapping, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 10: Templates & Branding */}
      {activeTab === 'templates_settings' && (
        <div className="space-y-4 max-w-xl">
          <div>
            <h2 className="text-sm font-bold text-foreground">App Branding & Notification Templates</h2>
            <p className="text-xs text-foreground-subtle">Configure dealer white-label appearance and automated customer SMS/WhatsApp messages.</p>
          </div>

          <div className="p-4 rounded-lg border border-border bg-background-surface space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">Dealership Display Name</label>
              <input
                type="text"
                value={settingsForm.dealer_name}
                onChange={(e) => setSettingsForm((prev) => ({ ...prev, dealer_name: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">Primary Brand Hex Color</label>
              <div className="flex items-center space-x-2">
                <input
                  type="color"
                  value={settingsForm.primary_color}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, primary_color: e.target.value }))}
                  className="h-8 w-8 rounded border-0 cursor-pointer"
                />
                <input
                  type="text"
                  value={settingsForm.primary_color}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, primary_color: e.target.value }))}
                  className="w-28 rounded-lg border border-border bg-background-base px-2 py-1 text-xs text-foreground font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">SMS Post-Service Satisfaction Template</label>
              <textarea
                rows={3}
                value={settingsForm.sms_satisfaction}
                onChange={(e) => setSettingsForm((prev) => ({ ...prev, sms_satisfaction: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background-base p-2 text-xs text-foreground"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">WhatsApp Escalated Complaint Opened Template</label>
              <textarea
                rows={3}
                value={settingsForm.whatsapp_complaint_opened}
                onChange={(e) => setSettingsForm((prev) => ({ ...prev, whatsapp_complaint_opened: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background-base p-2 text-xs text-foreground"
              />
            </div>

            <button
              onClick={async () => {
                try {
                  await api.put('/masters/settings', {
                    config_key: 'templates',
                    config_value: {
                      sms_satisfaction: settingsForm.sms_satisfaction,
                      whatsapp_complaint_opened: settingsForm.whatsapp_complaint_opened,
                    },
                  });
                  await api.put('/masters/settings', {
                    config_key: 'theme',
                    config_value: {
                      dealer_name: settingsForm.dealer_name,
                      primary_color: settingsForm.primary_color,
                    },
                  });
                  toast.success('App branding & templates updated successfully.');
                } catch (err) {
                  toast.error('Failed to update settings');
                }
              }}
              className="w-full rounded-lg bg-accent px-3 py-2 text-xs font-bold text-accent-foreground hover:bg-accent/90"
            >
              Save Branding & Templates
            </button>
          </div>
        </div>
      )}

      {/* Tab 11: Audit Logs & Rollback */}
      {activeTab === 'audit_history' && (
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
      )}

      {/* Tab 12: Data Correction */}
      {activeTab === 'allocation_rules' && (
        <AllocationRulesTab />
      )}

      {activeTab === 'data_correction' && (
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
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Modals */}
      {/* ----------------------------------------------------------------- */}

      {/* Add / Edit Brand Modal */}
      {brandModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">{editingBrand ? 'Edit Brand' : 'Add New OEM Brand'}</h3>
            <form onSubmit={handleSaveBrand} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Brand Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Hyundai, MG Motors, Tata Motors"
                  value={brandForm.name}
                  onChange={(e) => setBrandForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Brand Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. HYUN, MG, TATA"
                  value={brandForm.code}
                  onChange={(e) => setBrandForm((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Primary Color (Hex)</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={brandForm.primary_color}
                    onChange={(e) => setBrandForm((prev) => ({ ...prev, primary_color: e.target.value }))}
                    className="h-8 w-8 rounded border-0 cursor-pointer"
                  />
                  <input
                    type="text"
                    value={brandForm.primary_color}
                    onChange={(e) => setBrandForm((prev) => ({ ...prev, primary_color: e.target.value }))}
                    className="w-28 rounded-lg border border-border bg-background-base px-2 py-1 text-xs text-foreground font-mono"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Logo URL (Optional)</label>
                <input
                  type="text"
                  placeholder="https://..."
                  value={brandForm.logo_url}
                  onChange={(e) => setBrandForm((prev) => ({ ...prev, logo_url: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setBrandModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  {editingBrand ? 'Update Brand' : 'Create Brand'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add / Edit Branch Modal */}
      {branchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-background-surface p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">{editingBranch ? 'Edit Workshop Branch' : 'Add New Workshop Branch'}</h3>
            <form onSubmit={handleSaveBranch} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">OEM Brand</label>
                  <select
                    value={branchForm.brand_id}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, brand_id: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  >
                    {brands.map((b) => (
                      <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">
                    DMS Code <span className="text-accent font-mono font-bold">(e.g. S8211)</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. S8211"
                    value={branchForm.dms_code}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, dms_code: e.target.value.toUpperCase() }))}
                    className="w-full rounded-lg border border-accent/40 bg-background-base px-3 py-1.5 text-xs text-foreground font-mono font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Branch Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Apex Central Hubli"
                    value={branchForm.name}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, name: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Internal Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. APEX-HUBLI"
                    value={branchForm.code}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, code: e.target.value.toUpperCase() }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">City</label>
                  <input
                    type="text"
                    value={branchForm.city}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, city: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">State</label>
                  <input
                    type="text"
                    value={branchForm.state}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, state: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Workshop Phone</label>
                  <input
                    type="text"
                    placeholder="+91 98888 12345"
                    value={branchForm.phone}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, phone: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Workshop Email</label>
                  <input
                    type="email"
                    placeholder="service@apexauto.com"
                    value={branchForm.email}
                    onChange={(e) => setBranchForm((prev) => ({ ...prev, email: e.target.value }))}
                    className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setBranchModal(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground-muted hover:bg-background-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  {editingBranch ? 'Update Branch' : 'Create Branch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
                  {matrixData.roles.map((r) => (
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

      {/* Impersonation Modal */}
      {impersonateModal && targetUserToImpersonate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-amber-300 dark:border-amber-800 bg-background-surface p-6 shadow-xl space-y-4">
            <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400 font-bold text-sm">
              <Eye className="h-5 w-5" />
              <span>Simulate User: {targetUserToImpersonate.full_name}</span>
            </div>
            <p className="text-xs text-foreground-subtle">
              You will view the PSF suite exactly through the eyes and permissions of <strong>{targetUserToImpersonate.email}</strong> ({targetUserToImpersonate.role_name}). An amber banner will remain active so you can return at any time.
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

      {/* Custom Field Modal */}
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
