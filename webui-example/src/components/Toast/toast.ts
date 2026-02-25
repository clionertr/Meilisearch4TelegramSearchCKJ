/**
 * 统一 Toast 通知入口
 * 封装 react-hot-toast，提供 success / error / warning / info 四种变体
 */
import { toast as hotToast } from 'react-hot-toast';

const DURATION = 3000;

const toast = {
    success: (message: string) =>
        hotToast.success(message, { duration: DURATION }),

    error: (message: string) =>
        hotToast.error(message, { duration: DURATION }),

    warning: (message: string) =>
        hotToast(message, {
            duration: DURATION,
            icon: '⚠️',
        }),

    info: (message: string) =>
        hotToast(message, {
            duration: DURATION,
            icon: 'ℹ️',
        }),
};

export default toast;
