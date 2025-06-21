'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

export default function Home() {
  const [scenes, setScenes] = useState([])
  const [recentPoses, setRecentPoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchSuggestions, setSearchSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  useEffect(() => {
    fetchScenes()
    fetchRecentPoses()
  }, [])

  const fetchScenes = async () => {
    try {
      const response = await fetch('/api/scenes')
      if (response.ok) {
        const data = await response.json()
        setScenes(data)
      }
    } catch (err) {
      console.log('Scenes API not ready:', err)
      // 使用基于后端数据库结构的默认场景
      setScenes([
        { id: 'indoor', name: '室内拍摄', icon: '🏠', pose_count: 0 },
        { id: 'outdoor', name: '户外拍摄', icon: '🌿', pose_count: 0 },
        { id: 'portrait', name: '人像写真', icon: '👤', pose_count: 0 },
        { id: 'couple', name: '情侣拍照', icon: '💕', pose_count: 0 },
        { id: 'street', name: '街头摄影', icon: '🏙️', pose_count: 0 },
        { id: 'cafe', name: '咖啡馆', icon: '☕', pose_count: 0 },
        { id: 'business', name: '商务形象', icon: '💼', pose_count: 0 },
        { id: 'creative', name: '创意摄影', icon: '🎨', pose_count: 0 }
      ])
    }
  }

  const fetchRecentPoses = async () => {
    try {
      const response = await fetch('/api/poses?limit=6&sort=latest')
      if (response.ok) {
        const data = await response.json()
        setRecentPoses(data.poses || [])
      }
    } catch (err) {
      console.log('Recent poses API not ready:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (query) => {
    if (query.length > 1) {
      try {
        const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`)
        if (response.ok) {
          const suggestions = await response.json()
          setSearchSuggestions(suggestions)
          setShowSuggestions(true)
        }
      } catch (error) {
        console.log('Search suggestions error:', error)
      }
    } else {
      setShowSuggestions(false)
    }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      window.location.href = `/poses?search=${encodeURIComponent(searchQuery.trim())}`
    }
  }

  const placeholderImage = "data:image/svg+xml,%3Csvg width='280' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100%25' height='100%25' fill='%23f7fafc'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='16' fill='%23a0aec0' text-anchor='middle' dy='.3em'%3E摄影姿势%3C/text%3E%3C/svg%3E"

  return (
    <div className="min-h-screen">
      {/* 顶部导航 - 保持原有样式 */}
      <header className="header">
        <div className="container">
          <Link href="/" className="header-logo">
            <h1>📸 摄影姿势速查库</h1>
          </Link>
          <nav className="nav">
            <button className="btn btn-secondary theme-toggle">🌙 切换主题</button>
          </nav>
        </div>
      </header>

      {/* 英雄区域搜索 - 升级原有搜索区域 */}
      <section className="hero-search-section">
        <div className="container">
          <div className="hero-content">
            <h2 className="hero-title">找到完美拍摄姿势</h2>
            <p className="hero-subtitle">场景适配 • 构图清晰 • 实用性强</p>
            
            <form onSubmit={handleSearchSubmit} className="search-form">
              <div className="search-container">
                <input 
                  type="text" 
                  placeholder="搜索场景、姿势、情绪..."
                  className="search-input"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    handleSearch(e.target.value)
                  }}
                  onFocus={() => searchQuery.length > 1 && setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                />
                <button type="submit" className="btn search-btn">
                  🔍 搜索
                </button>
                
                {/* 搜索建议下拉 */}
                {showSuggestions && searchSuggestions.length > 0 && (
                  <div className="search-suggestions">
                    {searchSuggestions.map((suggestion, index) => (
                      <div 
                        key={index} 
                        className="suggestion-item"
                        onClick={() => {
                          setSearchQuery(suggestion)
                          setShowSuggestions(false)
                        }}
                      >
                        🔍 {suggestion}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* 场景磁贴区域 - 替换原有分类标签 */}
      <section className="scenes-section">
        <div className="container">
          <h3 className="section-title">按场景浏览</h3>
          
          {loading ? (
            <div className="scenes-loading">
              {Array(8).fill(0).map((_, i) => (
                <div key={i} className="scene-card-skeleton"></div>
              ))}
            </div>
          ) : (
            <div className="scenes-grid">
              {scenes.map((scene) => (
                <Link 
                  key={scene.id} 
                  href={`/poses?category=${scene.id}`}
                  className="scene-card"
                >
                  <div className="scene-icon">{scene.icon}</div>
                  <h4 className="scene-name">{scene.name}</h4>
                  <p className="scene-count">
                    {scene.pose_count > 0 ? `${scene.pose_count} 个姿势` : '即将上线'}
                  </p>
                  <div className="scene-overlay">
                    <span className="overlay-text">立即查看 →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 最新姿势预览 - 保持原有卡片样式 */}
      {recentPoses.length > 0 && (
        <section className="recent-poses-section">
          <div className="container">
            <div className="section-header">
              <h3 className="section-title">最新上传</h3>
              <Link href="/poses?sort=latest" className="view-all-btn">
                查看全部 →
              </Link>
            </div>
            
            <div className="poses-grid preview-grid">
              {recentPoses.map((pose) => (
                <div key={pose.id} className="pose-card">
                  <img 
                    src={pose.image_url || placeholderImage} 
                    alt={pose.title}
                    className="pose-image"
                  />
                  <div className="pose-info">
                    <h3>{pose.title}</h3>
                    <p>{pose.description}</p>
                    <div className="pose-tags">
                      {pose.tags && pose.tags.split(',').slice(0, 3).map((tag, index) => (
                        <span key={index} className="tag">{tag.trim()}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 快速入口 */}
      <section className="quick-actions-section">
        <div className="container">
          <h3 className="section-title">快速入口</h3>
          <div className="quick-actions-grid">
            <Link href="/poses?sort=popular" className="quick-action-card">
              <span className="action-icon">🔥</span>
              <span className="action-text">热门姿势</span>
            </Link>
            <Link href="/poses?filter=beginner" className="quick-action-card">
              <span className="action-icon">🎯</span>
              <span className="action-text">新手友好</span>
            </Link>
            <Link href="/poses?filter=advanced" className="quick-action-card">
              <span className="action-icon">💎</span>
              <span className="action-text">进阶技巧</span>
            </Link>
            <Link href="/poses?angle=portrait" className="quick-action-card">
              <span className="action-icon">📸</span>
              <span className="action-text">人像精选</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="footer">
        <div className="container">
          <p>&copy; 2025 摄影姿势速查库 - 专注实用摄影技巧</p>
        </div>
      </footer>
    </div>
  )
}