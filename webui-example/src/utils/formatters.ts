export const formatTime = (isoStr: string) => {
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now.getTime() - d.getTime();
        if (diffMs < 60 * 60 * 1000) return `${Math.floor(diffMs / 60000)}m ago`;
        if (diffMs < 24 * 60 * 60 * 1000) {
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return 'Yesterday';
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
