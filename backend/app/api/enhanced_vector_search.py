from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import logging
import os

from ..services.enhanced_vector_search_service import EnhancedVectorSearchService
from ..services.enhanced_ai_analyzer import EnhancedAIAnalyzer
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# 获取向量索引路径
INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", "backend/vector_index/faiss.index")
ID_MAP_PATH = os.getenv("VECTOR_ID_MAP_PATH", "backend/vector_index/id_map.json")

# 全局服务实例，启动时初始化
_enhanced_vector_service = None
_enhanced_ai_analyzer = None

def get_enhanced_service():
    global _enhanced_vector_service
    if _enhanced_vector_service is None:
        _enhanced_vector_service = EnhancedVectorSearchService(INDEX_PATH, ID_MAP_PATH)
    return _enhanced_vector_service

def get_enhanced_analyzer():
    global _enhanced_ai_analyzer
    if _enhanced_ai_analyzer is None:
        _enhanced_ai_analyzer = EnhancedAIAnalyzer()
    return _enhanced_ai_analyzer


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    use_adaptive: bool = True
    use_enhanced: bool = True
    search_mode: str = "multi_stage"  # multi_stage, semantic_boost, hybrid, dynamic, paginated, multi_tier
    min_similarity: float = 0.3
    category_filter: Optional[str] = None
    angle_filter: Optional[str] = None
    # 新增分页参数
    page: int = 1
    page_size: int = 20
    # 新增动态搜索参数
    target_count: int = 20


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
    match_reason: str | None = None  # 匹配原因说明


class VectorSearchResponse(BaseModel):
    poses: List[PoseWithScore]
    total: int
    query_time_ms: int
    service_available: bool = True
    search_info: Dict = {}
    enhanced_info: Dict = {}  # 增强功能信息


class QueryAnalysisResponse(BaseModel):
    analysis: Dict[str, Any]
    suggestions: List[str]
    enhanced_query: str
    scene_keywords: List[str]
    pose_keywords: List[str]
    style_keywords: List[str]


@router.get("/search/vector/enhanced/status")
async def enhanced_vector_search_status():
    """检查增强版向量搜索服务状态"""
    try:
        service = get_enhanced_service()
        analyzer = get_enhanced_analyzer()
        
        return {
            "vector_service_available": service.is_available(),
            "ai_analyzer_available": analyzer.is_available(),
            "enhanced_features": {
                "multi_stage_search": True,
                "semantic_boost": True,
                "hybrid_search": True,
                "query_analysis": analyzer.is_available(),
                "intelligent_reranking": True
            },
            "message": "增强版向量搜索服务状态检查完成"
        }
    except Exception as e:
        logger.error(f"状态检查失败: {e}")
        return {
            "vector_service_available": False,
            "ai_analyzer_available": False,
            "enhanced_features": {
                "multi_stage_search": False,
                "semantic_boost": False,
                "hybrid_search": False,
                "query_analysis": False,
                "intelligent_reranking": False
            },
            "message": f"增强版向量搜索服务不可用: {str(e)}"
        }


@router.post("/search/vector/enhanced/analyze", response_model=QueryAnalysisResponse)
async def analyze_query(
    query: str,
    analyzer: EnhancedAIAnalyzer = Depends(get_enhanced_analyzer)
):
    """分析搜索查询，提供优化建议"""
    try:
        start = time.time()
        
        # 使用增强AI分析器
        analysis_result = analyzer.analyze_search_query(query)
        
        # 提取关键信息
        analysis = analysis_result.get("analysis", {})
        enhanced_query = analysis_result.get("enhanced_query", query)
        
        # 分类关键词
        scene_keywords = analysis.get("scene_related", [])
        pose_keywords = analysis.get("pose_related", [])
        style_keywords = analysis.get("style_related", [])
        
        # 生成搜索建议
        suggestions = []
        if analysis.get("intent") == "场景搜索":
            suggestions.append("尝试添加具体的拍摄角度，如「全身」「半身」「特写」")
        elif analysis.get("intent") == "姿势搜索":
            suggestions.append("可以结合场景关键词，如「室内坐姿」「户外站立」")
        elif analysis.get("intent") == "风格搜索":
            suggestions.append("建议添加具体场景，如「文艺咖啡馆」「商务办公室」")
        
        if not scene_keywords and not pose_keywords:
            suggestions.append("建议使用更具体的描述词汇")
        
        query_time = int((time.time() - start) * 1000)
        
        return QueryAnalysisResponse(
            analysis=analysis,
            suggestions=suggestions,
            enhanced_query=enhanced_query,
            scene_keywords=scene_keywords,
            pose_keywords=pose_keywords,
            style_keywords=style_keywords
        )
        
    except Exception as e:
        logger.error(f"查询分析失败: {e}")
        # 返回基础分析结果
        return QueryAnalysisResponse(
            analysis={"intent": "未知", "confidence": 0.0},
            suggestions=["请尝试使用更具体的关键词"],
            enhanced_query=query,
            scene_keywords=[],
            pose_keywords=[],
            style_keywords=[]
        )


@router.post("/search/vector/enhanced", response_model=VectorSearchResponse)
async def enhanced_vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    enhanced_service: EnhancedVectorSearchService = Depends(get_enhanced_service),
    analyzer: EnhancedAIAnalyzer = Depends(get_enhanced_analyzer)
):
    """增强版向量搜索 - 多模式智能检索"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # 检查服务是否可用
    if not enhanced_service.is_available():
        logger.warning("增强版向量搜索服务不可用，返回空结果")
        return VectorSearchResponse(
            poses=[], 
            total=0, 
            query_time_ms=0,
            service_available=False,
            enhanced_info={"error": "增强版向量搜索服务不可用"}
        )
    
    try:
        start = time.time()
        
        # 第一步：查询分析和优化
        enhanced_query = request.query
        query_analysis = {}
        
        if request.use_enhanced and analyzer.is_available():
            try:
                analysis_result = analyzer.analyze_search_query(request.query)
                query_analysis = analysis_result.get("analysis", {})
                enhanced_query = analysis_result.get("enhanced_query", request.query)
            except Exception as e:
                logger.warning(f"查询分析失败，使用原始查询: {e}")
        
        # 第二步：根据搜索模式执行搜索
        ids_scores = []
        search_method = "标准向量搜索"
        
        if request.search_mode == "multi_stage":
            # 多阶段搜索
            ids_scores = enhanced_service.multi_stage_search(
                query=enhanced_query,
                final_k=request.top_k,
                stage1_k=min(100, request.top_k * 5),
                min_similarity=request.min_similarity
            )
            search_method = "多阶段向量搜索"

        elif request.search_mode == "dynamic":
            # 动态阈值搜索
            ids_scores = enhanced_service.search_with_dynamic_threshold(
                query=enhanced_query,
                target_count=request.target_count,
                min_similarity=request.min_similarity
            )
            search_method = "动态阈值搜索"
            
        elif request.search_mode == "paginated":
            # 分页搜索
            search_result = enhanced_service.search_with_pagination(
                query=enhanced_query,
                page=request.page,
                page_size=request.page_size,
                similarity_threshold=2.0 - request.min_similarity  # 转换为距离阈值
            )
            ids_scores = search_result['results']
            search_method = "分页搜索"
            
            # 添加分页信息到搜索信息中
            search_info = {
                "found_results": len(ids_scores),
                "total_results": search_result['total'],
                "current_page": search_result['page'],
                "has_next_page": search_result['has_next'],
                "search_method": search_method
            }
            
        elif request.search_mode == "multi_tier":
            # 多层次搜索
            ids_scores = enhanced_service.multi_tier_search(
                query=enhanced_query,
                target_count=request.target_count
            )
            search_method = "多层次搜索"
            
        elif request.search_mode == "semantic_boost":
            # 语义增强搜索 - 目前使用基础搜索
            ids_scores = enhanced_service.search(
                query=enhanced_query,
                top_k=request.top_k
            )
            search_method = "语义增强搜索"
            
        elif request.search_mode == "hybrid":
            # 混合搜索 - 目前使用基础搜索
            ids_scores = enhanced_service.search(
                query=enhanced_query,
                top_k=request.top_k
            )
            search_method = "混合搜索"
            
        else:
            # 标准搜索
            ids_scores = enhanced_service.search(enhanced_query, top_k=request.top_k)
        
        pose_ids = [pid for pid, _ in ids_scores]

        if not pose_ids:
            return VectorSearchResponse(
                poses=[], 
                total=0, 
                query_time_ms=int((time.time() - start) * 1000),
                service_available=True,
                search_info={
                    "message": "未找到相关结果，请尝试其他关键词",
                    "suggestion": "尝试使用更通用的词汇，如「人像」「室内」「户外」等",
                    "enhanced_query": enhanced_query,
                    "search_method": search_method
                },
                enhanced_info={"query_analysis": query_analysis}
            )

        # 构建数据库查询，添加过滤条件
        where_conditions = ["id IN :ids", "status = 'active'"]
        params = {"ids": tuple(pose_ids)}
        
        if request.category_filter:
            where_conditions.append("scene_category = :category")
            params["category"] = request.category_filter
            
        if request.angle_filter:
            where_conditions.append("angle = :angle")
            params["angle"] = request.angle_filter
        
        where_clause = " AND ".join(where_conditions)
        
        result = db.execute(
            text(
                f"""
                SELECT id, oss_url, thumbnail_url, title, description,
                       scene_category, angle, shooting_tips, ai_tags,
                       view_count, created_at
                FROM poses
                WHERE {where_clause}
                """
            ),
            params,
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

        # 第三步：智能重排序和匹配原因生成
        poses = []
        for pid, score in ids_scores:
            data = pose_dict.get(pid)
            if data:
                # 生成匹配原因
                match_reason = _generate_match_reason(
                    data, enhanced_query, score, query_analysis
                )
                
                poses.append({
                    **data, 
                    "score": score,
                    "match_reason": match_reason
                })

        # 如果启用了增强功能，进行智能重排序
        if request.use_enhanced and len(poses) > 1:
            poses = _intelligent_rerank(poses, enhanced_query, query_analysis)

        query_time = int((time.time() - start) * 1000)
        
        # 生成搜索信息
        search_info = {
            "found_results": len(poses),
            "search_method": search_method,
            "enhanced_query": enhanced_query,
            "avg_similarity": round(sum(p["score"] for p in poses) / len(poses), 3) if poses else 0,
            "filters_applied": {
                "category": request.category_filter,
                "angle": request.angle_filter
            }
        }
        
        # 生成增强信息
        enhanced_info = {
            "query_analysis": query_analysis,
            "original_query": request.query,
            "enhanced_query": enhanced_query,
            "search_mode": request.search_mode,
            "ai_analyzer_used": analyzer.is_available(),
            "intelligent_reranking": request.use_enhanced
        }
        
        if poses:
            min_score = min(p["score"] for p in poses)
            max_score = max(p["score"] for p in poses)
            search_info["similarity_range"] = f"{min_score:.3f} - {max_score:.3f}"
            
            if min_score < request.min_similarity:
                search_info["quality_warning"] = "部分结果相关性较低，建议调整搜索词"
        
        return VectorSearchResponse(
            poses=poses, 
            total=len(poses), 
            query_time_ms=query_time,
            service_available=True,
            search_info=search_info,
            enhanced_info=enhanced_info
        )
        
    except Exception as e:
        logger.error(f"增强向量搜索执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"增强向量搜索失败: {str(e)}")


@router.post("/search/vector", response_model=VectorSearchResponse)
async def vector_search_compatibility(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
):
    """向量搜索兼容性接口 - 自动使用增强版功能"""
    try:
        enhanced_service = get_enhanced_service()
        analyzer = get_enhanced_analyzer()
        
        # 自动启用增强功能
        request.use_enhanced = True
        request.search_mode = "multi_stage"
        
        # 调用增强版搜索
        return await enhanced_vector_search(request, db, enhanced_service, analyzer)
        
    except Exception as e:
        logger.error(f"向量搜索兼容性接口失败: {e}")
        # 返回基础错误响应
        return VectorSearchResponse(
            poses=[], 
            total=0, 
            query_time_ms=0,
            service_available=False,
            enhanced_info={"error": f"向量搜索失败: {str(e)}"}
        )


def _generate_match_reason(
    pose_data: Dict[str, Any], 
    query: str, 
    score: float, 
    analysis: Dict[str, Any]
) -> str:
    """生成匹配原因说明"""
    reasons = []
    
    # 基于相似度分数
    if score > 0.8:
        reasons.append("高度相关")
    elif score > 0.6:
        reasons.append("较为相关")
    elif score > 0.4:
        reasons.append("部分相关")
    else:
        reasons.append("弱相关")
    
    # 基于分析结果
    if analysis:
        intent = analysis.get("intent", "")
        if intent == "场景搜索" and pose_data.get("scene_category"):
            reasons.append(f"场景匹配: {pose_data['scene_category']}")
        elif intent == "姿势搜索" and pose_data.get("angle"):
            reasons.append(f"角度匹配: {pose_data['angle']}")
        elif intent == "风格搜索" and pose_data.get("ai_tags"):
            reasons.append("风格标签匹配")
    
    # 基于文本匹配
    query_lower = query.lower()
    if pose_data.get("title") and any(word in pose_data["title"].lower() for word in query_lower.split()):
        reasons.append("标题匹配")
    elif pose_data.get("ai_tags") and any(word in pose_data["ai_tags"].lower() for word in query_lower.split()):
        reasons.append("标签匹配")
    
    return " · ".join(reasons) if reasons else "语义匹配"


def _intelligent_rerank(
    poses: List[Dict[str, Any]], 
    query: str, 
    analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """智能重排序"""
    # 简化版重排序逻辑
    # 可以根据查询意图、用户偏好等进行更复杂的排序
    
    def rerank_score(pose):
        base_score = pose["score"]
        
        # 根据查看次数调整
        view_boost = min(0.1, pose.get("view_count", 0) / 1000)
        
        # 根据查询意图调整
        intent_boost = 0.0
        if analysis.get("intent") == "场景搜索":
            if pose.get("scene_category"):
                intent_boost = 0.05
        elif analysis.get("intent") == "姿势搜索":
            if pose.get("angle"):
                intent_boost = 0.05
        
        return base_score + view_boost + intent_boost
    
    # 按重排序分数排序
    poses.sort(key=rerank_score, reverse=True)
    return poses


# 向后兼容的路由别名
@router.get("/search/vector/status")
async def vector_search_status():
    """向量搜索状态检查 - 兼容性接口"""
    return await enhanced_vector_search_status()

# 在现有的路由中添加新端点：

@router.post("/search/vector/paginated", response_model=VectorSearchResponse)
async def paginated_vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    enhanced_service: EnhancedVectorSearchService = Depends(get_enhanced_service),
):
    """专门的分页向量搜索端点"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not enhanced_service.is_available():
        return VectorSearchResponse(
            poses=[], 
            total=0, 
            query_time_ms=0,
            service_available=False
        )
    
    try:
        start = time.time()
        
        # 强制使用分页搜索
        search_result = enhanced_service.search_with_pagination(
            query=request.query,
            page=request.page,
            page_size=min(request.page_size, 50),  # 限制最大页大小
            similarity_threshold=2.0 - request.min_similarity
        )
        
        ids_scores = search_result['results']
        pose_ids = [pid for pid, _ in ids_scores]

        if not pose_ids:
            return VectorSearchResponse(
                poses=[], 
                total=search_result['total'], 
                query_time_ms=int((time.time() - start) * 1000),
                service_available=True,
                search_info={
                    "message": "当前页无结果",
                    "total_results": search_result['total'],
                    "current_page": search_result['page'],
                    "has_next_page": search_result['has_next']
                }
            )

        # 查询数据库获取pose详情
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

        pose_dict = {row[0]: {
            "id": row[0],
            "oss_url": row[1],
            "thumbnail_url": row[2],
            "title": row[3] or "",
            "description": row[4] or "",
            "scene_category": row[5],
            "angle": row[6],
            "shooting_tips": row[7],
            "ai_tags": row[8],
            "view_count": row[9] or 0,
            "created_at": row[10].isoformat() if row[10] else None,
        } for row in result}

        poses = []
        for pid, score in ids_scores:
            data = pose_dict.get(pid)
            if data:
                poses.append({**data, "score": score})

        query_time = int((time.time() - start) * 1000)
        
        return VectorSearchResponse(
            poses=poses, 
            total=search_result['total'], 
            query_time_ms=query_time,
            service_available=True,
            search_info={
                "found_results": len(poses),
                "total_results": search_result['total'],
                "current_page": search_result['page'],
                "has_next_page": search_result['has_next'],
                "search_method": "分页搜索",
                "page_size": request.page_size
            }
        )
        
    except Exception as e:
        logger.error(f"分页向量搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")