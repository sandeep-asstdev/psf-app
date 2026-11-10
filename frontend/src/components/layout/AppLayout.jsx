/**
 * ============================================================================
 * FILE PURPOSE: Master Dashboard Shell Layout.
 * Provides the persistent layout surrounding all dashboard pages:
 * renders the responsive Sidebar on the left, Header at the top, and scrollable content area.
 * 
 * KEY RESPONSIBILITIES:
 * - Houses `<Sidebar />` and `<Header />`.
 * - Manages mobile menu drawer open/close state.
 * - Renders active page component inside `<main>` via `<Outlet />`.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Page content hidden under header or off-screen
 *   -> Cause: CSS layout overflow or z-index issue.
 *   -> What should you do: Check responsive Tailwind classes in `AppLayout.jsx`.
 * ============================================================================
 */
import React, { useState } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

export default function AppLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

