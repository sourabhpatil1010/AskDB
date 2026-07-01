import apiClient from '../lib/apiClient';
import type { SearchHistory } from '../types/history';

export const historyApi = {
  getAll: async (): Promise<{ success: boolean; data: SearchHistory[] }> => {
    const res = await apiClient.get('/history');
    return res.data;
  },
  getOne: async (id: string): Promise<{ success: boolean; data: SearchHistory }> => {
    const res = await apiClient.get(`/history/${id}`);
    return res.data;
  },
  deleteAll: async (): Promise<{ success: boolean }> => {
    const res = await apiClient.delete('/history');
    return res.data;
  },
  deleteOne: async (id: string): Promise<{ success: boolean }> => {
    const res = await apiClient.delete(`/history/${id}`);
    return res.data;
  },
};
