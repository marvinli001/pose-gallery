from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PoseBase(BaseModel):
    title: str
    description: Optional[str] = None
    scene_category: Optional[str] = None
    angle: Optional[str] = None
    props: Optional[List[str]] = []
    shooting_tips: Optional[str] = None
    ai_tags: Optional[str] = None

class PoseCreate(PoseBase):
    oss_key: str
    oss_url: str
    thumbnail_url: Optional[str] = None

class PoseResponse(PoseBase):
    id: int
    oss_url: str
    thumbnail_url: Optional[str]
    view_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    q: str
    category: Optional[str] = None
    page: int = 1
    per_page: int = 20

class SearchResponse(BaseModel):
    poses: List[PoseResponse]
    total: int
    page: int
    per_page: int
    suggestions: Optional[List[str]] = []  # 搜索建议
