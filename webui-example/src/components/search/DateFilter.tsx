import React, { useState, useRef, useEffect } from 'react';

interface DateFilterProps {
    rangeType?: string;
    onChange: (rangeType: string, dateFrom?: string) => void;
}

export const DateFilter: React.FC<DateFilterProps> = ({ rangeType, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const options = [
        { label: 'Anytime', value: 'anytime' },
        { label: 'Last 24h', value: '24h' },
        { label: 'Last 7 days', value: '7d' },
        { label: 'Last 30 days', value: '30d' },
    ];

    const currentLabel = options.find(o => o.value === rangeType)?.label || 'Anytime';

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
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-1 px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap shadow-sm active:scale-95 transition-all border ${
                    isActive
                        ? 'bg-primary/10 dark:bg-primary/15 border-primary text-primary'
                        : 'bg-surface-light dark:bg-surface-dark border-slate-200 dark:border-border-dark'
                }`}
            >
                <span className="text-slate-500 dark:text-muted-dark relative z-0">Date:</span>
                <span className="text-primary relative z-0">{currentLabel}</span>
                <span className="material-symbols-outlined text-[18px] text-slate-400 relative z-0">expand_more</span>
            </button>

            {isOpen && (
                <div className="absolute top-full left-0 mt-2 w-48 bg-white dark:bg-dropdown-dark rounded-xl shadow-lg border border-slate-100 dark:border-border-dark py-1 z-50">
                    {options.map((option) => (
                        <button
                            key={option.label}
                            onClick={() => handleSelect(option.value)}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-surface-dark text-slate-700 dark:text-slate-200"
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};
