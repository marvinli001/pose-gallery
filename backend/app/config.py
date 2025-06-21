from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASS: str = ""
    DB_NAME: str = "pose_gallery"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None  # 可选的密码字段
    REDIS_DB: int = 0
    
    # API配置
    API_PREFIX: str = "/api/v1"
    
    # OSS配置
    OSS_ENDPOINT: str = ""
    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_BUCKET: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True  # 区分大小写

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
