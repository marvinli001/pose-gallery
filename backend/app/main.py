from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, desc, or_, func
from typing import Optional
import os
import asyncio
import logging
from .database import get_db, engine
from .api import ai_search
from .api import ai_database_search  # 新增

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Pose Gallery API",
    description="摄影姿势图库API",
    version="1.0.0"
)

# CORS配置 - 放宽限制，因为通过前端代理
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，因为通过前端代理
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册外部路由模块
app.include_router(ai_search.router, prefix="/api/v1", tags=["ai-search"])
app.include_router(ai_database_search.router, prefix="/api/v1", tags=["ai-database-search"])  # 新增
# 改进的启动事件处理
@app.on_event("startup")
async def startup_event():
    try:
        # 使用同步方式测试数据库连接，避免异步问题
        def test_db_connection():
            try:
                with engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()
                return True
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                return False
        
        # 在线程池中执行数据库连接测试
        loop = asyncio.get_event_loop()
        db_connected = await loop.run_in_executor(None, test_db_connection)
        
        if db_connected:
            logger.info("✅ 数据库连接成功")
        else:
            logger.warning("❌ 数据库连接失败，将使用模拟数据运行")
            
    except Exception as e:
        logger.error(f"启动事件处理失败: {e}")

# 添加关闭事件处理
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用正在关闭...")
    # 这里可以添加清理逻辑
    try:
        # 关闭数据库连接池
        engine.dispose()
        logger.info("数据库连接池已关闭")
    except Exception as e:
        logger.error(f"关闭时出现错误: {e}")

@app.get("/")
async def root():
    return {
        "message": "Pose Gallery API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    # 测试数据库连接状态
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status
    }

@app.get("/api/v1/poses")
async def get_poses(
    q: Optional[str] = None,
    category: Optional[str] = None,
    angle: Optional[str] = None,
    sort: str = "latest",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取姿势列表"""
    try:
        # 构建基础查询条件
        conditions = ["status = 'active'"]
        params = {}
        
        # 搜索条件
        if q and q.strip():
            conditions.append("""
                (title LIKE :search_term 
                OR description LIKE :search_term 
                OR ai_tags LIKE :search_term)
            """)
            params['search_term'] = f"%{q.strip()}%"
        
        # 分类筛选
        if category:
            conditions.append("scene_category = :category")
            params['category'] = category
        
        # 角度筛选
        if angle:
            conditions.append("angle = :angle")
            params['angle'] = angle
        
        # 排序
        sort_mapping = {
            'latest': 'created_at DESC',
            'popular': 'view_count DESC',
            'view_count': 'view_count DESC'
        }
        order_by = sort_mapping.get(sort, 'created_at DESC')
        
        # 分页
        offset = (page - 1) * per_page
        
        # 构建查询
        where_clause = " AND ".join(conditions)
        
        # 获取总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM poses 
            WHERE {where_clause}
        """
        
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result[0] if count_result else 0
        
        # 获取数据
        data_sql = f"""
            SELECT 
                id, oss_url, thumbnail_url, title, description,
                scene_category, angle, shooting_tips, ai_tags,
                view_count, created_at
            FROM poses 
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """
        
        params.update({
            'limit': per_page,
            'offset': offset
        })
        
        results = db.execute(text(data_sql), params).fetchall()
        
        # 转换结果
        poses = []
        for row in results:
            pose_data = {
                'id': row[0],
                'oss_url': row[1],
                'thumbnail_url': row[2],
                'title': row[3] or '',
                'description': row[4] or '',
                'scene_category': row[5],
                'angle': row[6],
                'shooting_tips': row[7],
                'ai_tags': row[8] or '',
                'view_count': row[9] or 0,
                'created_at': row[10].isoformat() if row[10] else None
            }
            poses.append(pose_data)
        
        return {
            "poses": poses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "hasMore": offset + len(poses) < total
        }
        
    except Exception as e:
        print(f"数据库查询错误: {e}")
        # 返回模拟数据作为降级
        return {
            "poses": [
                {
                    "id": 1,
                    "oss_url": "/placeholder.svg",
                    "title": "咖啡馆窗边坐姿",
                    "description": "自然光线下的优雅坐姿，适合表现文艺气质",
                    "scene_category": "咖啡馆",
                    "angle": "侧面",
                    "shooting_tips": "利用窗边自然光，注意光影对比",
                    "ai_tags": "咖啡馆,坐姿,自然光,文艺",
                    "view_count": 128,
                    "created_at": "2024-01-15T10:30:00"
                },
                {
                    "id": 2,
                    "oss_url": "/placeholder.svg",
                    "title": "街头漫步姿势",
                    "description": "城市街头的自然行走姿态，展现都市生活感",
                    "scene_category": "街头",
                    "angle": "全身",
                    "shooting_tips": "捕捉自然行走瞬间，背景虚化突出主体",
                    "ai_tags": "街头,行走,都市,全身",
                    "view_count": 96,
                    "created_at": "2024-01-14T16:45:00"
                },
                {
                    "id": 3,
                    "oss_url": "/placeholder.svg",
                    "title": "室内人像经典pose",
                    "description": "适合室内环境的经典人像姿势",
                    "scene_category": "室内",
                    "angle": "半身",
                    "shooting_tips": "注意室内灯光布置，避免过度曝光",
                    "ai_tags": "室内,人像,经典,半身",
                    "view_count": 234,
                    "created_at": "2024-01-13T14:20:00"
                }
            ],
            "total": 3,
            "page": page,
            "per_page": per_page,
            "hasMore": False
        }

@app.get("/api/v1/scenes")
async def get_scenes(db: Session = Depends(get_db)):
    """获取场景分类统计"""
    try:
        # 查询每个分类的数量
        result = db.execute(text("""
            SELECT scene_category, COUNT(*) as count 
            FROM poses 
            WHERE status = 'active' AND scene_category IS NOT NULL
            GROUP BY scene_category
            ORDER BY count DESC
        """))
        
        scenes = []
        # 图标映射
        icon_mapping = {
            "室内": "🏠", "咖啡馆": "☕", "街头": "🏙️", 
            "户外": "🌿", "人像": "👤", "情侣": "💕",
            "商务": "💼", "创意": "🎨"
        }
        
        for row in result:
            category = row[0]
            icon = "📸"  # 默认图标
            for key, value in icon_mapping.items():
                if key in category:
                    icon = value
                    break
                    
            scenes.append({
                "id": category.lower().replace(' ', '_').replace('拍摄', '').replace('摄影', ''),
                "name": category,
                "count": row[1],
                "icon": icon
            })
        
        return {"scenes": scenes}
        
    except Exception as e:
        print(f"数据库查询错误: {e}")
        # 返回模拟数据
        return {
            "scenes": [
                { "id": "indoor", "name": "室内拍摄", "icon": "🏠", "count": 120 },
                { "id": "outdoor", "name": "户外拍摄", "icon": "🌿", "count": 95 },
                { "id": "portrait", "name": "人像写真", "icon": "👤", "count": 156 },
                { "id": "couple", "name": "情侣拍照", "icon": "💕", "count": 78 },
                { "id": "street", "name": "街头摄影", "icon": "🏙️", "count": 89 },
                { "id": "cafe", "name": "咖啡馆", "icon": "☕", "count": 67 },
                { "id": "business", "name": "商务形象", "icon": "💼", "count": 43 },
                { "id": "creative", "name": "创意摄影", "icon": "🎨", "count": 92 }
            ]
        }

@app.get("/api/v1/search/suggestions")
async def get_suggestions(
    q: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取搜索建议"""
    try:
        # 从标题和标签中获取建议
        result = db.execute(text("""
            SELECT DISTINCT title 
            FROM poses 
            WHERE status = 'active' 
            AND title LIKE :prefix 
            AND title IS NOT NULL
            LIMIT 10
        """), {"prefix": f"%{q}%"})
        
        suggestions = [row[0] for row in result if row[0]]
        
        # 如果建议不够，添加一些固定建议
        if len(suggestions) < 5:
            fixed_suggestions = [
                '室内人像', '咖啡馆拍照', '街头摄影', '情侣写真',
                '商务头像', '自然光人像', '创意构图', '半身照',
                '全身照', '侧面角度', '逆光摄影', '优雅姿势'
            ]
            
            for suggestion in fixed_suggestions:
                if q.lower() in suggestion.lower() and suggestion not in suggestions:
                    suggestions.append(suggestion)
                    if len(suggestions) >= 8:
                        break
        
        return suggestions
        
    except Exception as e:
        print(f"搜索建议查询错误: {e}")
        # 返回固定建议
        return ['室内人像', '咖啡馆拍照', '街头摄影', '情侣写真']