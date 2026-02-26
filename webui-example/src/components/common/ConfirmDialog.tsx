import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

export interface ConfirmDialogProps {
    open: boolean;
    title: string;
    message: string;
    variant?: 'default' | 'danger';
    confirmLabel?: string;
    cancelLabel?: string;
    onConfirm: () => void;
    onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
    open,
    title,
    message,
    variant = 'default',
    confirmLabel,
    cancelLabel,
    onConfirm,
    onCancel,
}) => {
    const { t } = useTranslation();
    const shouldReduceMotion = useReducedMotion();
    const dialogRef = useRef<HTMLDivElement>(null);
    const cancelButtonRef = useRef<HTMLButtonElement>(null);

    // Close on Escape key
    useEffect(() => {
        if (!open) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onCancel();
            if (e.key === 'Tab' && dialogRef.current) {
                const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex=\"-1\"])'
                );
                if (focusable.length === 0) return;

                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                const activeElement = document.activeElement as HTMLElement | null;

                if (e.shiftKey && activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [open, onCancel]);

    useEffect(() => {
        if (!open) return;
        const previousFocus = document.activeElement as HTMLElement | null;
        cancelButtonRef.current?.focus();
        return () => previousFocus?.focus();
    }, [open]);

    const resolvedConfirmLabel = confirmLabel ?? t('common.confirm');
    const resolvedCancelLabel = cancelLabel ?? t('common.cancel');

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    key="confirm-overlay"
                    initial={shouldReduceMotion ? false : { opacity: 0 }}
                    animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1 }}
                    exit={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.15 }}
                    className="fixed inset-0 z-[999] flex items-center justify-center p-4"
                    aria-modal="true"
                    role="alertdialog"
                    aria-labelledby="confirm-dialog-title"
                    aria-describedby="confirm-dialog-message"
                >
                    {/* Backdrop */}
                    <motion.div
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                        onClick={onCancel}
                    />

                    {/* Card */}
                    <motion.div
                        ref={dialogRef}
                        initial={shouldReduceMotion ? false : { scale: 0.92, opacity: 0, y: 8 }}
                        animate={shouldReduceMotion ? { scale: 1, opacity: 1, y: 0 } : { scale: 1, opacity: 1, y: 0 }}
                        exit={shouldReduceMotion ? { scale: 1, opacity: 1, y: 0 } : { scale: 0.92, opacity: 0, y: 8 }}
                        transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                        tabIndex={-1}
                        className="relative w-full max-w-sm bg-white dark:bg-card-dark rounded-2xl shadow-2xl p-6 border border-slate-100 dark:border-white/5"
                    >
                        {/* Icon */}
                        <div className={`mx-auto mb-4 flex items-center justify-center w-12 h-12 rounded-full ${variant === 'danger'
                                ? 'bg-red-100 dark:bg-red-500/15'
                                : 'bg-primary/10 dark:bg-primary/15'
                            }`}>
                            <span className={`material-symbols-outlined text-2xl ${variant === 'danger' ? 'text-red-500' : 'text-primary'
                                }`}>
                                {variant === 'danger' ? 'warning' : 'help'}
                            </span>
                        </div>

                        <h2
                            id="confirm-dialog-title"
                            className="text-lg font-bold text-center text-slate-900 dark:text-white mb-2"
                        >
                            {title}
                        </h2>
                        <p
                            id="confirm-dialog-message"
                            className="text-sm text-center text-slate-500 dark:text-slate-400 mb-6"
                        >
                            {message}
                        </p>

                        <div className="flex gap-3">
                            <button
                                type="button"
                                ref={cancelButtonRef}
                                onClick={onCancel}
                                className="focus-ring flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-white/10 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                            >
                                {resolvedCancelLabel}
                            </button>
                            <button
                                type="button"
                                onClick={onConfirm}
                                className={`focus-ring flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition-colors ${variant === 'danger'
                                        ? 'bg-red-500 hover:bg-red-600'
                                        : 'bg-primary hover:bg-sky-500'
                                    }`}
                            >
                                {resolvedConfirmLabel}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
