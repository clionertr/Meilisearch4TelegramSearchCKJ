import { api } from './client';

export interface SearchRequest {
  q: string;
  limit?: number;
  offset?: number;
  chat_id?: number;
}

interface ChatInfo {
  id: number;
  type: string;
  title?: string | null;
  username?: string | null;
}

interface UserInfo {
  id: number;
  username?: string | null;
}

export interface SearchResult {
  id: string;
  chat: ChatInfo;
  from_user?: UserInfo | null;
  text: string;
  formatted_text?: string | null;
  date: string;
}

export interface SearchResponse {
  hits: SearchResult[];
  query: string;
  total_hits: number;
  limit: number;
  offset: number;
  processing_time_ms: number;
}

export const searchApi = {
  search: (params: SearchRequest) => api.get<{data: SearchResponse}>('/search', { params }),
};
