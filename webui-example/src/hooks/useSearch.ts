import { useInfiniteQuery } from '@tanstack/react-query';
import { searchApi, SearchRequest } from '@/api/search';

export const useSearchMessages = (params: SearchRequest) => {
  return useInfiniteQuery({
    queryKey: ['messages', 'search', params.q, params.chat_id],
    queryFn: ({ pageParam = 0 }) =>
      searchApi.search({ ...params, offset: pageParam, limit: params.limit || 20 })
        .then(res => res.data.data),
    getNextPageParam: (lastPage) => {
      const currentTotal = lastPage.offset + lastPage.limit;
      return currentTotal < lastPage.total_hits ? currentTotal : undefined;
    },
    initialPageParam: 0,
    enabled: !!params.q && params.q.length >= 2,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
