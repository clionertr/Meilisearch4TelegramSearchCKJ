const HISTORY_KEY = 'search_history';
const MAX_HISTORY = 20;

/**
 * Add a query to search history (FIFO, deduplicated, max 20).
 */
export function addSearchHistory(query: string): void {
    const trimmed = query.trim();
    if (!trimmed) return;
    const history = getSearchHistory().filter(h => h !== trimmed);
    history.unshift(trimmed);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

/**
 * Get all search history entries (most recent first).
 */
export function getSearchHistory(): string[] {
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        if (!raw) return [];
        return JSON.parse(raw) as string[];
    } catch {
        return [];
    }
}

/**
 * Clear all search history.
 */
export function clearSearchHistory(): void {
    localStorage.removeItem(HISTORY_KEY);
}

/**
 * Get autocomplete suggestions based on prefix match.
 * Empty input returns full history.
 */
export function getSuggestions(input: string): string[] {
    const history = getSearchHistory();
    if (!input.trim()) return history;
    const lower = input.toLowerCase();
    return history.filter(h => h.toLowerCase().startsWith(lower));
}
