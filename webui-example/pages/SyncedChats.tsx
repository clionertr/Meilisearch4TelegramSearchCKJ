import React from 'react';
import { useNavigate } from 'react-router-dom';

const SyncedChats: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="pb-32 bg-background-light dark:bg-background-dark min-h-screen">
            <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-30 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                    <span className="material-symbols-outlined text-2xl dark:text-white">arrow_back_ios_new</span>
                </button>
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">Manage Synced Chats</h2>
                <button className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                    <span className="material-symbols-outlined text-2xl dark:text-white">search</span>
                </button>
            </div>

            <div className="px-4 py-2 mb-2">
                <div className="bg-primary/10 border border-primary/20 rounded-2xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider">Sync Status</p>
                        <p className="text-lg font-bold dark:text-white">12 Active Chats</p>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-primary/20 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                        <span className="text-xs font-bold text-primary">Live</span>
                    </div>
                </div>
            </div>

            <div className="px-4 space-y-3">
                {/* Tech Community */}
                <div className="flex items-center gap-4 p-4 rounded-2xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-blue-500 to-cyan-400 flex items-center justify-center text-white font-bold text-lg">TC</div>
                        <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-green-500 border-2 border-white dark:border-[#192d33] rounded-full"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-sm truncate dark:text-white">Tech Community Global</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-500 font-bold uppercase tracking-tight">Real-time</span>
                            <span className="text-[10px] text-slate-400">4.2k messages indexed</span>
                        </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 text-xs font-bold hover:bg-slate-200 dark:hover:bg-white/10 transition-colors dark:text-white">Edit</button>
                </div>

                {/* AI Research */}
                <div className="flex items-center gap-4 p-4 rounded-2xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-orange-500 to-yellow-400 flex items-center justify-center text-white font-bold text-lg">AI</div>
                        <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-green-500 border-2 border-white dark:border-[#192d33] rounded-full"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-sm truncate dark:text-white">AI Research & Insights</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-500 font-bold uppercase tracking-tight">Real-time</span>
                            <span className="text-[10px] text-slate-400">12.8k messages indexed</span>
                        </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 text-xs font-bold hover:bg-slate-200 dark:hover:bg-white/10 transition-colors dark:text-white">Edit</button>
                </div>

                {/* UX Design */}
                <div className="flex items-center gap-4 p-4 rounded-2xl bg-white/60 dark:bg-[#192d33]/60 border border-slate-200 dark:border-white/5 shadow-sm opacity-80">
                    <div className="relative grayscale">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-purple-500 to-pink-400 flex items-center justify-center text-white font-bold text-lg">UX</div>
                        <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-slate-400 border-2 border-white dark:border-[#192d33] rounded-full"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-sm truncate text-slate-600 dark:text-slate-300">UX Design Weekly</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight">Paused</span>
                            <span className="text-[10px] text-slate-400">843 messages indexed</span>
                        </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 text-xs font-bold text-primary hover:bg-slate-200 dark:hover:bg-white/10 transition-colors">Resume</button>
                </div>
            </div>

            <button 
                onClick={() => navigate('/select-chats')}
                className="fixed bottom-24 right-6 w-14 h-14 rounded-full bg-primary text-background-dark shadow-2xl flex items-center justify-center active:scale-90 transition-transform z-40"
            >
                <span className="material-symbols-outlined text-3xl font-bold">add</span>
            </button>
        </div>
    );
};

export default SyncedChats;