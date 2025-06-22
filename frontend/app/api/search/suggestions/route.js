export async function GET(request) {
  const { searchParams } = new URL(request.url)
  const query = searchParams.get('q')
  
  if (!query || query.length < 2) {
    return Response.json([])
  }
  
  try {
    // 固定使用内网地址
    const backendUrl = 'http://127.0.0.1:8000'
    
    console.log('代理请求到后端搜索建议 API:', query)
    
    const response = await fetch(`${backendUrl}/api/v1/search/suggestions?q=${encodeURIComponent(query)}`, {
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
    console.log('搜索建议 API 不可用，使用模拟数据:', error.message)
    
    // 返回模拟搜索建议
    const mockSuggestions = [
      '咖啡馆拍照',
      '户外人像',
      '情侣合照',
      '商务形象照',
      '街头摄影',
      '室内写真',
      '自然光拍摄',
      '创意构图'
    ].filter(suggestion => 
      suggestion.toLowerCase().includes(query.toLowerCase())
    )
    
    return Response.json(mockSuggestions.slice(0, 5))
  }
}