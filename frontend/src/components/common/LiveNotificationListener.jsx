/**
 * ============================================================================
 * FILE PURPOSE: Real-Time WebSocket Allocation Notification Listener.
 * Maintains an active WebSocket connection to the backend Redis pub/sub channel
 * and immediately displays a bouncing toast alert whenever new calls are assigned to the logged-in CRE.
 * 
 * KEY RESPONSIBILITIES:
 * - Connects to `ws://localhost:8000/api/v1/allocation/ws/notifications/{token}`.
 * - Listens for `CALLS_ALLOCATED` broadcast events.
 * - Displays a toast notification with a 1-click button to open the PSF calling workspace.
 * - Re-establishes connection automatically if network drops.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Console warning: 'WebSocket connection failed'
 *   -> Cause: API server is down or token is invalid.
 *   -> What should you do: Listener automatically backs off and retries after 5 seconds.
 * ============================================================================
 */
import React, { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { PhoneCall } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export default function LiveNotificationListener() {
  const { user, token } = useAuthStore();
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    if (!token || !user) {
      if (socketRef.current) {
        socketRef.current.close();
      }
      return;
    }

    const connectWebSocket = () => {
      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
        let wsUrl;
        if (apiBase.startsWith('http')) {
          wsUrl = apiBase.replace(/^http/, 'ws') + `/allocation/ws/notifications/${token}`;
        } else {
          const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          wsUrl = `${proto}//${window.location.host}/api/v1/allocation/ws/notifications/${token}`;
        }

        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          console.log('📡 Connected to live CRE allocation notification channel');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'CALLS_ALLOCATED') {
              toast((t) => (
                <div className="flex items-start gap-3 p-1">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/60 text-blue-600 dark:text-blue-300">
                    <PhoneCall className="h-5 w-5 animate-bounce" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                      New Calls Assigned!
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
                      {data.message || `${data.count} new follow-up calls assigned to you.`}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <button 
                        onClick={() => {
                          toast.dismiss(t.id);
                          window.location.href = '/psf/calling';
                        }}
                        className="text-xs font-semibold px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white transition"
                      >
                        Open PSF Console
                      </button>
                      <button 
                        onClick={() => toast.dismiss(t.id)}
                        className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              ), { duration: 10000, position: 'top-right' });
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          // Reconnect with backoff
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = () => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        };
      } catch (err) {
        console.warn('Could not establish notification WebSocket:', err);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [token, user]);

  return null;
}

