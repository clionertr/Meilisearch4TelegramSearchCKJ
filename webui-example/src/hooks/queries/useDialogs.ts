import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dialogsApi } from '@/api/dialogs';
import { extractApiErrorMessage } from '@/api/error';

export const useSyncedDialogs = () => {
    return useQuery({
        queryKey: ['syncedDialogs'],
        queryFn: async () => {
            try {
                const response = await dialogsApi.getSynced();
                return response.data.data?.dialogs ?? [];
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load synced chats'));
            }
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    });
};

export const useAvailableDialogs = (limit: number = 200) => {
    return useQuery({
        queryKey: ['availableDialogs', limit],
        queryFn: async () => {
            try {
                const response = await dialogsApi.getAvailable({ limit });
                return response.data.data?.dialogs ?? [];
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load available chats'));
            }
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    });
};

export const useSyncDialogs = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (dialogIds: number[]) => {
            try {
                const response = await dialogsApi.sync({ dialog_ids: dialogIds });
                return response.data.data;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to start sync'));
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['syncedDialogs'] });
            queryClient.invalidateQueries({ queryKey: ['availableDialogs'] });
        },
    });
};

export const useToggleDialogSyncState = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ dialogId, newState }: { dialogId: number; newState: 'active' | 'paused' }) => {
            try {
                const response = await dialogsApi.patchSyncState(dialogId, newState);
                return response.data.data;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to update sync state'));
            }
        },
        onMutate: async ({ dialogId, newState }) => {
            // Optimistic update
            await queryClient.cancelQueries({ queryKey: ['syncedDialogs'] });

            const previousDialogs = queryClient.getQueryData<any[]>(['syncedDialogs']);

            if (previousDialogs) {
                queryClient.setQueryData(['syncedDialogs'], previousDialogs.map(d =>
                    d.id === dialogId ? { ...d, sync_state: newState } : d
                ));
            }

            return { previousDialogs };
        },
        onError: (err, variables, context) => {
            if (context?.previousDialogs) {
                queryClient.setQueryData(['syncedDialogs'], context.previousDialogs);
            }
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['syncedDialogs'] });
        },
    });
};
