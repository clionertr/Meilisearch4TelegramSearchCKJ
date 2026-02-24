import axios from 'axios';

interface ErrorResponseData {
  message?: unknown;
  detail?: unknown;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const pickMessage = (value: unknown): string | null => {
  if (typeof value === 'string' && value.trim().length > 0) {
    return value;
  }

  if (isRecord(value) && typeof value.message === 'string' && value.message.trim().length > 0) {
    return value.message;
  }

  return null;
};

export const extractApiErrorDetail = (error: unknown): string | null => {
  if (!axios.isAxiosError(error)) {
    return null;
  }

  const data = error.response?.data as ErrorResponseData | undefined;
  const detailMessage = pickMessage(data?.detail);
  return detailMessage;
};

export const extractApiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) {
    if (error instanceof Error && error.message.trim().length > 0) {
      return error.message;
    }
    return fallback;
  }

  const data = error.response?.data as ErrorResponseData | undefined;
  const message =
    pickMessage(data?.message) ??
    pickMessage(data?.detail) ??
    (typeof error.message === 'string' && error.message.trim().length > 0 ? error.message : null);

  return message ?? fallback;
};
