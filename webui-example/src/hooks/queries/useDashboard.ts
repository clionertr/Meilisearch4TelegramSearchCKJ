import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';
import { extractApiErrorMessage } from '@/api/error';

export const useDashboardActivities = (limit = 20) => {
    return useQuery({
        queryKey: ['dashboard', 'activities', limit],
        queryFn: async () => {
            try {
                const response = await dashboardApi.getActivity({ limit });
                return response.data.data?.items ?? [];
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load dashboard activity'));
            }
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    });
};

export const useDashboardBrief = () => {
    return useQuery({
        queryKey: ['dashboard', 'brief'],
        queryFn: async () => {
            try {
                const response = await dashboardApi.getBrief();
                return response.data.data ?? null;
            } catch (err) {
                throw new Error(extractApiErrorMessage(err, 'Failed to load dashboard brief'));
            }
        },
        staleTime: 1000 * 60 * 30, // 30 minutes
    });
};
