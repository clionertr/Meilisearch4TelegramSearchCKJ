/**
 * Dashboard 状态数据 Hooks — 作为 useDashboardStatus 的并行查询集合
 *  - useSearchStats: 获取索引消息总数
 *  - useSyncedDialogsCount: 获取已同步聊天数
 */
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '@/api/search';
import { dialogsApi } from '@/api/dialogs';
import { extractApiErrorMessage } from '@/api/error';

export const useSearchStats = () => {
    return useQuery({
        queryKey: ['search', 'stats'],
        queryFn: async () => {
            try {
                const response = await searchApi.getStats();
                return response.data.data?.total_documents ?? null;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load search stats'));
            }
        },
        staleTime: 1000 * 60 * 5,
    });
};

export const useSyncedDialogsCount = () => {
    return useQuery({
        queryKey: ['dialogs', 'synced', 'count'],
        queryFn: async () => {
            try {
                const response = await dialogsApi.getSynced();
                // SyncedDialogsData has { dialogs: SyncedDialogItem[], total: number }
                return response.data.data?.total ?? response.data.data?.dialogs?.length ?? 0;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load synced dialogs'));
            }
        },
        staleTime: 1000 * 60 * 5,
    });
};
