import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { controlApi } from '@/api/control';
import { extractApiErrorMessage } from '@/api/error';

export const useClientStatus = () => {
  return useQuery({
    queryKey: ['clientStatus'],
    queryFn: async () => {
      try {
        const response = await controlApi.getStatus();
        return response.data.data ?? null;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to load client status'));
      }
    },
    staleTime: 1000 * 5,
    refetchInterval: 1000 * 10,
  });
};

export const useStartClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      try {
        const response = await controlApi.startClient();
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to start client'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientStatus'] });
      queryClient.invalidateQueries({ queryKey: ['systemStatus'] });
    },
  });
};

export const useStopClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      try {
        const response = await controlApi.stopClient();
        return response.data.data;
      } catch (err) {
        throw new Error(extractApiErrorMessage(err, 'Failed to stop client'));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientStatus'] });
      queryClient.invalidateQueries({ queryKey: ['systemStatus'] });
    },
  });
};
