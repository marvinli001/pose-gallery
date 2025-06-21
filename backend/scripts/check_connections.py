import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import engine
from app.utils.redis_client import RedisClient

def check_mysql():
    """检查MySQL连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ MySQL连接成功")
            
            # 检查表是否存在
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = 'poses'",
                (settings.DB_NAME,)
            )
            if result.fetchone()[0] == 0:
                print("❌ poses表不存在，请先运行 init_db.py")
                return False
            else:
                print("✅ 数据库表已就绪")
        return True
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return False

def check_redis():
    """检查Redis连接"""
    redis = RedisClient.get_instance()
    if redis:
        print("✅ Redis连接成功")
        return True
    else:
        print("⚠️  Redis连接失败，搜索建议功能将不可用")
        return False

if __name__ == "__main__":
    mysql_ok = check_mysql()
    redis_ok = check_redis()
    
    if not mysql_ok:
        print("\n请检查MySQL配置并初始化数据库")
        sys.exit(1)
    
    if not redis_ok:
        print("\n搜索将在降级模式下运行（无自动补全）")
    
    print("\n所有检查完成，可以启动服务")
