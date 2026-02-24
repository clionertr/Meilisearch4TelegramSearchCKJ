import { api } from './client';

// ============ Response Types ============

export interface AiConfigData {
    provider: string;
    base_url: string;
    model: string;
    api_key_set: boolean;
    updated_at: string | null;
}

export interface AiConfigUpdateRequest {
    provider?: string;
    base_url: string;
    model: string;
    api_key?: string;
}

export interface AiConfigTestData {
    ok: boolean;
    error_code: string | null;
    error_message: string | null;
    latency_ms: number;
}

export interface AiModelsData {
    models: string[];
    fallback: boolean;
}

// ============ API ============

export const aiConfigApi = {
    getConfig: () =>
        api.get<{ data: AiConfigData }>('/ai/config'),

    updateConfig: (data: AiConfigUpdateRequest) =>
        api.put<{ data: AiConfigData }>('/ai/config', data),

    testConnection: () =>
        api.post<{ data: AiConfigTestData }>('/ai/config/test'),

    getModels: () =>
        api.get<{ data: AiModelsData }>('/ai/models'),
};
