# Pose Gallery

Pose Gallery 是一个包含摄影姿势示例的图库系统，后端使用 **FastAPI** 构建 API ，前端使用 **Next.js** 实现界面。项目支持从阿里云 OSS 批量导入图片并调用 OpenAI 接口进行自动化分析，可按场景、角度等条件进行搜索，并通过 Docker 一键部署。

## 目录结构

```
backend/   # FastAPI 应用和脚本
frontend/  # Next.js 前端应用
migrations/ # MySQL 初始化脚本
scripts/    # 自动化处理与管理工具
```

## 功能概览

- **图片处理**：`backend/scripts/auto_process_images.py` 与 `auto_process_images_enhanced.py` 可扫描 OSS 中的图片，调用 OpenAI 分析标题、描述、场景分类、角度、标签等信息并写入数据库。
- **搜索服务**：`SearchService` 支持关键词、同义词扩展、标签匹配、分类和角度筛选，并记录搜索历史。
- **管理脚本**：`scripts/manage.py` 提供统计信息查看、失败记录重试、数据导出等功能；`health_check.py` 用于检查数据库、Redis、OSS、OpenAI 等依赖的状态。
- **前端界面**：Next.js 构建的网页包含姿势列表、分类浏览、搜索及图片详情弹窗等组件，默认会在后端不可用时回退到示例数据。

## 环境准备

1. 克隆仓库并安装依赖：
   ```bash
   git clone https://github.com/yourname/pose-gallery.git
   cd pose-gallery
   ```
2. 复制并修改环境变量：
   ```bash
   cp backend/.env.example .env
   # 按需修改数据库、Redis、OSS 以及 OpenAI 配置
   ```
3. （可选）手动安装依赖运行：
   - 后端：在 `backend/` 创建虚拟环境并安装 `requirements.txt`，使用 `uvicorn app.main:app --reload` 启动。
   - 前端：进入 `frontend/` 执行 `npm install` 与 `npm run dev`。

## Docker 部署

项目提供两套 `docker-compose` 配置：

- `docker-compose.yml`：包含 MySQL 与 Redis 容器，适合本地快速启动。
- `docker-compose.external-db.yml`：用于连接外部数据库，仅启动前后端容器。

部署流程：

```bash
# 根据 .env 中的 DEPLOYMENT_MODE 选择使用本地数据库或外部数据库
./deploy.sh        # 构建并启动容器
./init-db.sh       # 初始化 MySQL 表结构
```

服务启动后，访问：

- 前端：http://localhost:3000
- 后端接口：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 数据库初始化

`migrations/init_database.sql` 包含完整的表结构和示例同义词数据。脚本 `backend/scripts/init_db.py` 会根据 `.env` 中的配置创建数据库并导入该 SQL 文件。

## 常用脚本

- `python backend/scripts/check_config.py`：检查环境变量是否配置完整。
- `python backend/scripts/check_connections.py`：测试 MySQL 和 Redis 连接状态。
- `python backend/scripts/auto_process_images.py --scan-oss`：扫描 OSS 并处理新图片。
- `python backend/scripts/manage.py stats`：查看当前统计信息。
- `python backend/scripts/health_check.py --verbose`：输出依赖服务的健康状态。

## 贡献与开发

1. 前端与后端均遵循常规的 eslint/flake8 代码规范。
2. 提交前请运行脚本或测试以确保功能正常。
3. 欢迎提交 Issue 或 Pull Request 进行改进。

