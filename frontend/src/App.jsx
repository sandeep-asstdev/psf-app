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
import React, { useEffect, Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useThemeStore } from './store/themeStore';
import { useAuthStore } from './store/authStore';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LoginPage from './pages/auth/LoginPage';
import LiveNotificationListener from './components/common/LiveNotificationListener';

// Route-level code splitting
const HomePage = lazy(() => import('./pages/HomePage'));
const UserActivityPage = lazy(() => import('./pages/auth/UserActivityPage'));
const UserManagementPage = lazy(() => import('./pages/users/UserManagementPage'));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage'));
const DataImportPage = lazy(() => import('./pages/imports/DataImportPage'));
const PsfDashboardPage = lazy(() => import('./pages/psf/PsfDashboardPage'));
const TnpsDashboardPage = lazy(() => import('./pages/tnps/TnpsDashboardPage'));
const ComplaintManagementPage = lazy(() => import('./pages/complaints/ComplaintManagementPage'));
const HappinessCallingPage = lazy(() => import('./pages/happiness/HappinessCallingPage'));
const AdvisorPortalPage = lazy(() => import('./pages/advisors/AdvisorPortalPage'));
const ReportsDashboardPage = lazy(() => import('./pages/reports/ReportsDashboardPage'));
const AdminConsolePage = lazy(() => import('./pages/admin/AdminConsolePage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

function RouteLoadingFallback() {
  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto animate-pulse">
      <div className="h-8 w-64 bg-slate-200 dark:bg-slate-800 rounded-lg" />
      <div className="h-4 w-96 bg-slate-100 dark:bg-slate-800/60 rounded" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 bg-slate-100 dark:bg-slate-800 rounded-xl" />
        ))}
      </div>
      <div className="h-64 bg-slate-100 dark:bg-slate-800 rounded-xl mt-4" />
    </div>
  );
}

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
              <Suspense fallback={<RouteLoadingFallback />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/activity" element={<UserActivityPage />} />
                  <Route path="/attendance" element={<UserActivityPage />} />
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
                    path="/tnps"
                    element={
                      <ProtectedRoute permission="call.view">
                        <TnpsDashboardPage />
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
              </Suspense>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
