@echo off

REM 激活虚拟环境
call venv\Scripts\activate

REM 检查连接
echo 检查数据库连接...
python scripts\check_connections.py

REM 启动服务
echo 启动FastAPI服务...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
