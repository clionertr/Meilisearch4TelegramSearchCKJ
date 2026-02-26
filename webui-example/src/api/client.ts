import axios from 'axios';
import { useAuthStore } from '@/store/authStore';
import { telemetry } from '@/utils/telemetry';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
const REQUEST_ID_HEADER = 'X-Request-ID';

interface RequestMetadata {
  startedAtMs: number;
  requestId: string;
}

type ConfigWithMetadata = {
  metadata?: RequestMetadata;
};

const createRequestId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().slice(0, 12);
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
};

const normalizeMethod = (method: string | undefined): string => (method ?? 'GET').toUpperCase();

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
  const metadata: RequestMetadata = {
    startedAtMs: performance.now(),
    requestId: createRequestId(),
  };
  (config as typeof config & ConfigWithMetadata).metadata = metadata;

  config.headers = config.headers ?? {};
  (config.headers as Record<string, string>)[REQUEST_ID_HEADER] = metadata.requestId;

  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  telemetry.apiStart({
    request_id: metadata.requestId,
    method: normalizeMethod(config.method),
    url: `${config.baseURL ?? ''}${config.url ?? ''}`,
  });

  return config;
});

// Response interceptor: handle 401 by dispatching event (decoupled from router)
api.interceptors.response.use(
  (response) => {
    const config = response.config as typeof response.config & ConfigWithMetadata;
    const metadata = config.metadata;
    const durationMs = metadata ? performance.now() - metadata.startedAtMs : undefined;
    const responseRequestId = (response.headers?.['x-request-id'] as string | undefined) ?? metadata?.requestId;

    telemetry.apiEnd({
      request_id: responseRequestId,
      method: normalizeMethod(response.config.method),
      url: `${response.config.baseURL ?? ''}${response.config.url ?? ''}`,
      status: response.status,
      duration_ms: durationMs ? Number(durationMs.toFixed(1)) : null,
    });
    return response;
  },
  (error) => {
    const config = error.config as (typeof error.config & ConfigWithMetadata) | undefined;
    const metadata = config?.metadata;
    const durationMs = metadata ? performance.now() - metadata.startedAtMs : undefined;
    const responseRequestId = (error.response?.headers?.['x-request-id'] as string | undefined) ?? metadata?.requestId;

    telemetry.apiError({
      request_id: responseRequestId,
      method: normalizeMethod(config?.method),
      url: `${config?.baseURL ?? ''}${config?.url ?? ''}`,
      status: error.response?.status ?? null,
      duration_ms: durationMs ? Number(durationMs.toFixed(1)) : null,
      error: error.message,
    });

    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      // Dispatch event instead of direct navigation (SPA-friendly)
      dispatchAuthExpired();
    }
    return Promise.reject(error);
  }
);
