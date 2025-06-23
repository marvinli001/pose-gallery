import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    // 修复：应该调用 /api/v1/search/ai 而不是 ai-database
    return await proxyToBackendWithTimeout(request, `/api/v1/search/ai`)
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