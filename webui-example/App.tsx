import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BottomNav from './components/BottomNav';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Settings from './pages/Settings';
import Search from './pages/Search';
import SyncedChats from './pages/SyncedChats';
import SelectChats from './pages/SelectChats';
import Storage from './pages/Storage';
import AIConfig from './pages/AIConfig';
import { ProtectedRoute } from './src/components/common/ProtectedRoute';
import { useStatusWebSocket } from './src/hooks/useWebSocket';
import { useStatusStore } from './src/store/statusStore';
import { AUTH_EXPIRED_EVENT } from './src/api/client';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const AppContent: React.FC = () => {
  const { lastMessage } = useStatusWebSocket();
  const updateTask = useStatusStore((state) => state.updateTask);
  const location = useLocation();
  const navigate = useNavigate();

  // Handle WebSocket status updates
  useEffect(() => {
    if (lastMessage && (lastMessage as any).task_id) {
      updateTask(lastMessage as any);
    }
  }, [lastMessage, updateTask]);

  // Listen for auth expiration event (from API client)
  useEffect(() => {
    const handleAuthExpired = () => {
      navigate('/login');
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    };
  }, [navigate]);

  const showBottomNav = location.pathname !== '/login';

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark max-w-md mx-auto relative shadow-2xl overflow-hidden">
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
        <Route path="/synced-chats" element={<ProtectedRoute><SyncedChats /></ProtectedRoute>} />
        <Route path="/select-chats" element={<ProtectedRoute><SelectChats /></ProtectedRoute>} />
        <Route path="/storage" element={<ProtectedRoute><Storage /></ProtectedRoute>} />
        <Route path="/ai-config" element={<ProtectedRoute><AIConfig /></ProtectedRoute>} />
      </Routes>
      {showBottomNav && <BottomNav />}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AppContent />
      </HashRouter>
    </QueryClientProvider>
  );
};

export default App;
