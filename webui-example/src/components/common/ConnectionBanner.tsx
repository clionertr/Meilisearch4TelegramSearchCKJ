/**
 * ConnectionBanner — global WebSocket connection status indicator.
 * Reads wsReadyState from the statusStore (updated once in AppContent)
 * to avoid creating a second WebSocket connection.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useStatusStore } from '@/store/statusStore';
import { motion, AnimatePresence } from 'framer-motion';

// ReadyState constants (mirrors react-use-websocket ReadyState enum)
const CONNECTING = 0;
const CLOSED = 3;

const ConnectionBanner: React.FC = () => {
    const { t } = useTranslation();
    const wsReadyState = useStatusStore((state) => state.wsReadyState);

    // -1 = not yet initialised (before first render), hide banner
    const isConnecting = wsReadyState === CONNECTING;
    const isDisconnected = wsReadyState === CLOSED;
    const showBanner = isConnecting || isDisconnected;

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
