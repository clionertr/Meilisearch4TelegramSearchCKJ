import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { NAV_ITEMS, isNavItemActive } from '@/components/layout/navigation';

const BottomNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();

  // Hide on login page
  if (location.pathname === '/login') return null;

  return (
    <nav
      aria-label={t('a11y.primaryNavigation')}
      className="fixed bottom-0 left-0 right-0 mx-auto max-w-md border-t border-slate-200 bg-white/85 px-6 pt-3 pb-[calc(env(safe-area-inset-bottom,2rem))] min-h-[5.5rem] backdrop-blur-xl dark:border-white/5 dark:bg-background-dark/85 md:hidden"
    >
      <div className="flex items-center justify-between">
        {NAV_ITEMS.map((item) => {
          const active = isNavItemActive(location.pathname, item);
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => navigate(item.to)}
              aria-current={active ? 'page' : undefined}
              aria-label={t(item.labelKey)}
              className={`focus-ring flex flex-col items-center gap-1 active:scale-95 transition-transform ${active ? 'text-primary' : 'text-slate-400'
                }`}
            >
              <span className={`material-symbols-outlined ${active ? 'fill-1' : ''}`} aria-hidden="true">{item.icon}</span>
              <span className="text-[10px] font-medium">{t(item.labelKey)}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default BottomNav;
