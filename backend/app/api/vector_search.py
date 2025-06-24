from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

from ..services.vector_search_service import VectorSearchService
from ..database import get_db

router = APIRouter()

# Dependency to create service instance


def get_service():
    return VectorSearchService()


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10


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


@router.post("/search/vector", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db),
    service: VectorSearchService = Depends(get_service),
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        start = time.time()
        ids_scores = service.search(request.query, top_k=request.top_k)
        pose_ids = [pid for pid, _ in ids_scores]

        if not pose_ids:
            return VectorSearchResponse(
                poses=[], total=0, query_time_ms=int((time.time() - start) * 1000)
            )

        result = db.execute(
            text(
                """
                SELECT id, oss_url, thumbnail_url, title, description,
                       scene_category, angle, shooting_tips, ai_tags,
                       view_count, created_at
                FROM poses
                WHERE id IN :ids
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
        return VectorSearchResponse(
            poses=poses, total=len(poses), query_time_ms=query_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

