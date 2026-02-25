import { useState, useEffect } from 'react';

export type Theme = 'dark' | 'light' | 'system';

export function useTheme() {
    const [theme, setTheme] = useState<Theme>(
        () => (localStorage.getItem('theme') as Theme) || 'system'
    );

    useEffect(() => {
        const root = document.documentElement;

        const updateTheme = () => {
            const isDark = theme === 'dark' ||
                (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

            root.classList.toggle('dark', Boolean(isDark));
            localStorage.setItem('theme', theme);
        };

        updateTheme();

        if (theme === 'system') {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const handleChange = () => updateTheme();
            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }
    }, [theme]);

    return { theme, setTheme };
}
