from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Enum, Index
from sqlalchemy.sql import func
from ..database import Base

class Pose(Base):
    __tablename__ = "poses"
    
    id = Column(Integer, primary_key=True, index=True)
    oss_key = Column(String(255), unique=True, nullable=False)
    oss_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    title = Column(String(200))
    description = Column(Text)
    scene_category = Column(String(50), index=True)
    angle = Column(String(50))
    props = Column(JSON)
    shooting_tips = Column(Text)
    ai_tags = Column(Text)  # 逗号分隔的标签
    
    # 统计字段
    view_count = Column(Integer, default=0)
    search_count = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(Enum('pending', 'active', 'hidden'), default='active')
    
    # 创建索引
    __table_args__ = (
        Index('idx_fulltext', 'title', 'description', 'ai_tags'),
    )
