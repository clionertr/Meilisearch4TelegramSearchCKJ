import { api } from './client';

export interface ClientStatusResponse {
  is_running: boolean;
  api_only_mode: boolean;
  state: 'stopped' | 'starting' | 'running' | 'stopping' | string;
  last_action_source: string | null;
  last_error: string | null;
  telegram_connected: boolean;
  bot_handler_initialized: boolean;
}

export interface ClientControlResponse {
  status: 'started' | 'stopped' | 'already_running' | 'already_stopped' | string;
  message: string;
}

export const controlApi = {
  getStatus: () =>
    api.get<{ data: ClientStatusResponse }>('/client/status'),

  startClient: () =>
    api.post<{ data: ClientControlResponse }>('/client/start'),

  stopClient: () =>
    api.post<{ data: ClientControlResponse }>('/client/stop'),
};
