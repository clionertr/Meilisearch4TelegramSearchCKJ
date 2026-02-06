import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const BottomNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Hide on login page
  if (location.pathname === '/login') return null;

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white/80 dark:bg-[#101d22]/80 backdrop-blur-xl border-t border-slate-200 dark:border-white/5 px-6 pt-3 pb-8 flex justify-between items-center z-50">
      <button 
        onClick={() => navigate('/')}
        className={`flex flex-col items-center gap-1 ${isActive('/') ? 'text-primary' : 'text-slate-400'}`}
      >
        <span className={`material-symbols-outlined ${isActive('/') ? 'fill-1' : ''}`}>forum</span>
        <span className="text-[10px] font-medium">Chats</span>
      </button>

      <button 
        onClick={() => navigate('/search')}
        className={`flex flex-col items-center gap-1 ${isActive('/search') ? 'text-primary' : 'text-slate-400'}`}
      >
        <span className="material-symbols-outlined">search</span>
        <span className="text-[10px] font-medium">Search</span>
      </button>

      <button 
        onClick={() => navigate('/settings')}
        className={`flex flex-col items-center gap-1 ${isActive('/settings') || isActive('/storage') || isActive('/ai-config') ? 'text-primary' : 'text-slate-400'}`}
      >
        <span className={`material-symbols-outlined ${isActive('/settings') ? 'fill-1' : ''}`}>settings</span>
        <span className="text-[10px] font-medium">Settings</span>
      </button>

      <button className="flex flex-col items-center gap-1 text-slate-400">
        <span className="material-symbols-outlined">person</span>
        <span className="text-[10px] font-medium">Profile</span>
      </button>
    </div>
  );
};

export default BottomNav;