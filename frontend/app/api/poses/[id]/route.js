import { proxyToBackendWithTimeout } from '@/lib/api-proxy'

export async function GET(request, { params }) {
  try {
    return await proxyToBackendWithTimeout(request, `/api/v1/poses/${params.id}`)
  } catch (error) {
    console.error('获取姿势详情失败:', error)
    return Response.json(
      { 
        error: 'Pose not found',
        message: '姿势数据不可用'
      }, 
      { status: 404 }
    )
  }
}

export async function PUT(request, { params }) {
  try {
    return await proxyToBackendWithTimeout(request, `/api/v1/poses/${params.id}`)
  } catch (error) {
    console.error('更新姿势失败:', error)
    return Response.json(
      { 
        error: 'Update failed',
        message: '更新失败'
      }, 
      { status: 500 }
    )
  }
}