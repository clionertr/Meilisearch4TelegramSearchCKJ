import React from 'react';
import { useTranslation } from 'react-i18next';

interface HeaderProps {
    onSettingsClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSettingsClick }) => {
    const { t } = useTranslation();

    return (
        <header className="sticky top-0 z-40 w-full bg-background-light/90 dark:bg-background-dark/90 backdrop-blur-md border-b border-gray-200 dark:border-white/5 px-4 py-3 flex items-center justify-between">
            <button
                type="button"
                aria-label={t('a11y.openMenu')}
                className="p-2 -ml-2 rounded-full text-slate-400 dark:text-slate-600 cursor-not-allowed"
                disabled
            >
                <span className="material-symbols-outlined" aria-hidden="true">menu</span>
            </button>
            <h1 className="text-lg font-bold tracking-tight flex items-center gap-2 dark:text-white">
                <span className="text-primary material-symbols-outlined !text-[20px] fill-1" aria-hidden="true">memory</span>
                TeleMemory
            </h1>
            <button
                type="button"
                onClick={onSettingsClick}
                aria-label={t('a11y.openSettings')}
                className="focus-ring p-2 -mr-2 rounded-full hover:bg-gray-200 dark:hover:bg-white/10 text-slate-600 dark:text-gray-300"
            >
                <span className="material-symbols-outlined" aria-hidden="true">settings</span>
            </button>
        </header>
    );
};

export default Header;
