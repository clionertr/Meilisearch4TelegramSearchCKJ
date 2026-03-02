/**
 * ConnectionBanner — global WebSocket connection status indicator.
 * Displays a subtle banner when the WebSocket connection is disconnected.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useStatusWebSocket } from '@/hooks/useWebSocket';
import { ReadyState } from 'react-use-websocket';
import { motion, AnimatePresence } from 'framer-motion';

const ConnectionBanner: React.FC = () => {
    const { t } = useTranslation();
    const { connectionStatus } = useStatusWebSocket();

    const isDisconnected = connectionStatus === ReadyState.CLOSED || connectionStatus === ReadyState.CLOSING;
    const isConnecting = connectionStatus === ReadyState.CONNECTING;

    const showBanner = isDisconnected || isConnecting;

    return (
        <AnimatePresence>
            {showBanner && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                >
                    <div
                        className={`flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium ${isConnecting
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                            }`}
                        role="status"
                        aria-live="polite"
                    >
                        {isConnecting ? (
                            <>
                                <span className="material-symbols-outlined text-[16px] animate-spin" aria-hidden="true">sync</span>
                                <span>{t('connection.reconnecting')}</span>
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-[16px]" aria-hidden="true">cloud_off</span>
                                <span>{t('connection.disconnected')}</span>
                            </>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default ConnectionBanner;
