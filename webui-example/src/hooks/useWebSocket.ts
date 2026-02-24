import useWebSocket from 'react-use-websocket';
import { useAuthStore } from '@/store/authStore';

const WS_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/^http/, 'ws') || `ws://${window.location.host}/api/v1`;

export const useStatusWebSocket = () => {
  const { token } = useAuthStore();
  const wsUrl = token ? `${WS_BASE_URL}/ws/status?token=${token}` : null;
  
  const { lastJsonMessage, readyState, sendMessage } = useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
  });

  return {
    lastMessage: lastJsonMessage,
    connectionStatus: readyState,
    sendMessage,
  };
};
