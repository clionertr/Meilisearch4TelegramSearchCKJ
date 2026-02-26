/**
 * SyncProgress — WebSocket 同步进度展示
 * 消费 useStatusStore.tasks，展示当前下载的聊天和进度条
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useStatusStore } from '@/store/statusStore';

const SyncProgress: React.FC = () => {
    const { t } = useTranslation();
    const tasks = useStatusStore((s) => s.tasks);
    const overallStatus = useStatusStore((s) => s.overallStatus);

    const activeTasks = Object.values(tasks).filter(
        (t) => t.status === 'downloading' || t.status === 'pending'
    );

    if (overallStatus === 'idle' || activeTasks.length === 0) {
        return null;
    }

    return (
        <section className="px-4" aria-live="polite">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                {t('dashboard.syncProgress')}
            </h2>
            <div className="space-y-3">
                {activeTasks.map((task) => (
                    <div
                        key={task.dialog_id}
                        className="p-3 rounded-xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 shadow-sm"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className="material-symbols-outlined text-primary text-base animate-spin" style={{ animationDuration: '2s' }}>
                                    sync
                                </span>
                                <p className="text-sm font-semibold dark:text-white truncate max-w-[180px]">
                                    {task.dialog_title || t('search.chatFallback', { id: task.dialog_id })}
                                </p>
                            </div>
                            <span className="text-xs font-bold text-primary">{task.percentage}%</span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                            <div
                                className="bg-primary h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${task.percentage}%` }}
                            />
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                            {t('dashboard.progressMessages', {
                                current: task.current.toLocaleString(),
                                total: task.total.toLocaleString(),
                            })}
                        </p>
                    </div>
                ))}
            </div>
        </section>
    );
};

export default SyncProgress;
