from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from ..database import get_db
from ..schemas.pose import SearchResponse, PoseResponse
from ..services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.get("/search", response_model=SearchResponse)
async def search_poses(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类筛选"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    搜索姿势图片
    
    支持功能：
    - 关键词搜索
    - 同义词扩展
    - 分类筛选
    - 分页
    """
    poses, total = search_service.search_poses(db, q, category, page, per_page)
    
    return SearchResponse(
        poses=[PoseResponse.from_orm(pose) for pose in poses],
        total=total,
        page=page,
        per_page=per_page
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
    - 拼音匹配
    - 基于搜索历史
    """
    suggestions = search_service.get_search_suggestions(prefix, limit)
    return suggestions

@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """获取所有分类及数量"""
    result = db.execute(
        text("""
            SELECT scene_category, COUNT(*) as count 
            FROM poses 
            WHERE status = 'active' AND scene_category IS NOT NULL
            GROUP BY scene_category
            ORDER BY count DESC
        """)
    ).fetchall()
    
    return [
        {"name": row[0], "count": row[1]} 
        for row in result
    ]
