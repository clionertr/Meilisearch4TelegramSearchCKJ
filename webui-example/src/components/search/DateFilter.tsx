import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface DateFilterProps {
    rangeType?: string;
    onChange: (rangeType: string, dateFrom?: string) => void;
}

export const DateFilter: React.FC<DateFilterProps> = ({ rangeType, onChange }) => {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const options = [
        { label: t('search.anytime'), value: 'anytime' },
        { label: t('search.last24h'), value: '24h' },
        { label: t('search.last7Days'), value: '7d' },
        { label: t('search.last30Days'), value: '30d' },
    ];

    const currentLabel = options.find((o) => o.value === rangeType)?.label || t('search.anytime');

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        const handleEscape = (event: KeyboardEvent) => {
            if (event.key === 'Escape') setIsOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, []);

    const handleSelect = (val: string) => {
        let dateFrom: string | undefined;
        if (val !== 'anytime') {
            const now = new Date();
            if (val === '24h') now.setHours(now.getHours() - 24);
            else if (val === '7d') now.setDate(now.getDate() - 7);
            else if (val === '30d') now.setDate(now.getDate() - 30);
            dateFrom = now.toISOString();
        }
        onChange(val, dateFrom);
        setIsOpen(false);
    };

    const isActive = rangeType !== 'anytime' && !!rangeType;

    return (
        <div className="relative" ref={containerRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                aria-haspopup="listbox"
                aria-expanded={isOpen}
                aria-label={t('search.dateLabel')}
                className={`focus-ring flex items-center gap-1 px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap shadow-sm active:scale-95 transition-all border ${
                    isActive
                        ? 'bg-primary/10 dark:bg-primary/15 border-primary text-primary'
                        : 'bg-surface-light dark:bg-surface-dark border-slate-200 dark:border-border-dark'
                }`}
            >
                <span className="text-slate-500 dark:text-muted-dark relative z-0">{t('search.dateLabel')}:</span>
                <span className="text-primary relative z-0">{currentLabel}</span>
                <span className="material-symbols-outlined text-[18px] text-slate-400 relative z-0" aria-hidden="true">expand_more</span>
            </button>

            {isOpen && (
                <div
                    role="listbox"
                    className="absolute top-full left-0 mt-2 w-48 bg-white dark:bg-dropdown-dark rounded-xl shadow-lg border border-slate-100 dark:border-border-dark py-1 z-50"
                >
                    {options.map((option) => (
                        <button
                            type="button"
                            role="option"
                            aria-selected={option.value === (rangeType || 'anytime')}
                            key={option.label}
                            onClick={() => handleSelect(option.value)}
                            className="focus-ring w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-surface-dark text-slate-700 dark:text-slate-200"
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};
