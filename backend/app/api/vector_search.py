from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Tuple

from ..services.vector_search_service import VectorSearchService

router = APIRouter()

# Dependency to create service instance

def get_service():
    return VectorSearchService()


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10


class VectorSearchResponse(BaseModel):
    results: List[Tuple[int, float]]


@router.post("/search/vector", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchRequest, service: VectorSearchService = Depends(get_service)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        results = service.search(request.query, top_k=request.top_k)
        return VectorSearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
