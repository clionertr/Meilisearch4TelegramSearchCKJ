import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInfiniteQuery } from '@tanstack/react-query';
import { searchApi } from '../src/api/search';
import { extractApiErrorMessage } from '../src/api/error';
import { Highlight } from '../src/components/common/Highlight';

const Search: React.FC = () => {
    const navigate = useNavigate();
    const [query, setQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedQuery(query);
        }, 300);
        return () => clearTimeout(timer);
    }, [query]);

    const {
        data,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
        isLoading,
        error
    } = useInfiniteQuery({
        queryKey: ['search', debouncedQuery],
        queryFn: ({ pageParam = 0 }) => 
            searchApi.search({ q: debouncedQuery, offset: pageParam, limit: 20 }),
        getNextPageParam: (lastPage) => {
            const { offset, limit, total_hits } = lastPage.data.data;
            return offset + limit < total_hits ? offset + limit : undefined;
        },
        enabled: debouncedQuery.length > 0,
        initialPageParam: 0,
    });

    const allResults = useMemo(() => {
        return data?.pages.flatMap(page => page.data.data.hits) || [];
    }, [data]);

    const totalResults = data?.pages[0]?.data.data.total_hits || 0;

    return (
        <div className="flex flex-col h-screen relative bg-background-light dark:bg-background-dark overflow-hidden">
            {/* Header & Search Bar */}
            <div className="px-4 pt-6 pb-2 shrink-0 z-10 bg-background-light dark:bg-background-dark sticky top-0">
                <div className="flex items-center justify-between mb-4">
                    <button onClick={() => navigate(-1)} className="p-2 -ml-2 rounded-full hover:bg-slate-200 dark:hover:bg-surface-dark transition-colors text-slate-500 dark:text-slate-400">
                        <span className="material-symbols-outlined">arrow_back</span>
                    </button>
                    <h1 className="text-lg font-semibold flex-1 text-center pr-8 dark:text-white">Search</h1>
                </div>
                
                <div className="relative w-full group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="material-symbols-outlined text-primary">search</span>
                    </div>
                    <input 
                        className="block w-full pl-10 pr-10 py-3 rounded-xl border-none bg-surface-light dark:bg-surface-dark text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-primary/50 shadow-sm text-base" 
                        placeholder="Search messages..." 
                        type="text" 
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    {query && (
                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                            <button 
                                onClick={() => setQuery('')}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                <span className="material-symbols-outlined text-[20px]">cancel</span>
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Filter Chips */}
            <div className="px-4 py-2 shrink-0 overflow-x-auto no-scrollbar flex gap-2 pb-4">
                <button className="flex items-center gap-1 px-4 py-1.5 rounded-full bg-surface-light dark:bg-surface-dark border border-slate-200 dark:border-[#233f48] text-sm font-medium whitespace-nowrap shadow-sm active:scale-95 transition-transform">
                    <span className="text-slate-500 dark:text-slate-400">Date:</span>
                    <span className="text-primary">Anytime</span>
                    <span className="material-symbols-outlined text-[18px] text-slate-400">expand_more</span>
                </button>
                <button className="flex items-center gap-1 px-4 py-1.5 rounded-full bg-surface-light dark:bg-surface-dark border border-slate-200 dark:border-[#233f48] text-sm font-medium whitespace-nowrap shadow-sm active:scale-95 transition-transform">
                    <span className="text-slate-500 dark:text-slate-400">Sender:</span>
                    <span className="text-slate-900 dark:text-white">All</span>
                    <span className="material-symbols-outlined text-[18px] text-slate-400">expand_more</span>
                </button>
            </div>

            {/* Results Info */}
            <div className="px-4 py-2 flex items-center justify-between text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {isLoading ? (
                    <span>Searching...</span>
                ) : (
                    <span>{debouncedQuery ? `${totalResults} matches found` : 'Enter keywords to search'}</span>
                )}
                {debouncedQuery && <button className="text-primary hover:underline">Sort by Relevance</button>}
            </div>

            {/* Results List */}
            <div className="flex-1 overflow-y-auto px-4 pb-24 space-y-4 no-scrollbar">
                {error && (
                    <div className="p-4 text-center text-red-500">
                        Error: {extractApiErrorMessage(error, 'Failed to fetch results')}
                    </div>
                )}

                {allResults.map((result) => (
                    <div key={result.id} className="bg-surface-light dark:bg-surface-dark rounded-2xl p-4 shadow-sm border border-transparent dark:border-[#233f48]/50">
                        <div className="flex items-start gap-3 mb-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/20">
                                <span className="text-white font-bold text-sm">
                                    {(result.chat.title || result.chat.username || 'NA').substring(0, 2).toUpperCase()}
                                </span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-start">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                        {result.chat.title || result.chat.username || `Chat ${result.chat.id}`}
                                    </h3>
                                    <span className="text-xs text-slate-400 whitespace-nowrap">
                                        {new Date(result.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <p className="text-xs text-primary truncate">
                                    Sender: {result.from_user?.username || `User ${result.from_user?.id ?? 'Unknown'}`}
                                </p>
                            </div>
                        </div>
                        <div className="relative pl-4 border-l-2 border-slate-200 dark:border-[#233f48] space-y-2.5">
                            <div className="text-sm text-slate-800 dark:text-slate-200 bg-primary/10 dark:bg-primary/5 -ml-4 pl-4 pr-2 py-2 rounded-r-lg border-l-2 border-primary">
                                <Highlight html={result.formatted_text || result.text} />
                            </div>
                        </div>
                    </div>
                ))}
                
                {hasNextPage && (
                    <button 
                        onClick={() => fetchNextPage()}
                        disabled={isFetchingNextPage}
                        className="w-full py-4 text-primary text-sm font-medium"
                    >
                        {isFetchingNextPage ? 'Loading more...' : 'Load more'}
                    </button>
                )}

                {debouncedQuery && !isLoading && allResults.length === 0 && (
                    <div className="text-center py-10 text-slate-500">
                        No results found for "{debouncedQuery}"
                    </div>
                )}
            </div>
            
            <div className="absolute bottom-24 right-6 z-20">
                <button className="bg-primary hover:bg-sky-500 text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg shadow-primary/40 transition-colors">
                    <span className="material-symbols-outlined text-[28px]">search_check</span>
                </button>
            </div>
        </div>
    );
};

export default Search;
