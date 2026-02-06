import React from 'react';
import { useNavigate } from 'react-router-dom';
import DonutChart from '../components/DonutChart';

const Settings: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-10 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-md">
        <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
          <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
        </button>
        <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center dark:text-white">Settings & Management</h2>
        <button className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5">
          <span className="material-symbols-outlined text-2xl">more_horiz</span>
        </button>
      </div>

      {/* Storage Card */}
      <div className="p-4">
        <div className="flex flex-col items-stretch justify-start rounded-xl p-5 shadow-lg bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Device Health</p>
              <h3 className="text-2xl font-bold leading-tight dark:text-white">Storage Usage</h3>
            </div>
            <span className="material-symbols-outlined text-primary text-3xl">database</span>
          </div>
          <div className="flex items-center gap-6 mb-6">
            <DonutChart percentage={48} color="#13b6ec" bgColor="#111e22" />
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex justify-between items-end dark:text-white">
                <p className="text-2xl font-bold">2.4<span className="text-sm font-normal text-slate-400 ml-1">GB</span></p>
                <p className="text-sm text-slate-400">of 5GB used</p>
              </div>
              <div className="w-full h-2 bg-slate-100 dark:bg-[#111e22] rounded-full overflow-hidden">
                <div className="bg-primary h-full w-[48%] rounded-full"></div>
              </div>
              <p className="text-slate-500 dark:text-[#92bbc9] text-xs font-normal leading-relaxed mt-1">
                TeleMemory is indexing 14,202 messages and 843 media files locally.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => navigate('/storage')} className="flex-1 flex cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 bg-primary text-background-dark text-sm font-bold shadow-md active:scale-95 transition-transform">
              <span className="material-symbols-outlined text-lg">cleaning</span>
              <span>Quick Clean</span>
            </button>
            <button className="w-12 flex items-center justify-center rounded-lg h-12 bg-slate-100 dark:bg-[#111e22] text-slate-600 dark:text-white border border-slate-200 dark:border-white/5">
              <span className="material-symbols-outlined">settings</span>
            </button>
          </div>
        </div>
      </div>

      {/* Configurations */}
      <div className="px-4 py-2">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">Configurations</h3>
        <div className="grid grid-cols-2 gap-4">
          <div onClick={() => navigate('/ai-config')} className="flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">psychology</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">AI Configuration</p>
              <p className="text-slate-500 dark:text-[#92bbc9] text-xs mt-1">OpenAI, Claude, Local</p>
            </div>
            <div className="flex -space-x-2 mt-1">
              <div className="w-6 h-6 rounded-full bg-slate-800 border-2 border-[#192d33] flex items-center justify-center text-[8px] font-bold text-white">GPT</div>
              <div className="w-6 h-6 rounded-full bg-orange-600 border-2 border-[#192d33] flex items-center justify-center text-[8px] font-bold text-white">CL</div>
              <div className="w-6 h-6 rounded-full bg-primary border-2 border-[#192d33] flex items-center justify-center text-[8px] font-bold text-white">LLM</div>
            </div>
          </div>
          <div onClick={() => navigate('/synced-chats')} className="flex flex-col gap-4 p-4 rounded-xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5 shadow-sm cursor-pointer active:scale-95 transition-transform">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">sync</span>
              </div>
              <span className="material-symbols-outlined text-slate-400 text-sm">arrow_forward_ios</span>
            </div>
            <div>
              <p className="font-bold text-base dark:text-white">Synced Chats</p>
              <p className="text-slate-500 dark:text-[#92bbc9] text-xs mt-1">12 Active Syncs</p>
            </div>
            <div className="mt-1 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-[10px] text-green-500 font-medium">Real-time sync active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Memory Index */}
      <div className="px-4 py-6">
        <h3 className="text-lg font-bold leading-tight tracking-tight mb-4 dark:text-white">Memory Index</h3>
        <div className="space-y-3">
          <div className="flex items-center gap-4 p-4 rounded-xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5">
            <div className="w-12 h-12 rounded-lg bg-cover bg-center overflow-hidden" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBgxRUoem31aWld-lMwnUTLoXzNBG_ERJwlPIKhJzwd6ofci-p_FABD_AsxvSPAi_Ira2NYQ_BaslGiN0VazE3UAb2LcrFVzv_4nhhPqALjFOkRsA4zrDGbTGfs53I-T1-fLU997uqEJK4hGUYBB8IQgMkLt3JtH4MuztUf_tREe8nqkSRd8Nr6p-k9xaSNXdmslNwL6J-X2Y3lGAXZd4VHT4RWwkptJlYbYN3YgLl9b9rAqdim8e5JmB1RokVZAfEfqNtpn79Fxkg')" }}></div>
            <div className="flex-1">
              <p className="font-bold text-sm text-slate-900 dark:text-white">Message Summaries</p>
              <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Daily group activity digests</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-400">On</span>
              <div className="w-10 h-5 bg-primary rounded-full relative cursor-pointer">
                <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full"></div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 p-4 rounded-xl bg-white dark:bg-[#192d33] border border-slate-200 dark:border-white/5">
            <div className="w-12 h-12 rounded-lg bg-cover bg-center overflow-hidden" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDBpBak3QoLST73NKzcD_4N5uym-IK7sgaz_m1MFCeFIaKEtwk_RWnenc5IcVa73NVCK3qoVPd16ECVebECfKT1ia-FURiHmGei6tqrhpmGCyeXX9Sx4WqFBrRhr9xxocOKur7Np3njk6sxu_KtCbFSTfa_RQvCHcyzeTXRx7WtqE8pi45gqwKCj2cq3HlNyPQmciDVwLRXxchaLxZd9bgJAdeK3FDDkf9OmwJF8VB9r7BR1ZMoo2gNSKcybhEk8XH4tteeNEXHw9o')" }}></div>
            <div className="flex-1">
              <p className="font-bold text-sm text-slate-900 dark:text-white">Semantic Search</p>
              <p className="text-xs text-slate-500 dark:text-[#92bbc9]">Natural language indexing</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-400">On</span>
              <div className="w-10 h-5 bg-primary rounded-full relative cursor-pointer">
                <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;