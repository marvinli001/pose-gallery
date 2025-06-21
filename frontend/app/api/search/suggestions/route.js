export async function GET(request) {
  const { searchParams } = new URL(request.url)
  const query = searchParams.get('q')

  // 模拟搜索建议数据
  const suggestions = [
    '室内人像', '咖啡馆拍照', '街头摄影', '情侣写真',
    '商务头像', '自然光人像', '创意构图', '半身照',
    '全身照', '侧面角度', '逆光摄影', '优雅姿势'
  ]

  const filtered = suggestions.filter(item => 
    item.toLowerCase().includes(query?.toLowerCase() || '')
  ).slice(0, 6)

  return Response.json(filtered)
}