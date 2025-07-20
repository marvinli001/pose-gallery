from fastapi import APIRouter, Depends
from app.services.enhanced_vector_search_service import EnhancedVectorSearchService
from app.api.enhanced_vector_search import get_enhanced_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/debug/vector-status")
async def debug_vector_status(
    service: EnhancedVectorSearchService = Depends(get_enhanced_service)
):
    """调试向量搜索状态"""
    return {
        "service_available": service.is_available(),
        "has_index": hasattr(service, 'index') and service.index is not None,
        "has_id_map": hasattr(service, 'id_map') and service.id_map is not None,
        "id_map_size": len(service.id_map) if hasattr(service, 'id_map') and service.id_map else 0,
        "embedding_model": "text-embedding-ada-002"
    }

@router.post("/debug/raw-search")
async def debug_raw_search(
    query: str,
    service: EnhancedVectorSearchService = Depends(get_enhanced_service)
):
    """原始向量搜索调试"""
    if not service.is_available():
        return {"error": "Service not available"}
    
    try:
        # 测试嵌入生成
        query_vec = service._embed(query)
        if query_vec is None:
            return {"error": "Failed to generate embedding"}
        
        # 原始faiss搜索
        distances, indices = service.index.search(query_vec.reshape(1, -1), 50)
        
        results = []
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            if idx >= 0:
                pose_id = service.id_map.get(str(idx), f"unknown_{idx}")
                similarity = service._distance_to_similarity(dist)
                results.append({
                    "rank": i,
                    "faiss_idx": int(idx),
                    "pose_id": pose_id,
                    "distance": float(dist),
                    "similarity": float(similarity)
                })
        
        return {
            "query": query,
            "embedding_shape": query_vec.shape,
            "total_candidates": len([i for i in indices[0] if i >= 0]),
            "results": results[:10]
        }
        
    except Exception as e:
        logger.error(f"Debug search failed: {e}")
        return {"error": str(e)}