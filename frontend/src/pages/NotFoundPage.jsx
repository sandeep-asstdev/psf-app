/**
 * ============================================================================
 * FILE PURPOSE: 404 Not Found Fallback Page.
 * Displayed whenever a user navigates to an invalid or unmapped URL path.
 * Shows a friendly error message with a button to safely return back to the Home page.
 * 
 * KEY RESPONSIBILITIES:
 * - Catches unmatched router paths in React Router (`path='*'`).
 * - Provides a 1-click button to navigate safely back to Home (`/`).
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: User repeatedly lands on 404 page when clicking menu links
 *   -> Cause: The clicked route path does not match any Route definition in App.jsx.
 *   -> What should you do: Verify the URL path in `frontend/src/components/layout/Sidebar.jsx` matches `App.jsx`.
 * ============================================================================
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Home } from 'lucide-react';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="rounded-2xl border border-border bg-background-card p-8 shadow-card max-w-md">
        <AlertTriangle className="mx-auto h-12 w-12 text-status-warning" />
        <h2 className="mt-4 text-2xl font-bold text-foreground">Page Not Found</h2>
        <p className="mt-2 text-sm text-foreground-muted">
          The requested page does not exist or has been moved.
        </p>
        <button
          onClick={() => navigate('/')}
          className="mt-6 inline-flex items-center space-x-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
        >
          <Home className="h-4 w-4" />
          <span>Back to Home</span>
        </button>
      </div>
    </div>
  );
}

