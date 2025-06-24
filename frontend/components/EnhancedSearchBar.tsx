'use client';

import React, { useState, useEffect, useRef } from 'react';

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
  title: string;
  description: string;
  scene_category: string;
  angle: string;
  ai_tags: string;
  view_count: number;
  created_at: string;
  ai_relevance_explanation?: string;
  shooting_tips?: string;
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
  const [isAiDatabaseLoading, setIsAiDatabaseLoading] = useState(false);
  const [isVectorLoading, setIsVectorLoading] = useState(false);
  const [useVectorSearch, setUseVectorSearch] = useState(false);
  
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

  // AI数据库搜索功能
  const handleAiDatabaseSearch = async () => {
    if (!query.trim()) {
      if (onResetSearch) {
        onResetSearch();
      }
      return;
    }

    setIsAiDatabaseLoading(true);
    setShowSuggestions(false);
    
    try {
      console.log('开始AI数据库搜索:', query);
      
      const response = await fetch('/api/search/ai-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: query.trim(),
          max_results: 20 
        })
      });
        
      if (response.ok) {
        const data = await response.json();
        console.log('AI数据库搜索响应:', data);
        
        setSearchInfo({
          original_query: query,
          ai_explanation: data.ai_explanation || '使用AI分析找到最相关的拍照姿势',
          search_intent: data.search_intent?.intent_type || '智能匹配',
          query_time: data.query_time_ms,
          expanded_queries: [],
          suggestions: []
        });
          
        if (data.poses && Array.isArray(data.poses) && data.poses.length > 0) {
          console.log('调用AI搜索结果回调，姿势数量:', data.poses.length);
          if (onAISearchResult) {
            onAISearchResult(data.poses);
          } else {
            console.warn('onAISearchResult回调未定义，执行普通搜索');
            onSearch(query);
          }
        } else {
          console.warn('AI搜索结果为空，执行普通搜索');
          const fallbackQuery = data.suggested_query || data.corrected_query || query;
          setQuery(fallbackQuery);
          onSearch(fallbackQuery);
        }
      } else {
        const errorText = await response.text();
        console.error('AI数据库搜索API响应错误:', response.status, errorText);
        onSearch(query);
      }
    } catch (error) {
      console.error('AI数据库搜索失败:', error);
      onSearch(query);
    } finally {
      setIsAiDatabaseLoading(false);
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
      console.log('开始向量搜索:', query);
      
      // 首先检查向量搜索服务状态
      const statusResponse = await fetch('/api/search/vector/status');
      let serviceAvailable = true;
      
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        serviceAvailable = statusData.available;
        console.log('向量搜索服务状态:', statusData);
      }
      
      if (!serviceAvailable) {
        console.warn('向量搜索服务不可用，回退到普通搜索');
        setSearchInfo({
          original_query: query,
          ai_explanation: '向量搜索服务暂时不可用，已为您执行普通搜索',
          search_intent: '服务降级',
          query_time: 0,
          expanded_queries: [],
          suggestions: [],
        });
        onSearch(query);
        return;
      }
      
      const response = await fetch('/api/search/vector', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          top_k: 20,
          use_adaptive: true,  // 使用自适应搜索
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('向量搜索响应:', data);

        // 构建搜索信息，包含质量指标
        let explanation = '使用向量相似度匹配找到最相关的姿势';
        
        if (data.search_info) {
          const info = data.search_info;
          explanation += `\n找到 ${info.found_results} 个结果`;
          
          if (info.avg_similarity) {
            explanation += `，平均相似度: ${info.avg_similarity}`;
          }
          
          if (info.quality_warning) {
            explanation += `\n⚠️ ${info.quality_warning}`;
          }
          
          if (info.similarity_range) {
            explanation += `\n相似度范围: ${info.similarity_range}`;
          }
        }

        setSearchInfo({
          original_query: query,
          ai_explanation: data.service_available 
            ? explanation
            : '向量搜索服务不可用，已为您执行普通搜索',
          search_intent: data.service_available ? '向量匹配' : '服务降级',
          query_time: data.query_time_ms,
          expanded_queries: [],
          suggestions: [],
        });

        if (data.poses && Array.isArray(data.poses) && data.poses.length > 0) {
          if (onAISearchResult) {
            onAISearchResult(data.poses);
          } else {
            onSearch(query);
          }
        } else {
          console.log('向量搜索无结果，执行普通搜索');
          onSearch(query);
        }
      } else {
        const errorText = await response.text();
        console.error('向量搜索API响应错误:', response.status, errorText);
        onSearch(query);
      }
    } catch (error) {
      console.error('向量搜索失败:', error);
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
          disabled={isLoading || isAiDatabaseLoading}
        />
        
        {/* AI数据库/向量 搜索按钮 */}
        <button
          type="button"
          onClick={() => {
            if (useVectorSearch) {
              handleVectorSearch();
            } else {
              handleAiDatabaseSearch();
            }
          }}
          disabled={isLoading || isAiDatabaseLoading || isVectorLoading}
          className="absolute right-12 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-purple-600 disabled:opacity-50 transition-colors flex items-center justify-center w-8 h-8"
          title="AI智能搜索"
        >
          {isAiDatabaseLoading || isVectorLoading ? (
            <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <span className="text-lg">✨</span>
          )}
        </button>

        {/* 普通搜索按钮 */}
        <button
          type="submit"
          disabled={isLoading || isAiDatabaseLoading || isVectorLoading}
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
      <div className="flex items-center mt-2 text-sm">
        <input
          id="vector-toggle"
          type="checkbox"
          className="mr-2"
          checked={useVectorSearch}
          onChange={(e) => setUseVectorSearch(e.target.checked)}
        />
        <label htmlFor="vector-toggle">使用向量搜索</label>
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
