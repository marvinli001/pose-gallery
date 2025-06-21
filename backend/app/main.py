from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 创建FastAPI应用
app = FastAPI(
    title="Pose Gallery API",
    description="摄影姿势图库API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路径
@app.get("/")
async def root():
    return {
        "message": "Pose Gallery API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 临时搜索接口
@app.get("/api/v1/search")
async def search(q: str = "", page: int = 1, per_page: int = 20):
    # 返回模拟数据
    return {
        "poses": [
            {
                "id": 1,
                "oss_url": "https://example.com/image1.jpg",
                "title": "咖啡馆休闲坐姿",
                "description": "在咖啡馆窗边的自然坐姿",
                "scene_category": "咖啡馆",
                "view_count": 100,
                "created_at": "2024-01-01T00:00:00"
            }
        ],
        "total": 1,
        "page": page,
        "per_page": per_page
    }

@app.get("/api/v1/categories")
async def get_categories():
    return [
        {"name": "咖啡馆", "count": 10},
        {"name": "街头", "count": 20},
        {"name": "室内", "count": 15}
    ]

@app.get("/api/v1/search/suggestions")
async def get_suggestions(prefix: str):
    # 模拟搜索建议
    suggestions = ["咖啡馆", "咖啡厅", "街拍", "街头", "坐姿", "站姿"]
    return [s for s in suggestions if s.startswith(prefix)]
