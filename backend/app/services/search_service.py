import redis
from ..config import settings

class SearchService:
    def __init__(self):
        # Redis连接（支持密码）
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,  # 添加密码
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        # 测试Redis连接
        try:
            self.redis_client.ping()
            print("Redis连接成功")
        except redis.ConnectionError:
            print("Redis连接失败，将使用降级模式")
            self.redis_client = None
