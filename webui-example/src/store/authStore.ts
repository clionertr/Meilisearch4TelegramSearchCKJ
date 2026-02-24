import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UserInfo } from '@/api/auth';

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  isLoggedIn: boolean;
  setAuth: (token: string, user: UserInfo) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoggedIn: false,
      setAuth: (token, user) => {
        set({ token, user, isLoggedIn: true });
      },
      logout: () => {
        set({ token: null, user: null, isLoggedIn: false });
      },
    }),
    {
      name: 'telememory-auth',
      onRehydrateStorage: () => (state) => {
        if (state?.token) state.isLoggedIn = true;
      },
    }
  )
);
