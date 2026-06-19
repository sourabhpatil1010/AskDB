import axios from 'axios';
import type { SearchHistory } from '../types/history';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const historyApi = {
  getAll: async (): Promise<{success: boolean, data: SearchHistory[]}> => {
    const res = await axios.get(`${API_URL}/api/v1/history`);
    return res.data;
  },
  getOne: async (id: string): Promise<{success: boolean, data: SearchHistory}> => {
    const res = await axios.get(`${API_URL}/api/v1/history/${id}`);
    return res.data;
  },
  deleteAll: async (): Promise<{success: boolean}> => {
    const res = await axios.delete(`${API_URL}/api/v1/history`);
    return res.data;
  },
  deleteOne: async (id: string): Promise<{success: boolean}> => {
    const res = await axios.delete(`${API_URL}/api/v1/history/${id}`);
    return res.data;
  }
};
