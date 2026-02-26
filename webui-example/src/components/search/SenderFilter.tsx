import React, { useState, useRef, useEffect } from 'react';

interface SenderFilterProps {
    value?: string;
    onChange: (sender?: string) => void;
}

export const SenderFilter: React.FC<SenderFilterProps> = ({ value, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [inputValue, setInputValue] = useState(value || '');
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setInputValue(value || '');
    }, [value]);

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

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onChange(inputValue.trim() || undefined);
        setIsOpen(false);
    };

    const handleClear = () => {
        setInputValue('');
        onChange(undefined);
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={containerRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-1 px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap shadow-sm active:scale-95 transition-all border ${value
                        ? 'bg-primary/10 dark:bg-primary/15 border-primary text-primary'
                        : 'bg-surface-light dark:bg-surface-dark border-slate-200 dark:border-border-dark'
                    }`}
            >
                <span className="text-slate-500 dark:text-muted-dark relative z-0">Sender:</span>
                <span className="text-slate-900 dark:text-white relative z-0">{value || 'All'}</span>
                <span className="material-symbols-outlined text-[18px] text-slate-400 relative z-0">expand_more</span>
            </button>

            {isOpen && (
                <div className="absolute top-full -left-4 sm:left-0 mt-2 w-56 sm:w-64 bg-white dark:bg-dropdown-dark rounded-xl shadow-lg border border-slate-100 dark:border-border-dark p-3 z-50">
                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <input
                            type="text"
                            autoFocus
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Username..."
                            className="flex-1 min-w-0 text-sm rounded bg-slate-50 dark:bg-surface-dark border border-slate-200 dark:border-border-dark px-2 py-1.5 text-slate-900 dark:text-white focus:outline-none focus:border-primary"
                        />
                        <div className="flex gap-1">
                            {inputValue && (
                                <button type="button" onClick={handleClear} className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" title="Clear">
                                    <span className="material-symbols-outlined text-[16px]">close</span>
                                </button>
                            )}
                            <button type="submit" className="bg-primary text-white p-1.5 rounded hover:bg-sky-500">
                                <span className="material-symbols-outlined text-[16px]">search</span>
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
};
