'use client';

import { useState, useCallback } from 'react';
import SearchBar from '@/components/SearchBar';
import CategoryFilter from '@/components/CategoryFilter';
import PoseGrid from '@/components/PoseGrid';
import { useSearch } from '@/hooks/useSearch';
import { useDebounce } from '@/hooks/useDebounce';

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const [allPoses, setAllPoses] = useState<any[]>([]);
  
  const debouncedQuery = useDebounce(searchQuery, 500);
  
  const { data, isLoading } = useSearch({
    query: debouncedQuery,
    category,
    page,
    per_page: 20
  });

  // 处理搜索
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setPage(1);
    setAllPoses([]);
  }, []);

  // 处理分类切换
  const handleCategoryChange = useCallback((newCategory: string) => {
    setCategory(newCategory);
    setPage(1);
    setAllPoses([]);
  }, []);

  // 加载更多
  const handleLoadMore = useCallback(() => {
    if (!isLoading && data && page * 20 < data.total) {
      setPage(prev => prev + 1);
    }
  }, [isLoading, data, page]);

  // 合并数据
  const poses = page === 1 ? (data?.poses || []) : [...allPoses, ...(data?.poses || [])];
  
  // 更新所有数据
  if (data && page > 1 && allPoses.length < poses.length) {
    setAllPoses(poses);
  }

  const hasMore = data ? page * 20 < data.total : false;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900 text-center mb-4">
            摄影姿势灵感库
          </h1>
          <SearchBar onSearch={handleSearch} initialValue={searchQuery} />
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* 分类筛选 */}
        <CategoryFilter selected={category} onChange={handleCategoryChange} />
        
        {/* 搜索信息 */}
        {searchQuery && data && (
          <div className="mb-4 text-sm text-gray-600">
            找到 <span className="font-medium">{data.total}</span> 个相关姿势
          </div>
        )}

        {/* 图片网格 */}
        <PoseGrid
          poses={poses}
          loading={isLoading && page === 1}
          hasMore={hasMore}
          onLoadMore={handleLoadMore}
        />
      </main>
    </div>
  );
}
