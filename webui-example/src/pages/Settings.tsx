import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Skeleton } from '@/components/common/Skeleton';
import { useStorageStats } from '@/hooks/queries/useStorage';
import { useSystemStatus } from '@/hooks/queries/useStatus';
import { formatBytes } from '@/utils/formatters';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import { useTheme } from '@/hooks/useTheme';
import toast from '@/components/Toast/toast';
import { useConfirm } from '@/hooks/useConfirm';

const Settings: React.FC = () => {
  const navigate = useNavigate();

  const { data: storageStats, isLoading: storageLoading, error: storageError } = useStorageStats();
  const { data: systemStatus, isLoading: statusLoading, error: statusError } = useSystemStatus();
  const { theme, setTheme } = useTheme();
  const { confirm } = useConfirm();

  const loading = storageLoading || statusLoading;
  const error = storageError?.message || statusError?.message;

  const handleLogout = async () => {
    const ok = await confirm({
      title: 'Logout',
      message: 'Are you sure you want to log out of this session?',
      variant: 'danger',
      confirmLabel: 'Logout',
    });
    if (!ok) return;
    try {
      await authApi.logout();
    } catch {
      // Backend failure is acceptable — always clear local credentials
    }
    useAuthStore.getState().logout();
    toast.success('Logged out successfully');
    navigate('/login');
  };

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-md">
        <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
          <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
        </button>
        <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">Settings & Management</h2>
        <button className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
          <span className="material-symbols-outlined text-2xl">more_horiz</span>
        </button>
      </div>

      {loading && (
        <div className="p-4 space-y-4">
          {/* Storage card skeleton */}
          <Skeleton variant="card" height="10rem" />
          {/* System status 2-col grid skeleton */}
          <div className="grid grid-cols-2 gap-3">
            <Skeleton variant="card" height="5rem" />
            <Skeleton variant="card" height="5rem" />
          </div>
        </div>
      )}

      {error && (
        <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm mb-3">
          {error}
        </div>
      )}

      {/* Storage Card */}
      <div className="p-4">
        <div className="flex flex-col items-stretch justify-start rounded-xl p-5 shadow-lg bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Device Health</p>
              <h3 className="text-2xl font-bold leading-tight dark:text-white">Storage Usage</h3>
            </div>
            <span className="material-symbols-outlined text-primary text-3xl">database</span>
          </div>
          <div className="flex items-center gap-6 mb-6">
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex justify-between items-end dark:text-white">
                <p className="text-2xl font-bold">{formatBytes(storageStats?.total_bytes ?? null)}</p>
              </div>
              <p className="text-slate-500 dark:text-muted-dark text-xs font-normal leading-relaxed mt-1">
                {systemStatus
                  ? `TeleMemory is indexing ${systemStatus.indexed_messages.toLocaleString()} messages.`
                  : 'Loading status...'
                }
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => navigate('/storage')} className="flex-1 flex cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 bg-primary text-background-dark text-sm font-bold shadow-md active:scale-95 transition-transform">
              <span className="material-symbols-outlined text-lg">cleaning</span>
              <span>Quick Clean</span>
            </button>
            <button className="w-12 flex items-center justify-center rounded-lg h-12 bg-slate-100 dark:bg-button-secondary-dark text-slate-600 dark:text-white border border-slate-200 dark:border-white/5">
              <span className="material-symbols-outlined">settings</span>
            </button>
          </div>
        </div>
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="px-4 py-2">
          <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">System Status</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${systemStatus.meili_connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">MeiliSearch</span>
              </div>
              <p className={`text-sm font-bold ${systemStatus.meili_connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {systemStatus.meili_connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${systemStatus.telegram_connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Telegram</span>
              </div>
              <p className={`text-sm font-bold ${systemStatus.telegram_connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {systemStatus.telegram_connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Appearance */}
      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">Appearance</h3>
        <div className="p-1 rounded-xl bg-slate-100 dark:bg-card-dark border border-slate-200 dark:border-white/5 flex gap-1">
          {(['light', 'dark', 'system'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold capitalize transition-all ${theme === t
                ? 'bg-white dark:bg-white/10 text-primary shadow-sm dark:text-white'
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
                }`}
            >
              <span className="material-symbols-outlined text-[18px]">
                {t === 'light' ? 'light_mode' : t === 'dark' ? 'dark_mode' : 'desktop_windows'}
              </span>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Configurations */}
      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">Configurations</h3>
        <div className="grid grid-cols-2 gap-4">
          <div onClick={() => navigate('/ai-config')} className="flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">psychology</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">AI Configuration</p>
              <p className="text-slate-500 dark:text-muted-dark text-xs mt-1">OpenAI, Claude, Local</p>
            </div>
          </div>
          <div onClick={() => navigate('/synced-chats')} className="flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">sync</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">Synced Chats</p>
              <p className="text-slate-500 dark:text-muted-dark text-xs mt-1">Manage sync settings</p>
            </div>
          </div>
        </div>
      </div>

      {/* Logout */}
      <div className="px-4 pb-6 pt-2">
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-red-300 dark:border-red-500/40 text-red-500 dark:text-red-400 font-semibold hover:bg-red-50 dark:hover:bg-red-500/10 active:scale-[0.98] transition-all"
        >
          <span className="material-symbols-outlined text-xl">logout</span>
          Logout
        </button>
      </div>
    </div>
  );
};

export default Settings;
