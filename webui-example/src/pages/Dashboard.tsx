import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboardActivities, useDashboardBrief } from '@/hooks/queries/useDashboard';
import Header from '@/components/layout/Header';
import BriefCard from '@/components/dashboard/BriefCard';
import ActivityList from '@/components/dashboard/ActivityList';
import StatusCard from '@/components/dashboard/StatusCard';
import SyncProgress from '@/components/SyncProgress';
import { Skeleton } from '@/components/common/Skeleton';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
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

    const loading = activitiesLoading || briefLoading;
    const error = activitiesError?.message || briefError?.message;

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchQuery.trim()) {
            navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
        }
    };

    return (
        <div className="flex flex-col gap-6 pb-24">
            <Header onSettingsClick={() => navigate('/settings')} />

            {/* Search */}
            <section className="px-4 pt-2">
                <form onSubmit={handleSearch} className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="material-symbols-outlined text-gray-400 group-focus-within:text-primary transition-colors">search</span>
                    </div>
                    <input
                        className="block w-full pl-10 pr-10 py-3.5 border-none rounded-xl bg-surface-light dark:bg-surface-dark text-slate-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 shadow-sm dark:shadow-none"
                        placeholder="Search history (CJK support)..."
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
                        <button
                            type="submit"
                            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-white/5 text-gray-400"
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
                <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
                    {error}
                </div>
            ) : (
                <ActivityList activities={activities} />
            )}

            <div className="fixed bottom-24 right-6 z-40">
                <button
                    onClick={() => navigate('/select-chats')}
                    className="flex items-center justify-center w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all hover:scale-105"
                >
                    <span className="material-symbols-outlined">chat_add_on</span>
                </button>
            </div>
        </div>
    );
};

export default Dashboard;
