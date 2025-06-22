#!/bin/bash

echo "🚀 Pose Gallery Docker 部署脚本"
echo "================================="

# 检查.env文件
if [ ! -f .env ]; then
    echo "❌ 未找到 .env 文件，请先复制 .env.example 为 .env 并配置"
    exit 1
fi

# 读取部署模式
source .env
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-local}

echo "📋 当前部署模式: $DEPLOYMENT_MODE"

# 停止现有容器
echo "🛑 停止现有容器..."
docker-compose down
docker-compose -f docker-compose-external.yml down 2>/dev/null || true

# 根据部署模式选择配置文件
if [ "$DEPLOYMENT_MODE" = "external" ]; then
    echo "🌐 使用外部数据库模式..."
    
    # 测试外部数据库连接
    echo "🔍 测试外部数据库连接..."
    if command -v mysql &> /dev/null; then
        mysql -h"${EXTERNAL_DB_HOST}" -P"${EXTERNAL_DB_PORT}" -u"${EXTERNAL_DB_USER}" -p"${EXTERNAL_DB_PASS}" -e "SELECT 1;" 2>/dev/null && echo "✅ MySQL连接成功" || echo "❌ MySQL连接失败"
    fi
    
    if command -v redis-cli &> /dev/null; then
        redis-cli -h "${EXTERNAL_REDIS_HOST}" -p "${EXTERNAL_REDIS_PORT}" ${EXTERNAL_REDIS_PASSWORD:+-a $EXTERNAL_REDIS_PASSWORD} ping 2>/dev/null && echo "✅ Redis连接成功" || echo "❌ Redis连接失败"
    fi
    
    docker-compose -f docker-compose-external.yml up -d
else
    echo "🏠 使用本地容器数据库模式..."
    docker-compose up -d
fi

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
echo "Backend健康检查:"
curl -f http://localhost:8000/health || echo "❌ Backend未就绪"

echo "Frontend检查:"
curl -f http://localhost:3000 || echo "❌ Frontend未就绪"

echo ""
echo "🎉 部署完成！"
echo "📱 前端地址: http://localhost:3000"
echo "🔧 后端API: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"