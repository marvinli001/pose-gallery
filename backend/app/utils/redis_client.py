import redis
from typing import Optional
from ..config import settings

class RedisClient:
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_instance(cls) -> Optional[redis.Redis]:
        """获取Redis单例实例"""
        if cls._instance is None:
            try:
                cls._instance = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # 测试连接
                cls._instance.ping()
                print(f"Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except redis.ConnectionError as e:
                print(f"Redis连接失败: {e}")
                cls._instance = None
        
        return cls._instance
    
    @classmethod
    def close(cls):
        """关闭Redis连接"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
