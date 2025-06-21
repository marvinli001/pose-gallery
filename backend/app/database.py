from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置 - 从环境变量读取
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASS", "")  # 注意这里使用 DB_PASS
DB_NAME = os.getenv("DB_NAME", "pose_gallery")

# 构建数据库URL - 确保密码被正确包含
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

print(f"数据库连接URL (隐藏密码): mysql+pymysql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 改为 False 减少日志
    pool_pre_ping=True,  # 自动重连
    pool_recycle=3600,   # 连接回收时间
)

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()