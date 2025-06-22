export async function GET(request) {
  const { searchParams } = new URL(request.url)
  
  try {
    // 构建查询参数
    const params = new URLSearchParams()
    
    // 基本参数
    params.append('page', searchParams.get('page') || '1')
    params.append('per_page', searchParams.get('per_page') || '20')
    
    // 搜索和筛选参数
    if (searchParams.get('search')) {
      params.append('q', searchParams.get('search'))
    }
    if (searchParams.get('category')) {
      params.append('category', searchParams.get('category'))
    }
    if (searchParams.get('angle')) {
      params.append('angle', searchParams.get('angle'))
    }
    if (searchParams.get('sort')) {
      params.append('sort', searchParams.get('sort'))
    }
    
    // 请求后端API，增加超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10秒超时
    
    // 修改这里：在host网络环境中使用正确的后端地址
    const backendUrl = process.env.BACKEND_URL || 
                      process.env.NEXT_PUBLIC_API_URL || 
                      'http://127.0.0.1:8000'
    
    console.log('尝试连接后端:', `${backendUrl}/api/v1/poses?${params}`) // 添加调试日志
    
    const response = await fetch(`${backendUrl}/api/v1/poses?${params}`, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    clearTimeout(timeoutId)
    
    if (response.ok) {
      const data = await response.json()
      console.log('后端数据获取成功:', data) // 添加调试日志
      return Response.json(data)
    } else {
      throw new Error(`Backend API error: ${response.status}`)
    }
  } catch (error) {
    console.log('Backend not available, using mock data:', error)
    
    // 返回模拟数据，确保结构正确
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('per_page') || '20')
    
    const mockPoses = [
      {
        id: 1,
        oss_url: '/placeholder.svg',
        title: '咖啡馆窗边坐姿',
        description: '自然光线下的优雅坐姿，适合表现文艺气质',
        scene_category: '咖啡馆',
        angle: '侧面',
        shooting_tips: '利用窗边自然光，注意光影对比',
        ai_tags: '咖啡馆,坐姿,自然光,文艺',
        view_count: 128,
        created_at: '2024-01-15T10:30:00'
      },
      {
        id: 2,
        oss_url: '/placeholder.svg',
        title: '街头漫步姿势',
        description: '城市街头的自然行走姿态，展现都市生活感',
        scene_category: '街头',
        angle: '全身',
        shooting_tips: '捕捉自然行走瞬间，背景虚化突出主体',
        ai_tags: '街头,行走,都市,全身',
        view_count: 96,
        created_at: '2024-01-14T16:45:00'
      },
      {
        id: 3,
        oss_url: '/placeholder.svg',
        title: '室内人像经典pose',
        description: '适合室内环境的经典人像姿势',
        scene_category: '室内',
        angle: '半身',
        shooting_tips: '注意室内灯光布置，避免过度曝光',
        ai_tags: '室内,人像,经典,半身',
        view_count: 234,
        created_at: '2024-01-13T14:20:00'
      }
    ]
    
    return Response.json({
      poses: mockPoses,
      total: mockPoses.length,
      page: page,
      per_page: limit,
      hasMore: false
    })
  }
}