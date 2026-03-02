import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useDashboardActivities, useDashboardBrief } from '@/hooks/queries/useDashboard';
import { useSystemStatus } from '@/hooks/queries/useStatus';
import Header from '@/components/layout/Header';
import BriefCard from '@/components/dashboard/BriefCard';
import ActivityList from '@/components/dashboard/ActivityList';
import StatusCard from '@/components/dashboard/StatusCard';
import SyncProgress from '@/components/SyncProgress';
import { Skeleton } from '@/components/common/Skeleton';
import { ErrorAlert } from '@/components/common/ErrorAlert';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const [searchQuery, setSearchQuery] = useState('');

    const {
        data: activities = [],
        isLoading: activitiesLoading,
        error: activitiesError
    } = useDashboardActivities(20);

    const {
        data: brief = null,
        isLoading: briefLoading,
        error: briefError
    } = useDashboardBrief();

    const { data: systemStatus } = useSystemStatus();

    const loading = activitiesLoading || briefLoading;
    const error = activitiesError?.message || briefError?.message;

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchQuery.trim()) {
            navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
        }
    };

    const meiliOk = systemStatus?.meili_connected ?? null;
    const telegramOk = systemStatus?.telegram_connected ?? null;

    return (
        <div className="flex flex-col gap-6 pb-24 md:pb-8">
            <Header onSettingsClick={() => navigate('/settings')} />

            {/* Connection Status Strip */}
            {systemStatus && (
                <section className="px-4 -mt-2">
                    <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm">
                        <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${meiliOk ? 'bg-green-500' : 'bg-red-500'}`} />
                            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">{t('status.meilisearch')}</span>
                        </div>
                        <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />
                        <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${telegramOk ? 'bg-green-500' : 'bg-red-500'}`} />
                            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">{t('status.telegram')}</span>
                        </div>
                        <div className="ml-auto flex items-center gap-1.5">
                            <span className={`text-xs font-semibold ${meiliOk && telegramOk ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                                {meiliOk && telegramOk ? t('status.online') : t('status.offline')}
                            </span>
                        </div>
                    </div>
                </section>
            )}

            {/* Search */}
            <section className="px-4 pt-0">
                <form onSubmit={handleSearch} className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="material-symbols-outlined text-gray-400 group-focus-within:text-primary transition-colors">search</span>
                    </div>
                    <input
                        className="block w-full pl-10 pr-10 py-3.5 border-none rounded-xl bg-surface-light dark:bg-surface-dark text-slate-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 shadow-sm dark:shadow-none"
                        placeholder={t('dashboard.searchPlaceholder')}
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        aria-label={t('a11y.searchMessages')}
                    />
                    <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
                        <button
                            type="submit"
                            className="focus-ring p-1 rounded-md hover:bg-gray-100 dark:hover:bg-white/5 text-gray-400"
                            aria-label={t('search.openFilters')}
                        >
                            <span className="material-symbols-outlined !text-[20px]">tune</span>
                        </button>
                    </div>
                </form>
            </section>

            {/* System Status KPI Cards */}
            <StatusCard />

            {/* WebSocket Sync Progress */}
            <SyncProgress />

            <BriefCard brief={brief} />

            {loading ? (
                <section className="px-4 flex flex-col gap-3">
                    <div className="px-4 flex items-center justify-between mb-2 -mx-4">
                        <Skeleton variant="text" width="8rem" className="h-6" />
                    </div>
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="flex gap-3 p-4 bg-surface-light dark:bg-surface-dark rounded-2xl">
                            <Skeleton variant="avatar" />
                            <div className="flex-1 space-y-2 py-1">
                                <Skeleton variant="text" width="60%" />
                                <Skeleton variant="text" width="100%" />
                            </div>
                        </div>
                    ))}
                </section>
            ) : error ? (
                <div className="px-4">
                    <ErrorAlert message={error} />
                </div>
            ) : (
                <ActivityList activities={activities} />
            )}

            <div className="fixed bottom-24 right-6 z-40 md:bottom-8">
                <button
                    type="button"
                    onClick={() => navigate('/sync')}
                    className="focus-ring flex items-center justify-center w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all hover:scale-105"
                    aria-label={t('dashboard.addChats')}
                >
                    <span className="material-symbols-outlined">chat_add_on</span>
                </button>
            </div>
        </div>
    );
};

export default Dashboard;
