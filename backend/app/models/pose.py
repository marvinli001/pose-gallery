from sqlalchemy import Column, Integer, String, Text, JSON, TIMESTAMP, Enum, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Pose(Base):
    __tablename__ = "poses"
    
    id = Column(Integer, primary_key=True, index=True)
    oss_key = Column(String(255), unique=True, nullable=False)
    oss_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    title = Column(String(200))
    description = Column(Text)
    scene_category = Column(String(50))
    angle = Column(String(50))
    props = Column(JSON)
    shooting_tips = Column(Text)
    ai_tags = Column(Text)
    
    # AI分析相关
    ai_analyzed_at = Column(TIMESTAMP)
    ai_confidence = Column(DECIMAL(3, 2), default=0.90)
    processing_status = Column(Enum('pending', 'processing', 'completed', 'failed'), default='pending')
    error_message = Column(Text)
    
    # 统计字段
    view_count = Column(Integer, default=0)
    search_count = Column(Integer, default=0)
    
    # 时间字段
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # 状态字段
    status = Column(Enum('pending', 'active', 'hidden'), default='active')
    
    # 关联关系
    pose_tags = relationship("PoseTag", back_populates="pose")