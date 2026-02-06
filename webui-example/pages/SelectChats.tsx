import React from 'react';
import { useNavigate } from 'react-router-dom';

const SelectChats: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col text-slate-900 dark:text-white">
            <header className="flex items-center justify-between px-4 py-3 sticky top-0 z-30 bg-background-light dark:bg-background-dark">
                <button onClick={() => navigate(-1)} className="flex items-center justify-center p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                    <span className="material-symbols-outlined text-2xl">arrow_back</span>
                </button>
                <div className="flex-1 flex justify-end px-2">
                    <button className="text-sm font-semibold text-primary hover:opacity-80 transition-opacity">Select All</button>
                </div>
            </header>

            <main className="flex-1 flex flex-col overflow-y-auto no-scrollbar pb-32">
                <div className="px-6 pt-2 pb-6">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Select Chats to Index</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-[15px] leading-relaxed">
                        Selected chats will be downloaded and indexed locally on your device for fast, private searching and AI summaries.
                    </p>
                </div>

                <div className="px-4 space-y-2">
                    {/* Saved Messages */}
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white dark:bg-[#15262d] border border-slate-100 dark:border-slate-800/50 shadow-sm">
                        <div className="flex items-center gap-3 overflow-hidden">
                            <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-2xl">bookmark</span>
                            </div>
                            <div className="flex flex-col truncate">
                                <span className="font-semibold text-base truncate">Saved Messages</span>
                                <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                                    <span>1.2k messages</span>
                                    <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></span>
                                    <span>Private</span>
                                </div>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0 ml-4">
                            <input type="checkbox" defaultChecked className="sr-only peer" />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                    </div>

                    {/* Silicon Valley Tech */}
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white dark:bg-[#15262d] border border-slate-100 dark:border-slate-800/50 shadow-sm">
                        <div className="flex items-center gap-3 overflow-hidden">
                            <div className="w-12 h-12 rounded-full overflow-hidden shrink-0 relative">
                                <img alt="Silicon Valley Tech" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB9XVRFs4CUx_0pyGVf1q4S65zcNEEfDRMr6JNrWLwiBCr1DMabwK21P072CKqbtHFo20Sac7Dp4n-EiKNYu4KrHMpjbO7c73REbPtMUR52rpbWlBpqu4NLjIIcX0DYOLcCUG4054ffbjMLnGjh8DGbp_QzOjEG9nV_ZQOCuSf7k6sa9TI3-ORPmm7iPM-K4jww_K-wRbru_-eDS-Z0aOdE7xmR82mPTPqmlc3nh0Blc-RGoxPN7clsOhkMIadJialJFfFCQWuVud0" />
                            </div>
                            <div className="flex flex-col truncate">
                                <span className="font-semibold text-base truncate">Silicon Valley Tech</span>
                                <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                                    <span>15.2k messages</span>
                                    <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></span>
                                    <span>Group</span>
                                </div>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0 ml-4">
                            <input type="checkbox" defaultChecked className="sr-only peer" />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                    </div>

                    {/* Crypto Alerts */}
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-white dark:bg-[#15262d] border border-slate-100 dark:border-slate-800/50 shadow-sm">
                        <div className="flex items-center gap-3 overflow-hidden">
                            <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-emerald-600 dark:text-emerald-400 text-2xl">currency_bitcoin</span>
                            </div>
                            <div className="flex flex-col truncate">
                                <span className="font-semibold text-base truncate">Crypto Alerts</span>
                                <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                                    <span>42.1k messages</span>
                                    <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-600"></span>
                                    <span>Channel</span>
                                </div>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0 ml-4">
                            <input type="checkbox" className="sr-only peer" />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                    </div>
                </div>

                <p className="text-xs text-slate-400 text-center mt-6">
                    You can modify these selections later in settings.
                </p>
            </main>

            <footer className="fixed bottom-0 left-0 right-0 p-6 pb-8 bg-gradient-to-t from-background-light dark:from-background-dark via-background-light/95 dark:via-background-dark/95 to-transparent z-40">
                <button onClick={() => navigate('/synced-chats')} className="w-full bg-primary hover:bg-sky-500 text-white font-bold py-4 px-6 rounded-2xl shadow-xl shadow-primary/30 active:scale-[0.98] transition-all flex items-center justify-center gap-3">
                    <span>Start Syncing</span>
                    <span className="material-symbols-outlined text-[22px]">sync</span>
                </button>
            </footer>
        </div>
    );
};

export default SelectChats;