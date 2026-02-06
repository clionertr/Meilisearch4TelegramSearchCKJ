import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, SendCodeRequest, SignInRequest } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export const useSendCode = () => {
  return useMutation({
    mutationFn: (data: SendCodeRequest) => authApi.sendCode(data).then(res => res.data.data),
  });
};

export const useSignIn = () => {
  const setAuth = useAuthStore((state) => state.setAuth);
  return useMutation({
    mutationFn: (data: SignInRequest) => authApi.signIn(data).then(res => res.data.data),
    onSuccess: (data) => {
      setAuth(data.token, data.user);
    },
  });
};

export const useMe = () => {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.me().then(res => res.data.data),
    retry: false,
  });
};

export const useLogout = () => {
  const clearAuth = useAuthStore((state) => state.logout);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      clearAuth();
      queryClient.clear();
    },
  });
};
