from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(Enum('scene', 'mood', 'pose', 'prop', 'style', 'angle', 'lighting', 'other'), default='other')
    usage_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # 关联关系
    pose_tags = relationship("PoseTag", back_populates="tag")

class PoseTag(Base):
    __tablename__ = "pose_tags"
    
    pose_id = Column(Integer, ForeignKey("poses.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    confidence = Column(DECIMAL(3, 2), default=1.00)
    created_at = Column(TIMESTAMP, default=func.now())
    
    # 关联关系
    pose = relationship("Pose", back_populates="pose_tags")
    tag = relationship("Tag", back_populates="pose_tags")