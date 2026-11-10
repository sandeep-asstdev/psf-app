/**
 * ============================================================================
 * FILE PURPOSE: Client-Side Route Authentication Guard.
 * Protects private dashboard pages: if the user is not authenticated, it immediately
 * redirects them to `/login` while preserving their attempted destination URL.
 * 
 * KEY RESPONSIBILITIES:
 * - Checks if an active user session exists in AuthStore.
 * - Redirects unauthenticated visitors to `/login`.
 * - Renders protected route content (`<Outlet />` or children) for logged-in users.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: User repeatedly kicked back to login page
 *   -> Cause: JWT token is missing, corrupted, or expired in localStorage.
 *   -> What should you do: Clear browser localStorage and log in again at `/login`.
 * ============================================================================
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export default function ProtectedRoute({ children, permission, permissionAny, allowedRoles }) {
  const { isAuthenticated, can, canAny, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Pure data-driven permission checks
  if (permission && !can(permission)) {
    return <Navigate to="/" replace />;
  }

  if (permissionAny && Array.isArray(permissionAny) && !canAny(...permissionAny)) {
    return <Navigate to="/" replace />;
  }

  // Backward compatibility fallback for allowedRoles
  if (allowedRoles && allowedRoles.length > 0) {
    const isSuper = user?.is_super_admin || user?.role_name?.toUpperCase() === 'SUPER_ADMIN';
    const userRole = user?.role_name?.toUpperCase() || '';
    if (!isSuper && !allowedRoles.map((r) => r.toUpperCase()).includes(userRole)) {
      return <Navigate to="/" replace />;
    }
  }

  return children;
}
