/**
 * 统一 Toast 通知入口
 * 封装 react-hot-toast，提供 success / error / warning / info 四种变体
 */
import { toast as hotToast } from 'react-hot-toast';

const DURATION = 3000;
const ariaProps = {
    role: 'status',
    'aria-live': 'polite' as const,
};

const toast = {
    success: (message: string) =>
        hotToast.success(message, { duration: DURATION, ariaProps }),

    error: (message: string) =>
        hotToast.error(message, { duration: DURATION, ariaProps }),

    warning: (message: string) =>
        hotToast(message, {
            duration: DURATION,
            icon: '!',
            ariaProps,
        }),

    info: (message: string) =>
        hotToast(message, {
            duration: DURATION,
            icon: 'i',
            ariaProps,
        }),
};

export default toast;
