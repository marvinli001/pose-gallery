import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    return await proxyToBackendWithTimeout(request, `/api/v1/search/vector`)
  } catch (error) {
    console.error('Vector search request failed:', error)
    return Response.json(
      {
        poses: [],
        total: 0,
        query_time_ms: 0,
        service_available: false,
        error: 'Vector search failed',
        message: '向量搜索暂时不可用，请使用普通搜索'
      },
      { status: 200 } // 改为200状态码，避免前端报错
    )
  }
}