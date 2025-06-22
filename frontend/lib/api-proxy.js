// API代理配置 - 固定后端地址
const BACKEND_BASE_URL = 'http://127.0.0.1:8000'

/**
 * 通用API代理函数
 * @param {Request} request - 原始请求对象
 * @param {string} endpoint - 后端API端点
 * @param {Object} options - 额外配置选项
 */
export async function proxyToBackend(request, endpoint, options = {}) {
  const url = new URL(request.url)
  const targetUrl = `${BACKEND_BASE_URL}${endpoint}${url.search}`
  
  try {
    console.log('代理请求:', targetUrl)
    
    const fetchOptions = {
      method: request.method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      signal: options.signal,
    }
    
    // 如果不是 GET 请求，添加请求体
    if (request.method !== 'GET') {
      try {
        fetchOptions.body = await request.text()
      } catch (_e) {
        // 忽略读取body的错误
      }
    }
    
    const response = await fetch(targetUrl, fetchOptions)
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return Response.json(data)
    
  } catch (error) {
    console.error('代理请求失败:', error.message)
    throw error
  }
}

/**
 * 带超时的代理请求
 * @param {Request} request - 原始请求对象
 * @param {string} endpoint - 后端API端点
 * @param {number} timeout - 超时时间（毫秒）
 */
export async function proxyToBackendWithTimeout(request, endpoint, timeout = 10000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const result = await proxyToBackend(request, endpoint, {
      signal: controller.signal
    })
    clearTimeout(timeoutId)
    return result
  } catch (error) {
    clearTimeout(timeoutId)
    throw error
  }
}