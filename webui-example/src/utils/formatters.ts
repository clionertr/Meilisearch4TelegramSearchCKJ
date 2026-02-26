export const formatTime = (isoStr: string, locale: string = 'en-US') => {
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now.getTime() - d.getTime();
        if (diffMs < 60 * 60 * 1000) {
            const mins = Math.max(1, Math.floor(diffMs / 60000));
            return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(-mins, 'minute');
        }
        if (diffMs < 24 * 60 * 60 * 1000) {
            return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
        }
        return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
    } catch {
        return '';
    }
};

export const getInitial = (title: string) => title.charAt(0).toUpperCase();

export const formatBytes = (bytes: number | null | undefined): string => {
    if (bytes === null || bytes === undefined) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};
