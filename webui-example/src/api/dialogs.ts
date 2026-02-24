import { api } from './client';

// ============ Response Types ============

export interface AvailableDialogItem {
    id: number;
    title: string;
    type: string;
    message_count: number | null;
    sync_state: string;
}

export interface AvailableDialogsData {
    dialogs: AvailableDialogItem[];
    total: number;
}

export interface AvailableDialogsMeta {
    cached: boolean;
    cache_ttl_sec: number;
}

export interface AvailableDialogsResponse {
    success: boolean;
    data: AvailableDialogsData;
    meta: AvailableDialogsMeta;
}

export interface SyncedDialogItem {
    id: number;
    title: string;
    type: string;
    sync_state: string;
    last_synced_at: string | null;
    is_syncing: boolean;
    updated_at: string;
}

export interface SyncedDialogsData {
    dialogs: SyncedDialogItem[];
    total: number;
}

export interface SyncRequest {
    dialog_ids: number[];
    default_sync_state?: 'active' | 'paused';
}

export interface SyncResult {
    accepted: number[];
    ignored: number[];
    not_found: number[];
}

export interface PatchSyncStateResult {
    id: number;
    sync_state: string;
    updated_at: string;
}

export interface DeleteSyncResult {
    removed: boolean;
    purge_index: boolean;
    purge_error: string | null;
}

// ============ API ============

export const dialogsApi = {
    getAvailable: (params?: { refresh?: boolean; limit?: number }) =>
        api.get<AvailableDialogsResponse>('/dialogs/available', { params }),

    getSynced: () =>
        api.get<{ data: SyncedDialogsData }>('/dialogs/synced'),

    sync: (data: SyncRequest) =>
        api.post<{ data: SyncResult }>('/dialogs/sync', data),

    patchSyncState: (dialogId: number, sync_state: 'active' | 'paused') =>
        api.patch<{ data: PatchSyncStateResult }>(`/dialogs/${dialogId}/sync-state`, { sync_state }),

    deleteSync: (dialogId: number, purgeIndex?: boolean) =>
        api.delete<{ data: DeleteSyncResult }>(`/dialogs/${dialogId}/sync`, {
            params: purgeIndex !== undefined ? { purge_index: purgeIndex } : undefined,
        }),
};
