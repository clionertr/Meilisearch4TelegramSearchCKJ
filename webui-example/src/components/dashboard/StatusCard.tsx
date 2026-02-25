/**
 * StatusCard — Dashboard KPI 状态卡片
 * 展示 3 个 KPI：MeiliSearch 连接状态、总索引消息数、已同步聊天数
 */
import React from 'react';
import { useSystemStatus } from '@/hooks/queries/useStatus';
import { useSyncedDialogsCount } from '@/hooks/queries/useDashboardStatus';
import { useSearchStats } from '@/hooks/queries/useDashboardStatus';

interface KpiCardProps {
    label: string;
    value: React.ReactNode;
    icon: string;
    iconColor?: string;
    isLoading?: boolean;
    isError?: boolean;
}

const KpiCard: React.FC<KpiCardProps> = ({ label, value, icon, iconColor = 'text-primary', isLoading, isError }) => (
    <div className="flex flex-col gap-2 p-4 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm">
        <div className="flex items-center justify-between">
            <span className={`material-symbols-outlined text-2xl ${iconColor}`}>{icon}</span>
        </div>
        <div>
            {isLoading ? (
                <div className="h-6 w-16 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            ) : isError ? (
                <p className="text-sm font-bold text-red-500">—</p>
            ) : (
                <p className="text-lg font-bold dark:text-white">{value}</p>
            )}
            <p className="text-xs text-slate-500 dark:text-muted-dark mt-0.5">{label}</p>
        </div>
    </div>
);

const StatusCard: React.FC = () => {
    const { data: status, isLoading: statusLoading, isError: statusError } = useSystemStatus();
    const { data: totalMessages, isLoading: statsLoading, isError: statsError } = useSearchStats();
    const { data: syncedCount, isLoading: dialogsLoading, isError: dialogsError } = useSyncedDialogsCount();

    return (
        <section className="px-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                System Status
            </h2>
            <div className="grid grid-cols-3 gap-3">
                <KpiCard
                    label="MeiliSearch"
                    icon={status?.meili_connected ? 'cloud_done' : 'cloud_off'}
                    iconColor={
                        statusLoading ? 'text-slate-400' :
                            statusError ? 'text-red-500' :
                                status?.meili_connected ? 'text-green-500' : 'text-red-500'
                    }
                    value={status?.meili_connected ? 'Online' : 'Offline'}
                    isLoading={statusLoading}
                    isError={statusError}
                />
                <KpiCard
                    label="Indexed Messages"
                    icon="database"
                    value={(totalMessages ?? 0).toLocaleString()}
                    isLoading={statsLoading}
                    isError={statsError}
                />
                <KpiCard
                    label="Synced Chats"
                    icon="sync"
                    value={syncedCount ?? 0}
                    isLoading={dialogsLoading}
                    isError={dialogsError}
                />
            </div>
        </section>
    );
};

export default StatusCard;
