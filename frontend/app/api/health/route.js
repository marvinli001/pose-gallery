import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function GET(request) {
  try {
    return await proxyToBackendWithTimeout(request, '/health', 5000)
  } catch (error) {
    console.error('健康检查失败:', error)
    return Response.json({
      status: 'unhealthy',
      frontend: 'ok',
      backend: 'unavailable',
      timestamp: new Date().toISOString()
    })
  }
}