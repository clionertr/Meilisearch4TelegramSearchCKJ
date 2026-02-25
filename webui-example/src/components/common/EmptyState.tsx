import React from 'react';

export interface EmptyStateProps {
    icon: string;
    title: string;
    description?: string;
    actionLabel?: string;
    onAction?: () => void;
    className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, actionLabel, onAction, className = '' }) => {
    return (
        <div className={`flex flex-col items-center justify-center p-8 text-center bg-surface-light dark:bg-surface-dark rounded-2xl border border-slate-200 dark:border-divider-dark border-dashed ${className}`}>
            <span className="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500 mb-4">
                {icon}
            </span>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                {title}
            </h3>
            {description && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 max-w-sm">
                    {description}
                </p>
            )}
            {actionLabel && onAction && (
                <button
                    onClick={onAction}
                    className="px-6 py-2.5 bg-primary hover:bg-primary/90 active:bg-primary text-white font-bold rounded-xl transition-all shadow-md hover:scale-105 active:scale-95 flex items-center gap-2 mx-auto"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
};
