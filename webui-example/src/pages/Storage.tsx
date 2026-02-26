import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useStorageStats, useToggleAutoClean, useCleanupCache, useCleanupMedia } from '@/hooks/queries/useStorage';
import { formatBytes } from '@/utils/formatters';
import toast from '@/components/Toast/toast';
import { useConfirm } from '@/hooks/useConfirm';

const Storage: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const [autoClean, setAutoClean] = useState(false);
    const { confirm } = useConfirm();

    const { data: stats, isLoading: loading, error: fetchError } = useStorageStats();

    const toggleAutoCleanMutation = useToggleAutoClean();
    const cleanupCacheMutation = useCleanupCache();
    const cleanupMediaMutation = useCleanupMedia();

    const handleAutoCleanToggle = () => {
        const newState = !autoClean;
        toggleAutoCleanMutation.mutate(newState, {
            onSuccess: () => {
                setAutoClean(newState);
            },
        });
    };

    const handleCleanupCache = async () => {
        const ok = await confirm({
            title: t('storage.clearCacheConfirmTitle'),
            message: t('storage.clearCacheConfirmMessage'),
            variant: 'danger',
            confirmLabel: t('storage.clear'),
        });
        if (!ok) return;
        cleanupCacheMutation.mutate(undefined, {
            onSuccess: (data) => {
                const cleared = data?.targets_cleared ?? [];
                const targets = cleared.length > 0 ? cleared.join(', ') : t('storage.noTargets');
                toast.success(t('storage.cacheCleared', { targets }));
            },
            onError: () => {
                toast.error(t('storage.cacheClearFailed'));
            },
        });
    };

    const handleCleanupMedia = async () => {
        const ok = await confirm({
            title: t('storage.clearMediaConfirmTitle'),
            message: t('storage.clearMediaConfirmMessage'),
            variant: 'default',
            confirmLabel: t('common.confirm'),
        });
        if (!ok) return;
        cleanupMediaMutation.mutate(undefined, {
            onSuccess: () => {
                toast.info(t('storage.mediaUnavailable'));
            },
            onError: () => {
                toast.error(t('storage.mediaFailed'));
            },
        });
    };

    const isCleaning = cleanupCacheMutation.isPending || cleanupMediaMutation.isPending;
    const error = fetchError?.message || toggleAutoCleanMutation.error?.message ||
        cleanupCacheMutation.error?.message || cleanupMediaMutation.error?.message;

    return (
        <div className="pb-10 md:pb-6 bg-background-light dark:bg-background-dark min-h-screen text-slate-900 dark:text-white">
            <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <button
                    type="button"
                    onClick={() => navigate(-1)}
                    className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5"
                    aria-label={t('a11y.back')}
                >
                    <span className="material-symbols-outlined text-2xl" aria-hidden="true">arrow_back_ios_new</span>
                </button>
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">{t('storage.title')}</h2>
                <button type="button" className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5" aria-label={t('storage.info')}>
                    <span className="material-symbols-outlined text-2xl" aria-hidden="true">info</span>
                </button>
            </div>

            {loading && (
                <div className="flex items-center justify-center py-12" aria-busy="true">
                    <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                </div>
            )}

            {error && (
                <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm mb-3">
                    {error}
                </div>
            )}

            <div className="p-4 space-y-4">
                <div className="bg-white dark:bg-card-dark rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-end mb-4">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">{t('storage.totalUsage')}</p>
                            <h3 className="text-3xl font-bold">{formatBytes(stats?.total_bytes ?? null)}</h3>
                        </div>
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-primary" />
                                <span className="text-sm font-medium">{t('storage.textIndex')}</span>
                            </div>
                            <span className="text-sm font-semibold">{formatBytes(stats?.index_bytes ?? null)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-slate-400" />
                                <span className="text-sm font-medium">{t('storage.media')}</span>
                            </div>
                            <span className="text-sm font-semibold text-slate-400">
                                {stats?.media_supported ? formatBytes(stats?.media_bytes ?? null) : t('storage.notSupported')}
                            </span>
                        </div>
                    </div>
                    {stats?.notes && stats.notes.length > 0 && (
                        <div className="mt-4 text-xs text-slate-400">
                            {stats.notes.map((note, i) => <p key={i}>- {note}</p>)}
                        </div>
                    )}
                </div>

                <div className="bg-white dark:bg-card-dark rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <span className="material-symbols-outlined text-primary" aria-hidden="true">auto_delete</span>
                            </div>
                            <div>
                                <p className="font-bold">{t('storage.autoCleanTitle')}</p>
                                <p className="text-xs text-slate-500 dark:text-muted-dark">{t('storage.autoCleanDescription')}</p>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" checked={autoClean} onChange={handleAutoCleanToggle} className="sr-only peer" aria-label={t('storage.autoCleanTitle')} />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary" />
                        </label>
                    </div>
                </div>

                <div className="pt-2">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">{t('storage.cleanupActions')}</h3>
                    <div className="space-y-3">
                        <button
                            type="button"
                            onClick={handleCleanupCache}
                            disabled={isCleaning}
                            className="focus-ring w-full flex items-center justify-between p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform disabled:opacity-50"
                        >
                            <div className="text-left">
                                <p className="font-bold text-sm">{t('storage.clearCache')}</p>
                                <p className="text-xs text-slate-500 dark:text-muted-dark">{t('storage.clearCacheHint')}</p>
                            </div>
                            <div className="bg-primary/10 text-primary px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">
                                {cleanupCacheMutation.isPending ? t('storage.clearing') : t('storage.cleanUp')}
                            </div>
                        </button>
                        <button
                            type="button"
                            onClick={handleCleanupMedia}
                            disabled={isCleaning}
                            className="focus-ring w-full flex items-center justify-between p-4 bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform group disabled:opacity-50"
                        >
                            <div className="text-left">
                                <p className="font-bold text-sm text-red-500">{t('storage.clearMedia')}</p>
                                <p className="text-xs text-slate-500 dark:text-muted-dark">{t('storage.clearMediaHint')}</p>
                            </div>
                            <div className="bg-red-500/10 text-red-500 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">
                                {cleanupMediaMutation.isPending ? t('storage.clearing') : t('storage.clear')}
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Storage;
