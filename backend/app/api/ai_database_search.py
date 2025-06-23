from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from ..database import get_db
from ..services.ai_database_search import AIDatabaseSearchService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
ai_db_search_service = AIDatabaseSearchService()

class AISearchRequest(BaseModel):
    query: str
    max_results: int = 20

class AISearchResponse(BaseModel):
    poses: List[Dict[str, Any]]
    total: int
    search_intent: Dict[str, Any]
    ai_explanation: str
    query_time_ms: int

@router.post("/search/ai-database", response_model=AISearchResponse)
async def ai_database_search(
    request: AISearchRequest,
    db: Session = Depends(get_db)
):
    """
    AI数据库搜索
    
    使用AI理解用户查询意图，生成精确的数据库查询，
    并对结果进行智能排序
    """
    import time
    start_time = time.time()
    
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        logger.info(f"开始AI数据库搜索: {request.query}")
        
        result = ai_db_search_service.ai_search_database(db, request.query.strip())
        
        # 限制结果数量
        if len(result["poses"]) > request.max_results:
            result["poses"] = result["poses"][:request.max_results]
        
        query_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"AI数据库搜索完成: {len(result['poses'])} 个结果，耗时 {query_time}ms")
        
        return AISearchResponse(
            poses=result["poses"],
            total=result["total"],
            search_intent=result["search_intent"],
            ai_explanation=result["ai_explanation"],
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"AI数据库搜索失败: {e}")
        raise HTTPException(
            status_code=500, 
            detail="AI数据库搜索服务暂时不可用"
        )

@router.get("/search/ai-database/explain")
async def explain_ai_search(
    query: str,
    db: Session = Depends(get_db)
):
    """
    解释AI搜索逻辑（用于调试和用户理解）
    """
    try:
        search_intent = ai_db_search_service._analyze_search_intent(query)
        sql_conditions = ai_db_search_service._generate_sql_conditions(search_intent)
        
        return {
            "user_query": query,
            "search_intent": search_intent,
            "sql_conditions": sql_conditions,
            "explanation": search_intent.get("explanation", "")
        }
        
    except Exception as e:
        logger.error(f"解释AI搜索失败: {e}")
        raise HTTPException(status_code=500, detail="解释服务不可用")