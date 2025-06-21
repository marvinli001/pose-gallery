from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from ..database import get_db
from ..schemas.pose import SearchResponse, PoseResponse
from ..services.search_service import SearchService
import time

router = APIRouter()
search_service = SearchService()

@router.get("/search", response_model=SearchResponse)
async def search_poses(
    request: Request,
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: Optional[str] = Query(None, description="场景分类筛选"),
    angle: Optional[str] = Query(None, description="角度筛选"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    搜索姿势图片
    
    支持功能：
    - 关键词搜索（全文索引）
    - 同义词扩展
    - 标签搜索
    - 分类和角度筛选
    - 分页
    - 搜索历史记录
    """
    poses, total = search_service.search_poses(
        db, q, category, angle, page, per_page
    )
    
    return SearchResponse(
        poses=[PoseResponse.from_orm(pose) for pose in poses],
        total=total,
        page=page,
        per_page=per_page,
        query=q
    )

@router.get("/search/suggestions", response_model=List[str])
async def get_suggestions(
    prefix: str = Query(..., min_length=1, description="搜索前缀"),
    limit: int = Query(10, ge=1, le=20, description="建议数量")
):
    """
    获取搜索建议（自动补全）
    
    支持：
    - 前缀匹配
    - 基于热门搜索
    - 标签建议
    """
    suggestions = search_service.get_search_suggestions(prefix, limit)
    return suggestions

@router.get("/search/popular")
async def get_popular_searches(
    limit: int = Query(10, ge=1, le=20, description="数量限制"),
    db: Session = Depends(get_db)
):
    """获取热门搜索词"""
    return search_service.get_popular_searches(db, limit)

@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """获取所有场景分类及数量"""
    return search_service.get_categories_with_count(db)

@router.get("/angles")
async def get_angles(db: Session = Depends(get_db)):
    """获取所有拍摄角度及数量"""
    return search_service.get_angles_with_count(db)

@router.get("/filters")
async def get_all_filters(db: Session = Depends(get_db)):
    """获取所有筛选选项"""
    return {
        "categories": search_service.get_categories_with_count(db),
        "angles": search_service.get_angles_with_count(db)
    }

@router.get("/stats")
async def get_search_stats(db: Session = Depends(get_db)):
    """获取搜索统计信息"""
    result = db.execute(
        text("""
            SELECT 
                COUNT(*) as total_searches,
                COUNT(DISTINCT normalized_query) as unique_queries,
                AVG(response_time_ms) as avg_response_time,
                AVG(results_count) as avg_results
            FROM search_history 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
    ).fetchone()
    
    return {
        "total_searches": result[0] or 0,
        "unique_queries": result[1] or 0,
        "avg_response_time_ms": round(result[2] or 0, 2),
        "avg_results": round(result[3] or 0, 2)
    }