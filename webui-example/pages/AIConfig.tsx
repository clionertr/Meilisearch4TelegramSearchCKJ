import React from 'react';
import { useNavigate } from 'react-router-dom';

const AIConfig: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="bg-background-dark text-white min-h-screen">
            <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden max-w-[430px] mx-auto bg-background-dark border-x border-white/5 pb-32">
                <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-30 bg-background-dark/80 backdrop-blur-xl border-b border-white/5">
                    <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full active:bg-white/10 transition-colors">
                        <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
                    </button>
                    <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">AI Configuration</h2>
                    <div className="w-10"></div>
                </div>

                <div className="p-4 space-y-6">
                    <section className="space-y-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">API Settings</h3>
                        <div className="p-4 rounded-2xl bg-[#192d33] border border-white/5 space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 block px-1">API Endpoint URL</label>
                                <div className="relative">
                                    <input className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none" placeholder="https://api.openai.com/v1" type="text" defaultValue="https://api.openai.com/v1" />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 block px-1">API Key</label>
                                <div className="relative">
                                    <input className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none" placeholder="Enter your API key" type="password" defaultValue="sk-••••••••••••••••" />
                                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xl cursor-pointer">visibility</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between p-1">
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-green-500 text-sm">check_circle</span>
                                    <span className="text-xs text-slate-300">Connection Verified</span>
                                </div>
                                <button className="text-xs font-bold text-primary px-3 py-1 bg-primary/10 rounded-full active:scale-95 transition-all">Test Connection</button>
                            </div>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">Model Selection</h3>
                        <div className="p-4 rounded-2xl bg-[#192d33] border border-white/5 space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 block px-1">Model Name</label>
                                <div className="relative">
                                    <input className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none" placeholder="e.g. gpt-4o" type="text" defaultValue="gpt-4o" />
                                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">expand_more</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">Prompt Customization</h3>
                        <div className="p-4 rounded-2xl bg-[#192d33] border border-white/5 space-y-4">
                            <div className="space-y-3">
                                <div className="flex justify-between items-center px-1">
                                    <label className="text-xs font-medium text-slate-300">Summary Style</label>
                                    <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold uppercase tracking-tight">Professional</span>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <button className="py-2.5 px-3 rounded-xl border border-white/10 text-xs font-medium bg-white/5 flex items-center justify-center gap-2 transition-all active:scale-95">
                                        <span className="material-symbols-outlined text-sm">comedy_mask</span> Funny
                                    </button>
                                    <button className="py-2.5 px-3 rounded-xl border border-primary/40 text-xs font-medium bg-primary/10 text-primary flex items-center justify-center gap-2 transition-all active:scale-95">
                                        <span className="material-symbols-outlined text-sm">business_center</span> Professional
                                    </button>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 block px-1">Custom Instructions</label>
                                <textarea className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary resize-none placeholder:text-slate-600 leading-relaxed outline-none" placeholder="Define how the AI should summarize group history..." rows={4} defaultValue="Write a professional, bulleted summary of the last 24 hours of messages. Focus on key decisions, important links shared, and action items. Keep it concise and use a polite tone."></textarea>
                            </div>
                        </div>
                        <p className="text-[11px] text-slate-500 leading-relaxed px-1">
                            These instructions guide how your assistant generates daily digests from indexed messages.
                        </p>
                    </section>
                </div>

                <div className="fixed bottom-0 left-0 right-0 max-w-[430px] mx-auto p-4 bg-background-dark/80 backdrop-blur-xl border-t border-white/5 z-40 pb-10">
                    <button className="w-full h-14 bg-primary text-background-dark font-bold rounded-2xl flex items-center justify-center shadow-lg active:scale-[0.98] transition-all">
                        Save Configuration
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AIConfig;