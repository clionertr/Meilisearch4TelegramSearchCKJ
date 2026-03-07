import React from 'react';
import BottomNav from '@/components/BottomNav';
import SideNav from '@/components/layout/SideNav';
import ConnectionBanner from '@/components/common/ConnectionBanner';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen min-h-dvh overflow-x-hidden bg-background-light dark:bg-background-dark md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <SideNav />
      <div className="min-w-0 flex flex-col">
        <ConnectionBanner />
        <main id="main-content" className="mx-auto w-full max-w-md md:max-w-none pb-28 md:pb-8 flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
};
