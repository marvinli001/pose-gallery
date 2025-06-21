'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

export default function PosesPage() {
  const searchParams = useSearchParams()
  const [poses, setPoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(1)
  const [viewMode, setViewMode] = useState('grid') // 'grid' | 'waterfall'
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [selectedPose, setSelectedPose] = useState(null)
  const [filters, setFilters] = useState({
    category: searchParams.get('category') || '',
    search: searchParams.get('search') || '',
    angle: '',
    sort: searchParams.get('sort') || 'latest'
  })

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

  useEffect(() => {
    fetchPoses(true)
  }, [filters])

  const fetchPoses = async (reset = false) => {
    setLoading(reset)
    try {
      const queryParams = new URLSearchParams({
        page: reset ? 1 : page,
        per_page: 20,
        ...filters
      })

      const response = await fetch(`/api/poses?${queryParams}`)
      if (response.ok) {
        const data = await response.json()
        
        if (reset) {
          setPoses(data.poses || [])
          setPage(2)
        } else {
          setPoses(prev => [...prev, ...(data.poses || [])])
          setPage(prev => prev + 1)
        }
        
        setHasMore(data.hasMore !== false && (data.poses || []).length === 20)
      }
    } catch (error) {
      console.error('Fetch poses error:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      fetchPoses(false)
    }
  }, [loading, hasMore])

  // 无限滚动
  useEffect(() => {
    const handleScroll = () => {
      if (window.innerHeight + document.documentElement.scrollTop 
          >= document.documentElement.offsetHeight - 1000) {
        loadMore()
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [loadMore])

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: prev[filterType] === value ? '' : value
    }))
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setFilters(prev => ({ ...prev, search: searchQuery }))
  }

  const placeholderImage = "data:image/svg+xml,%3Csvg width='280' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100%25' height='100%25' fill='%23f7fafc'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='16' fill='%23a0aec0' text-anchor='middle' dy='.3em'%3E摄影姿势%3C/text%3E%3C/svg%3E"

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

      {/* 搜索栏 */}
      <section className="poses-search-section">
        <div className="container">
          <form onSubmit={handleSearchSubmit} className="search-box">
            <input 
              type="text" 
              placeholder="搜索摄影姿势..." 
              className="search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="btn search-btn">搜索</button>
          </form>
        </div>
      </section>

      {/* 筛选区域 */}
      <section className="filters-section">
        <div className="container">
          {/* 分类筛选 */}
          <div className="filter-group">
            <span className="filter-label">场景：</span>
            <div className="filter-options">
              {filterOptions.categories.map(cat => (
                <button 
                  key={cat.id}
                  className={`category-tag ${filters.category === cat.id ? 'active' : ''}`}
                  onClick={() => handleFilterChange('category', cat.id)}
                >
                  <span className="category-icon">{cat.icon}</span>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>

          {/* 其他筛选 */}
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
        </div>
      </section>

      {/* 姿势列表 */}
      <main className="poses-content">
        <div className="container">
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

          {loading && poses.length > 0 && (
            <div className="loading-more">
              <div className="loading-spinner"></div>
              <span>加载更多...</span>
            </div>
          )}

          {!hasMore && poses.length > 0 && (
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
  )
}

// 姿势卡片组件
function PoseCard({ pose, onClick }) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const placeholderImage = "data:image/svg+xml,%3Csvg width='280' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100%25' height='100%25' fill='%23f7fafc'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='16' fill='%23a0aec0' text-anchor='middle' dy='.3em'%3E摄影姿势%3C/text%3E%3C/svg%3E"

  return (
    <div className="pose-card" onClick={onClick}>
      <div className="pose-image-container">
        <img
          src={pose.oss_url || placeholderImage}
          alt={pose.title}
          className={`pose-image ${imageLoaded ? 'loaded' : ''}`}
          onLoad={() => setImageLoaded(true)}
          loading="lazy"
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
  )
}

// 姿势详情模态框
function PoseModal({ pose, onClose }) {
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  return (
    <div className="pose-modal-overlay" onClick={onClose}>
      <div className="pose-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="pose-modal-close" onClick={onClose}>
          ✕
        </button>
        
        <div className="pose-modal-body">
          <div className="pose-modal-image">
            <img src={pose.oss_url} alt={pose.title} />
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
              <span>时间: {new Date(pose.created_at).toLocaleDateString('zh-CN')}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}