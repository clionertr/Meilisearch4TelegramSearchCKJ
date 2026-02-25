import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const BottomNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Hide on login page
  if (location.pathname === '/login') return null;

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white/80 dark:bg-background-dark/80 backdrop-blur-xl border-t border-slate-200 dark:border-white/5 px-6 pt-3 pb-8 flex justify-between items-center z-50">
      <button
        onClick={() => navigate('/dashboard')}
        className={`flex flex-col items-center gap-1 ${isActive('/dashboard') ? 'text-primary' : 'text-slate-400'}`}
      >
        <span className={`material-symbols-outlined ${isActive('/dashboard') ? 'fill-1' : ''}`}>forum</span>
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

      <button
        onClick={() => {
          // Coming Soon toast or alert
          // Assuming toast from sonner is used in the app, but falling back to simple alert if not imported.
          // Since we might not want to import sonner here if not needed, let's use a native alert or a simple state.
          // Or just dispatch a custom event if toast is configured globally.
          // For simplicity and to not break anything, let's use a simple visually disabled state.
          // Wait, the spec says "toast Coming Soon" OR "disabled with Soon tag". 
          // Let's implement the disabled state with "Soon" tag, it's safer.
        }}
        className="flex flex-col items-center gap-1 text-slate-300 dark:text-slate-600 cursor-not-allowed relative"
        disabled
      >
        <span className="material-symbols-outlined">person</span>
        <span className="text-[10px] font-medium">Profile</span>
        <span className="absolute -top-2 -right-2 bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-[8px] px-1.5 py-0.5 rounded-full font-bold scale-75 origin-bottom-left">
          SOON
        </span>
      </button>
    </div>
  );
};

export default BottomNav;