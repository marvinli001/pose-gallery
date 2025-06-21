export async function GET() {
  try {
    const response = await fetch('http://localhost:8000/api/categories')
    
    if (!response.ok) {
      return Response.json(
        { error: 'Backend API not available' }, 
        { status: 503 }
      )
    }
    
    const data = await response.json()
    return Response.json(data)
  } catch {} {
    // 返回默认分类
    return Response.json([
      { id: 1, name: '人像摄影' },
      { id: 2, name: '情侣写真' },
      { id: 3, name: '街拍风格' },
      { id: 4, name: '商务形象' },
      { id: 5, name: '创意摄影' }
    ])
  }
}