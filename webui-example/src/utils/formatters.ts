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
