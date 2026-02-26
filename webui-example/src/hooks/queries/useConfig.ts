import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { configApi } from '@/api/config';
import { extractApiErrorMessage } from '@/api/error';

export const useSystemConfig = () => {
  return useQuery({
    queryKey: ['systemConfig'],
    queryFn: async () => {
      try {
        const response = await configApi.getConfig();
        return response.data.data ?? null;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to load config'));
      }
    },
    staleTime: 1000 * 30,
  });
};

export const useAddToWhitelist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const response = await configApi.addToWhitelist(ids);
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to add to whitelist'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemConfig'] });
    },
  });
};

export const useRemoveFromWhitelist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const response = await configApi.removeFromWhitelist(ids);
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to remove from whitelist'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemConfig'] });
    },
  });
};

export const useAddToBlacklist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const response = await configApi.addToBlacklist(ids);
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to add to blacklist'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemConfig'] });
    },
  });
};

export const useRemoveFromBlacklist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const response = await configApi.removeFromBlacklist(ids);
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to remove from blacklist'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemConfig'] });
    },
  });
};
