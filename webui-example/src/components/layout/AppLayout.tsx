import React from 'react';
import BottomNav from '@/components/BottomNav';
import SideNav from '@/components/layout/SideNav';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <SideNav />
      <div className="min-w-0">
        <main id="main-content" className="mx-auto w-full max-w-md md:max-w-none pb-28 md:pb-8">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
};
