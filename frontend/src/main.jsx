/**
 * ============================================================================
 * FILE PURPOSE: React Application Root Entry Point.
 * Initializes the React virtual DOM tree, mounts the root React component into index.html,
 * and sets up global CSS stylesheets and fonts.
 * 
 * KEY RESPONSIBILITIES:
 * - Imports React and ReactDOM Client (`createRoot`).
 * - Mounts the `<App />` component into the DOM element with ID `root`.
 * - Imports global styles (`./index.css`).
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Blank white screen in browser on load
 *   -> Cause: JavaScript runtime crash before React mounts, or missing #root div in index.html.
 *   -> What should you do: Open browser DevTools Console (F12) to inspect the initial error trace.
 * ============================================================================
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App';
import './index.css';
import './i18n';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 2, // 2 minutes
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <Toaster position="top-right" />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);

