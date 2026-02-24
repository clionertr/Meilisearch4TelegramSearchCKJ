import React, { useEffect, useState } from 'react';
import { dashboardApi, DashboardActivityItem, DashboardBriefData } from '../src/api/dashboard';

const Dashboard: React.FC = () => {
    const [activities, setActivities] = useState<DashboardActivityItem[]>([]);
    const [brief, setBrief] = useState<DashboardBriefData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const [activityRes, briefRes] = await Promise.all([
                    dashboardApi.getActivity({ limit: 20 }),
                    dashboardApi.getBrief(),
                ]);
                setActivities(activityRes.data.data?.items ?? []);
                setBrief(briefRes.data.data ?? null);
            } catch (err: any) {
                setError(err.response?.data?.message || 'Failed to load dashboard');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const formatTime = (isoStr: string) => {
        try {
            const d = new Date(isoStr);
            const now = new Date();
            const diffMs = now.getTime() - d.getTime();
            if (diffMs < 60 * 60 * 1000) return `${Math.floor(diffMs / 60000)}m ago`;
            if (diffMs < 24 * 60 * 60 * 1000) {
                return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            return 'Yesterday';
        } catch {
            return '';
        }
    };

    const getInitial = (title: string) => title.charAt(0).toUpperCase();
    const gradients = [
        'bg-gradient-to-br from-blue-500 to-cyan-400',
        'bg-gradient-to-br from-orange-500 to-yellow-400',
        'bg-gradient-to-br from-indigo-500 to-purple-600',
        'bg-gradient-to-br from-emerald-500 to-teal-400',
        'bg-gradient-to-br from-pink-500 to-rose-400',
    ];

    return (
        <div className="flex flex-col gap-6 pb-24">
            {/* Header */}
            <header className="sticky top-0 z-40 w-full bg-background-light/90 dark:bg-background-dark/90 backdrop-blur-md border-b border-gray-200 dark:border-white/5 px-4 py-3 flex items-center justify-between">
                <button className="p-2 -ml-2 rounded-full hover:bg-gray-200 dark:hover:bg-white/10 text-slate-600 dark:text-gray-300">
                    <span className="material-symbols-outlined">menu</span>
                </button>
                <h1 className="text-lg font-bold tracking-tight flex items-center gap-2 dark:text-white">
                    <span className="text-primary material-symbols-outlined !text-[20px] fill-1">memory</span>
                    TeleMemory
                </h1>
                <button className="p-2 -mr-2 rounded-full hover:bg-gray-200 dark:hover:bg-white/10 text-slate-600 dark:text-gray-300">
                    <span className="material-symbols-outlined">settings</span>
                </button>
            </header>

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

            {/* Brief Card */}
            {brief && brief.summary && (
                <section className="px-4">
                    <div className="p-4 rounded-2xl bg-primary/10 border border-primary/20">
                        <div className="flex items-start gap-3">
                            <span className="material-symbols-outlined text-primary mt-0.5">auto_awesome</span>
                            <div>
                                <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">Daily Brief</p>
                                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{brief.summary}</p>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {/* Loading / Error */}
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

            {/* Recent Activity */}
            {!loading && !error && (
                <section className="flex flex-col">
                    <div className="px-4 flex items-center justify-between mb-2">
                        <h2 className="text-lg font-bold text-slate-800 dark:text-white">Recent Activity</h2>
                        <span className="text-xs text-slate-400">{activities.length} chats</span>
                    </div>
                    {activities.length === 0 ? (
                        <div className="px-4 py-8 text-center text-slate-400 text-sm">
                            No activity in the last 24 hours
                        </div>
                    ) : (
                        <div className="flex flex-col divide-y divide-gray-100 dark:divide-white/5 bg-surface-light dark:bg-surface-dark rounded-none sm:rounded-2xl mx-0 sm:mx-4 shadow-sm">
                            {activities.map((activity, idx) => (
                                <div key={activity.chat_id} className="group flex gap-3 p-4 hover:bg-gray-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors">
                                    <div className="relative shrink-0">
                                        <div className={`w-12 h-12 rounded-full ${gradients[idx % gradients.length]} flex items-center justify-center text-white text-lg font-bold ring-2 ring-gray-100 dark:ring-white/10`}>
                                            {getInitial(activity.chat_title)}
                                        </div>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-baseline justify-between mb-0.5">
                                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate pr-2">{activity.chat_title}</h3>
                                            <span className="text-[10px] text-gray-400 shrink-0">{formatTime(activity.latest_message_time)}</span>
                                        </div>
                                        <div className="flex gap-1.5 items-start">
                                            <span className="material-symbols-outlined text-primary text-[14px] mt-0.5 shrink-0">smart_toy</span>
                                            <p className="text-xs text-slate-600 dark:text-gray-400 line-clamp-2 leading-relaxed">
                                                {activity.sample_message || activity.top_keywords.join(', ')}
                                            </p>
                                        </div>
                                    </div>
                                    {activity.message_count > 0 && (
                                        <div className="flex flex-col items-end justify-center gap-1">
                                            <span className={`flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded-full text-[10px] font-bold ${activity.message_count > 10 ? 'bg-primary text-white' : 'bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-400'}`}>
                                                {activity.message_count > 99 ? '99+' : activity.message_count}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            )}

            <div className="fixed bottom-24 right-6 z-40">
                <button className="flex items-center justify-center w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all hover:scale-105">
                    <span className="material-symbols-outlined">chat_add_on</span>
                </button>
            </div>
        </div>
    );
};

export default Dashboard;