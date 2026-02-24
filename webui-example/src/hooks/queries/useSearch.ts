import { useInfiniteQuery } from '@tanstack/react-query';
import { searchApi } from '@/api/search';

export const useSearchQuery = (query: string, limit: number = 20) => {
    return useInfiniteQuery({
        queryKey: ['search', query],
        queryFn: ({ pageParam = 0 }) =>
            searchApi.search({ q: query, offset: pageParam, limit }),
        getNextPageParam: (lastPage) => {
            const { offset, limit, total_hits } = lastPage.data.data;
            return offset + limit < total_hits ? offset + limit : undefined;
        },
        enabled: query.trim().length > 0,
        initialPageParam: 0,
        staleTime: 1000 * 60, // 1 minute
    });
};
