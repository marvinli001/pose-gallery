import useSWR from 'swr';
import { searchAPI } from '@/lib/api';
import { SearchResponse } from '@/lib/types';

interface UseSearchParams {
  query: string;
  category?: string;
  page?: number;
  per_page?: number;
}

export function useSearch(params: UseSearchParams) {
  const { query, category, page = 1, per_page = 20 } = params;
  
  const { data, error, isLoading, mutate } = useSWR<SearchResponse>(
    query ? ['search', query, category, page, per_page] : null,
    () => searchAPI.searchPoses({ q: query, category, page, per_page }),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  );

  return {
    data,
    isLoading,
    isError: error,
    mutate,
  };
}
