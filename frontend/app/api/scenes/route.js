export async function GET() {
  try {
    // 固定使用内网地址
    const backendUrl = 'http://127.0.0.1:8000'
    
    console.log('代理请求到后端 scenes API')
    
    const response = await fetch(`${backendUrl}/api/v1/scenes`, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return Response.json(data)
    } else {
      throw new Error(`Backend API error: ${response.status}`)
    }
  } catch (error) {
    console.log('Scenes API 不可用，使用模拟数据:', error.message)
    
    // 返回模拟场景数据
    const mockScenes = [
      { id: 'indoor', name: '室内拍摄', icon: '🏠', pose_count: 15 },
      { id: 'outdoor', name: '户外拍摄', icon: '🌿', pose_count: 23 },
      { id: 'portrait', name: '人像写真', icon: '👤', pose_count: 18 },
      { id: 'couple', name: '情侣拍照', icon: '💕', pose_count: 12 },
      { id: 'street', name: '街头摄影', icon: '🏙️', pose_count: 8 },
      { id: 'cafe', name: '咖啡馆', icon: '☕', pose_count: 6 },
      { id: 'business', name: '商务形象', icon: '💼', pose_count: 9 },
      { id: 'creative', name: '创意摄影', icon: '🎨', pose_count: 14 }
    ]
    
    return Response.json({
      scenes: mockScenes,
      total: mockScenes.length
    })
  }
}