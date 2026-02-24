import { api } from './client';

// ============ Response Types ============

export interface ConfigModel {
    white_list: number[];
    black_list: number[];
    owner_ids: number[];
    batch_msg_num: number;
    results_per_page: number;
    max_page: number;
    search_cache: boolean;
    cache_expire_seconds: number;
}

export interface ListUpdateResponse {
    updated_list: number[];
    added: number[];
    removed: number[];
}

// ============ API ============

export const configApi = {
    getConfig: () =>
        api.get<{ data: ConfigModel }>('/config'),

    addToWhitelist: (ids: number[]) =>
        api.post<{ data: ListUpdateResponse }>('/config/whitelist', { ids }),

    removeFromWhitelist: (ids: number[]) =>
        api.delete<{ data: ListUpdateResponse }>('/config/whitelist', { data: { ids } }),

    addToBlacklist: (ids: number[]) =>
        api.post<{ data: ListUpdateResponse }>('/config/blacklist', { ids }),

    removeFromBlacklist: (ids: number[]) =>
        api.delete<{ data: ListUpdateResponse }>('/config/blacklist', { data: { ids } }),
};
