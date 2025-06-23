'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useDebounce } from '@/hooks/useDebounce';

interface SearchSuggestion {
  text: string;
  type: 'history' | 'tag' | 'synonym';
  weight: number;
}

interface SearchInfo {
  original_query: string;
  corrected_query?: string;
  expanded_queries: string[];
  suggestions: string[];
  ai_explanation?: string;
  search_intent?: string;
  query_time?: number;
}

interface Props {
  onSearch: (query: string) => void;
  onAISearchResult?: (poses: any[]) => void;  // 新增AI搜索结果回调
  initialValue?: string;
  showSearchInfo?: boolean;
}

const EnhancedSearchBar: React.FC<Props> = ({ 
  onSearch, 
  onAISearchResult,  // 新增参数
  initialValue = '', 
  showSearchInfo = false 
}) => {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [searchInfo, setSearchInfo] = useState<SearchInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  const debouncedQuery = useDebounce(query, 300);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // 获取智能搜索建议
  useEffect(() => {
    if (debouncedQuery && debouncedQuery.length > 0) {
      fetchSuggestions(debouncedQuery);
    } else {
      setSuggestions([]);
    }
  }, [debouncedQuery]);

  const fetchSuggestions = async (prefix: string) => {
    try {
      const response = await fetch(
        `/api/search/v2/suggestions?prefix=${encodeURIComponent(prefix)}&limit=8`
      );
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data);
      }
    } catch (error) {
      console.error('获取搜索建议失败:', error);
      setSuggestions([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setShowSuggestions(false);
    
    try {
      // 调用增强搜索 API
      const response = await fetch(
        `/api/search/v2/search?q=${encodeURIComponent(query)}&enable_fuzzy=true`
      );
      
      if (response.ok) {
        const data = await response.json();
        setSearchInfo(data.search_info);
        onSearch(query);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      onSearch(query);
    } finally {
      setIsLoading(false);
    }
  };

  // 新增：AI 搜索功能
  const handleAiSearch = async () => {
    if (!query.trim()) return;

    setIsAiLoading(true);
    setShowSuggestions(false);
    
    try {
      // 调用 AI 搜索 API
      const response = await fetch('/api/v1/search/ai', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query.trim() })
      });
      
      if (response.ok) {
        const data = await response.json();
        // 使用 AI 优化后的查询进行搜索
        if (data.optimized_query) {
          setQuery(data.optimized_query);
          setSearchInfo({
            original_query: query,
            corrected_query: data.optimized_query,
            expanded_queries: data.expanded_queries || [data.optimized_query],
            suggestions: data.suggestions || []
          });
          onSearch(data.optimized_query);
        }
      }
    } catch (error) {
      console.error('AI搜索失败:', error);
      // 回退到普通搜索
      onSearch(query);
    } finally {
      setIsAiLoading(false);
    }
  };

    const handleAiDatabaseSearch = async () => {
    if (!query.trim()) return;

    setIsAiLoading(true);
    setShowSuggestions(false);
    
    try {
        const response = await fetch('/api/v1/search/ai-database', {
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
            
            // 显示AI搜索结果和解释
            setSearchInfo({
                original_query: query,
                ai_explanation: data.ai_explanation,
                search_intent: data.search_intent,
                query_time: data.query_time_ms,
                expanded_queries: [],
                suggestions: []
            });
            
            // 使用AI搜索结果
            if (onAISearchResult) {
                onAISearchResult(data.poses);
            } else {
                // 如果没有AI搜索结果回调，回退到普通搜索
                onSearch(query);
            }
        }
    } catch (error) {
        console.error('AI数据库搜索失败:', error);
        // 回退到普通搜索
        onSearch(query);
    } finally {
        setIsAiLoading(false);
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
            className="w-full px-4 py-3 pr-32 text-gray-900 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
            disabled={isLoading || isAiLoading}
          />
          
          {/* AI数据库搜索按钮 */}
          <button
            type="button"
            onClick={handleAiDatabaseSearch}
            disabled={isLoading || isAiLoading}
            className="absolute right-24 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-green-600 disabled:opacity-50 transition-colors"
            title="AI数据库搜索"
          >
            {isAiLoading ? (
              <div className="w-5 h-5 border-2 border-green-600 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            )}
          </button>

          {/* AI 搜索按钮 */}
          <button
            type="button"
            onClick={handleAiSearch}
            disabled={isLoading || isAiLoading}
            className="absolute right-12 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-purple-600 disabled:opacity-50 transition-colors"
            title="AI智能搜索"
          >
            {isAiLoading ? (
              <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            )}
          </button>

          {/* 普通搜索按钮 */}
          <button
            type="submit"
            disabled={isLoading || isAiLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-500 hover:text-blue-600 disabled:opacity-50"
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

      {/* 搜索信息展示 */}
      {showSearchInfo && searchInfo && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
          {searchInfo.corrected_query && (
            <div className="text-orange-600 mb-2">
              🔧 已自动纠正：{searchInfo.original_query} → {searchInfo.corrected_query}
            </div>
          )}
          {searchInfo.expanded_queries.length > 1 && (
            <div className="text-blue-600 mb-2">
              🔍 扩展搜索：{searchInfo.expanded_queries.join(', ')}
            </div>
          )}
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