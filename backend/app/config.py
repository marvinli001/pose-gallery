import os
from pydantic import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # 数据库配置
    db_host: str
    db_port: int = 3306
    db_user: str
    db_pass: str
    db_name: str
    
    @property
    def database_url(self) -> str:
        return f"mysql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # Redis配置
    redis_host: str
    redis_port: int = 6379
    redis_password: str
    redis_db: int = 0
    
    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # API配置
    api_prefix: str = "/api/v1"
    
    # OSS配置
    oss_endpoint: str
    oss_access_key: str
    oss_secret_key: str
    oss_bucket: str
    oss_custom_domain: Optional[str] = None
    
    # OSS图片样式配置
    oss_image_style_thumbnail: str = "?x-oss-process=image/resize,w_400,h_400,m_lfit,q_80"
    oss_image_style_medium: str = "?x-oss-process=image/resize,w_800,h_800,m_lfit,q_85"
    oss_image_style_large: str = "?x-oss-process=image/resize,w_1200,h_1200,m_lfit,q_90"
    
    # OpenAI配置
    openai_api_key: str
    openai_model: str = "gpt-4-vision-preview"
    openai_max_tokens: int = 1500
    openai_temperature: float = 0.3
    
    # 处理配置
    batch_size: int = 5
    max_retries: int = 3
    processing_delay: int = 2
    max_concurrent_requests: int = 3
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/ai_analyzer.log"
    log_max_size: int = 10485760  # 10MB
    log_backup_count: int = 5
    
    # 安全配置
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.allowed_hosts.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # 缓存配置
    cache_expire_time: int = 3600  # 1小时
    search_cache_expire_time: int = 300  # 5分钟
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()