import axios from 'axios';
import type { SearchRequest, SearchResponse } from '../types/search';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const searchApi = {
  executeSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    try {
      const response = await axios.post<SearchResponse>(`${API_URL}/api/v1/search`, request);
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw new Error(error.response.data.detail || error.message);
      }
      throw error;
    }
  }
};
