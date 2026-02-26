import { useContext } from 'react';
import { ConfirmContext } from '@/components/common/ConfirmProvider';

export interface ConfirmOptions {
    title: string;
    message: string;
    variant?: 'default' | 'danger';
    confirmLabel?: string;
    cancelLabel?: string;
}

/**
 * Imperative confirm hook.
 * Usage: const { confirm } = useConfirm();
 *        const ok = await confirm({ title: 'Delete?', message: '...', variant: 'danger' });
 *        if (ok) { doAction(); }
 */
export function useConfirm() {
    const context = useContext(ConfirmContext);
    if (!context) {
        throw new Error('useConfirm must be used within a ConfirmProvider');
    }
    return context;
}
