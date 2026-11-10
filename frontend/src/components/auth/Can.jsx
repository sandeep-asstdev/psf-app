/**
 * ============================================================================
 * FILE PURPOSE: Declarative Permission-Gated Wrapper Component.
 * Wraps UI elements (like buttons, links, or sections) and conditionally renders them
 * ONLY if the current user has the required permission key.
 * 
 * KEY RESPONSIBILITIES:
 * - Checks `can(permission)` from AuthStore.
 * - Renders `children` if authorized; otherwise renders `fallback` or null.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: A button wrapped in <Can> is invisible
 *   -> Cause: The user's role does not have the specified permission key.
 *   -> What should you do: Verify the permission key name or check the user's role in the Admin Console.
 * ============================================================================
 */
import React from 'react';
import { useAuthStore } from '../../store/authStore';

/**
 * Declarative component for dynamic data-driven permission checks.
 * Usage:
 *   <Can do="complaint.close">
 *     <button>Resolve Ticket</button>
 *   </Can>
 * 
 *   <Can do={['brand.manage', 'branch.manage']} fallback={<span>No access</span>}>
 *     <AdminSettings />
 *   </Can>
 */
export default function Can({ do: permissionKey, any = false, fallback = null, children }) {
  const { can, canAny, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) return fallback;

  if (Array.isArray(permissionKey)) {
    const hasAccess = any 
      ? canAny(...permissionKey)
      : permissionKey.every((k) => can(k));
    return hasAccess ? children : fallback;
  }

  return can(permissionKey) ? children : fallback;
}

