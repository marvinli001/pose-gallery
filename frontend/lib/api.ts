import axios from 'axios';
import { SearchResponse, Category } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const searchAPI = {
  // 搜索姿势
  searchPoses: async (params: {
    q: string;
    category?: string;
    page?: number;
    per_page?: number;
  }): Promise<SearchResponse> => {
    const response = await api.get('/search', { params });
    return response.data;
  },

  // 获取搜索建议
  getSuggestions: async (prefix: string): Promise<string[]> => {
    const response = await api.get('/search/suggestions', {
      params: { prefix, limit: 10 }
    });
    return response.data;
  },

  // 获取分类
  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/categories');
    return response.data;
  }
};
