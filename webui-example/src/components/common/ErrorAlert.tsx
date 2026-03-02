/**
 * ErrorAlert — unified error display component.
 * Replaces inconsistent ad-hoc error divs across pages.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

export interface ErrorAlertProps {
    message: string;
    icon?: string;
    className?: string;
    onRetry?: () => void;
    retryLabel?: string;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
    message,
    icon = 'error',
    className = '',
    onRetry,
    retryLabel,
}) => {
    const { t } = useTranslation();
    const label = retryLabel ?? t('common.retry');

    return (
        <div
            role="alert"
            className={`flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-300 ${className}`}
        >
            <span className="material-symbols-outlined text-[20px] mt-0.5 shrink-0" aria-hidden="true">
                {icon}
            </span>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium break-words">{message}</p>
            </div>
            {onRetry && (
                <button
                    type="button"
                    onClick={onRetry}
                    className="focus-ring shrink-0 px-3 py-1 rounded-lg text-xs font-semibold text-red-600 dark:text-red-300 bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                >
                    {label}
                </button>
            )}
        </div>
    );
};
