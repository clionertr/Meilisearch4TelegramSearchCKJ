import React from 'react';
import { Skeleton } from './Skeleton';

/**
 * Full-page loading skeleton used as Suspense fallback during lazy page loads.
 */
export const PageSkeleton: React.FC = () => {
    return (
        <div className="flex flex-col h-screen bg-background-light dark:bg-background-dark p-4 space-y-4">
            {/* Header skeleton */}
            <div className="flex items-center justify-between py-2">
                <Skeleton variant="avatar" className="w-10 h-10 rounded-xl" />
                <Skeleton variant="text" width="7rem" className="h-5" />
                <Skeleton variant="avatar" className="w-10 h-10 rounded-xl" />
            </div>
            {/* Card skeletons */}
            <Skeleton variant="card" height="9rem" />
            <div className="grid grid-cols-2 gap-3">
                <Skeleton variant="card" height="6rem" />
                <Skeleton variant="card" height="6rem" />
            </div>
            <Skeleton variant="card" height="7rem" />
            <Skeleton variant="card" height="5rem" />
        </div>
    );
};
