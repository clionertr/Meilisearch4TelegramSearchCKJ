import React from 'react';
import { useTranslation } from 'react-i18next';
import { DashboardBriefData } from '@/api/dashboard';

interface BriefCardProps {
    brief: DashboardBriefData | null;
}

const BriefCard: React.FC<BriefCardProps> = ({ brief }) => {
    const { t } = useTranslation();

    if (!brief || !brief.summary) return null;

    return (
        <section className="px-4">
            <div className="p-4 rounded-2xl bg-primary/10 border border-primary/20">
                <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-primary mt-0.5">auto_awesome</span>
                    <div>
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">{t('dashboard.dailyBrief')}</p>
                        <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{brief.summary}</p>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default BriefCard;
