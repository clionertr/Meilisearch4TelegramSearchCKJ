import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import BottomNav from '@/components/BottomNav';
import Dashboard from '@/pages/Dashboard';
import Login from '@/pages/Login';
import Settings from '@/pages/Settings';
import Search from '@/pages/Search';
import SyncedChats from '@/pages/SyncedChats';
import SelectChats from '@/pages/SelectChats';
import Storage from '@/pages/Storage';
import AIConfig from '@/pages/AIConfig';
import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { PageTransition } from '@/components/common/PageTransition';
import { AnimatePresence, MotionConfig } from 'framer-motion';
import { useStatusWebSocket } from '@/hooks/useWebSocket';
import { ProgressData, useStatusStore } from '@/store/statusStore';
import { AUTH_EXPIRED_EVENT } from '@/api/client';

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
    const message = lastMessage as { type?: string; data?: ProgressData } | null;
    if (message?.type === 'progress' && message.data?.dialog_id) {
      updateTask(message.data);
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
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/login" element={<PageTransition><Login /></PageTransition>} />

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<ProtectedRoute><PageTransition><Dashboard /></PageTransition></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><PageTransition><Settings /></PageTransition></ProtectedRoute>} />
          <Route path="/search" element={<ProtectedRoute><PageTransition><Search /></PageTransition></ProtectedRoute>} />
          <Route path="/synced-chats" element={<ProtectedRoute><PageTransition><SyncedChats /></PageTransition></ProtectedRoute>} />
          <Route path="/select-chats" element={<ProtectedRoute><PageTransition><SelectChats /></PageTransition></ProtectedRoute>} />
          <Route path="/storage" element={<ProtectedRoute><PageTransition><Storage /></PageTransition></ProtectedRoute>} />
          <Route path="/ai-config" element={<ProtectedRoute><PageTransition><AIConfig /></PageTransition></ProtectedRoute>} />
        </Routes>
      </AnimatePresence>
      {showBottomNav && <BottomNav />}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <HashRouter>
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              className: '',
              style: {
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '14px',
                fontWeight: '500',
              },
            }}
          />
        </HashRouter>
      </MotionConfig>
    </QueryClientProvider>
  );
};


export default App;
