import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Building2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function BrandsBranchesTab({ onNavigateToTenants }) {
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

  useEffect(() => {
    loadBrandsAndBranches();
  }, []);

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

  return (
    <div className="space-y-6">
      {onNavigateToTenants && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <Building2 className="w-5 h-5 text-blue-600 shrink-0" />
            <div>
              <span className="font-bold text-blue-900 block">Looking to onboard a new Dealership Tenant?</span>
              <span className="text-blue-700">Multi-tenant dealerships (with isolated database space, brands, branches, and admin credentials) can be created from Tenant Management.</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onNavigateToTenants}
            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shrink-0 shadow-sm transition cursor-pointer"
          >
            + Create New Tenant
          </button>
        </div>
      )}

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
                      {b.enable_tnps ? 'TNPS Brand Program Active' : b.has_happiness_calling ? '15/30 Day Happiness Calling Enabled' : 'Standard Follow-up Flow'}
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

      {/* Brand Modal */}
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

      {/* Branch Modal */}
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
    </div>
  );
}

