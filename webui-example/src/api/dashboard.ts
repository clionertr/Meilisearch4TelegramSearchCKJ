import { api } from './client';

// ============ Response Types ============

export interface DashboardActivityItem {
    chat_id: number;
    chat_title: string;
    chat_type: string;
    message_count: number;
    latest_message_time: string;
    top_keywords: string[];
    sample_message: string;
}

export interface DashboardActivityData {
    items: DashboardActivityItem[];
    total: number;
    sampled: boolean;
    sample_size: number;
}

export interface DashboardBriefData {
    summary: string;
    template_id: string;
    source_count: number;
    reason: string | null;
    sampled: boolean;
    sample_size: number;
}

// ============ API ============

export const dashboardApi = {
    getActivity: (params?: { window_hours?: number; limit?: number; offset?: number }) =>
        api.get<{ data: DashboardActivityData }>('/dashboard/activity', { params }),

    getBrief: (params?: { window_hours?: number; min_messages?: number }) =>
        api.get<{ data: DashboardBriefData }>('/dashboard/brief', { params }),
};
