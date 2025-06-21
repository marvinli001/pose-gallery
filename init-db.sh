#!/bin/bash

echo "🗄️ 数据库初始化脚本"
echo "==================="

# 检查部署模式
source .env
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-local}

if [ "$DEPLOYMENT_MODE" = "local" ]; then
    echo "🏠 本地数据库模式 - 等待MySQL容器启动..."
    
    # 等待MySQL容器就绪
    until docker-compose exec mysql mysqladmin ping -h"localhost" --silent; do
        echo "⏳ 等待MySQL启动..."
        sleep 2
    done
    
    echo "✅ MySQL已就绪，执行数据库初始化..."
    docker-compose exec backend python scripts/init_db.py
else
    echo "🌐 外部数据库模式 - 直接初始化..."
    docker-compose exec backend python scripts/init_db.py
fi

echo "🎉 数据库初始化完成！"