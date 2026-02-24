import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { storageApi } from '@/api/storage';
import { extractApiErrorMessage } from '@/api/error';

export const useStorageStats = () => {
    return useQuery({
        queryKey: ['storageStats'],
        queryFn: async () => {
            try {
                const response = await storageApi.getStats();
                return response.data.data ?? null;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load storage stats'));
            }
        },
        staleTime: 1000 * 60, // 1 minute
    });
};

export const useToggleAutoClean = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (enabled: boolean) => {
            try {
                const response = await storageApi.patchAutoClean({ enabled });
                return response.data.data;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to update auto-clean'));
            }
        },
        onSuccess: () => {
            // Invalidate storage stats because auto-clean might change them
            // actually, just patching auto clean enabled doesn't change stats immediately 
            // but it's good practice.
            queryClient.invalidateQueries({ queryKey: ['storageStats'] });
        },
    });
};

export const useCleanupCache = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            try {
                const response = await storageApi.cleanupCache();
                return response.data.data;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to cleanup cache'));
            }
        },
        onSuccess: () => {
            // Refresh storage stats to get new sizes
            queryClient.invalidateQueries({ queryKey: ['storageStats'] });
        },
    });
};

export const useCleanupMedia = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            try {
                const response = await storageApi.cleanupMedia();
                return response.data.data;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to cleanup media'));
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['storageStats'] });
        },
    });
};
