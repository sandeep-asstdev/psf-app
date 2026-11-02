import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export default function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = user?.role_name?.toUpperCase() || '';
    if (userRole !== 'SUPER_ADMIN' && !allowedRoles.map((r) => r.toUpperCase()).includes(userRole)) {
      return <Navigate to="/" replace />;
    }
  }

  return children;
}
