import { api } from './client';

// ============ Response Types ============

export interface SystemStatus {
    uptime_seconds: number;
    meili_connected: boolean;
    bot_connected: boolean;
    telegram_connected: boolean;
    indexed_messages: number;
    memory_usage_mb: number;
    version: string;
}

export interface DialogInfo {
    id: number;
    title: string;
    type: string;
    message_count: number;
    last_synced: string | null;
    is_syncing: boolean;
}

export interface DialogListResponse {
    dialogs: DialogInfo[];
    total: number;
}

export interface ProgressData {
    [key: string]: {
        dialog_id: number;
        dialog_title: string;
        current: number;
        total: number;
        percentage: number;
        status: string;
    };
}

export interface DownloadProgressResponse {
    progress: ProgressData;
    count: number;
}

// ============ API ============

export const statusApi = {
    getStatus: () =>
        api.get<{ data: SystemStatus }>('/status'),

    getDialogs: () =>
        api.get<{ data: DialogListResponse }>('/status/dialogs'),

    getProgress: () =>
        api.get<{ data: DownloadProgressResponse }>('/status/progress'),
};
