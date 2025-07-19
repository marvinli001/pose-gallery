import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    console.log('Enhanced vector search request received')
    
    // Parse request body to get search parameters
    const body = await request.json()
    console.log('Enhanced vector search parameters:', body)
    
    // Create a new request object with the parameters
    const enhancedRequest = new Request(request.url, {
      method: 'POST',
      headers: request.headers,
      body: JSON.stringify(body)
    })
    
    return await proxyToBackendWithTimeout(enhancedRequest, `/api/v1/search/vector/enhanced`)
  } catch (error) {
    console.error('Enhanced vector search request failed:', error)
    return Response.json(
      {
        poses: [],
        total: 0,
        query_time_ms: 0,
        service_available: false,
        error: 'Enhanced vector search failed',
        message: '增强向量搜索暂时不可用，请使用普通搜索',
        search_info: {
          error_details: error.message,
          fallback_available: true
        }
      },
      { status: 200 } // Return 200 to avoid frontend errors
    )
  }
}