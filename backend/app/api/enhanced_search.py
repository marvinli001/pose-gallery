from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from ..database import get_db
from ..services.enhanced_search_service import EnhancedSearchService
from ..schemas.pose import PoseResponse
import redis
import os

router = APIRouter(prefix="/api/search/v2", tags=["Enhanced Search"])

# Redis 连接
redis_client = None
if os.getenv("REDIS_URL"):
    redis_client = redis.from_url(os.getenv("REDIS_URL"))

enhanced_search_service = EnhancedSearchService(redis_client=redis_client)

class EnhancedSearchResponse(BaseModel):
    poses: List[PoseResponse]
    total: int
    page: int
    per_page: int
    search_info: dict

class SearchSuggestion(BaseModel):
    text: str
    type: str  # 'history', 'tag', 'synonym'
    weight: int

@router.get("/search", response_model=EnhancedSearchResponse)
async def enhanced_search(
    request: Request,
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: Optional[str] = Query(None, description="场景分类筛选"),
    angle: Optional[str] = Query(None, description="角度筛选"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    enable_fuzzy: bool = Query(True, description="启用模糊匹配和拼写纠正"),
    db: Session = Depends(get_db)
):
    """
    增强版搜索API
    
    新功能：
    - 智能分词和关键词提取
    - 同义词扩展
    - 模糊匹配和拼写纠正
    - 多重搜索策略
    - 智能排序
    """
    poses, total, search_info = enhanced_search_service.search_poses_enhanced(
        db=db,
        query=q,
        category=category,
        angle=angle,
        page=page,
        per_page=per_page,
        enable_fuzzy=enable_fuzzy
    )
    
    return EnhancedSearchResponse(
        poses=[PoseResponse.from_orm(pose) for pose in poses],
        total=total,
        page=page,
        per_page=per_page,
        search_info=search_info
    )

@router.get("/suggestions", response_model=List[SearchSuggestion])
async def get_smart_suggestions(
    prefix: str = Query(..., min_length=1, description="搜索前缀"),
    limit: int = Query(10, ge=1, le=20, description="建议数量"),
    db: Session = Depends(get_db)
):
    """
    智能搜索建议
    
    功能：
    - 基于搜索历史
    - 基于标签库
    - 基于同义词
    - 智能排序和去重
    """
    suggestions = enhanced_search_service.get_smart_suggestions(db, prefix, limit)
    return [SearchSuggestion(**suggestion) for suggestion in suggestions]

@router.get("/analytics")
async def get_search_analytics(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db)
):
    """搜索分析数据"""
    return enhanced_search_service.get_search_analytics(db, days)

@router.post("/feedback")
async def search_feedback(
    query: str = Query(..., description="搜索词"),
    helpful: bool = Query(..., description="是否有帮助"),
    selected_result_id: Optional[int] = Query(None, description="选择的结果ID"),
    db: Session = Depends(get_db)
):
    """搜索反馈收集"""
    # TODO: 实现搜索反馈逻辑，用于改进搜索算法
    return {"message": "感谢您的反馈"}