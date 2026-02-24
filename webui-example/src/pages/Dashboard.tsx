import React from 'react';
import { useDashboardActivities, useDashboardBrief } from '@/hooks/queries/useDashboard';
import Header from '@/components/layout/Header';
import BriefCard from '@/components/dashboard/BriefCard';
import ActivityList from '@/components/dashboard/ActivityList';

const Dashboard: React.FC = () => {
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

    return (
        <div className="flex flex-col gap-6 pb-24">
            <Header />

            {/* Search */}
            <section className="px-4 pt-2">
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <span className="material-symbols-outlined text-gray-400 group-focus-within:text-primary transition-colors">search</span>
                    </div>
                    <input
                        className="block w-full pl-10 pr-10 py-3.5 border-none rounded-xl bg-surface-light dark:bg-surface-dark text-slate-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 shadow-sm dark:shadow-none"
                        placeholder="Search history (CJK support)..."
                        type="text"
                    />
                    <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
                        <button className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-white/5 text-gray-400">
                            <span className="material-symbols-outlined !text-[20px]">tune</span>
                        </button>
                    </div>
                </div>
            </section>

            <BriefCard brief={brief} />

            {loading && (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                </div>
            )}

            {error && !loading && (
                <div className="mx-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {!loading && <ActivityList activities={activities} />}

            <div className="fixed bottom-24 right-6 z-40">
                <button className="flex items-center justify-center w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all hover:scale-105">
                    <span className="material-symbols-outlined">chat_add_on</span>
                </button>
            </div>
        </div>
    );
};

export default Dashboard;
