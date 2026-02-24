import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStorageStats, useToggleAutoClean, useCleanupCache, useCleanupMedia } from '@/hooks/queries/useStorage';

const Storage: React.FC = () => {
    const navigate = useNavigate();
    const [autoClean, setAutoClean] = useState(false);

    const { data: stats, isLoading: loading, error: fetchError } = useStorageStats();

    const toggleAutoCleanMutation = useToggleAutoClean();
    const cleanupCacheMutation = useCleanupCache();
    const cleanupMediaMutation = useCleanupMedia();

    const formatBytes = (bytes: number | null | undefined): string => {
        if (bytes === null || bytes === undefined) return '—';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    };

    const handleAutoCleanToggle = () => {
        const newState = !autoClean;
        toggleAutoCleanMutation.mutate(newState, {
            onSuccess: () => {
                setAutoClean(newState);
            }
        });
    };

    const handleCleanupCache = () => {
        cleanupCacheMutation.mutate(undefined, {
            onSuccess: (data) => {
                const cleared = data?.targets_cleared ?? [];
                alert(`Cache cleared: ${cleared.length > 0 ? cleared.join(', ') : 'no targets'}`);
            }
        });
    };

    const handleCleanupMedia = () => {
        cleanupMediaMutation.mutate(undefined, {
            onSuccess: () => {
                alert('Media cleanup is not available in current version');
            }
        });
    };

    const isCleaning = cleanupCacheMutation.isPending || cleanupMediaMutation.isPending;
    // Combine fetch errors and mutation errors
    const error = fetchError?.message || toggleAutoCleanMutation.error?.message ||
        cleanupCacheMutation.error?.message || cleanupMediaMutation.error?.message;

    return (
        <div className="pb-32 bg-background-light dark:bg-background-dark min-h-screen text-slate-900 dark:text-white">
            <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
                    <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
                </button>
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">Storage & Cleanup</h2>
                <button className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
                    <span className="material-symbols-outlined text-2xl">info</span>
                </button>
            </div>

            {loading && (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                </div>
            )}

            {error && (
                <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm mb-3">
                    {error}
                </div>
            )}

            <div className="p-4 space-y-4">
                {/* Stats Card */}
                <div className="bg-white dark:bg-[#192d33] rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-end mb-4">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Total Usage</p>
                            <h3 className="text-3xl font-bold">{formatBytes(stats?.total_bytes ?? null)}</h3>
                        </div>
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-primary"></div>
                                <span className="text-sm font-medium">Text Index</span>
                            </div>
                            <span className="text-sm font-semibold">{formatBytes(stats?.index_bytes ?? null)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-slate-400"></div>
                                <span className="text-sm font-medium">Media</span>
                            </div>
                            <span className="text-sm font-semibold text-slate-400">
                                {stats?.media_supported ? formatBytes(stats?.media_bytes ?? null) : 'Not supported'}
                            </span>
                        </div>
                    </div>
                    {stats?.notes && stats.notes.length > 0 && (
                        <div className="mt-4 text-xs text-slate-400">
                            {stats.notes.map((note, i) => <p key={i}>• {note}</p>)}
                        </div>
                    )}
                </div>

                {/* Auto-clean */}
                <div className="bg-white dark:bg-[#192d33] rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <span className="material-symbols-outlined text-primary">auto_delete</span>
                            </div>
                            <div>
                                <p className="font-bold">Auto-clean Storage</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Manage space automatically</p>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" checked={autoClean} onChange={handleAutoCleanToggle} className="sr-only peer" />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                    </div>
                </div>

                {/* Cleanup Actions */}
                <div className="pt-2">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">Cleanup Actions</h3>
                    <div className="space-y-3">
                        <button
                            onClick={handleCleanupCache}
                            disabled={isCleaning}
                            className="w-full flex items-center justify-between p-4 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform disabled:opacity-50"
                        >
                            <div className="text-left">
                                <p className="font-bold text-sm">Clear Cache</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Removes search & config cache</p>
                            </div>
                            <div className="bg-primary/10 text-primary px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">
                                {cleanupCacheMutation.isPending ? 'Clearing...' : 'Clean Up'}
                            </div>
                        </button>
                        <button
                            onClick={handleCleanupMedia}
                            disabled={isCleaning}
                            className="w-full flex items-center justify-between p-4 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform group disabled:opacity-50"
                        >
                            <div className="text-left">
                                <p className="font-bold text-sm text-red-500">Clear Media</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Not available in current version</p>
                            </div>
                            <div className="bg-red-500/10 text-red-500 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">
                                {cleanupMediaMutation.isPending ? 'Clearing...' : 'Clear'}
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Storage;
