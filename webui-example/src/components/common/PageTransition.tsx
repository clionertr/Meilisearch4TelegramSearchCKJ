import { motion, useReducedMotion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import React, { PropsWithChildren } from 'react';

const variants = {
    enter: { opacity: 0, x: 20 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
};

export function PageTransition({ children }: PropsWithChildren) {
    const location = useLocation();
    const shouldReduceMotion = useReducedMotion();

    if (shouldReduceMotion) {
        return <>{children}</>;
    }

    return (
        <motion.div
            key={location.pathname}
            variants={variants}
            initial="enter" animate="center" exit="exit"
            transition={{ duration: 0.2 }}
            className="w-full min-h-screen"
        >
            {children}
        </motion.div>
    );
}
