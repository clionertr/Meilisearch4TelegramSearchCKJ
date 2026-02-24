import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAvailableDialogs, useSyncDialogs } from '@/hooks/queries/useDialogs';

const SelectChats: React.FC = () => {
    const navigate = useNavigate();
    const [selected, setSelected] = useState<Set<number>>(new Set());

    const { data: dialogs = [], isLoading: loading, error: fetchError } = useAvailableDialogs(200);
    const syncMutation = useSyncDialogs();

    // Pre-select currently active sync sessions once the dialogs are loaded
    useEffect(() => {
        if (dialogs.length > 0 && selected.size === 0) {
            const activeDialogs = dialogs.filter((d) => d.sync_state === 'active').map((d) => d.id);
            if (activeDialogs.length > 0) {
                setSelected(new Set(activeDialogs));
            }
        }
    }, [dialogs, selected.size]);

    const toggleSelect = (id: number) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const selectAll = () => {
        if (selected.size === dialogs.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(dialogs.map(d => d.id)));
        }
    };

    const handleSync = () => {
        if (selected.size === 0) return;
        syncMutation.mutate(Array.from(selected), {
            onSuccess: () => {
                navigate('/synced-chats');
            }
        });
    };

    const error = fetchError?.message || syncMutation.error?.message;
    const syncing = syncMutation.isPending;

    const getIcon = (type: string) => {
        switch (type) {
            case 'channel': return 'campaign';
            case 'private': return 'person';
            default: return 'group';
        }
    };

    const getIconColor = (type: string) => {
        switch (type) {
            case 'channel': return 'text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30';
            case 'private': return 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30';
            default: return 'text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/30';
        }
    };

    const getSyncStateLabel = (syncState: string) => {
        switch (syncState) {
            case 'active':
                return {
                    text: 'Synced - Active',
                    className: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
                };
            case 'paused':
                return {
                    text: 'Synced - Paused',
                    className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
                };
            default:
                return {
                    text: 'Not Synced',
                    className: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
                };
        }
    };

    return (
        <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col text-slate-900 dark:text-white">
            <header className="flex items-center justify-between px-4 py-3 sticky top-0 z-30 bg-background-light dark:bg-background-dark">
                <button onClick={() => navigate(-1)} className="flex items-center justify-center p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                    <span className="material-symbols-outlined text-2xl">arrow_back</span>
                </button>
                <div className="flex-1 flex justify-end px-2">
                    <button onClick={selectAll} className="text-sm font-semibold text-primary hover:opacity-80 transition-opacity">
                        {selected.size === dialogs.length ? 'Deselect All' : 'Select All'}
                    </button>
                </div>
            </header>

            <main className="flex-1 flex flex-col overflow-y-auto no-scrollbar pb-32">
                <div className="px-6 pt-2 pb-6">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Select Chats to Index</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-[15px] leading-relaxed">
                        Selected chats will be downloaded and indexed locally on your device for fast, private searching and AI summaries.
                    </p>
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

                <div className="px-4 space-y-2">
                    {dialogs.map(dialog => {
                        const syncStateMeta = getSyncStateLabel(dialog.sync_state);
                        return (
                            <div key={dialog.id} className="flex items-center justify-between p-4 rounded-2xl bg-white dark:bg-[#15262d] border border-slate-100 dark:border-slate-800/50 shadow-sm">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${getIconColor(dialog.type)}`}>
                                        <span className="material-symbols-outlined text-2xl">{getIcon(dialog.type)}</span>
                                    </div>
                                    <div className="flex flex-col truncate">
                                        <span className="font-semibold text-base truncate">{dialog.title}</span>
                                        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                                            {dialog.message_count !== null && <span>{dialog.message_count.toLocaleString()} messages</span>}
                                            <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></span>
                                            <span className="capitalize">{dialog.type}</span>
                                        </div>
                                        <div className="mt-1">
                                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${syncStateMeta.className}`}>
                                                {syncStateMeta.text}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer shrink-0 ml-4">
                                    <input
                                        type="checkbox"
                                        checked={selected.has(dialog.id)}
                                        onChange={() => toggleSelect(dialog.id)}
                                        className="sr-only peer"
                                    />
                                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                                </label>
                            </div>
                        );
                    })}
                </div>

                <p className="text-xs text-slate-400 text-center mt-6">
                    You can modify these selections later in settings.
                </p>
            </main>

            <footer className="fixed bottom-0 left-0 right-0 p-6 pb-8 bg-gradient-to-t from-background-light dark:from-background-dark via-background-light/95 dark:via-background-dark/95 to-transparent z-40">
                <button
                    onClick={handleSync}
                    disabled={selected.size === 0 || syncing}
                    className="w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-bold py-4 px-6 rounded-2xl shadow-xl shadow-primary/30 active:scale-[0.98] transition-all flex items-center justify-center gap-3"
                >
                    <span>{syncing ? 'Syncing...' : `Start Syncing (${selected.size})`}</span>
                    <span className="material-symbols-outlined text-[22px]">sync</span>
                </button>
            </footer>
        </div>
    );
};

export default SelectChats;
