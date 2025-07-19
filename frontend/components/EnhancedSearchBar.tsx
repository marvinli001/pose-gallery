'use client';

import React, { useState, useEffect, useRef } from 'react';
import { searchVectorPaginated, searchVectorEnhanced, checkVectorSearchStatus } from '@/lib/api';

interface SearchSuggestion {
  text: string;
  type: 'history' | 'tag' | 'synonym';
  weight: number;
}

interface SearchInfo {
  original_query: string;
  ai_explanation?: string;
  search_intent?: string;
  query_time?: number;
  expanded_queries: string[];
  suggestions: string[];
}

// 定义AI搜索结果类型
interface AIPoseResult {
  id: number;
  oss_url: string;
  thumbnail_url?: string;
  title?: string;
  description?: string;
  scene_category?: string;
  angle?: string;
  ai_tags?: string;
  view_count?: number;
  created_at?: string;
  ai_relevance_explanation?: string;
  shooting_tips?: string;
  score?: number;
}


interface Props {
  onSearch: (query: string) => void;
  onAISearchResult?: (poses: AIPoseResult[]) => void;
  onResetSearch?: () => void;
  initialValue?: string;
  showSearchInfo?: boolean;
}

const EnhancedSearchBar: React.FC<Props> = ({ 
  onSearch, 
  onAISearchResult,
  onResetSearch,
  initialValue = '', 
  showSearchInfo = false 
}) => {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [searchInfo, setSearchInfo] = useState<SearchInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVectorLoading, setIsVectorLoading] = useState(false);
  const [vectorSearchMode, setVectorSearchMode] = useState<'paginated' | 'dynamic'>('dynamic');
  const [vectorServiceStatus, setVectorServiceStatus] = useState<{
    available: boolean;
    message: string;
    lastChecked?: Date;
  }>({
    available: true,
    message: '未检查'
  });
  
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // 简化建议功能 - 使用本地建议而不是API调用
  const getLocalSuggestions = (prefix: string): SearchSuggestion[] => {
    const commonSuggestions = [
      { text: '俏皮可爱', type: 'tag' as const, weight: 0.9 },
      { text: '咖啡厅拍照', type: 'tag' as const, weight: 0.8 },
      { text: '坐姿写真', type: 'tag' as const, weight: 0.7 },
      { text: '户外人像', type: 'tag' as const, weight: 0.8 },
      { text: '情侣拍照', type: 'tag' as const, weight: 0.9 },
      { text: '街头摄影', type: 'tag' as const, weight: 0.7 },
      { text: '室内写真', type: 'tag' as const, weight: 0.8 },
      { text: '商务形象', type: 'tag' as const, weight: 0.6 },
    ];

    return commonSuggestions
      .filter(s => s.text.includes(prefix))
      .slice(0, 5);
  };

  // 检查向量搜索服务状态
  const checkServiceStatus = async () => {
    try {
      console.log('检查向量搜索服务状态...');
      const status = await checkVectorSearchStatus();
      console.log('向量搜索服务状态:', status);
      
      setVectorServiceStatus({
        available: status.available,
        message: status.message,
        lastChecked: new Date()
      });
      
      return status;
    } catch (error) {
      console.error('服务状态检查失败:', error);
      setVectorServiceStatus({
        available: false,
        message: '状态检查失败',
        lastChecked: new Date()
      });
      return { available: false, message: '状态检查失败' };
    }
  };

  // 当输入变化时显示建议
  useEffect(() => {
    if (query && query.length > 0) {
      const localSuggestions = getLocalSuggestions(query);
      setSuggestions(localSuggestions);
    } else {
      setSuggestions([]);
    }
  }, [query]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    setSearchInfo(null);
    
    if (!query.trim()) {
      if (onResetSearch) {
        onResetSearch();
      }
      return;
    }

    setIsLoading(true);
    
    try {
      onSearch(query);
    } catch (error) {
      console.error('搜索失败:', error);
      onSearch(query);
    } finally {
      setIsLoading(false);
    }
  };

  // 分页向量搜索函数
  const handlePaginatedSearch = async (query: string) => {
    try {
      console.log('开始分页向量搜索:', { query, timestamp: new Date().toISOString() });
      
      const result = await searchVectorPaginated({
        query,
        search_mode: 'paginated',
        page_size: 20,
        min_similarity: 0.3
      });

      console.log('分页向量搜索结果:', {
        service_available: result.service_available,
        poses_count: result.poses?.length || 0,
        total: result.total,
        query_time_ms: result.query_time_ms,
        search_info: result.search_info
      });

      setSearchInfo({
        original_query: query,
        ai_explanation: result.service_available 
          ? `使用向量相似度匹配找到最相关的姿势\n找到 ${result.search_info?.found_results || result.poses?.length || 0} 个结果`
          : `向量搜索服务不可用，已为您执行普通搜索\n错误信息: ${result.error || '服务连接失败'}`,
        search_intent: result.service_available ? '向量匹配' : '服务降级',
        query_time: result.query_time_ms,
        expanded_queries: [],
        suggestions: []
      });

      return result;
    } catch (error) {
      console.error('分页向量搜索失败:', {
        error: error instanceof Error ? error.message : String(error),
        query,
        timestamp: new Date().toISOString()
      });
      throw error;
    }
  };

  // 动态向量搜索函数  
  const handleDynamicSearch = async (query: string) => {
    try {
      console.log('开始动态向量搜索:', { query, timestamp: new Date().toISOString() });
      
      const result = await searchVectorEnhanced({
        query,
        search_mode: 'dynamic',
        target_count: 30,
        min_similarity: 0.3
      });

      console.log('动态向量搜索结果:', {
        service_available: result.service_available,
        poses_count: result.poses?.length || 0,
        total: result.total,
        query_time_ms: result.query_time_ms,
        search_info: result.search_info
      });

      setSearchInfo({
        original_query: query,
        ai_explanation: result.service_available
          ? `使用向量相似度匹配找到最相关的姿势\n找到 ${result.search_info?.found_results || result.poses?.length || 0} 个结果`
          : `向量搜索服务不可用，已为您执行普通搜索\n错误信息: ${result.error || '服务连接失败'}`,
        search_intent: result.service_available ? '向量匹配' : '服务降级',
        query_time: result.query_time_ms,
        expanded_queries: [],
        suggestions: []
      });

      return result;
    } catch (error) {
      console.error('动态向量搜索失败:', {
        error: error instanceof Error ? error.message : String(error),
        query,
        timestamp: new Date().toISOString()
      });
      throw error;
    }
  };

  const handleVectorSearch = async () => {
    if (!query.trim()) {
      if (onResetSearch) {
        onResetSearch();
      }
      return;
    }

    setIsVectorLoading(true);
    setShowSuggestions(false);

    try {
      console.log('开始向量搜索:', { 
        query: query.trim(), 
        mode: vectorSearchMode, 
        timestamp: new Date().toISOString() 
      });
      
      // 先检查服务状态
      const serviceStatus = await checkServiceStatus();
      
      if (!serviceStatus.available) {
        console.log('向量搜索服务不可用，直接执行普通搜索');
        setSearchInfo({
          original_query: query.trim(),
          ai_explanation: `向量搜索服务不可用: ${serviceStatus.message}`,
          search_intent: '服务不可用，已回退到普通搜索',
          query_time: 0,
          expanded_queries: [],
          suggestions: []
        });
        onSearch(query);
        return;
      }
      
      // 根据选择的模式调用不同的API
      const data = vectorSearchMode === 'paginated' 
        ? await handlePaginatedSearch(query.trim())
        : await handleDynamicSearch(query.trim());

      console.log('向量搜索完成:', {
        service_available: data.service_available,
        poses_found: data.poses?.length || 0,
        has_results: data.poses && Array.isArray(data.poses) && data.poses.length > 0
      });

      if (data.poses && Array.isArray(data.poses) && data.poses.length > 0) {
        console.log('向量搜索成功，返回结果给父组件');
        if (onAISearchResult) {
          onAISearchResult(data.poses);
        } else {
          onSearch(query);
        }
      } else {
        console.log('向量搜索无结果，执行普通搜索:', {
          service_available: data.service_available,
          error: data.error
        });
        onSearch(query);
      }
    } catch (error) {
      console.error('向量搜索失败，回退到普通搜索:', {
        error: error instanceof Error ? error.message : String(error),
        query: query.trim(),
        mode: vectorSearchMode,
        timestamp: new Date().toISOString()
      });
      
      // 设置错误信息显示
      setSearchInfo({
        original_query: query.trim(),
        ai_explanation: `向量搜索失败: ${error instanceof Error ? error.message : String(error)}`,
        search_intent: '搜索失败，已回退到普通搜索',
        query_time: 0,
        expanded_queries: [],
        suggestions: []
      });
      
      onSearch(query);
    } finally {
      setIsVectorLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          const selected = suggestions[selectedIndex];
          setQuery(selected.text);
          onSearch(selected.text);
          setShowSuggestions(false);
        } else {
          handleSubmit(e);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    setQuery(suggestion.text);
    onSearch(suggestion.text);
    setShowSuggestions(false);
  };

  const getSuggestionIcon = (type: string) => {
    switch (type) {
      case 'history': return '🕒';
      case 'tag': return '🏷️';
      case 'synonym': return '💡';
      default: return '🔍';
    }
  };

  const getSuggestionTypeText = (type: string) => {
    switch (type) {
      case 'history': return '历史搜索';
      case 'tag': return '相关标签';
      case 'synonym': return '相关词汇';
      default: return '';
    }
  };

  // 点击外部关闭建议
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

return (
  <div className="relative w-full max-w-2xl mx-auto">
    <form onSubmit={handleSubmit}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowSuggestions(true);
            setSelectedIndex(-1);
          }}
          onFocus={() => setShowSuggestions(true)}
          onKeyDown={handleKeyDown}
          placeholder="智能搜索：「俏皮可爱」「咖啡厅拍照」「坐姿写真」..."
          className="w-full px-4 py-3 pr-20 text-gray-900 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
          disabled={isLoading}
        />
        
        {/* AI数据库/向量 搜索按钮 */}
        <button
          type="button"
          onClick={handleVectorSearch}
          disabled={isLoading || isVectorLoading}
          className="absolute right-12 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-purple-600 disabled:opacity-50 transition-colors flex items-center justify-center w-8 h-8"
          title="AI向量搜索"
        >
          {isVectorLoading ? (
            <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <span className="text-lg">✨</span>
          )}
        </button>

        {/* 普通搜索按钮 */}
        <button
          type="submit"
          disabled={isLoading || isVectorLoading}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-blue-600 disabled:opacity-50 transition-colors flex items-center justify-center w-8 h-8"
          title="普通搜索"
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </button>
      </div>
    </form>

    

      {/* 搜索建议下拉框 */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
        >
          {suggestions.map((suggestion, index) => (
            <div
              key={`${suggestion.type}-${suggestion.text}`}
              className={`flex items-center px-4 py-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                index === selectedIndex ? 'bg-blue-50' : ''
              }`}
              onClick={() => handleSuggestionClick(suggestion)}
            >
              <span className="text-lg mr-3">{getSuggestionIcon(suggestion.type)}</span>
              <div className="flex-1">
                <div className="text-gray-900">{suggestion.text}</div>
                <div className="text-xs text-gray-500">{getSuggestionTypeText(suggestion.type)}</div>
              </div>
              <div className="text-xs text-gray-400">
                权重: {suggestion.weight}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 向量搜索模式选择和服务状态 */}
      <div className="flex items-center justify-between mt-2 text-sm">
        <div className="flex items-center">
          <span className="mr-2 text-gray-600">向量搜索模式:</span>
          <select
            value={vectorSearchMode}
            onChange={(e) => setVectorSearchMode(e.target.value as 'paginated' | 'dynamic')}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="dynamic">动态搜索</option>
            <option value="paginated">分页搜索</option>
          </select>
        </div>
        
        <div className="flex items-center">
          <span className="mr-2 text-gray-600">服务状态:</span>
          <div className={`flex items-center text-xs px-2 py-1 rounded ${
            vectorServiceStatus.available 
              ? 'bg-green-100 text-green-700' 
              : 'bg-red-100 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full mr-1 ${
              vectorServiceStatus.available ? 'bg-green-500' : 'bg-red-500'
            }`}></span>
            {vectorServiceStatus.message}
          </div>
          <button
            onClick={checkServiceStatus}
            className="ml-2 text-blue-600 hover:text-blue-800 text-xs"
            title="刷新状态"
          >
            🔄
          </button>
        </div>
      </div>

      {/* 搜索信息展示 */}
      {showSearchInfo && searchInfo && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
          {searchInfo.ai_explanation && (
            <div className="text-green-600 mb-2">
              🤖 AI解释：{searchInfo.ai_explanation}
            </div>
          )}
          {searchInfo.search_intent && (
            <div className="text-purple-600 mb-2">
              🎯 搜索意图：{searchInfo.search_intent}
            </div>
          )}
          {searchInfo.query_time && (
            <div className="text-gray-500">
              ⏱️ 查询时间：{searchInfo.query_time}ms
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EnhancedSearchBar;