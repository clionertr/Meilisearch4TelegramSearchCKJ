import React, { createContext, useCallback, useRef, useState } from 'react';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

interface ConfirmOptions {
    title: string;
    message: string;
    variant?: 'default' | 'danger';
    confirmLabel?: string;
    cancelLabel?: string;
}

interface ConfirmContextValue {
    confirm: (options: ConfirmOptions) => Promise<boolean>;
}

export const ConfirmContext = createContext<ConfirmContextValue | null>(null);

export const ConfirmProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [dialogState, setDialogState] = useState<(ConfirmOptions & { open: boolean }) | null>(null);
    const resolveRef = useRef<((value: boolean) => void) | null>(null);

    const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
        return new Promise<boolean>((resolve) => {
            resolveRef.current = resolve;
            setDialogState({ ...options, open: true });
        });
    }, []);

    const handleConfirm = () => {
        resolveRef.current?.(true);
        resolveRef.current = null;
        setDialogState(null);
    };

    const handleCancel = () => {
        resolveRef.current?.(false);
        resolveRef.current = null;
        setDialogState(null);
    };

    return (
        <ConfirmContext.Provider value={{ confirm }}>
            {children}
            {dialogState && (
                <ConfirmDialog
                    open={dialogState.open}
                    title={dialogState.title}
                    message={dialogState.message}
                    variant={dialogState.variant}
                    confirmLabel={dialogState.confirmLabel}
                    cancelLabel={dialogState.cancelLabel}
                    onConfirm={handleConfirm}
                    onCancel={handleCancel}
                />
            )}
        </ConfirmContext.Provider>
    );
};
