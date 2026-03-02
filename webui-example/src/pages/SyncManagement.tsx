import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion, useReducedMotion } from 'framer-motion';
import { SyncedDialogItem } from '@/api/dialogs';
import { useSyncedDialogs, useToggleDialogSyncState } from '@/hooks/queries/useDialogs';
import {
    useAddToBlacklist,
    useAddToWhitelist,
    useRemoveFromBlacklist,
    useRemoveFromWhitelist,
    useSystemConfig,
} from '@/hooks/queries/useConfig';
import { Skeleton } from '@/components/common/Skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import toast from '@/components/Toast/toast';

// ── Tabs ─────────────────────────────────────────────────────────────────
type SyncTab = 'synced' | 'policy';

// ── Policy ID parser (reused from old Settings) ──────────────────────────
const parsePolicyId = (value: string): number | null => {
    const trimmed = value.trim();
    if (!/^-?\d+$/.test(trimmed)) return null;
    const parsed = Number(trimmed);
    return Number.isSafeInteger(parsed) ? parsed : null;
};

// ── Avatar gradient palette ──────────────────────────────────────────────
const gradients = [
    'from-blue-500 to-cyan-400',
    'from-orange-500 to-yellow-400',
    'from-purple-500 to-pink-400',
    'from-emerald-500 to-teal-400',
    'from-red-500 to-rose-400',
];

// ─────────────────────────────────────────────────────────────────────────
// Synced Chats Sub-panel
// ─────────────────────────────────────────────────────────────────────────
const SyncedPanel: React.FC = () => {
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

    if (loading) {
        return (
            <div className="space-y-3 mt-2" aria-busy="true">
                {[1, 2, 3, 4].map((i) => (
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
        );
    }

    if (error) {
        return <ErrorAlert message={error} />;
    }

    if (dialogs.length === 0) {
        return (
            <div className="mt-4">
                <EmptyState
                    icon="cloud_sync"
                    title={t('syncedChats.noChatsTitle')}
                    description={t('syncedChats.noChatsDescription')}
                    actionLabel={t('syncedChats.startSyncing')}
                    onAction={() => navigate('/select-chats')}
                />
            </div>
        );
    }

    return (
        <>
            <div className="bg-primary/10 border border-primary/20 rounded-2xl p-4 flex items-center justify-between mb-4">
                <div>
                    <p className="text-xs font-semibold text-primary uppercase tracking-wider">{t('syncedChats.syncStatus')}</p>
                    <p className="text-lg font-bold dark:text-white">{t('syncedChats.activeChats', { count: activeCount })}</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-primary/20 rounded-full">
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    <span className="text-xs font-bold text-primary">{t('syncedChats.live')}</span>
                </div>
            </div>

            <motion.div
                initial={shouldReduceMotion ? false : 'hidden'}
                animate="show"
                variants={{
                    hidden: { opacity: 0 },
                    show: { opacity: 1, transition: { staggerChildren: shouldReduceMotion ? 0 : 0.05 } },
                }}
                className="space-y-3"
                aria-live="polite"
            >
                {dialogs.map((dialog, idx) => {
                    const isActive = dialog.sync_state === 'active';
                    return (
                        <motion.div
                            key={dialog.id}
                            variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
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

            <button
                type="button"
                onClick={() => navigate('/select-chats')}
                aria-label={t('syncedChats.add')}
                className="focus-ring fixed bottom-24 right-6 md:bottom-8 w-14 h-14 rounded-full bg-primary text-background-dark shadow-2xl flex items-center justify-center active:scale-90 transition-transform z-40"
            >
                <span className="material-symbols-outlined text-3xl font-bold" aria-hidden="true">add</span>
            </button>
        </>
    );
};

// ─────────────────────────────────────────────────────────────────────────
// Policy Sub-panel (migrated from Settings)
// ─────────────────────────────────────────────────────────────────────────
const PolicyPanel: React.FC = () => {
    const { t } = useTranslation();

    const [whitelistInput, setWhitelistInput] = useState('');
    const [blacklistInput, setBlacklistInput] = useState('');

    const { data: systemConfig, isLoading: configLoading, error: configError } = useSystemConfig();
    const addToWhitelistMutation = useAddToWhitelist();
    const removeFromWhitelistMutation = useRemoveFromWhitelist();
    const addToBlacklistMutation = useAddToBlacklist();
    const removeFromBlacklistMutation = useRemoveFromBlacklist();

    const policyError =
        configError?.message ||
        addToWhitelistMutation.error?.message ||
        removeFromWhitelistMutation.error?.message ||
        addToBlacklistMutation.error?.message ||
        removeFromBlacklistMutation.error?.message;

    const isWhitelistPending = addToWhitelistMutation.isPending || removeFromWhitelistMutation.isPending;
    const isBlacklistPending = addToBlacklistMutation.isPending || removeFromBlacklistMutation.isPending;

    const whitelist = systemConfig?.white_list ?? [];
    const blacklist = systemConfig?.black_list ?? [];
    const ownerIds = systemConfig?.owner_ids ?? [];

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
        } else {
            addToBlacklistMutation.mutate([parsedId], {
                onSuccess: () => {
                    setBlacklistInput('');
                    toast.success(t('settings.policyAdded', { id: parsedId, list: t('settings.blacklist') }));
                },
            });
        }
    };

    const handleRemovePolicyId = (kind: 'whitelist' | 'blacklist', id: number) => {
        if (kind === 'whitelist') {
            removeFromWhitelistMutation.mutate([id], {
                onSuccess: () => {
                    toast.success(t('settings.policyRemoved', { id, list: t('settings.whitelist') }));
                },
            });
        } else {
            removeFromBlacklistMutation.mutate([id], {
                onSuccess: () => {
                    toast.success(t('settings.policyRemoved', { id, list: t('settings.blacklist') }));
                },
            });
        }
    };

    if (configLoading) {
        return <Skeleton variant="card" height="13rem" />;
    }

    return (
        <div className="space-y-3 mt-2">
            {policyError && (
                <ErrorAlert message={policyError} />
            )}

            {/* Whitelist */}
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
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleAddPolicyId('whitelist');
                        }}
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

            {/* Blacklist */}
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
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleAddPolicyId('blacklist');
                        }}
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

            {/* Policy summary */}
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
    );
};

// ─────────────────────────────────────────────────────────────────────────
// Main SyncManagement Page
// ─────────────────────────────────────────────────────────────────────────
const SyncManagement: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<SyncTab>('synced');

    const tabs: { key: SyncTab; labelKey: string; icon: string }[] = [
        { key: 'synced', labelKey: 'syncManagement.tabSynced', icon: 'cloud_done' },
        { key: 'policy', labelKey: 'syncManagement.tabPolicy', icon: 'policy' },
    ];

    return (
        <div className="pb-24 md:pb-8 min-h-screen">
            {/* Header */}
            <div className="flex items-center justify-between p-4 pb-2 sticky top-0 z-30 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <div className="w-10" /> {/* spacer for balanced layout with nav */}
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">
                    {t('syncManagement.title')}
                </h2>
                {/* Add chats shortcut in header */}
                <button
                    type="button"
                    onClick={() => navigate('/select-chats')}
                    aria-label={t('syncManagement.addChats')}
                    className="focus-ring w-10 h-10 flex items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                >
                    <span className="material-symbols-outlined text-primary text-2xl" aria-hidden="true">add_circle</span>
                </button>
            </div>

            {/* Tab bar — only real sub-panels */}
            <div className="px-4 pt-2 pb-4">
                <div className="p-1 rounded-xl bg-slate-100 dark:bg-card-dark border border-slate-200 dark:border-white/5 flex gap-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.key}
                            type="button"
                            onClick={() => setActiveTab(tab.key)}
                            className={`focus-ring flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-semibold transition-all ${activeTab === tab.key
                                    ? 'bg-white dark:bg-white/10 text-primary shadow-sm dark:text-white'
                                    : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
                                }`}
                        >
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{tab.icon}</span>
                            {t(tab.labelKey)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab content */}
            <div className="px-4">
                {activeTab === 'synced' && <SyncedPanel />}
                {activeTab === 'policy' && <PolicyPanel />}
            </div>
        </div>
    );
};

export default SyncManagement;
