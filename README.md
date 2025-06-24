# Pose Gallery ![Platform](https://img.shields.io/badge/Platform-Docker-blue?logo=docker&logoColor=white) ![License](https://img.shields.io/badge/license-MIT-green.svg)

> 📸 **AI 驱动的摄影姿势图库**
>
> 结合 FastAPI 与 Next.js，自动从 OSS 导入图片并调用 OpenAI 进行分析，提供智能搜索与一键部署。

## 目录结构

```text
backend/   # FastAPI 应用和脚本
frontend/  # Next.js 前端应用
migrations/ # MySQL 初始化脚本
scripts/    # 自动化处理与管理工具
```

## 亮点功能

- **自动化图片处理**：`backend/scripts/auto_process_images_enhanced.py` 能批量从阿里云 OSS 获取图片并调用 OpenAI 识别场景、角度、道具及标签。
- **AI 搜索优化**：`ai_search_service` 与 `ai_database_search_service` 让用户只需输入自然语言即可获得相关性排序的结果，支持模糊匹配、同义词扩展和智能建议。
- **搜索统计与分析**：`SearchService` 记录查询历史，`manage.py` 可查看热门搜索词与响应时间等指标。
- **前端交互**：Next.js 15 实现无限滚动、类别过滤及弹窗查看大图，当后端不可用时自动回退到示例数据。
- **脚本工具**：`deploy.sh`、`init-db.sh` 等脚本帮助快速部署、初始化和监控服务状态。

## 环境准备

1. 克隆仓库：
   ```bash
   git clone https://github.com/yourname/pose-gallery.git
   cd pose-gallery
   ```
2. 按需修改环境变量：
   ```bash
   cp backend/.env.example .env
   # 配置数据库、Redis、OSS 以及 OpenAI
   ```
3. 手动运行（可选）：
   - 后端：`cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`
   - 前端：`cd frontend && npm install && npm run dev`

## Docker 部署

项目自带 `docker-compose.yml`（自带数据库） 与 `docker-compose.external-db.yml`（使用外部数据库）。

```bash
# 根据 .env 中的 DEPLOYMENT_MODE 选择模式
./deploy.sh        # 构建并启动容器
./init-db.sh       # 初始化数据库
```

向量索引数据默认位于 `backend/vector_index`，容器会将该目录挂载到本地以保持数据持久化。

启动后访问：

- 🌐 前端：http://localhost:3000
- 🛠️ 后端接口：http://localhost:8000
- 📚 API 文档：http://localhost:8000/docs

向量检索接口：

```bash
curl -X POST http://localhost:8000/api/v1/search/vector \
  -H 'Content-Type: application/json' \
  -d '{"query": "咖啡馆 坐姿", "top_k": 5}'
```

## 向量搜索基础

1. 运行 `python backend/scripts/build_vector_index.py` 生成向量索引，文件位于 `backend/vector_index/`。
2. 服务启动后可通过 `GET /api/v1/search/vector/status` 查看向量搜索是否可用。
3. 检索接口 `POST /api/v1/search/vector` 支持 `query`、`top_k` 与 `use_adaptive` 参数，其中 `use_adaptive` 会根据结果数量自动调整阈值。

## 数据库初始化

`migrations/init_database.sql` 含完整表结构及示例同义词。运行 `backend/scripts/init_db.py` 会根据 `.env` 自动创建数据库并导入数据。

## 常用脚本

- `python backend/scripts/check_config.py`：检查配置是否齐全。
- `python backend/scripts/check_connections.py`：测试 MySQL 与 Redis 连接。
- `python backend/scripts/auto_process_images_enhanced.py --scan-oss`：扫描 OSS 并处理新图片。
- `python backend/scripts/manage.py stats`：查看统计信息及热门搜索词。
- `python backend/scripts/health_check.py --verbose`：输出依赖服务状态。
- `python backend/scripts/build_vector_index.py`：生成姿势文本的向量索引。
  结果存储在 `backend/vector_index/`，该目录通过 Docker 卷持久化。

## 贡献 & 开发

1. 前后端遵循 eslint/flake8 规范，提交前请确保代码通过检查。
2. 欢迎通过 Issue 或 Pull Request 反馈问题与贡献改进。

## 未来优化方向

- 持续改进向量搜索结果的排序与召回质量。
- 计划以向量搜索替换现有 `AI 数据库搜索`，统一检索逻辑。
