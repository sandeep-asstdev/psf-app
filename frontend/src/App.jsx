/**
 * ============================================================================
 * FILE PURPOSE: Top-Level Application Router & Toast Notification Shell.
 * Configures all client-side page routes using React Router, wraps authenticated pages
 * inside ProtectedRoute and AppLayout, and mounts the global Toast notification container.
 * 
 * KEY RESPONSIBILITIES:
 * - Defines application URL routing hierarchy (Home, PSF, Import, Complaints, Admin, Users, Settings).
 * - Guards private routes using `<ProtectedRoute />`.
 * - Mounts `<LiveNotificationListener />` for real-time WebSocket toast alerts.
 * - Configures `<Toaster />` for notification banners.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: User navigates to a URL and sees nothing or 404
 *   -> Cause: Route path was not added to the `<Routes>` list in this file.
 *   -> What should you do: Add the `<Route path='/your-path' element={<YourComponent />} />` inside `<Routes>`.
 * ============================================================================
 */
import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useThemeStore } from './store/themeStore';
import { useAuthStore } from './store/authStore';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LoginPage from './pages/auth/LoginPage';
import AttendanceLogsPage from './pages/auth/AttendanceLogsPage';
import UserManagementPage from './pages/users/UserManagementPage';
import SettingsPage from './pages/settings/SettingsPage';
import DataImportPage from './pages/imports/DataImportPage';
import PsfDashboardPage from './pages/psf/PsfDashboardPage';
import ComplaintManagementPage from './pages/complaints/ComplaintManagementPage';
import HappinessCallingPage from './pages/happiness/HappinessCallingPage';
import AdvisorPortalPage from './pages/advisors/AdvisorPortalPage';
import ReportsDashboardPage from './pages/reports/ReportsDashboardPage';
import AdminConsolePage from './pages/admin/AdminConsolePage';
import LiveNotificationListener from './components/common/LiveNotificationListener';
import HomePage from './pages/HomePage';
import PlaceholderPage from './pages/PlaceholderPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  const initTheme = useThemeStore((state) => state.initTheme);
  const { fetchProfile, isAuthenticated } = useAuthStore();

  useEffect(() => {
    initTheme();
    if (isAuthenticated) {
      fetchProfile();
    }
  }, [initTheme, isAuthenticated]);

  return (
    <Routes>
      {/* Public Login Route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes inside AppLayout */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <LiveNotificationListener />
            <AppLayout>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/attendance" element={<AttendanceLogsPage />} />
                <Route
                  path="/users"
                  element={
                    <ProtectedRoute permissionAny={['user.create', 'user.edit']}>
                      <UserManagementPage />
                    </ProtectedRoute>
                  }
                />

                {/* PSF Calling Console */}
                <Route
                  path="/psf"
                  element={
                    <ProtectedRoute permission="call.view">
                      <PsfDashboardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/happiness"
                  element={
                    <ProtectedRoute permission="call.view">
                      <HappinessCallingPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/complaints"
                  element={
                    <ProtectedRoute permission="complaint.view">
                      <ComplaintManagementPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/advisor"
                  element={
                    <ProtectedRoute permission="advisor.action">
                      <AdvisorPortalPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/reports"
                  element={
                    <ProtectedRoute permission="report.view">
                      <ReportsDashboardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/import"
                  element={
                    <ProtectedRoute permission="jobcard.import">
                      <DataImportPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin-console"
                  element={
                    <ProtectedRoute permissionAny={['role.manage', 'permission.manage', 'brand.manage', 'data.correct']}>
                      <AdminConsolePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute permissionAny={['brand.manage', 'settings.manage', 'config.view']}>
                      <SettingsPage />
                    </ProtectedRoute>
                  }
                />

                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
