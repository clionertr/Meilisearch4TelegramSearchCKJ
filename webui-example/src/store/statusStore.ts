import { create } from 'zustand';

export interface ProgressEvent {
  task_id: number;
  status: string;
  progress: number;
  message?: string;
}

interface StatusState {
  tasks: Record<number, ProgressEvent>;
  overallStatus: 'idle' | 'syncing' | 'error';
  updateTask: (event: ProgressEvent) => void;
  setOverallStatus: (status: 'idle' | 'syncing' | 'error') => void;
}

export const useStatusStore = create<StatusState>((set) => ({
  tasks: {},
  overallStatus: 'idle',
  updateTask: (event) => set((state) => ({
    tasks: { ...state.tasks, [event.task_id]: event }
  })),
  setOverallStatus: (status) => set({ overallStatus: status }),
}));
