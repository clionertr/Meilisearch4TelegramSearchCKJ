import { useInfiniteQuery } from '@tanstack/react-query';
import { searchApi } from '@/api/search';

export interface SearchFilters {
    dateFrom?: string;
    dateTo?: string;
    senderUsername?: string;
}

export const useSearchQuery = (query: string, limit: number = 20, filters?: SearchFilters) => {
    return useInfiniteQuery({
        queryKey: ['search', query, filters],
        queryFn: ({ pageParam = 0 }) =>
            searchApi.search({
                q: query,
                offset: pageParam,
                limit,
                date_from: filters?.dateFrom,
                date_to: filters?.dateTo,
                sender_username: filters?.senderUsername,
            }),
        getNextPageParam: (lastPage) => {
            const { offset, limit, total_hits } = lastPage.data.data;
            return offset + limit < total_hits ? offset + limit : undefined;
        },
        enabled: query.trim().length > 0,
        initialPageParam: 0,
        staleTime: 1000 * 60, // 1 minute
    });
};
