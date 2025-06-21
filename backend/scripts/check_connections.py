import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.config import settings
import redis
from sqlalchemy import text
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_mysql():
    """检查MySQL连接"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ MySQL连接成功")
        return True
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return False

def check_redis():
    """检查Redis连接"""
    try:
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,  # 添加超时设置
            socket_timeout=5
        )
        r.ping()
        print(f"✅ Redis连接成功: {settings.redis_host}:{settings.redis_port}")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def main():
    print("=== 连接状态检查 ===\n")
    
    mysql_ok = check_mysql()
    redis_ok = check_redis()
    
    if mysql_ok and redis_ok:
        print("\n🎉 所有服务连接正常！")
        return 0
    elif mysql_ok:
        print("\n⚠️ MySQL正常，Redis异常（Redis是可选的，不影响基本功能）")
        return 0
    else:
        print("\n❌ 请检查服务配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)