import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.config import settings
import redis
from sqlalchemy import text

def check_mysql():
    """检查MySQL连接"""
    try:
        with engine.connect() as connection:
            # 使用 text() 包装 SQL 语句
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
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        r.ping()
        print(f"✅ Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
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
    elif mysql_ok:
        print("\n⚠️ MySQL正常，Redis异常（Redis是可选的，不影响基本功能）")
    else:
        print("\n❌ 请检查服务配置")

if __name__ == "__main__":
    main()