import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    return await proxyToBackendWithTimeout(request, `/api/search/ai`)
  } catch (error) {
    console.error('AI搜索请求失败:', error)
    return Response.json(
      { 
        error: 'AI search failed',
        message: 'AI搜索暂时不可用，请使用普通搜索'
      }, 
      { status: 500 }
    )
  }
}