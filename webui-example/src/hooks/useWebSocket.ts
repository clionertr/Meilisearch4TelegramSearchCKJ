import { useEffect, useMemo } from 'react';
import useWebSocket from 'react-use-websocket';
import { useAuthStore } from '@/store/authStore';
import { telemetry } from '@/utils/telemetry';

const resolveWsBaseUrl = (): string => {
  const rawApiUrl = import.meta.env.VITE_API_URL || '/api/v1';

  if (rawApiUrl.startsWith('ws://') || rawApiUrl.startsWith('wss://')) {
    return rawApiUrl;
  }

  if (rawApiUrl.startsWith('http://') || rawApiUrl.startsWith('https://')) {
    return rawApiUrl.replace(/^http/, 'ws');
  }

  if (typeof window === 'undefined') {
    return rawApiUrl;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  if (rawApiUrl.startsWith('/')) {
    return `${protocol}//${window.location.host}${rawApiUrl}`;
  }
  return `${protocol}//${rawApiUrl}`;
};

const readyStateToText = (state: number): string => {
  switch (state) {
    case 0:
      return 'CONNECTING';
    case 1:
      return 'OPEN';
    case 2:
      return 'CLOSING';
    case 3:
      return 'CLOSED';
    default:
      return 'UNINSTANTIATED';
  }
};

export const useStatusWebSocket = () => {
  const { token } = useAuthStore();
  const wsBaseUrl = useMemo(() => resolveWsBaseUrl(), []);
  const wsUrl = useMemo(() => {
    if (!token) {
      return null;
    }
    return `${wsBaseUrl}/ws/status?token=${encodeURIComponent(token)}`;
  }, [token, wsBaseUrl]);

  const { lastJsonMessage, readyState, sendMessage } = useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
  });

  useEffect(() => {
    telemetry.wsState({
      state: readyStateToText(readyState),
      ws_url: wsUrl ? `${wsBaseUrl}/ws/status` : null,
    });
  }, [readyState, wsBaseUrl, wsUrl]);

  useEffect(() => {
    if (!lastJsonMessage || typeof lastJsonMessage !== 'object') {
      return;
    }
    const eventType = 'type' in lastJsonMessage ? String(lastJsonMessage.type) : 'unknown';
    telemetry.wsMessage({ event_type: eventType });
  }, [lastJsonMessage]);

  return {
    lastMessage: lastJsonMessage,
    connectionStatus: readyState,
    sendMessage,
  };
};
