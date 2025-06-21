#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 检查MySQL连接
echo "检查MySQL连接..."
python -c "
import pymysql
from app.config import settings
try:
    conn = pymysql.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        database=settings.DB_NAME
    )
    print('MySQL连接成功')
    conn.close()
except Exception as e:
    print(f'MySQL连接失败: {e}')
    exit(1)
"

# 检查Redis连接
echo "检查Redis连接..."
python -c "
from app.utils.redis_client import RedisClient
redis = RedisClient.get_instance()
if redis:
    print('Redis连接成功')
else:
    print('Redis连接失败，将在降级模式下运行')
"

# 启动服务
echo "启动FastAPI服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
