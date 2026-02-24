import { api } from './client';

// ============ Response Types ============

export interface StorageStatsData {
    total_bytes: number | null;
    index_bytes: number | null;
    media_bytes: number | null;
    cache_bytes: number | null;
    media_supported: boolean;
    cache_supported: boolean;
    notes: string[];
}

export interface AutoCleanData {
    enabled: boolean;
    media_retention_days: number;
}

export interface CacheCleanupData {
    targets_cleared: string[];
    freed_bytes: number | null;
}

export interface MediaCleanupData {
    not_applicable: boolean;
    reason: string;
    freed_bytes: number;
}

// ============ API ============

export const storageApi = {
    getStats: () =>
        api.get<{ data: StorageStatsData }>('/storage/stats'),

    patchAutoClean: (data: { enabled: boolean; media_retention_days?: number }) =>
        api.patch<{ data: AutoCleanData }>('/storage/auto-clean', data),

    cleanupCache: () =>
        api.post<{ data: CacheCleanupData }>('/storage/cleanup/cache'),

    cleanupMedia: () =>
        api.post<{ data: MediaCleanupData }>('/storage/cleanup/media'),
};
