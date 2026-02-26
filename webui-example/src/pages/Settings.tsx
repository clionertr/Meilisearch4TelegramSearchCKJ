import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  const { t, i18n } = useTranslation();

  const { data: storageStats, isLoading: storageLoading, error: storageError } = useStorageStats();
  const { data: systemStatus, isLoading: statusLoading, error: statusError } = useSystemStatus();
  const { theme, setTheme } = useTheme();
  const { confirm } = useConfirm();

  const loading = storageLoading || statusLoading;
  const error = storageError?.message || statusError?.message;

  const handleLogout = async () => {
    const ok = await confirm({
      title: t('settings.logoutConfirmTitle'),
      message: t('settings.logoutConfirmMessage'),
      variant: 'danger',
      confirmLabel: t('settings.logout'),
    });
    if (!ok) return;
    try {
      await authApi.logout();
    } catch {
      // Backend failure is acceptable — always clear local credentials
    }
    useAuthStore.getState().logout();
    toast.success(t('settings.logoutSuccess'));
    navigate('/login');
  };

  const handleLanguageChange = async (lng: 'en-US' | 'zh-CN') => {
    await i18n.changeLanguage(lng);
    const languageLabel = lng === 'zh-CN' ? t('language.chinese') : t('language.english');
    toast.info(t('language.switched', { language: languageLabel }));
  };

  return (
    <div className="pb-24 md:pb-8">
      <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-md">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label={t('a11y.back')}
          className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5"
        >
          <span className="material-symbols-outlined text-2xl" aria-hidden="true">arrow_back_ios_new</span>
        </button>
        <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">{t('settings.title')}</h2>
        <button type="button" className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5" aria-label={t('settings.moreOptions')}>
          <span className="material-symbols-outlined text-2xl" aria-hidden="true">more_horiz</span>
        </button>
      </div>

      {loading && (
        <div className="p-4 space-y-4" aria-busy="true">
          <Skeleton variant="card" height="10rem" />
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

      <div className="p-4">
        <div className="flex flex-col items-stretch justify-start rounded-xl p-5 shadow-lg bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">{t('settings.deviceHealth')}</p>
              <h3 className="text-2xl font-bold leading-tight dark:text-white">{t('settings.storageUsage')}</h3>
            </div>
            <span className="material-symbols-outlined text-primary text-3xl" aria-hidden="true">database</span>
          </div>
          <div className="flex items-center gap-6 mb-6">
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex justify-between items-end dark:text-white">
                <p className="text-2xl font-bold">{formatBytes(storageStats?.total_bytes ?? null)}</p>
              </div>
              <p className="text-slate-500 dark:text-muted-dark text-xs font-normal leading-relaxed mt-1">
                {systemStatus
                  ? t('settings.indexedMessagesHint', { count: systemStatus.indexed_messages.toLocaleString() })
                  : t('settings.loadingStatus')
                }
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/storage')}
              className="focus-ring flex-1 flex cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 bg-primary text-background-dark text-sm font-bold shadow-md active:scale-95 transition-transform"
            >
              <span className="material-symbols-outlined text-lg" aria-hidden="true">cleaning</span>
              <span>{t('settings.quickClean')}</span>
            </button>
            <button type="button" className="focus-ring w-12 flex items-center justify-center rounded-lg h-12 bg-slate-100 dark:bg-button-secondary-dark text-slate-600 dark:text-white border border-slate-200 dark:border-white/5" aria-label={t('settings.configurations')}>
              <span className="material-symbols-outlined" aria-hidden="true">settings</span>
            </button>
          </div>
        </div>
      </div>

      {systemStatus && (
        <div className="px-4 py-2">
          <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.systemStatus')}</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`w-2 h-2 rounded-full ${systemStatus.meili_connected ? 'bg-green-500' : 'bg-red-500'}`}
                  aria-label={t('a11y.statusIndicator', {
                    label: t('status.meilisearch'),
                    status: systemStatus.meili_connected ? t('status.connected') : t('status.disconnected'),
                  })}
                />
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('status.meilisearch')}</span>
              </div>
              <p className={`text-sm font-bold ${systemStatus.meili_connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {systemStatus.meili_connected ? t('status.connected') : t('status.disconnected')}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5">
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`w-2 h-2 rounded-full ${systemStatus.telegram_connected ? 'bg-green-500' : 'bg-red-500'}`}
                  aria-label={t('a11y.statusIndicator', {
                    label: t('status.telegram'),
                    status: systemStatus.telegram_connected ? t('status.connected') : t('status.disconnected'),
                  })}
                />
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('status.telegram')}</span>
              </div>
              <p className={`text-sm font-bold ${systemStatus.telegram_connected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {systemStatus.telegram_connected ? t('status.connected') : t('status.disconnected')}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.appearance')}</h3>
        <div className="p-1 rounded-xl bg-slate-100 dark:bg-card-dark border border-slate-200 dark:border-white/5 flex gap-1">
          {(['light', 'dark', 'system'] as const).map((currentTheme) => (
            <button
              key={currentTheme}
              type="button"
              onClick={() => setTheme(currentTheme)}
              aria-label={t(`theme.${currentTheme}`)}
              className={`focus-ring flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${theme === currentTheme
                ? 'bg-white dark:bg-white/10 text-primary shadow-sm dark:text-white'
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
                }`}
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                {currentTheme === 'light' ? 'light_mode' : currentTheme === 'dark' ? 'dark_mode' : 'desktop_windows'}
              </span>
              {t(`theme.${currentTheme}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.language')}</h3>
        <div className="p-1 rounded-xl bg-slate-100 dark:bg-card-dark border border-slate-200 dark:border-white/5 flex gap-1">
          <button
            type="button"
            onClick={() => handleLanguageChange('en-US')}
            className={`focus-ring flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${i18n.language === 'en-US'
              ? 'bg-white dark:bg-white/10 text-primary shadow-sm dark:text-white'
              : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
          >
            {t('language.english')}
          </button>
          <button
            type="button"
            onClick={() => handleLanguageChange('zh-CN')}
            className={`focus-ring flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${i18n.language === 'zh-CN'
              ? 'bg-white dark:bg-white/10 text-primary shadow-sm dark:text-white'
              : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
          >
            {t('language.chinese')}
          </button>
        </div>
      </div>

      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.configurations')}</h3>
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => navigate('/ai-config')}
            className="focus-ring text-left flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary" aria-hidden="true">psychology</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm" aria-hidden="true">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">{t('settings.aiConfiguration')}</p>
              <p className="text-slate-500 dark:text-muted-dark text-xs mt-1">{t('settings.aiProviders')}</p>
            </div>
          </button>
          <button
            type="button"
            onClick={() => navigate('/synced-chats')}
            className="focus-ring text-left flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary" aria-hidden="true">sync</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm" aria-hidden="true">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">{t('settings.syncedChats')}</p>
              <p className="text-slate-500 dark:text-muted-dark text-xs mt-1">{t('settings.manageSyncSettings')}</p>
            </div>
          </button>
        </div>
      </div>

      <div className="px-4 pb-6 pt-2">
        <button
          type="button"
          onClick={handleLogout}
          className="focus-ring w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-red-300 dark:border-red-500/40 text-red-500 dark:text-red-400 font-semibold hover:bg-red-50 dark:hover:bg-red-500/10 active:scale-[0.98] transition-all"
        >
          <span className="material-symbols-outlined text-xl" aria-hidden="true">logout</span>
          {t('settings.logout')}
        </button>
      </div>
    </div>
  );
};

export default Settings;
