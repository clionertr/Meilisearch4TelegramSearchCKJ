import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { SyncedDialogItem } from '@/api/dialogs';
import { useSyncedDialogs, useToggleDialogSyncState } from '@/hooks/queries/useDialogs';
import { Skeleton } from '@/components/common/Skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { motion, useReducedMotion } from 'framer-motion';

const SyncedChats: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const shouldReduceMotion = useReducedMotion();

    const { data: dialogs = [], isLoading: loading, error: fetchError } = useSyncedDialogs();
    const toggleSyncStateMutation = useToggleDialogSyncState();

    const handleToggleState = (dialog: SyncedDialogItem) => {
        const newState = dialog.sync_state === 'active' ? 'paused' : 'active';
        toggleSyncStateMutation.mutate({ dialogId: dialog.id, newState });
    };

    const error = fetchError?.message || toggleSyncStateMutation.error?.message;
    const activeCount = dialogs.filter((d: SyncedDialogItem) => d.sync_state === 'active').length;

    const gradients = [
        'from-blue-500 to-cyan-400',
        'from-orange-500 to-yellow-400',
        'from-purple-500 to-pink-400',
        'from-emerald-500 to-teal-400',
        'from-red-500 to-rose-400',
    ];

    return (
        <div className="pb-24 md:pb-8 bg-background-light dark:bg-background-dark min-h-screen">
            <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-30 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <button
                    type="button"
                    onClick={() => navigate(-1)}
                    className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                    aria-label={t('a11y.back')}
                >
                    <span className="material-symbols-outlined text-2xl dark:text-white" aria-hidden="true">arrow_back_ios_new</span>
                </button>
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">{t('syncedChats.title')}</h2>
                <button type="button" className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors" aria-label={t('search.title')}>
                    <span className="material-symbols-outlined text-2xl dark:text-white" aria-hidden="true">search</span>
                </button>
            </div>

            <div className="px-4 py-2 mb-2">
                <div className="bg-primary/10 border border-primary/20 rounded-2xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider">{t('syncedChats.syncStatus')}</p>
                        <p className="text-lg font-bold dark:text-white">{t('syncedChats.activeChats', { count: activeCount })}</p>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-primary/20 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                        <span className="text-xs font-bold text-primary">{t('syncedChats.live')}</span>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="px-4 space-y-3 mt-4" aria-busy="true">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="flex items-center gap-4 p-4 rounded-2xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm">
                            <Skeleton variant="avatar" className="w-12 h-12" />
                            <div className="flex-1 space-y-2 py-1">
                                <Skeleton variant="text" width="60%" />
                                <Skeleton variant="text" width="40%" />
                            </div>
                            <Skeleton variant="button" className="w-16 h-8 rounded-lg" />
                        </div>
                    ))}
                </div>
            ) : error ? (
                <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm mb-3">
                    {error}
                </div>
            ) : dialogs.length === 0 ? (
                <div className="px-4 mt-8">
                    <EmptyState
                        icon="cloud_sync"
                        title={t('syncedChats.noChatsTitle')}
                        description={t('syncedChats.noChatsDescription')}
                        actionLabel={t('syncedChats.startSyncing')}
                        onAction={() => navigate('/select-chats')}
                    />
                </div>
            ) : (
                <motion.div
                    initial={shouldReduceMotion ? false : 'hidden'}
                    animate="show"
                    variants={{
                        hidden: { opacity: 0 },
                        show: { opacity: 1, transition: { staggerChildren: shouldReduceMotion ? 0 : 0.05 } },
                    }}
                    className="px-4 space-y-3"
                    aria-live="polite"
                >
                    {dialogs.map((dialog, idx) => {
                        const isActive = dialog.sync_state === 'active';
                        return (
                            <motion.div
                                key={dialog.id}
                                variants={{
                                    hidden: { opacity: 0, y: 10 },
                                    show: { opacity: 1, y: 0 },
                                }}
                                className={`flex items-center gap-4 p-4 rounded-2xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm ${!isActive ? 'opacity-80' : ''}`}
                            >
                                <div className="relative">
                                    <div className={`w-12 h-12 rounded-full bg-gradient-to-tr ${gradients[idx % gradients.length]} flex items-center justify-center text-white font-bold text-lg ${!isActive ? 'grayscale' : ''}`}>
                                        {dialog.title.charAt(0).toUpperCase()}
                                    </div>
                                    <div
                                        className={`absolute -bottom-0.5 -right-0.5 w-4 h-4 ${isActive ? 'bg-green-500' : 'bg-slate-400'} border-2 border-white dark:border-card-dark rounded-full`}
                                        aria-label={t('a11y.statusIndicator', {
                                            label: dialog.title,
                                            status: isActive ? t('syncedChats.realtime') : t('syncedChats.paused'),
                                        })}
                                    />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className={`font-bold text-sm truncate ${isActive ? 'dark:text-white' : 'text-slate-600 dark:text-slate-300'}`}>{dialog.title}</h3>
                                    <div className="flex items-center gap-1.5 mt-0.5">
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-tight ${isActive ? 'bg-green-500/10 text-green-500' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'}`}>
                                            {isActive ? t('syncedChats.realtime') : t('syncedChats.paused')}
                                        </span>
                                        <span className="text-[10px] text-slate-400">{dialog.type}</span>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => handleToggleState(dialog)}
                                    className={`focus-ring px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${isActive
                                        ? 'bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 dark:text-white'
                                        : 'bg-slate-100 dark:bg-white/5 text-primary hover:bg-slate-200 dark:hover:bg-white/10'
                                        }`}
                                >
                                    {isActive ? t('syncedChats.pause') : t('syncedChats.resume')}
                                </button>
                            </motion.div>
                        );
                    })}
                </motion.div>
            )}

            <button
                type="button"
                onClick={() => navigate('/select-chats')}
                aria-label={t('syncedChats.add')}
                className="focus-ring fixed bottom-24 right-6 md:bottom-8 w-14 h-14 rounded-full bg-primary text-background-dark shadow-2xl flex items-center justify-center active:scale-90 transition-transform z-40"
            >
                <span className="material-symbols-outlined text-3xl font-bold" aria-hidden="true">add</span>
            </button>
        </div>
    );
};

export default SyncedChats;
