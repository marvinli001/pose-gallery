from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import logging

from ..services.vector_search_service import EnhancedVectorSearchService
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局服务实例，启动时初始化
_vector_service = None

def get_service():
    global _vector_service
    if _vector_service is None:
        _vector_service = EnhancedVectorSearchService()
    return _vector_service


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    use_adaptive: bool = True  # 新增：是否使用自适应阈值


class PoseWithScore(BaseModel):
    id: int
    oss_url: str
    thumbnail_url: str | None = None
    title: str | None = None
    description: str | None = None
    scene_category: str | None = None
    angle: str | None = None
    shooting_tips: str | None = None
    ai_tags: str | None = None
    view_count: int | None = 0
    created_at: str | None = None
    score: float


class VectorSearchResponse(BaseModel):
    poses: List[PoseWithScore]
    total: int
    query_time_ms: int
    service_available: bool = True
    search_info: Dict = {}  # 新增：搜索信息


@router.get("/search/vector/status")
async def vector_search_status():
    """检查向量搜索服务状态"""
    service = get_service()
    return {
        "available": service.is_available(),
        "message": "向量搜索服务可用" if service.is_available() else "向量搜索服务不可用，请生成向量索引"
    }


@router.post("/search/vector", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    service: EnhancedVectorSearchService = Depends(get_service),
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # 检查服务是否可用
    if not service.is_available():
        logger.warning("向量搜索服务不可用，返回空结果")
        return VectorSearchResponse(
            poses=[], 
            total=0, 
            query_time_ms=0,
            service_available=False
        )
    
    try:
        start = time.time()
        
        # 使用自适应搜索或标准搜索
        if request.use_adaptive:
            ids_scores = service.search_with_adaptive_threshold(
                request.query, 
                top_k=request.top_k,
                min_results=max(1, request.top_k // 2)  # 至少返回一半数量
            )
        else:
            ids_scores = service.search(request.query, top_k=request.top_k)
        
        pose_ids = [pid for pid, _ in ids_scores]

        if not pose_ids:
            return VectorSearchResponse(
                poses=[], 
                total=0, 
                query_time_ms=int((time.time() - start) * 1000),
                service_available=True,
                search_info={
                    "message": "未找到相关结果，请尝试其他关键词",
                    "suggestion": "尝试使用更通用的词汇，如「人像」「室内」「户外」等"
                }
            )

        result = db.execute(
            text(
                """
                SELECT id, oss_url, thumbnail_url, title, description,
                       scene_category, angle, shooting_tips, ai_tags,
                       view_count, created_at
                FROM poses
                WHERE id IN :ids AND status = 'active'
                """
            ),
            {"ids": tuple(pose_ids)},
        ).fetchall()

        pose_dict: Dict[int, Dict[str, Any]] = {}
        for row in result:
            pose_dict[row[0]] = {
                "id": row[0],
                "oss_url": row[1],
                "thumbnail_url": row[2],
                "title": row[3] or "",
                "description": row[4] or "",
                "scene_category": row[5],
                "angle": row[6],
                "shooting_tips": row[7],
                "ai_tags": row[8] or "",
                "view_count": row[9] or 0,
                "created_at": row[10].isoformat() if row[10] else None,
            }

        poses = []
        for pid, score in ids_scores:
            data = pose_dict.get(pid)
            if data:
                poses.append({**data, "score": score})

        query_time = int((time.time() - start) * 1000)
        
        # 生成搜索信息
        search_info = {
            "found_results": len(poses),
            "search_method": "自适应向量搜索" if request.use_adaptive else "向量搜索",
            "avg_similarity": round(sum(p["score"] for p in poses) / len(poses), 3) if poses else 0
        }
        
        if poses:
            min_score = min(p["score"] for p in poses)
            max_score = max(p["score"] for p in poses)
            search_info["similarity_range"] = f"{min_score:.3f} - {max_score:.3f}"
            
            if min_score < 0.3:
                search_info["quality_warning"] = "部分结果相关性较低，建议调整搜索词"
        
        return VectorSearchResponse(
            poses=poses, 
            total=len(poses), 
            query_time_ms=query_time,
            service_available=True,
            search_info=search_info
        )
        
    except Exception as e:
        logger.error(f"向量搜索执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"向量搜索失败: {str(e)}")