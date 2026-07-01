import apiClient from '../lib/apiClient';
import type { SearchRequest, SearchResponse } from '../types/search';

export const searchApi = {
  executeSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    try {
      const response = await apiClient.post<SearchResponse>('/search', request);
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw new Error(error.response.data.detail || error.message);
      }
      throw error;
    }
  },
};
