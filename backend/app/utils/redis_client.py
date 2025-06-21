import redis
import json
import logging
from typing import Any, Optional, Dict, List
from ..config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端封装"""
    
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)
        self._test_connection()
    
    def _test_connection(self):
        """测试Redis连接"""
        try:
            self.client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis GET失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """设置值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            if expire:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET失败 {key}: {e}")
    
    def setex(self, key: str, expire: int, value: Any):
        """设置值并指定过期时间"""
        self.set(key, value, expire)
    
    def delete(self, key: str):
        """删除键"""
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE失败 {key}: {e}")
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS失败 {key}: {e}")
            return False
    
    def expire(self, key: str, seconds: int):
        """设置过期时间"""
        try:
            self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE失败 {key}: {e}")
    
    def ttl(self, key: str) -> int:
        """获取剩余生存时间"""
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL失败 {key}: {e}")
            return -1
    
    def keys(self, pattern: str) -> List[str]:
        """查找匹配模式的键"""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS失败 {pattern}: {e}")
            return []
    
    def cache_search_result(self, query: str, category: str, page: int, result: Dict):
        """缓存搜索结果"""
        cache_key = f"search:{query}:{category or 'all'}:{page}"
        self.setex(cache_key, settings.search_cache_expire_time, result)
    
    def get_cached_search_result(self, query: str, category: str, page: int) -> Optional[Dict]:
        """获取缓存的搜索结果"""
        cache_key = f"search:{query}:{category or 'all'}:{page}"
        return self.get(cache_key)
    
    def cache_pose_detail(self, pose_id: int, pose_data: Dict):
        """缓存姿势详情"""
        cache_key = f"pose:{pose_id}"
        self.setex(cache_key, settings.cache_expire_time, pose_data)
    
    def get_cached_pose_detail(self, pose_id: int) -> Optional[Dict]:
        """获取缓存的姿势详情"""
        cache_key = f"pose:{pose_id}"
        return self.get(cache_key)
    
    def increment_view_count(self, pose_id: int) -> int:
        """增加浏览次数"""
        cache_key = f"view_count:{pose_id}"
        try:
            return self.client.incr(cache_key)
        except Exception as e:
            logger.error(f"增加浏览次数失败 {pose_id}: {e}")
            return 0
    
    def get_popular_searches(self, limit: int = 10) -> List[Dict]:
        """获取热门搜索"""
        cache_key = "popular_searches"
        cached = self.get(cache_key)
        if cached:
            return cached[:limit]
        return []
    
    def update_popular_searches(self, searches: List[Dict]):
        """更新热门搜索"""
        cache_key = "popular_searches"
        self.setex(cache_key, 3600, searches)  # 缓存1小时