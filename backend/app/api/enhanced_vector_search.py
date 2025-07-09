@router.post("/search/vector/enhanced", response_model=VectorSearchResponse)
async def enhanced_vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    enhanced_service: EnhancedVectorSearchService = Depends(get_enhanced_service),
):
    """增强版向量搜索 - 多阶段检索"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        start = time.time()
        
        # 多阶段搜索
        ids_scores = enhanced_service.multi_stage_search(
            query=request.query,
            final_k=request.top_k,
            stage1_k=min(100, request.top_k * 5),  # 第一阶段召回5倍数量
            min_similarity=0.3
        )
        
        # 后续处理逻辑与原来相同...
        
        search_info = {
            "found_results": len(poses),
            "search_method": "多阶段向量搜索",
            "stage1_candidates": min(100, request.top_k * 5),
            "final_results": len(poses),
            "avg_similarity": round(sum(p["score"] for p in poses) / len(poses), 3) if poses else 0
        }
        
        return VectorSearchResponse(
            poses=poses,
            total=len(poses),
            query_time_ms=query_time,
            service_available=True,
            search_info=search_info
        )
        
    except Exception as e:
        logger.error(f"增强向量搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")