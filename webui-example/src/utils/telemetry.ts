const truthyValues = new Set(['1', 'true', 'yes', 'on']);

const isTruthy = (value: unknown): boolean => {
  if (typeof value !== 'string') {
    return false;
  }
  return truthyValues.has(value.toLowerCase());
};

const toPositiveNumber = (value: unknown, fallback: number): number => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const enabled = Boolean(import.meta.env.DEV) || isTruthy(import.meta.env.VITE_ENABLE_DEBUG_LOGS);
const slowApiWarnMs = toPositiveNumber(import.meta.env.VITE_SLOW_API_WARN_MS, 1200);

const pickLogger = (level: 'debug' | 'info' | 'warn' | 'error') => {
  if (level === 'error') return console.error;
  if (level === 'warn') return console.warn;
  if (level === 'info') return console.info;
  return console.debug;
};

const write = (level: 'debug' | 'info' | 'warn' | 'error', event: string, payload: Record<string, unknown>): void => {
  if (!enabled) {
    return;
  }
  pickLogger(level)(`[telemetry] ${event}`, payload);
};

export const telemetry = {
  enabled,
  slowApiWarnMs,
  apiStart(payload: Record<string, unknown>): void {
    write('debug', 'api.start', payload);
  },
  apiEnd(payload: Record<string, unknown>): void {
    const durationMs = typeof payload.duration_ms === 'number' ? payload.duration_ms : 0;
    const level = durationMs >= slowApiWarnMs ? 'warn' : 'info';
    write(level, 'api.end', payload);
  },
  apiError(payload: Record<string, unknown>): void {
    write('error', 'api.error', payload);
  },
  wsState(payload: Record<string, unknown>): void {
    write('info', 'ws.state', payload);
  },
  wsMessage(payload: Record<string, unknown>): void {
    write('debug', 'ws.message', payload);
  },
};
