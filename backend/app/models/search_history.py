from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base

class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(200), nullable=False)
    normalized_query = Column(String(200))
    results_count = Column(Integer, default=0)
    response_time_ms = Column(Integer)
    filter_category = Column(String(50))
    user_ip = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())