/**
 * ============================================================================
 * FILE PURPOSE: Axios HTTP Client with Automatic Token Injection & Interceptors.
 * Handles all HTTP network calls between the React frontend and the FastAPI backend.
 * Automatically attaches the user's JWT Bearer token to outgoing requests and handles 401 token expiration.
 * 
 * KEY RESPONSIBILITIES:
 * - Configures base URL (`http://localhost:8000/api/v1` or environment variable).
 * - Request Interceptor: Automatically injects `Authorization: Bearer <token>` from AuthStore.
 * - Response Interceptor: Automatically clears token and redirects to `/login` if server returns 401 Unauthorized.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Network Error or net::ERR_CONNECTION_REFUSED
 *   -> Cause: Backend API server on port 8000 is not running or unreachable.
 *   -> What should you do: Verify that `psf_api` container is running using `docker ps`. Restart it with `docker restart psf_api`.
 * - Error: Repeated redirect to /login
 *   -> Cause: Stored JWT access token has expired and could not be refreshed.
 *   -> What should you do: Log in again with valid credentials.
 * ============================================================================
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Sends and receives httpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to inject bearer token if stored in memory/localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('psf_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor to handle session expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('psf_token');
        localStorage.removeItem('psf_user');
        window.location.href = '/login?expired=1';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

