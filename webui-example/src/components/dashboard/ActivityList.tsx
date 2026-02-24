import React from 'react';
import { DashboardActivityItem } from '@/api/dashboard';
import { formatTime, getInitial } from '@/utils/formatters';
import { gradients } from '@/utils/constants';

interface ActivityListProps {
    activities: DashboardActivityItem[];
}

const ActivityList: React.FC<ActivityListProps> = ({ activities }) => {
    return (
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
    );
};

export default ActivityList;
