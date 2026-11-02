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
