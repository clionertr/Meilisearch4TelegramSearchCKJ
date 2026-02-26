import React, { lazy, Suspense, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence, MotionConfig } from 'framer-motion';
import Login from '@/pages/Login';       // Login: eager (首屏必需)
import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { PageTransition } from '@/components/common/PageTransition';
import { PageSkeleton } from '@/components/common/PageSkeleton';
import { ConfirmProvider } from '@/components/common/ConfirmProvider';
import { AppLayout } from '@/components/layout/AppLayout';
import { useStatusWebSocket } from '@/hooks/useWebSocket';
import { ProgressData, useStatusStore } from '@/store/statusStore';
import { AUTH_EXPIRED_EVENT } from '@/api/client';

// Lazy-loaded pages (code splitting)
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Settings = lazy(() => import('@/pages/Settings'));
const Search = lazy(() => import('@/pages/Search'));
const SyncedChats = lazy(() => import('@/pages/SyncedChats'));
const SelectChats = lazy(() => import('@/pages/SelectChats'));
const Storage = lazy(() => import('@/pages/Storage'));
const AIConfig = lazy(() => import('@/pages/AIConfig'));

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

  return (
    <Suspense fallback={<PageSkeleton />}>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/login" element={<PageTransition><Login /></PageTransition>} />

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={<ProtectedRoute><AppLayout><PageTransition><Dashboard /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/settings"
            element={<ProtectedRoute><AppLayout><PageTransition><Settings /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/search"
            element={<ProtectedRoute><AppLayout><PageTransition><Search /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/synced-chats"
            element={<ProtectedRoute><AppLayout><PageTransition><SyncedChats /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/select-chats"
            element={<ProtectedRoute><AppLayout><PageTransition><SelectChats /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/storage"
            element={<ProtectedRoute><AppLayout><PageTransition><Storage /></PageTransition></AppLayout></ProtectedRoute>}
          />
          <Route
            path="/ai-config"
            element={<ProtectedRoute><AppLayout><PageTransition><AIConfig /></PageTransition></AppLayout></ProtectedRoute>}
          />
        </Routes>
      </AnimatePresence>
    </Suspense>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <HashRouter>
          <ConfirmProvider>
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
          </ConfirmProvider>
        </HashRouter>
      </MotionConfig>
    </QueryClientProvider>
  );
};


export default App;
