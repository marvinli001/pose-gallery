export async function GET() {
  try {
    // 固定使用内网地址
    const backendUrl = 'http://127.0.0.1:8000'
    
    console.log('代理请求到后端分类 API')
    
    const response = await fetch(`${backendUrl}/api/v1/categories`, {
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
    console.log('分类 API 不可用，使用模拟数据:', error.message)
    
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