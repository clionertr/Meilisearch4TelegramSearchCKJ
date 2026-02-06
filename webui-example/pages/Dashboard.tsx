import React from 'react';
import { ActivityItem } from '../types';

const activities: ActivityItem[] = [
    {
        id: 1,
        title: "Tech Enthusiasts Group",
        time: "10:45 AM",
        summary: "Discussed new Apple Vision Pro updates and Python 3.12 release notes.",
        count: 12,
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuCahu-lP2nOeJ8xzKFOwIarPx7piY8jJY4zJkotAQupPrvQMcDHmBOFIqtprMhZu6yQ0-RWxbX40ttEkQerDsHVobfFxzVLdMTR4yVoR4VAFAT7uaWiUY3JTPgQqTq-Kjg8T1a3OUFualuuOLVCO3XtBjMWZowXSvAjKhzVqpAPgVDDHKiOaQ3Li6_Q7kFfQFX3xQhZjJB5GYpTNhgMZWODEuEyGBZZjZ99aM_gy3JXtr0XZf3JaDpEuIrvBz38D968MMzMPDaX3Bo",
        isOnline: true
    },
    {
        id: 2,
        title: "Foodie Adventures HK",
        time: "09:30 AM",
        summary: "Consensus on trying the new Dim Sum place in Central this Saturday.",
        count: 5,
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuAhr_771TOCULExgWGMRLkAL9yHFm50T9kJo9JmxfznMnzrDMyO64j_FiuOl6aV90iPym4y5nBlD8IUrAcGZXNZmjrcTYptrVakbwx1cmdwkEDNGGepmY4WTnK7ylBgVEwrVlxlLm4NcNnLM69rGeZXKEQbO_kosSay9e6SSww-Pk2_KCl7mD3xQKN5jMHWGogpUyxPJAQJrwt5Jp2BwvsBM7UHU6wuRyBPLGdz5hBTnbdnY-IBFJa2Y_yuGy0HxBbLUQhACT8IUvc"
    },
    {
        id: 3,
        title: "Project Alpha Team",
        time: "Yesterday",
        summary: "John uploaded the Q3 financial reports. Meeting rescheduled to next Monday...",
        initial: "P",
        bgGradient: "bg-gradient-to-br from-indigo-500 to-purple-600"
    },
    {
        id: 4,
        title: "Crypto Signals & News",
        time: "Yesterday",
        summary: "Market analysis suggests a bullish trend for ETH. Warnings about phishing scams...",
        count: 99,
        image: "https://lh3.googleusercontent.com/aida-public/AB6AXuDfzPy5NvzHMlKxxLpHD4-YbrDBIwRdByupzM4RXn7LGxCYAsZXexpdMUQqCaerD8aizzLSa2bGEloxJ4anpJ3QrnZHHoNsU0WSE7nA4C1p3ic_grBbZfABrozXCSM-S5pZymhCPSNlTHJm-MAltRcT8v-964vATLWpS37atcfJasQVPSrNqx1mZzZ2HI6ybZEQI7T_3ClQBA2QVluaMOYO-FYFvwfka3HGUhWkRxq-W_loEG7SFTyABvODCN3yzkB1JMBLkP_gZls"
    }
];

const Dashboard: React.FC = () => {
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

            {/* Cards */}
            <section className="grid grid-cols-2 gap-3 px-4">
                <button className="relative overflow-hidden rounded-xl aspect-[4/3] group shadow-md dark:shadow-none">
                    <div className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBWwKrHvOue9uCFBq7_9hvjEJACpA0UQoGkaMBENK5tCPfMbizmquuFTS0HHCHa4Rb616dwUSwiIhCJJbHWbFJiDM0RaXeriteTgQgdK1Hdj-T9IEEYN-I1F-dszqJ8wBpXSVgXyAlxybvzM85TwGNWaoqk1sg2hif3KfRqjGEb-LWMcaHCTseuoD8yTs6yGwQu7JldZoT-J35ImgPDtW60EqBoTzMbmxELCgF6Mix6RDyyxHq94NuMaSTcaxOMRRzeLkSWiaooVjQ')" }}></div>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent"></div>
                    <div className="absolute bottom-0 left-0 p-3 w-full text-left">
                        <div className="mb-1 w-8 h-8 rounded-full bg-primary/20 backdrop-blur-sm flex items-center justify-center text-primary">
                            <span className="material-symbols-outlined !text-[18px]">public</span>
                        </div>
                        <p className="text-white font-semibold text-sm leading-tight">Global Search</p>
                        <p className="text-gray-300 text-[10px] mt-0.5">Index entire history</p>
                    </div>
                </button>
                <button className="relative overflow-hidden rounded-xl aspect-[4/3] group shadow-md dark:shadow-none">
                    <div className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCqpUC89KEFqq_aK7yut9UpzBz8rI6cUfu4FPiojsuyH8pfxPKQMr4aV51oW2IqP7CZt_b2LA-1bfbKl-qoW12NSNG_PurhepVfMcoMy79oiN1r9oIFI5G8ARSXrwuFcO9Z_u9okj-zksdRL69fWb7G242vtljqvbrexkAWmw_fBtdzZDMvEs7hV9b6ktYguu9dKyK4uNItF2IcfV_TCwBIwPOHjC1XdFoaqOUOtVBsw5PIdxgSrP6AkbyHdU3B7G3OFvPK9km4H3E')" }}></div>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent"></div>
                    <div className="absolute bottom-0 left-0 p-3 w-full text-left">
                        <div className="mb-1 w-8 h-8 rounded-full bg-purple-500/30 backdrop-blur-sm flex items-center justify-center text-purple-300">
                            <span className="material-symbols-outlined !text-[18px]">auto_awesome</span>
                        </div>
                        <p className="text-white font-semibold text-sm leading-tight">AI Daily Brief</p>
                        <p className="text-gray-300 text-[10px] mt-0.5">Generate insights</p>
                    </div>
                </button>
            </section>

            {/* Recent Activity */}
            <section className="flex flex-col">
                <div className="px-4 flex items-center justify-between mb-2">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-white">Recent Activity</h2>
                    <button className="text-xs font-medium text-primary hover:text-primary/80 transition-colors">View All</button>
                </div>
                <div className="flex flex-col divide-y divide-gray-100 dark:divide-white/5 bg-surface-light dark:bg-surface-dark rounded-none sm:rounded-2xl mx-0 sm:mx-4 shadow-sm">
                    {activities.map(activity => (
                        <div key={activity.id} className="group flex gap-3 p-4 hover:bg-gray-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors">
                            <div className="relative shrink-0">
                                {activity.image ? (
                                    <img src={activity.image} alt={activity.title} className="w-12 h-12 rounded-full object-cover ring-2 ring-gray-100 dark:ring-white/10" />
                                ) : (
                                    <div className={`w-12 h-12 rounded-full ${activity.bgGradient} flex items-center justify-center text-white text-lg font-bold ring-2 ring-gray-100 dark:ring-white/10`}>
                                        {activity.initial}
                                    </div>
                                )}
                                {activity.isOnline && (
                                    <div className="absolute -bottom-0.5 -right-0.5 bg-background-light dark:bg-background-dark p-[2px] rounded-full">
                                        <div className="w-2.5 h-2.5 bg-green-500 rounded-full border border-background-light dark:border-background-dark"></div>
                                    </div>
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-baseline justify-between mb-0.5">
                                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate pr-2">{activity.title}</h3>
                                    <span className="text-[10px] text-gray-400 shrink-0">{activity.time}</span>
                                </div>
                                <div className="flex gap-1.5 items-start">
                                    <span className="material-symbols-outlined text-primary text-[14px] mt-0.5 shrink-0">smart_toy</span>
                                    <p className="text-xs text-slate-600 dark:text-gray-400 line-clamp-2 leading-relaxed">
                                        <span className="text-primary/80 font-medium">Summary:</span> {activity.summary}
                                    </p>
                                </div>
                            </div>
                            {activity.count && (
                                <div className="flex flex-col items-end justify-center gap-1">
                                    <span className={`flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded-full text-[10px] font-bold ${activity.count > 10 ? 'bg-primary text-white' : 'bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-400'}`}>
                                        {activity.count > 99 ? '99+' : activity.count}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>
            
            <div className="fixed bottom-24 right-6 z-40">
                <button className="flex items-center justify-center w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all hover:scale-105">
                    <span className="material-symbols-outlined">chat_add_on</span>
                </button>
            </div>
        </div>
    );
};

export default Dashboard;