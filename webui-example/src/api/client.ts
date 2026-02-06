import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Custom event for auth expiration (allows App.tsx to handle navigation)
export const AUTH_EXPIRED_EVENT = 'auth:expired';

export const dispatchAuthExpired = () => {
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
};

// Request interceptor: add Bearer Token from Zustand store
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 by dispatching event (decoupled from router)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      // Dispatch event instead of direct navigation (SPA-friendly)
      dispatchAuthExpired();
    }
    return Promise.reject(error);
  }
);
