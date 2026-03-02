import { create } from 'zustand';

export interface ProgressData {
  dialog_id: number;
  dialog_title: string;
  current: number;
  total: number;
  percentage: number;
  status: string;
  started_at?: string;
  updated_at?: string;
  error?: string;
}

interface StatusState {
  tasks: Record<number, ProgressData>;
  overallStatus: 'idle' | 'syncing' | 'error';
  wsReadyState: number; // ReadyState: 0=CONNECTING 1=OPEN 2=CLOSING 3=CLOSED -1=UNINSTANTIATED
  updateTask: (event: ProgressData) => void;
  setOverallStatus: (status: 'idle' | 'syncing' | 'error') => void;
  setWsReadyState: (state: number) => void;
}

export const useStatusStore = create<StatusState>((set) => ({
  tasks: {},
  overallStatus: 'idle',
  wsReadyState: -1,
  updateTask: (event) => set((state) => ({
    tasks: { ...state.tasks, [event.dialog_id]: event },
    overallStatus: event.status === 'failed'
      ? 'error'
      : event.status === 'downloading'
        ? 'syncing'
        : state.overallStatus,
  })),
  setOverallStatus: (status) => set({ overallStatus: status }),
  setWsReadyState: (wsReadyState) => set({ wsReadyState }),
}));

