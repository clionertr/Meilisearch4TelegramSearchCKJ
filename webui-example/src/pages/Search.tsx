import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Virtuoso } from 'react-virtuoso';
import { extractApiErrorMessage } from '@/api/error';
import { Highlight } from '@/components/common/Highlight';
import { useSearchQuery, SearchFilters } from '@/hooks/queries/useSearch';
import { DateFilter } from '@/components/search/DateFilter';
import { SenderFilter } from '@/components/search/SenderFilter';
import { Skeleton } from '@/components/common/Skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { motion, useReducedMotion } from 'framer-motion';
import {
    addSearchHistory,
    getSearchHistory,
    clearSearchHistory,
    getSuggestions,
} from '@/utils/searchHistory';
import { getTelegramLink } from '@/utils/telegramLinks';

interface SearchSuggestionsProps {
    suggestions: string[];
    onSelect: (item: string) => void;
    onClearHistory: () => void;
    hasHistory: boolean;
}

const SearchSuggestions: React.FC<SearchSuggestionsProps> = ({
    suggestions,
    onSelect,
    onClearHistory,
    hasHistory,
}) => {
    const { t } = useTranslation();

    if (suggestions.length === 0) return null;
    return (
        <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-dropdown-dark rounded-xl shadow-xl border border-slate-100 dark:border-border-dark z-50 overflow-hidden"
            role="listbox"
            aria-label={t('search.recentSearches')}
        >
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 dark:border-border-dark">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    {t('search.recentSearches')}
                </span>
                {hasHistory && (
                    <button
                        type="button"
                        onClick={onClearHistory}
                        className="focus-ring text-xs text-red-500 hover:text-red-600 font-medium"
                    >
                        {t('search.clearHistory')}
                    </button>
                )}
            </div>
            <ul>
                {suggestions.map((item) => (
                    <li key={item}>
                        <button
                            type="button"
                            onMouseDown={(e) => { e.preventDefault(); onSelect(item); }}
                            className="focus-ring w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-surface-dark transition-colors text-left"
                        >
                            <span className="material-symbols-outlined text-[16px] text-slate-400" aria-hidden="true">history</span>
                            {item}
                        </button>
                    </li>
                ))}
            </ul>
        </motion.div>
    );
};

interface SearchResultCardProps {
    result: {
        id: string;
        chat: { id: number; title?: string | null; username?: string | null };
        from_user?: { id?: number; username?: string | null } | null;
        date: string;
        text: string;
        formatted_text?: string | null;
        msg_id?: number;
    };
}

const SearchResultCard: React.FC<SearchResultCardProps> = ({ result }) => {
    const { t, i18n } = useTranslation();
    const tgLink = getTelegramLink(result.chat.id, result.msg_id ?? null, result.chat.username);

    return (
        <motion.div
            variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
            className="bg-surface-light dark:bg-surface-dark rounded-2xl p-4 shadow-sm border border-transparent dark:border-divider-dark/50"
        >
            <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/20">
                    <span className="text-white font-bold text-sm">
                        {(result.chat.title || result.chat.username || 'NA').substring(0, 2).toUpperCase()}
                    </span>
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-2">
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1 break-all">
                            {result.chat.title || result.chat.username || t('search.chatFallback', { id: result.chat.id })}
                        </h3>
                        <div className="flex items-center gap-2 shrink-0">
                            <span className="text-xs text-slate-400 whitespace-nowrap">
                                {new Date(result.date).toLocaleTimeString(i18n.language, { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {tgLink && (
                                <a
                                    href={tgLink}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    aria-label={t('a11y.openInTelegram')}
                                    title={t('a11y.openInTelegram')}
                                    className="focus-ring text-slate-400 hover:text-primary transition-colors"
                                >
                                    <span className="material-symbols-outlined text-[16px]" aria-hidden="true">open_in_new</span>
                                </a>
                            )}
                        </div>
                    </div>
                    <p className="text-xs text-primary truncate">
                        {t('search.senderPrefix')}: {result.from_user?.username || t('search.senderUser', { id: result.from_user?.id ?? t('search.senderUnknown') })}
                    </p>
                </div>
            </div>
            <div className="relative pl-4 border-l-2 border-slate-200 dark:border-divider-dark space-y-2.5">
                <div className="text-sm text-slate-800 dark:text-slate-200 bg-primary/10 dark:bg-primary/5 -ml-4 pl-4 pr-2 py-2 rounded-r-lg border-l-2 border-primary break-words whitespace-pre-wrap">
                    <Highlight html={result.formatted_text || result.text} />
                </div>
            </div>
        </motion.div>
    );
};

const Search: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { t } = useTranslation();
    const shouldReduceMotion = useReducedMotion();

    const initialQuery = searchParams.get('q') ?? '';
    const [query, setQuery] = useState(initialQuery);
    const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
    const [filters, setFilters] = useState<SearchFilters>({});
    const [debouncedFilters, setDebouncedFilters] = useState<SearchFilters>({});
    const [dateRangeType, setDateRangeType] = useState<string>('anytime');

    const [showSuggestions, setShowSuggestions] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [historyExists, setHistoryExists] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedQuery(query);
            setDebouncedFilters({ ...filters });
        }, 300);
        return () => clearTimeout(timer);
    }, [query, filters]);

    useEffect(() => {
        const suggestionList = getSuggestions(query);
        setSuggestions(suggestionList);
        setHistoryExists(getSearchHistory().length > 0);
    }, [query, showSuggestions]);

    const {
        data,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
        isLoading,
        error,
    } = useSearchQuery(debouncedQuery, 20, debouncedFilters);

    useEffect(() => {
        if (debouncedQuery.trim().length >= 2) {
            addSearchHistory(debouncedQuery.trim());
        }
    }, [debouncedQuery]);

    const isPending = query.trim() !== debouncedQuery.trim();

    const allResults = useMemo(() => {
        return data?.pages.flatMap((page) => page.data.data.hits) || [];
    }, [data]);

    const totalResults = debouncedQuery ? (data?.pages[0]?.data.data.total_hits || 0) : 0;
    const activeFilterCount = Number(Boolean(filters.senderUsername)) + Number(dateRangeType !== 'anytime');

    const handleSelectSuggestion = useCallback((item: string) => {
        setQuery(item);
        setShowSuggestions(false);
        inputRef.current?.blur();
    }, []);

    const handleClearHistory = useCallback(() => {
        clearSearchHistory();
        setSuggestions([]);
        setHistoryExists(false);
        setShowSuggestions(false);
    }, []);

    const loadMore = useCallback(() => {
        if (hasNextPage && !isFetchingNextPage) {
            fetchNextPage();
        }
    }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark overflow-hidden xl:grid xl:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="flex min-h-screen min-w-0 flex-col overflow-hidden">
                <div className="px-4 pt-6 pb-2 shrink-0 z-30 bg-background-light dark:bg-background-dark sticky top-0">
                    <div className="flex items-center justify-between mb-4">
                        <button
                            type="button"
                            onClick={() => navigate(-1)}
                            aria-label={t('a11y.back')}
                            className="focus-ring p-2 -ml-2 rounded-full hover:bg-slate-200 dark:hover:bg-surface-dark transition-colors text-slate-500 dark:text-slate-400"
                        >
                            <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
                        </button>
                        <h1 className="text-lg font-semibold flex-1 text-center pr-8 dark:text-white">{t('search.title')}</h1>
                    </div>

                    <div className="relative w-full group">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="material-symbols-outlined text-primary" aria-hidden="true">search</span>
                        </div>
                        <input
                            ref={inputRef}
                            className="block w-full pl-10 pr-10 py-3 rounded-xl border-none bg-surface-light dark:bg-surface-dark text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-primary/50 shadow-sm text-base"
                            placeholder={t('search.placeholder')}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onFocus={() => setShowSuggestions(true)}
                            onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
                            aria-label={t('a11y.searchMessages')}
                            aria-autocomplete="list"
                            aria-expanded={showSuggestions && suggestions.length > 0}
                        />
                        {query && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                                <button
                                    type="button"
                                    onClick={() => setQuery('')}
                                    aria-label={t('a11y.clearSearch')}
                                    className="focus-ring text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                >
                                    <span className="material-symbols-outlined text-[20px]" aria-hidden="true">cancel</span>
                                </button>
                            </div>
                        )}

                        {showSuggestions && suggestions.length > 0 && (
                            <SearchSuggestions
                                suggestions={suggestions}
                                onSelect={handleSelectSuggestion}
                                onClearHistory={handleClearHistory}
                                hasHistory={historyExists}
                            />
                        )}
                    </div>
                </div>

                <div className="px-4 py-2 shrink-0 flex flex-wrap gap-2 pb-4 relative z-20">
                    <DateFilter
                        rangeType={dateRangeType}
                        onChange={(rangeType, dateFrom) => {
                            setDateRangeType(rangeType);
                            setFilters((prev) => ({ ...prev, dateFrom }));
                        }}
                    />
                    <SenderFilter
                        value={filters.senderUsername}
                        onChange={(senderUsername) => setFilters((prev) => ({ ...prev, senderUsername }))}
                    />
                    {(dateRangeType !== 'anytime' || filters.senderUsername) && (
                        <button
                            type="button"
                            onClick={() => {
                                setFilters({});
                                setDateRangeType('anytime');
                            }}
                            className="focus-ring flex items-center gap-1 px-4 py-1.5 rounded-full bg-slate-100 dark:bg-code-dark border border-slate-200 dark:border-divider-dark text-sm font-medium hover:text-red-500 dark:hover:text-red-400 whitespace-nowrap shadow-sm transition-colors text-slate-500 dark:text-slate-400"
                        >
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">filter_alt_off</span>
                            {t('search.clearFilters')}
                        </button>
                    )}
                </div>

                <div className="px-4 py-2 flex items-center justify-between text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400 shrink-0">
                    {(isLoading || isPending) ? (
                        <Skeleton variant="text" width="6rem" className="h-4" />
                    ) : (
                        <span>{debouncedQuery ? t('search.matchesFound', { count: totalResults }) : t('search.enterKeywords')}</span>
                    )}
                    {debouncedQuery && <span className="text-primary">{totalResults > 0 ? t('search.sortedByRelevance') : ''}</span>}
                </div>

                <div className="flex-1 overflow-hidden" aria-live="polite">
                    {error && (
                        <div className="px-4 py-4 text-center text-red-500">
                            {extractApiErrorMessage(error, t('search.fetchError'))}
                        </div>
                    )}

                    {(isLoading || isPending) && (
                        <div className="space-y-4 px-4 pt-2" aria-busy="true">
                            {[1, 2, 3].map((i) => (
                                <Skeleton key={i} variant="card" height="9rem" />
                            ))}
                        </div>
                    )}

                    {!isLoading && !isPending && allResults.length > 0 && (
                        <Virtuoso
                            style={{ height: '100%' }}
                            data={allResults}
                            endReached={loadMore}
                            overscan={200}
                            className="no-scrollbar"
                            itemContent={(_, result) => (
                                <motion.div
                                    key={result.id}
                                    className="pb-4 px-4"
                                    initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: shouldReduceMotion ? 0 : 0.2 }}
                                >
                                    <SearchResultCard result={result as SearchResultCardProps['result']} />
                                </motion.div>
                            )}
                            components={{
                                Footer: () => (
                                    hasNextPage ? (
                                        <div className="py-4 text-center">
                                            <span className="text-primary text-sm font-medium">
                                                {isFetchingNextPage ? t('search.loadingMore') : ''}
                                            </span>
                                        </div>
                                    ) : null
                                ),
                            }}
                        />
                    )}

                    {debouncedQuery && !isLoading && !isPending && allResults.length === 0 && (
                        <div className="mt-8 px-4">
                            <EmptyState
                                icon="search_off"
                                title={t('search.noResultsTitle')}
                                description={t('search.noResultsDescription', { query: debouncedQuery })}
                            />
                        </div>
                    )}
                </div>
            </div>

            <aside className="hidden xl:block border-l border-slate-200/80 dark:border-white/5 bg-white/60 dark:bg-background-dark/40 p-5">
                <div className="sticky top-5 space-y-4">
                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-white dark:bg-card-dark/70">
                        <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-2">{t('search.rightPanelTitle')}</h2>
                        <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{t('search.rightPanelDescription')}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-white dark:bg-card-dark/70">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">{t('search.rightPanelStatsTitle')}</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex items-center justify-between">
                                <span className="text-slate-500 dark:text-slate-400">{t('search.queryLength')}</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-100">{query.trim().length}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-slate-500 dark:text-slate-400">{t('search.activeFilters')}</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-100">{activeFilterCount}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>
        </div>
    );
};

export default Search;
