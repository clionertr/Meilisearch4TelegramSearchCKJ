import { api } from './client';

export interface SearchRequest {
  q: string;
  limit?: number;
  offset?: number;
  chat_id?: number;
}

export interface SearchResult {
  id: number;
  chat_id: number;
  chat_title: string;
  sender_name: string;
  text: string;
  formatted_text: string;
  date: string;
  message_id: number;
}

export interface SearchResponse {
  hits: SearchResult[];
  total: number;
  limit: number;
  offset: number;
  processing_time_ms: number;
}

export const searchApi = {
  search: (params: SearchRequest) => api.get<{data: SearchResponse}>('/search', { params }),
};
