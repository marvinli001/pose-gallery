export async function GET() {
  try {
    // 尝试从后端获取真实数据
    const response = await fetch('http://localhost:8000/api/scenes')
    
    if (response.ok) {
      const data = await response.json()
      return Response.json(data)
    }
  } catch (error) {
    console.log('Backend not available, using mock data')
  }

  // 返回模拟数据
  return Response.json({
    scenes: [
      { id: 'indoor', name: '室内拍摄', icon: '🏠', count: 120 },
      { id: 'street', name: '街头摄影', icon: '🏙️', count: 89 },
      { id: 'cafe', name: '咖啡馆', icon: '☕', count: 67 },
      { id: 'outdoor', name: '户外自然', icon: '🌿', count: 95 },
      { id: 'portrait', name: '人像写真', icon: '👤', count: 156 },
      { id: 'couple', name: '情侣拍照', icon: '💕', count: 78 },
      { id: 'business', name: '商务形象', icon: '💼', count: 43 },
      { id: 'creative', name: '创意摄影', icon: '🎨', count: 92 }
    ]
  })
}