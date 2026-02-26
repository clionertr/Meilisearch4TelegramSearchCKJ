import { motion, useReducedMotion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import React, { PropsWithChildren, Suspense } from 'react';
import { PageSkeleton } from './PageSkeleton';

const variants = {
    enter: { opacity: 0, x: 20 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
};

export function PageTransition({ children }: PropsWithChildren) {
    const location = useLocation();
    const shouldReduceMotion = useReducedMotion();

    if (shouldReduceMotion) {
        return <Suspense fallback={<PageSkeleton />}>{children}</Suspense>;
    }

    return (
        <motion.div
            key={location.pathname}
            variants={variants}
            initial="enter" animate="center" exit="exit"
            transition={{ duration: 0.2 }}
            className="w-full min-h-screen"
        >
            <Suspense fallback={<PageSkeleton />}>
                {children}
            </Suspense>
        </motion.div>
    );
}
