import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Skeleton } from '@/components/common/Skeleton';
import { useStorageStats } from '@/hooks/queries/useStorage';
import { useSystemStatus } from '@/hooks/queries/useStatus';
import {
  useAddToBlacklist,
  useAddToWhitelist,
  useRemoveFromBlacklist,
  useRemoveFromWhitelist,
  useSystemConfig,
} from '@/hooks/queries/useConfig';
import { useClientStatus, useStartClient, useStopClient } from '@/hooks/queries/useControl';
import { formatBytes } from '@/utils/formatters';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import { useTheme } from '@/hooks/useTheme';
import toast from '@/components/Toast/toast';
import { useConfirm } from '@/hooks/useConfirm';

const parsePolicyId = (value: string): number | null => {
  const trimmed = value.trim();
  if (!/^-?\d+$/.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) ? parsed : null;
};

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  const [whitelistInput, setWhitelistInput] = useState('');
  const [blacklistInput, setBlacklistInput] = useState('');

  const { data: storageStats, isLoading: storageLoading, error: storageError } = useStorageStats();
  const { data: systemStatus, isLoading: statusLoading, error: statusError } = useSystemStatus();
  const { data: systemConfig, isLoading: configLoading, error: configError } = useSystemConfig();
  const { data: clientStatus, isLoading: clientStatusLoading, error: clientStatusError } = useClientStatus();
  const addToWhitelistMutation = useAddToWhitelist();
  const removeFromWhitelistMutation = useRemoveFromWhitelist();
  const addToBlacklistMutation = useAddToBlacklist();
  const removeFromBlacklistMutation = useRemoveFromBlacklist();
  const startClientMutation = useStartClient();
  const stopClientMutation = useStopClient();

  const { theme, setTheme } = useTheme();
  const { confirm } = useConfirm();

  const loading = storageLoading || statusLoading;
  const error = storageError?.message || statusError?.message;
  const runtimeError = clientStatusError?.message || startClientMutation.error?.message || stopClientMutation.error?.message;
  const policyError =
    configError?.message ||
    addToWhitelistMutation.error?.message ||
    removeFromWhitelistMutation.error?.message ||
    addToBlacklistMutation.error?.message ||
    removeFromBlacklistMutation.error?.message;

  const isRuntimePending = startClientMutation.isPending || stopClientMutation.isPending;
  const isWhitelistPending = addToWhitelistMutation.isPending || removeFromWhitelistMutation.isPending;
  const isBlacklistPending = addToBlacklistMutation.isPending || removeFromBlacklistMutation.isPending;

  const whitelist = systemConfig?.white_list ?? [];
  const blacklist = systemConfig?.black_list ?? [];
  const ownerIds = systemConfig?.owner_ids ?? [];

  const runtimeState = clientStatus?.state ?? 'unknown';
  const runtimeStateLabel = t(`settings.runtimeStates.${runtimeState}`, { defaultValue: runtimeState });
  const runtimeSource = clientStatus?.last_action_source ?? 'unknown';
  const runtimeSourceLabel = t(`settings.runtimeSources.${runtimeSource}`, { defaultValue: runtimeSource });
  const canStartClient = !(clientStatus?.api_only_mode ?? false);

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
      // Backend failure is acceptable — always clear local credentials.
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

  const handleRuntimeAction = () => {
    if (!clientStatus) {
      return;
    }

    if (clientStatus.is_running) {
      stopClientMutation.mutate(undefined, {
        onSuccess: (res) => {
          toast.success(res?.message || t('settings.runtimeStopSuccess'));
        },
      });
      return;
    }

    if (!canStartClient) {
      toast.error(t('settings.runtimeApiOnlyError'));
      return;
    }

    startClientMutation.mutate(undefined, {
      onSuccess: (res) => {
        toast.success(res?.message || t('settings.runtimeStartSuccess'));
      },
    });
  };

  const handleAddPolicyId = (kind: 'whitelist' | 'blacklist') => {
    const rawValue = kind === 'whitelist' ? whitelistInput : blacklistInput;
    const parsedId = parsePolicyId(rawValue);

    if (parsedId === null) {
      toast.error(t('settings.policyInvalidId'));
      return;
    }

    const targetList = kind === 'whitelist' ? whitelist : blacklist;
    if (targetList.includes(parsedId)) {
      toast.info(t('settings.policyAlreadyExists', { id: parsedId }));
      return;
    }

    if (kind === 'whitelist') {
      addToWhitelistMutation.mutate([parsedId], {
        onSuccess: () => {
          setWhitelistInput('');
          toast.success(t('settings.policyAdded', { id: parsedId, list: t('settings.whitelist') }));
        },
      });
      return;
    }

    addToBlacklistMutation.mutate([parsedId], {
      onSuccess: () => {
        setBlacklistInput('');
        toast.success(t('settings.policyAdded', { id: parsedId, list: t('settings.blacklist') }));
      },
    });
  };

  const handleRemovePolicyId = (kind: 'whitelist' | 'blacklist', id: number) => {
    if (kind === 'whitelist') {
      removeFromWhitelistMutation.mutate([id], {
        onSuccess: () => {
          toast.success(t('settings.policyRemoved', { id, list: t('settings.whitelist') }));
        },
      });
      return;
    }

    removeFromBlacklistMutation.mutate([id], {
      onSuccess: () => {
        toast.success(t('settings.policyRemoved', { id, list: t('settings.blacklist') }));
      },
    });
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
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.runtimeControl')}</h3>

        {clientStatusLoading ? (
          <Skeleton variant="card" height="10rem" />
        ) : (
          <div className="rounded-xl p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm space-y-4">
            {runtimeError && (
              <div className="p-3 rounded-lg bg-red-100 border border-red-400 text-red-700 text-sm">
                {runtimeError}
              </div>
            )}

            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('settings.runtimeStateLabel')}</p>
                <p className="text-base font-bold dark:text-white">{runtimeStateLabel}</p>
              </div>
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${clientStatus?.is_running ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
                {clientStatus?.is_running ? t('settings.runtimeRunning') : t('settings.runtimeStopped')}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.runtimeSourceLabel')}</p>
                <p className="font-semibold dark:text-white">{runtimeSourceLabel}</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.runtimeModeLabel')}</p>
                <p className="font-semibold dark:text-white">
                  {clientStatus?.api_only_mode ? t('settings.runtimeApiOnlyMode') : t('settings.runtimeFullMode')}
                </p>
              </div>
            </div>

            {clientStatus?.last_error && (
              <div className="rounded-lg bg-amber-100/70 dark:bg-amber-900/20 border border-amber-300/60 dark:border-amber-700/50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">{t('settings.runtimeLastError')}</p>
                <p className="text-sm mt-1 text-amber-800 dark:text-amber-200 break-words">{clientStatus.last_error}</p>
              </div>
            )}

            <p className="text-xs text-slate-500 dark:text-slate-400">
              {clientStatus?.api_only_mode ? t('settings.runtimeApiOnlyHint') : t('settings.runtimeHint')}
            </p>

            <button
              type="button"
              onClick={handleRuntimeAction}
              disabled={isRuntimePending || (!canStartClient && !(clientStatus?.is_running ?? false))}
              className={`focus-ring w-full h-11 rounded-lg font-semibold text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${clientStatus?.is_running ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-primary hover:bg-primary/90 text-white'}`}
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                {clientStatus?.is_running ? 'stop_circle' : 'play_circle'}
              </span>
              {isRuntimePending
                ? (clientStatus?.is_running ? t('settings.runtimeStopping') : t('settings.runtimeStarting'))
                : (clientStatus?.is_running ? t('settings.runtimeActionStop') : t('settings.runtimeActionStart'))}
            </button>
          </div>
        )}
      </div>

      <div className="px-4 py-4">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">{t('settings.syncPolicy')}</h3>

        {configLoading ? (
          <Skeleton variant="card" height="13rem" />
        ) : (
          <div className="space-y-3">
            {policyError && (
              <div className="p-3 rounded-lg bg-red-100 border border-red-400 text-red-700 text-sm">
                {policyError}
              </div>
            )}

            <div className="rounded-xl p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold dark:text-white">{t('settings.whitelist')}</h4>
                <span className="text-xs text-slate-500 dark:text-slate-400">{whitelist.length}</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={whitelistInput}
                  onChange={(e) => setWhitelistInput(e.target.value)}
                  placeholder={t('settings.policyInputPlaceholder')}
                  className="flex-1 h-10 rounded-lg border border-slate-200 dark:border-white/10 px-3 bg-white dark:bg-slate-900/40 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label={t('settings.policyInputWhitelistA11y')}
                />
                <button
                  type="button"
                  onClick={() => handleAddPolicyId('whitelist')}
                  disabled={isWhitelistPending}
                  className="focus-ring h-10 px-3 rounded-lg bg-primary text-white text-sm font-semibold disabled:opacity-60"
                >
                  {t('settings.policyAddWhitelist')}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {whitelist.length === 0 && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyEmptyWhitelist')}</p>
                )}
                {whitelist.map((id) => (
                  <span key={`white-${id}`} className="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-3 py-1 text-xs font-medium">
                    <span className="font-mono">{id}</span>
                    <button
                      type="button"
                      onClick={() => handleRemovePolicyId('whitelist', id)}
                      disabled={isWhitelistPending}
                      aria-label={t('settings.policyRemoveA11y', { id, list: t('settings.whitelist') })}
                      className="focus-ring rounded-full hover:bg-green-200/70 dark:hover:bg-green-800/60"
                    >
                      <span className="material-symbols-outlined text-sm" aria-hidden="true">close</span>
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-xl p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold dark:text-white">{t('settings.blacklist')}</h4>
                <span className="text-xs text-slate-500 dark:text-slate-400">{blacklist.length}</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={blacklistInput}
                  onChange={(e) => setBlacklistInput(e.target.value)}
                  placeholder={t('settings.policyInputPlaceholder')}
                  className="flex-1 h-10 rounded-lg border border-slate-200 dark:border-white/10 px-3 bg-white dark:bg-slate-900/40 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label={t('settings.policyInputBlacklistA11y')}
                />
                <button
                  type="button"
                  onClick={() => handleAddPolicyId('blacklist')}
                  disabled={isBlacklistPending}
                  className="focus-ring h-10 px-3 rounded-lg bg-slate-900 dark:bg-slate-200 text-white dark:text-slate-900 text-sm font-semibold disabled:opacity-60"
                >
                  {t('settings.policyAddBlacklist')}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {blacklist.length === 0 && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyEmptyBlacklist')}</p>
                )}
                {blacklist.map((id) => (
                  <span key={`black-${id}`} className="inline-flex items-center gap-1 rounded-full bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 px-3 py-1 text-xs font-medium">
                    <span className="font-mono">{id}</span>
                    <button
                      type="button"
                      onClick={() => handleRemovePolicyId('blacklist', id)}
                      disabled={isBlacklistPending}
                      aria-label={t('settings.policyRemoveA11y', { id, list: t('settings.blacklist') })}
                      className="focus-ring rounded-full hover:bg-slate-300/70 dark:hover:bg-slate-700/70"
                    >
                      <span className="material-symbols-outlined text-sm" aria-hidden="true">close</span>
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-xl p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm space-y-3">
              <h4 className="text-sm font-bold dark:text-white">{t('settings.policySummary')}</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyResultsPerPage')}</p>
                  <p className="font-semibold dark:text-white">{systemConfig?.results_per_page ?? '-'}</p>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyMaxPage')}</p>
                  <p className="font-semibold dark:text-white">{systemConfig?.max_page ?? '-'}</p>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyCache')}</p>
                  <p className="font-semibold dark:text-white">
                    {systemConfig?.search_cache ? t('settings.policyEnabled') : t('settings.policyDisabled')}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">{t('settings.policyCacheExpire')}</p>
                  <p className="font-semibold dark:text-white">{systemConfig?.cache_expire_seconds ?? '-'}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{t('settings.policyOwnerIds')}</p>
                {ownerIds.length === 0 ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">{t('settings.policyNoOwner')}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {ownerIds.map((id) => (
                      <span key={`owner-${id}`} className="inline-flex rounded-full px-3 py-1 text-xs font-medium bg-primary/10 text-primary">
                        <span className="font-mono">{id}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

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
