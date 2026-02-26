import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { NAV_ITEMS, isNavItemActive } from '@/components/layout/navigation';

const SideNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();

  return (
    <nav
      aria-label={t('a11y.primaryNavigation')}
      className="hidden md:flex md:sticky md:top-0 md:h-screen md:w-64 md:flex-col md:border-r md:border-slate-200 md:bg-white/70 md:backdrop-blur md:dark:border-white/5 md:dark:bg-background-dark/50"
    >
      <div className="px-6 pt-8 pb-6 border-b border-slate-200 dark:border-white/5">
        <div className="flex items-center gap-2">
          <span className="text-primary material-symbols-outlined !text-[22px] fill-1" aria-hidden="true">memory</span>
          <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">TeleMemory</span>
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{t('layout.desktopNavigationHint')}</p>
      </div>

      <ul className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = isNavItemActive(location.pathname, item);
          return (
            <li key={item.key}>
              <button
                type="button"
                onClick={() => navigate(item.to)}
                aria-current={active ? 'page' : undefined}
                aria-label={t(item.labelKey)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${active
                    ? 'bg-primary/10 text-primary dark:bg-primary/20'
                    : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-200'
                  }`}
              >
                <span className={`material-symbols-outlined ${active ? 'fill-1' : ''}`} aria-hidden="true">{item.icon}</span>
                <span>{t(item.labelKey)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};

export default SideNav;
