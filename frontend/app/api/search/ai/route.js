import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    return await proxyToBackendWithTimeout(request, `/api/v1/search/ai-database`)
  } catch (error) {
    console.error('AI数据库搜索请求失败:', error)
    return Response.json(
      { 
        error: 'AI database search failed',
        message: 'AI数据库搜索暂时不可用，请使用普通搜索'
      }, 
      { status: 500 }
    )
  }
}