import React from 'react';

export interface SkeletonProps {
    variant: 'text' | 'card' | 'avatar' | 'button';
    width?: string;
    height?: string;
    count?: number;
    className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ variant, width, height, count = 1, className = '' }) => {
    const baseClass = "animate-pulse bg-slate-200 dark:bg-slate-700/50";

    let variantClass = "";
    if (variant === 'text') variantClass = "rounded h-4 w-full";
    if (variant === 'card') variantClass = "rounded-2xl h-32 w-full";
    if (variant === 'avatar') variantClass = "rounded-full h-10 w-10 shrink-0";
    if (variant === 'button') variantClass = "rounded-xl h-10 w-24";

    const getStyle = () => {
        const style: React.CSSProperties = {};
        if (width) style.width = width;
        if (height) style.height = height;
        return style;
    };

    const elements = Array.from({ length: count }, (_, i) => (
        <div
            key={i}
            className={`${baseClass} ${variantClass} ${className}`}
            style={getStyle()}
            role={i === 0 ? "status" : undefined}
            aria-busy={i === 0 ? "true" : undefined}
        />
    ));

    if (count === 1) return <>{elements[0]}</>;

    return <div className="space-y-3 w-full" aria-busy="true">{elements}</div>;
};
