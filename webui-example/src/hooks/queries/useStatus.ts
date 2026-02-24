import { useQuery } from '@tanstack/react-query';
import { statusApi } from '@/api/status';
import { extractApiErrorMessage } from '@/api/error';

export const useSystemStatus = () => {
    return useQuery({
        queryKey: ['systemStatus'],
        queryFn: async () => {
            try {
                const response = await statusApi.getStatus();
                return response.data.data ?? null;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load system status'));
            }
        },
        refetchInterval: 1000 * 30, // Auto refresh every 30 seconds
        staleTime: 1000 * 10, // 10 seconds
    });
};
