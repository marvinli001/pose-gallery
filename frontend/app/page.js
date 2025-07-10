'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import EnhancedSearchBar from '@/components/EnhancedSearchBar'

// 将使用 useSearchParams 的逻辑提取到单独组件
function PosesPageContent() {
  const searchParams = useSearchParams()
  const [poses, setPoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(1)
  const [viewMode, setViewMode] = useState('grid')
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [selectedPose, setSelectedPose] = useState(null)
  const [isAISearch, setIsAISearch] = useState(false) // 标记是否为AI搜索
  const [searchType, setSearchType] = useState('normal') // 新增：记录搜索类型 'normal' | 'ai' | 'vector'
  const [filters, setFilters] = useState({
    category: searchParams.get('category') || '',
    search: searchParams.get('search') || '',
    angle: '',
    sort: searchParams.get('sort') || 'latest'
  })

  // 新增：处理AI搜索结果的回调
  const handleAISearchResult = useCallback((aiPoses) => {
    console.log('接收到AI搜索结果:', aiPoses);
    setPoses(aiPoses || []);
    setPage(1);
    setHasMore(false); // AI搜索结果不需要分页
    setIsAISearch(true); // 标记为AI搜索
    setSearchType(aiPoses && aiPoses.length > 0 ? 'ai' : 'normal'); // 设置搜索类型
    setLoading(false);
  }, []);

  // 筛选选项
  const filterOptions = {
    angles: ['正面', '侧面', '背面', '俯视', '仰视', '半身', '全身'],
    categories: [
      { id: 'indoor', name: '室内拍摄', icon: '🏠' },
      { id: 'outdoor', name: '户外拍摄', icon: '🌿' },
      { id: 'portrait', name: '人像写真', icon: '👤' },
      { id: 'couple', name: '情侣拍照', icon: '💕' },
      { id: 'street', name: '街头摄影', icon: '🏙️' },
      { id: 'cafe', name: '咖啡馆', icon: '☕' },
      { id: 'business', name: '商务形象', icon: '💼' },
      { id: 'creative', name: '创意摄影', icon: '🎨' }
    ]
  }

  // 将 fetchPoses 包装为 useCallback - 必须在 useEffect 之前定义
  const fetchPoses = useCallback(async (reset = false) => {
    // 如果是AI搜索结果且不是重置操作，不进行普通搜索
    if ((isAISearch || searchType === 'ai' || searchType === 'vector') && !reset) {
      console.log('跳过普通搜索，当前搜索类型:', searchType);
      return;
    }
    
    setLoading(reset);
    try {
      const queryParams = new URLSearchParams({
        page: reset ? 1 : page,
        per_page: 20,
        ...filters
      });

      console.log('发起普通搜索请求:', queryParams.toString());
      
      const response = await fetch(`/api/poses?${queryParams}`);
      if (response.ok) {
        const data = await response.json();
        console.log('普通搜索结果:', data);
        
        if (reset) {
          setPoses(data.poses || []);
          setPage(2);
          setIsAISearch(false); // 重置AI搜索标记
          setSearchType('normal'); // 重置搜索类型
        } else {
          setPoses(prev => [...prev, ...(data.poses || [])]);
          setPage(prev => prev + 1);
        }
        
        setHasMore(data.hasMore !== false && (data.poses || []).length === 20);
      }
    } catch (error) {
      console.error('Fetch poses error:', error);
    } finally {
      setLoading(false);
    }
  }, [page, filters, isAISearch, searchType]);

  // loadMore 也需要更新依赖
  const loadMore = useCallback(() => {
    if (!loading && hasMore && searchType === 'normal') { // 只有普通搜索支持加载更多
      fetchPoses(false);
    }
  }, [loading, hasMore, fetchPoses, searchType]);

  // 监听filters变化，触发搜索 - 修复依赖数组
  useEffect(() => {
    // 如果当前是AI搜索状态，不要触发普通搜索
    if (searchType === 'ai' || searchType === 'vector') {
      console.log('跳过filters触发的搜索，当前搜索类型:', searchType);
      return;
    }
    
    console.log('Filters changed, 触发普通搜索:', filters);
    fetchPoses(true);
  }, [filters, fetchPoses, searchType]); // 添加缺失的依赖项

  // 无限滚动 - 只在普通搜索时生效
  useEffect(() => {
    const handleScroll = () => {
      if (searchType === 'normal' && 
          window.innerHeight + document.documentElement.scrollTop 
          >= document.documentElement.offsetHeight - 1000) {
        loadMore();
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [loadMore, searchType]);

  const handleFilterChange = (filterType, value) => {
    console.log('Filter change:', filterType, value);
    setFilters(prev => ({
      ...prev,
      [filterType]: prev[filterType] === value ? '' : value
    }));
    setIsAISearch(false); // 重置AI搜索标记
    setSearchType('normal'); // 重置搜索类型
  };

  // 修复：处理搜索提交 - 正确的参数类型
  const handleSearchSubmit = useCallback((query) => {
    console.log('处理普通搜索提交:', query);
    setSearchQuery(query);
    setFilters(prev => ({ ...prev, search: query }));
    setIsAISearch(false); // 重置AI搜索标记
    setSearchType('normal'); // 设置为普通搜索
  }, []);
  
  // 新增：重置搜索状态的回调 - 修复依赖数组
  const handleResetSearch = useCallback(() => {
    console.log('重置搜索状态');
    setSearchQuery('');
    setFilters(prev => ({ 
      ...prev, 
      search: '' 
    }));
    setIsAISearch(false);
    setSearchType('normal');
    setPoses([]);
    setPage(1);
    setHasMore(true);
    // 重新加载默认姿势
    fetchPoses(true);
  }, [fetchPoses]); // 添加缺失的依赖项

  return (
    <div className="min-h-screen">
      {/* 顶部导航 */}
      <header className="header">
        <div className="container">
          <Link href="/" className="header-logo">
            <h1>📸 摄影姿势速查库</h1>
          </Link>
          <nav className="nav">
            <div className="view-controls">
              <button 
                className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                onClick={() => setViewMode('grid')}
              >
                ⊞ 网格
              </button>
              <button 
                className={`view-btn ${viewMode === 'waterfall' ? 'active' : ''}`}
                onClick={() => setViewMode('waterfall')}
              >
                ⋮ 瀑布流
              </button>
            </div>
          </nav>
        </div>
      </header>

      {/* 搜索区域 - 替换为增强版搜索组件 */}
      <section className="search-section">
        <div className="container">
          <h2 className="search-title">发现完美拍照姿势</h2>
          <p className="search-subtitle">让每一次拍摄都充满创意和美感</p>
          
          <EnhancedSearchBar
            onSearch={handleSearchSubmit}
            onAISearchResult={handleAISearchResult}
            onResetSearch={handleResetSearch}
            initialValue={searchQuery}
            showSearchInfo={true}
          />
        </div>
      </section>

      {/* 筛选区域 */}
      <section className="filters-section">
        <div className="container">
          {/* 分类筛选 */}
          <section className="categories-section">
            <div className="container">
              <div className="categories-grid">
                {filterOptions.categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => handleFilterChange('category', category.id)}
                    className={`category-tag ${filters.category === category.id ? 'active' : ''}`}
                  >
                    <span className="category-icon">{category.icon}</span>
                    {category.name}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* 其他筛选 - AI搜索时隐藏 */}
          {searchType === 'normal' && (
            <div className="advanced-filters">
              <div className="filter-row">
                <div className="filter-group">
                  <span className="filter-label">角度：</span>
                  <div className="filter-options">
                    {filterOptions.angles.map(angle => (
                      <button 
                        key={angle}
                        className={`filter-tag ${filters.angle === angle ? 'active' : ''}`}
                        onClick={() => handleFilterChange('angle', angle)}
                      >
                        {angle}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="filter-group">
                  <span className="filter-label">排序：</span>
                  <div className="filter-options">
                    <button 
                      className={`filter-tag ${filters.sort === 'latest' ? 'active' : ''}`}
                      onClick={() => handleFilterChange('sort', 'latest')}
                    >
                      最新
                    </button>
                    <button 
                      className={`filter-tag ${filters.sort === 'popular' ? 'active' : ''}`}
                      onClick={() => handleFilterChange('sort', 'popular')}
                    >
                      热门
                    </button>
                    <button 
                      className={`filter-tag ${filters.sort === 'view_count' ? 'active' : ''}`}
                      onClick={() => handleFilterChange('sort', 'view_count')}
                    >
                      浏览量
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 姿势列表 */}
      <main className="main-content">
        <div className="container">
          {/* AI搜索结果提示 */}
          {(searchType === 'ai' || searchType === 'vector') && poses.length > 0 && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 flex items-center justify-between">
              {searchType === 'vector' ? '🔍' : '🤖'} 
              {searchType === 'vector' ? '向量搜索结果' : 'AI智能搜索结果'} - 共找到 {poses.length} 个相关姿势
              <button 
                className="reset-search-btn"
                onClick={handleResetSearch}
              >
                返回普通搜索
              </button>
            </div>
          )}

          {loading && poses.length === 0 ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>加载中...</p>
            </div>
          ) : (
            <div className={`poses-grid ${viewMode}`}>
              {poses.map((pose) => (
                <PoseCard 
                  key={pose.id} 
                  pose={pose} 
                  onClick={() => setSelectedPose(pose)}
                />
              ))}
            </div>
          )}

          {loading && poses.length > 0 && searchType === 'normal' && (
            <div className="loading-more">
              <div className="loading-spinner"></div>
              <span>加载更多...</span>
            </div>
          )}

          {!hasMore && poses.length > 0 && searchType === 'normal' && (
            <div className="end-message">
              已加载全部内容
            </div>
          )}

          {!loading && poses.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">📸</div>
              <h2>暂无符合条件的姿势</h2>
              <p>尝试调整筛选条件或搜索其他关键词</p>
            </div>
          )}
        </div>
      </main>

      {/* 姿势详情模态框 */}
      {selectedPose && (
        <PoseModal 
          pose={selectedPose} 
          onClose={() => setSelectedPose(null)} 
        />
      )}
    </div>
  );
}

// Loading 组件
function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="loading-spinner"></div>
      <span className="ml-2">加载中...</span>
    </div>
  );
}

// 主导出组件，使用 Suspense 包装
export default function PosesPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <PosesPageContent />
    </Suspense>
  );
}

// 姿势卡片组件
function PoseCard({ pose, onClick }) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)
  const placeholderImage = "data:image/svg+xml,%3Csvg width='280' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100%25' height='100%25' fill='%23f7fafc'/%3E%3Ctext x='50%25' y='50%25' fill='%23a0aec0' text-anchor='middle' dy='.3em'%3E%E5%8A%A0%E8%BD%BD%E4%B8%AD...%3C/text%3E%3C/svg%3E"

  const handleImageError = () => {
    console.error('Image load error for pose:', pose.id, pose.oss_url)
    setImageError(true)
    setImageLoaded(true)
  }

  const handleImageLoad = () => {
    console.log('Image loaded successfully for pose:', pose.id)
    setImageLoaded(true)
  }

  return (
    <div className="pose-card" onClick={onClick}>
      <div className="pose-image-container">
        <Image
          src={imageError ? placeholderImage : (pose.oss_url || placeholderImage)}
          alt={pose.title || '摄影姿势'}
          width={280}
          height={200}
          className={`pose-image ${imageLoaded ? 'loaded' : ''}`}
          onLoad={handleImageLoad}
          onError={handleImageError}
          placeholder="blur"
          blurDataURL={placeholderImage}
          unoptimized={true}
        />
        {!imageLoaded && <div className="image-placeholder"></div>}
        
        {/* 场景标签 */}
        {pose.scene_category && (
          <div className="pose-category-badge">
            {pose.scene_category}
          </div>
        )}
        
        {/* 浏览次数 */}
        <div className="pose-view-count">
          👁️ {pose.view_count || 0}
        </div>
      </div>
      
      <div className="pose-overlay">
        <h3 className="pose-title">{pose.title}</h3>
        {pose.description && (
          <p className="pose-description">{pose.description}</p>
        )}
        <div className="pose-tags">
          {pose.ai_tags && pose.ai_tags.split(',').slice(0, 3).map((tag, index) => (
            <span key={index} className="tag">{tag.trim()}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

// 修改 PoseModal 组件中的图片部分
function PoseModal({ pose, onClose }) {
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleImageError = () => {
    console.error('Modal image load error for pose:', pose.id, pose.oss_url);
    setImageError(true);
  };

  const placeholderImage = "data:image/svg+xml,%3Csvg width='800' height='600' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100%25' height='100%25' fill='%23f7fafc'/%3E%3Ctext x='50%25' y='50%25' fill='%23a0aec0' text-anchor='middle' dy='.3em'%3E%E5%8A%A0%E8%BD%BD%E4%B8%AD...%3C/text%3E%3C/svg%3E";

  return (
    <div className="pose-modal-overlay" onClick={onClose}>
      <div className="pose-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="pose-modal-close" onClick={onClose}>
          ✕
        </button>
        
        <div className="pose-modal-body">
          <div className="pose-modal-image">
            <Image 
              src={imageError ? placeholderImage : (pose.oss_url || placeholderImage)}
              alt={pose.title || '摄影姿势'}
              width={800}
              height={600}
              style={{ objectFit: 'contain', width: '100%', height: 'auto' }}
              onError={handleImageError}
              unoptimized={true}
            />
          </div>
          
          <div className="pose-modal-info">
            <h2>{pose.title}</h2>
            {pose.description && <p className="description">{pose.description}</p>}
            
            {pose.scene_category && (
              <div className="info-item">
                <span className="label">场景:</span>
                <span className="value">{pose.scene_category}</span>
              </div>
            )}
            
            {pose.angle && (
              <div className="info-item">
                <span className="label">角度:</span>
                <span className="value">{pose.angle}</span>
              </div>
            )}
            
            {pose.shooting_tips && (
              <div className="info-item tips">
                <span className="label">拍摄建议:</span>
                <p className="tips-content">💡 {pose.shooting_tips}</p>
              </div>
            )}
            
            {pose.ai_tags && (
              <div className="info-item">
                <span className="label">标签:</span>
                <div className="tags">
                  {pose.ai_tags.split(',').map((tag, index) => (
                    <span key={index} className="tag">#{tag.trim()}</span>
                  ))}
                </div>
              </div>
            )}
            
            <div className="pose-stats">
              <span>浏览: {pose.view_count || 0}</span>
              {pose.created_at && (
                <span>时间: {new Date(pose.created_at).toLocaleDateString('zh-CN')}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}