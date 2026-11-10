/**
 * ============================================================================
 * FILE PURPOSE: Enterprise Admin Console (Super Admin Control Center).
 * Provides Super Admins with full control over the dealership system: the RBAC Role Permission Matrix
 * (who can do what and at what data scope level), follow-up programs, system-wide allocation rules,
 * and supervisor data corrections.
 * ============================================================================
 */
import React, { useState } from 'react';
import {
  ShieldCheck,
  Key,
  CalendarCheck,
  Users,
  Building2,
  ListPlus,
  FileQuestion,
  Gauge,
  Database,
  LayoutDashboard,
  FileSpreadsheet,
  MessageSquare,
  History,
  Wrench,
  SplitSquareVertical,
} from 'lucide-react';

import RolesMatrixTab from './tabs/RolesMatrixTab';
import ProgramsTab from './tabs/ProgramsTab';
import BrandsBranchesTab from './tabs/BrandsBranchesTab';
import UsersTab from './tabs/UsersTab';
import DropdownMastersTab from './tabs/DropdownMastersTab';
import QuestionnairesTab from './tabs/QuestionnairesTab';
import RatingSlasTab from './tabs/RatingSlasTab';
import AllocationRulesTab from '../../components/allocation/AllocationRulesTab';
import CustomFieldsTab from './tabs/CustomFieldsTab';
import DashboardMenusTab from './tabs/DashboardMenusTab';
import ImportTemplatesTab from './tabs/ImportTemplatesTab';
import TemplatesSettingsTab from './tabs/TemplatesSettingsTab';
import AuditHistoryTab from './tabs/AuditHistoryTab';
import DataCorrectionTab from './tabs/DataCorrectionTab';

import { useAuthStore } from '../../store/authStore';

export default function AdminConsolePage() {
  const { user, can } = useAuthStore();
  const isSuperAdmin = user?.is_super_admin || user?.role_name === 'SUPER_ADMIN';

  // Automatically default tab: Super Admin starts at 'programs' or 'matrix', others start at 'users'
  const [activeTab, setActiveTab] = useState(isSuperAdmin ? 'programs' : 'users');

  // Tab definitions: strictly filter based on dynamic permissions
  const availableTabs = [
    { id: 'programs', label: 'Follow-Up Programs', icon: CalendarCheck, visible: isSuperAdmin || can('config.manage') || can('program.manage') },
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
            Configure dealership multi-brand hierarchy, follow-up programs, role matrix, questionnaires, and policies without code changes.
          </p>
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

      {/* Active Tab Content */}
      <div className="pt-2">
        {activeTab === 'programs' && <ProgramsTab />}
        {activeTab === 'matrix' && <RolesMatrixTab isSuperAdmin={isSuperAdmin} />}
        {activeTab === 'brands_branches' && <BrandsBranchesTab />}
        {activeTab === 'users' && <UsersTab isSuperAdmin={isSuperAdmin} />}
        {activeTab === 'masters' && <DropdownMastersTab />}
        {activeTab === 'questionnaires' && <QuestionnairesTab />}
        {activeTab === 'rating_slas' && <RatingSlasTab />}
        {activeTab === 'allocation_rules' && <AllocationRulesTab />}
        {activeTab === 'custom_fields' && <CustomFieldsTab />}
        {activeTab === 'dashboard_menus' && <DashboardMenusTab />}
        {activeTab === 'import_templates' && <ImportTemplatesTab />}
        {activeTab === 'templates_settings' && <TemplatesSettingsTab />}
        {activeTab === 'audit_history' && <AuditHistoryTab />}
        {activeTab === 'data_correction' && <DataCorrectionTab />}
      </div>
    </div>
  );
}
