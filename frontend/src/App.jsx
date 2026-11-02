import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useThemeStore } from './store/themeStore';
import AppLayout from './components/layout/AppLayout';
import HomePage from './pages/HomePage';
import PlaceholderPage from './pages/PlaceholderPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  const initTheme = useThemeStore((state) => state.initTheme);

  useEffect(() => {
    initTheme();
  }, [initTheme]);

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        
        {/* Workstation Routes */}
        <Route
          path="/psf"
          element={
            <PlaceholderPage
              phase="Phase 5"
              title="PSF Dashboard & Call Console"
              description="Main CRE Workspace with grouped job card widgets, drill-down tables, and split-layout call console."
            />
          }
        />
        <Route
          path="/happiness"
          element={
            <PlaceholderPage
              phase="Phase 6"
              title="Happiness Calling"
              description="15-day / 30-day post-delivery calling queues, satisfaction tracking, and advisor allocations."
            />
          }
        />
        <Route
          path="/complaints"
          element={
            <PlaceholderPage
              phase="Phase 6"
              title="Complaint Management"
              description="Full SLA lifecycle: Open, Assigned, In Progress, Resolved, Reconfirmation & Closure audit trail."
            />
          }
        />
        <Route
          path="/advisor"
          element={
            <PlaceholderPage
              phase="Phase 6"
              title="Service Advisor Follow-up"
              description="Restricted portal for Service Advisors to review dissatisfied customer VOC and input corrective remarks."
            />
          }
        />
        <Route
          path="/reports"
          element={
            <PlaceholderPage
              phase="Phase 7"
              title="Reports & Analytics Dashboard"
              description="CSAT/NPS trends, CRE productivity, complaint turnaround analysis, advisor scorecards, and Excel/PDF export."
            />
          }
        />
        <Route
          path="/import"
          element={
            <PlaceholderPage
              phase="Phase 4"
              title="DMS Data Import & Allocation"
              description="Excel/CSV job card upload, column mapping templates, duplicate detection, and round-robin auto-allocation."
            />
          }
        />
        <Route
          path="/users"
          element={
            <PlaceholderPage
              phase="Phase 2"
              title="User Management & Attendance Logs"
              description="Manage users, roles, brand/branch scopes, password resets, and attendance-style login/logout logs."
            />
          }
        />
        <Route
          path="/settings"
          element={
            <PlaceholderPage
              phase="Phase 3"
              title="Masters & Questionnaire Builder"
              description="Tenant settings, brand logos, branch masters, and dynamic brand questionnaire engine."
            />
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}
