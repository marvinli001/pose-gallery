import axios from 'axios';
import { SearchResponse, Category } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const searchAPI = {
  searchPoses: async (params: {
    q: string;
    category?: string;
    page?: number;
    per_page?: number;
  }): Promise<SearchResponse> => {
    const response = await api.get('/search', { params });
    return response.data;
  },

  getSuggestions: async (prefix: string): Promise<string[]> => {
    const response = await api.get('/search/suggestions', {
      params: { prefix, limit: 10 }
    });
    return response.data;
  },

  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/categories');
    return response.data;
  }
};
// 在现有的 api.ts 文件中添加新的接口和类型定义

export interface VectorSearchRequest {
  query: string;
  top_k?: number;
  search_mode?: 'multi_stage' | 'dynamic' | 'paginated' | 'multi_tier';
  min_similarity?: number;
  page?: number;
  page_size?: number;
  target_count?: number;
  use_enhanced?: boolean;
  category_filter?: string;
  angle_filter?: string;
}

export interface VectorSearchResponse {
  poses: Array<{
    id: number;
    oss_url: string;
    thumbnail_url?: string;
    title?: string;
    description?: string;
    scene_category?: string;
    angle?: string;
    shooting_tips?: string;
    ai_tags?: string;
    view_count?: number;
    created_at?: string;
    score: number;
  }>;
  total: number;
  query_time_ms: number;
  service_available: boolean;
  error?: string;
  message?: string;
  search_info?: Record<string, unknown>; // 修复：使用 unknown 替代 any
}

// 新增分页搜索函数
export const searchVectorPaginated = async (params: VectorSearchRequest): Promise<VectorSearchResponse> => {
  const response = await fetch('/api/search/vector/paginated', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  
  if (!response.ok) {
    throw new Error(`搜索失败: ${response.statusText}`);
  }
  
  return response.json();
};

// 更新现有的向量搜索函数以支持新参数
export const searchVectorEnhanced = async (params: VectorSearchRequest): Promise<VectorSearchResponse> => {
  const response = await fetch('/api/search/vector/enhanced', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  
  if (!response.ok) {
    throw new Error(`搜索失败: ${response.statusText}`);
  }
  
  return response.json();
};

// 新增向量搜索服务状态检查
export const checkVectorSearchStatus = async (): Promise<{
  available: boolean;
  message: string;
  version?: string;
}> => {
  try {
    const response = await fetch('/api/search/vector', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        query: 'test', 
        top_k: 1,
        min_similarity: 0.1 
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      return {
        available: data.service_available || false,
        message: data.service_available ? '向量搜索服务正常' : '向量搜索服务不可用',
        version: data.version
      };
    } else {
      return {
        available: false,
        message: `服务检查失败: ${response.statusText}`
      };
    }
  } catch (error) {
    return {
      available: false,
      message: `服务连接失败: ${error instanceof Error ? error.message : '未知错误'}`
    };
  }
};