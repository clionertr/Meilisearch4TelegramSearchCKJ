import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAvailableDialogs, useSyncDialogs } from '@/hooks/queries/useDialogs';

// ── 日期范围预设 ──────────────────────────────────────────────────────────
type DateRangeOption = '1m' | '3m' | '6m' | '1y' | '2y' | 'all';

interface DateRangePreset {
    key: DateRangeOption;
    labelKey: string;
    months: number | null; // null = all time
}

const DATE_RANGE_PRESETS: DateRangePreset[] = [
    { key: '1m', labelKey: 'selectChats.range1m', months: 1 },
    { key: '3m', labelKey: 'selectChats.range3m', months: 3 },
    { key: '6m', labelKey: 'selectChats.range6m', months: 6 },
    { key: '1y', labelKey: 'selectChats.range1y', months: 12 },
    { key: '2y', labelKey: 'selectChats.range2y', months: 24 },
    { key: 'all', labelKey: 'selectChats.rangeAll', months: null },
];

const SelectChats: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [searchQuery, setSearchQuery] = useState('');
    const [dateRange, setDateRange] = useState<DateRangeOption>('6m');

    const { data: dialogs = [], isLoading: loading, error: fetchError } = useAvailableDialogs(200);
    const syncMutation = useSyncDialogs();

    useEffect(() => {
        if (dialogs.length > 0 && selected.size === 0) {
            const activeDialogs = dialogs.filter((d) => d.sync_state === 'active').map((d) => d.id);
            if (activeDialogs.length > 0) {
                setSelected(new Set(activeDialogs));
            }
        }
    }, [dialogs, selected.size]);

    // ── 搜索过滤（支持 title + id 搜索）──────────────────────────────────
    const filteredDialogs = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        if (!q) return dialogs;
        return dialogs.filter(
            (d) =>
                d.title.toLowerCase().includes(q) ||
                String(d.id).includes(q)
        );
    }, [dialogs, searchQuery]);

    // ── 切换选中 ──────────────────────────────────────────────────────────
    const toggleSelect = (id: number) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    // 全选/取消全选（基于过滤后的列表）
    const selectAll = () => {
        const filteredIds = filteredDialogs.map((d) => d.id);
        const allSelected = filteredIds.every((id) => selected.has(id));
        setSelected((prev) => {
            const next = new Set(prev);
            if (allSelected) {
                filteredIds.forEach((id) => next.delete(id));
            } else {
                filteredIds.forEach((id) => next.add(id));
            }
            return next;
        });
    };

    const allFilteredSelected =
        filteredDialogs.length > 0 && filteredDialogs.every((d) => selected.has(d.id));

    // ── 提交同步 ──────────────────────────────────────────────────────────
    const handleSync = () => {
        if (selected.size === 0) return;

        // 计算 dateFrom（基于 dateRange）
        const preset = DATE_RANGE_PRESETS.find((p) => p.key === dateRange);
        let dateFrom: string | undefined;
        if (preset && preset.months !== null) {
            const d = new Date();
            d.setMonth(d.getMonth() - preset.months);
            dateFrom = d.toISOString();
        }

        // 目前后端 SyncRequest 仅接受 dialog_ids + default_sync_state
        // dateFrom 作为前端范围提示，未来可扩展到后端
        void dateFrom; // suppress unused warning until backend supports date_from

        syncMutation.mutate(Array.from(selected), {
            onSuccess: () => {
                navigate('/synced-chats');
            },
        });
    };

    const error = fetchError?.message || syncMutation.error?.message;
    const syncing = syncMutation.isPending;

    // ── 图标与颜色 ────────────────────────────────────────────────────────
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
                    text: t('selectChats.syncedActive'),
                    className: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
                };
            case 'paused':
                return {
                    text: t('selectChats.syncedPaused'),
                    className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
                };
            default:
                return {
                    text: t('selectChats.notSynced'),
                    className: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
                };
        }
    };

    const selectedPreset = DATE_RANGE_PRESETS.find((p) => p.key === dateRange)!;

    return (
        <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col text-slate-900 dark:text-white">
            {/* ── Header ── */}
            <header className="flex items-center justify-between px-4 py-3 sticky top-0 z-30 bg-background-light dark:bg-background-dark">
                <button
                    type="button"
                    onClick={() => navigate(-1)}
                    aria-label={t('a11y.back')}
                    className="focus-ring flex items-center justify-center p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                >
                    <span className="material-symbols-outlined text-2xl" aria-hidden="true">arrow_back</span>
                </button>
                <div className="flex-1 flex justify-end px-2">
                    <button
                        type="button"
                        onClick={selectAll}
                        className="focus-ring text-sm font-semibold text-primary hover:opacity-80 transition-opacity"
                    >
                        {allFilteredSelected ? t('selectChats.deselectAll') : t('selectChats.selectAll')}
                    </button>
                </div>
            </header>

            <main className="flex-1 flex flex-col overflow-y-auto no-scrollbar pb-4">
                {/* ── Title & Description ── */}
                <div className="px-6 pt-2 pb-4">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">{t('selectChats.title')}</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-[15px] leading-relaxed">
                        {t('selectChats.description')}
                    </p>
                </div>

                {/* ── Date Range Selector ── */}
                <div className="px-6 pb-4">
                    <div className="bg-white dark:bg-surface-alt-dark rounded-2xl border border-slate-100 dark:border-slate-800/50 shadow-sm p-4">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="material-symbols-outlined text-lg text-primary" aria-hidden="true">calendar_month</span>
                            <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                                {t('selectChats.downloadRange')}
                            </span>
                            <span className="ml-auto text-xs text-primary font-medium">
                                {t(selectedPreset.labelKey)}
                            </span>
                        </div>
                        <div className="flex flex-wrap gap-2" role="group" aria-label={t('selectChats.downloadRange')}>
                            {DATE_RANGE_PRESETS.map((preset) => (
                                <button
                                    key={preset.key}
                                    type="button"
                                    onClick={() => setDateRange(preset.key)}
                                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all focus-ring ${dateRange === preset.key
                                            ? 'bg-primary text-white shadow-md shadow-primary/30'
                                            : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                                        }`}
                                    aria-pressed={dateRange === preset.key}
                                >
                                    {t(preset.labelKey)}
                                </button>
                            ))}
                        </div>
                        <p className="text-xs text-slate-400 dark:text-slate-500 mt-2.5">
                            {t('selectChats.downloadRangeHint')}
                        </p>
                    </div>
                </div>

                {/* ── Search Box ── */}
                <div className="px-6 pb-4">
                    <div className="relative">
                        <span
                            className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl pointer-events-none"
                            aria-hidden="true"
                        >
                            search
                        </span>
                        <input
                            id="select-chats-search"
                            type="search"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder={t('selectChats.searchPlaceholder')}
                            aria-label={t('selectChats.searchPlaceholder')}
                            className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-surface-alt-dark text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/50 transition"
                        />
                        {searchQuery && (
                            <button
                                type="button"
                                onClick={() => setSearchQuery('')}
                                aria-label={t('a11y.clearSearch')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                            >
                                <span className="material-symbols-outlined text-xl" aria-hidden="true">close</span>
                            </button>
                        )}
                    </div>
                    {/* 搜索结果摘要 */}
                    {searchQuery && (
                        <p className="text-xs text-slate-400 mt-1.5 px-1">
                            {t('selectChats.searchResult', { count: filteredDialogs.length, total: dialogs.length })}
                        </p>
                    )}
                </div>

                {/* ── Loading ── */}
                {loading && (
                    <div className="flex items-center justify-center py-12" aria-busy="true">
                        <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                    </div>
                )}

                {/* ── Error ── */}
                {error && (
                    <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm mb-3">
                        {error}
                    </div>
                )}

                {/* ── Dialog List ── */}
                <div className="px-4 space-y-2" aria-live="polite">
                    {filteredDialogs.length === 0 && !loading && (
                        <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                            <span className="material-symbols-outlined text-4xl mb-2" aria-hidden="true">search_off</span>
                            <p className="text-sm">{t('selectChats.noResults')}</p>
                        </div>
                    )}

                    {filteredDialogs.map((dialog) => {
                        const syncStateMeta = getSyncStateLabel(dialog.sync_state);
                        const isChecked = selected.has(dialog.id);

                        return (
                            <div
                                key={dialog.id}
                                className={`flex items-center justify-between p-4 rounded-2xl border shadow-sm transition-all cursor-pointer ${isChecked
                                        ? 'bg-primary/5 dark:bg-primary/10 border-primary/30 dark:border-primary/40'
                                        : 'bg-white dark:bg-surface-alt-dark border-slate-100 dark:border-slate-800/50'
                                    }`}
                                onClick={() => toggleSelect(dialog.id)}
                                role="checkbox"
                                aria-checked={isChecked}
                                tabIndex={0}
                                onKeyDown={(e) => {
                                    if (e.key === ' ' || e.key === 'Enter') {
                                        e.preventDefault();
                                        toggleSelect(dialog.id);
                                    }
                                }}
                            >
                                {/* Left: Icon + Info */}
                                <div className="flex items-center gap-3 overflow-hidden flex-1 min-w-0">
                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${getIconColor(dialog.type)}`}>
                                        <span className="material-symbols-outlined text-2xl" aria-hidden="true">{getIcon(dialog.type)}</span>
                                    </div>
                                    <div className="flex flex-col truncate min-w-0">
                                        <span className="font-semibold text-base truncate">{dialog.title}</span>
                                        {/* Session ID + type + message count */}
                                        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
                                            {/* Session ID - prominently shown, searchable */}
                                            <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px] text-slate-500 dark:text-slate-400 select-all">
                                                {dialog.id}
                                            </span>
                                            <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600 shrink-0" />
                                            <span className="capitalize">{dialog.type}</span>
                                            {dialog.message_count !== null && (
                                                <>
                                                    <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600 shrink-0" />
                                                    <span>{t('selectChats.messagesCount', { count: dialog.message_count.toLocaleString() })}</span>
                                                </>
                                            )}
                                        </div>
                                        <div className="mt-1">
                                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${syncStateMeta.className}`}>
                                                {syncStateMeta.text}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Right: Toggle */}
                                <label
                                    className="relative inline-flex items-center cursor-pointer shrink-0 ml-4"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <input
                                        type="checkbox"
                                        checked={isChecked}
                                        onChange={() => toggleSelect(dialog.id)}
                                        aria-label={t('selectChats.toggleSelection', { title: dialog.title })}
                                        className="sr-only peer"
                                    />
                                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary" />
                                </label>
                            </div>
                        );
                    })}
                </div>

                <p className="text-xs text-slate-400 text-center mt-6 px-4">
                    {t('selectChats.modifyLater')}
                </p>
            </main>

            {/* ── Footer ── */}
            <footer className="sticky bottom-0 p-4 md:p-6 bg-gradient-to-t from-background-light dark:from-background-dark via-background-light/95 dark:via-background-dark/95 to-transparent z-40">
                {/* Selected count + date range summary */}
                {selected.size > 0 && (
                    <div className="flex items-center justify-center gap-2 mb-2 text-xs text-slate-500 dark:text-slate-400">
                        <span className="material-symbols-outlined text-base text-primary" aria-hidden="true">calendar_month</span>
                        <span>
                            {t('selectChats.syncSummary', {
                                count: selected.size,
                                range: t(selectedPreset.labelKey),
                            })}
                        </span>
                    </div>
                )}
                <button
                    type="button"
                    onClick={handleSync}
                    disabled={selected.size === 0 || syncing}
                    className="focus-ring w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-bold py-4 px-6 rounded-2xl shadow-xl shadow-primary/30 active:scale-[0.98] transition-all flex items-center justify-center gap-3"
                >
                    <span>{syncing ? t('selectChats.syncing') : t('selectChats.startSyncing', { count: selected.size })}</span>
                    <span className="material-symbols-outlined text-[22px]" aria-hidden="true">sync</span>
                </button>
            </footer>
        </div>
    );
};

export default SelectChats;
