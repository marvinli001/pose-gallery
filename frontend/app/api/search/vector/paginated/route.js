import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function POST(request) {
  try {
    console.log('Paginated vector search request received')
    
    // Parse request body to get search parameters
    const body = await request.json()
    console.log('Paginated vector search parameters:', body)
    
    // Create a new request object with the parameters
    const paginatedRequest = new Request(request.url, {
      method: 'POST',
      headers: request.headers,
      body: JSON.stringify(body)
    })
    
    return await proxyToBackendWithTimeout(paginatedRequest, `/api/v1/search/vector/paginated`)
  } catch (error) {
    console.error('Paginated vector search request failed:', error)
    return Response.json(
      {
        poses: [],
        total: 0,
        query_time_ms: 0,
        service_available: false,
        error: 'Paginated vector search failed',
        message: '分页向量搜索暂时不可用，请使用普通搜索',
        search_info: {
          error_details: error.message,
          fallback_available: true,
          page: body?.page || 1,
          page_size: body?.page_size || 20
        }
      },
      { status: 200 } // Return 200 to avoid frontend errors
    )
  }
}