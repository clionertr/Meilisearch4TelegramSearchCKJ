import React from 'react';
import { useNavigate } from 'react-router-dom';

const Storage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="pb-32 bg-background-light dark:bg-background-dark min-h-screen text-slate-900 dark:text-white">
            <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl">
                <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
                    <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
                </button>
                <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">Storage & Cleanup</h2>
                <button className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
                    <span className="material-symbols-outlined text-2xl">info</span>
                </button>
            </div>

            <div className="p-4 space-y-4">
                <div className="bg-white dark:bg-[#192d33] rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex justify-between items-end mb-4">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Total Usage</p>
                            <h3 className="text-3xl font-bold">2.4 <span className="text-lg font-normal text-slate-400">GB</span></h3>
                        </div>
                        <p className="text-sm text-slate-400 mb-1">of 5GB Available</p>
                    </div>
                    <div className="flex w-full h-3 bg-slate-100 dark:bg-[#111e22] rounded-full overflow-hidden mb-6">
                        <div className="bg-primary h-full w-[15%]" title="Text Index"></div>
                        <div className="bg-blue-400 h-full w-[45%]" title="Images"></div>
                        <div className="bg-indigo-500 h-full w-[25%]" title="Videos"></div>
                        <div className="bg-slate-400 h-full w-[5%]" title="Other"></div>
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-primary"></div>
                                <span className="text-sm font-medium">Text Index</span>
                            </div>
                            <span className="text-sm font-semibold">324 MB</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-blue-400"></div>
                                <span className="text-sm font-medium">Images</span>
                            </div>
                            <span className="text-sm font-semibold">1.2 GB</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                                <span className="text-sm font-medium">Videos</span>
                            </div>
                            <span className="text-sm font-semibold">0.8 GB</span>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-[#192d33] rounded-2xl p-5 border border-slate-200 dark:border-white/5 shadow-sm">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <span className="material-symbols-outlined text-primary">auto_delete</span>
                            </div>
                            <div>
                                <p className="font-bold">Auto-clean Storage</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Manage space automatically</p>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" defaultChecked className="sr-only peer" />
                            <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                        </label>
                    </div>
                </div>

                <div className="pt-2">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 px-1 mb-3">Cleanup Actions</h3>
                    <div className="space-y-3">
                        <button className="w-full flex items-center justify-between p-4 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform">
                            <div className="text-left">
                                <p className="font-bold text-sm">Delete Media &gt; 1 Month</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Frees up approx. 450 MB</p>
                            </div>
                            <div className="bg-primary/10 text-primary px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">Clean Up</div>
                        </button>
                        <button className="w-full flex items-center justify-between p-4 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 rounded-2xl active:scale-[0.98] transition-transform group">
                            <div className="text-left">
                                <p className="font-bold text-sm text-red-500">Clear All Cache</p>
                                <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Removes all temporary indexing data</p>
                            </div>
                            <div className="bg-red-500/10 text-red-500 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight">Clear</div>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Storage;