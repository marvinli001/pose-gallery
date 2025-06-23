from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List
from ..services.ai_search_service import AISearchService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 建议添加依赖注入，而不是全局实例
def get_ai_search_service():
    return AISearchService()

class AISearchRequest(BaseModel):
    query: str

class AISearchResponse(BaseModel):
    optimized_query: str
    expanded_queries: List[str]
    suggestions: List[str]
    explanation: str

@router.post("/search/ai", response_model=AISearchResponse)
async def ai_search_optimization(
    request: AISearchRequest,
    ai_service: AISearchService = Depends(get_ai_search_service)
):
    """
    AI搜索查询优化
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        logger.info(f"开始AI搜索优化: {request.query}")
        
        result = ai_service.optimize_search_query(request.query.strip())
        
        logger.info(f"AI优化完成: {request.query} -> {result['optimized_query']}")
        
        return AISearchResponse(**result)
        
    except Exception as e:
        logger.error(f"AI搜索优化失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail="AI搜索优化服务暂时不可用"
        )