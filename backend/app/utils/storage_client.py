import oss2
from typing import List, Optional
from urllib.parse import urlparse
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class OSSClient:
    """阿里云OSS客户端，支持自定义域名"""
    
    def __init__(self):
        self.auth = oss2.Auth(settings.oss_access_key, settings.oss_secret_key)
        self.bucket = oss2.Bucket(
            self.auth, 
            f"https://{settings.oss_endpoint}", 
            settings.oss_bucket
        )
        self.custom_domain = settings.oss_custom_domain
        self.bucket_name = settings.oss_bucket
        
        logger.info(f"OSS客户端初始化完成")
        logger.info(f"OSS Endpoint: {settings.oss_endpoint}")
        logger.info(f"OSS Bucket: {settings.oss_bucket}")
        logger.info(f"自定义域名: {self.custom_domain or '未设置'}")
    
    def list_images(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """列出所有图片文件"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif')
        images = []
        
        try:
            # 使用分页获取所有图片
            continuation_token = ""
            
            while True:
                if continuation_token:
                    result = self.bucket.list_objects_v2(
                        prefix=prefix,
                        max_keys=max_keys,
                        continuation_token=continuation_token
                    )
                else:
                    result = self.bucket.list_objects_v2(
                        prefix=prefix,
                        max_keys=max_keys
                    )
                
                # 过滤图片文件
                for obj in result.object_list:
                    key = obj.key
                    if key.lower().endswith(image_extensions):
                        # 排除缩略图等处理后的图片
                        if not any(x in key.lower() for x in ['_thumb', '_thumbnail', '_small', '_medium']):
                            images.append(key)
                
                # 检查是否还有更多对象
                if not result.is_truncated:
                    break
                continuation_token = result.next_continuation_token
            
            logger.info(f"在OSS中发现 {len(images)} 张图片")
            return images
            
        except Exception as e:
            logger.error(f"列出OSS图片失败: {e}")
            raise
    
    def get_public_url(self, key: str) -> str:
        """获取图片的公开访问URL"""
        if self.custom_domain:
            # 使用自定义域名
            base_url = self.custom_domain.rstrip('/')
            return f"{base_url}/{key}"
        else:
            # 使用默认OSS域名
            return f"https://{self.bucket_name}.{settings.oss_endpoint}/{key}"
    
    def get_thumbnail_url(self, key: str) -> str:
        """获取缩略图URL"""
        base_url = self.get_public_url(key)
        return f"{base_url}{settings.oss_image_style_thumbnail}"
    
    def get_medium_url(self, key: str) -> str:
        """获取中等尺寸图片URL"""
        base_url = self.get_public_url(key)
        return f"{base_url}{settings.oss_image_style_medium}"
    
    def get_large_url(self, key: str) -> str:
        """获取大尺寸图片URL"""
        base_url = self.get_public_url(key)
        return f"{base_url}{settings.oss_image_style_large}"
    
    def get_image_urls(self, key: str) -> dict:
        """获取图片的所有尺寸URL"""
        return {
            "original": self.get_public_url(key),
            "thumbnail": self.get_thumbnail_url(key),
            "medium": self.get_medium_url(key),
            "large": self.get_large_url(key)
        }
    
    def check_object_exists(self, key: str) -> bool:
        """检查对象是否存在"""
        try:
            return self.bucket.object_exists(key)
        except Exception as e:
            logger.error(f"检查对象存在性失败 {key}: {e}")
            return False
    
    def get_object_info(self, key: str) -> Optional[dict]:
        """获取对象信息"""
        try:
            meta = self.bucket.head_object(key)
            return {
                "key": key,
                "size": meta.content_length,
                "last_modified": meta.last_modified,
                "content_type": meta.content_type,
                "etag": meta.etag
            }
        except Exception as e:
            logger.error(f"获取对象信息失败 {key}: {e}")
            return None
    
    def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        """生成预签名URL（用于私有访问）"""
        try:
            return self.bucket.sign_url('GET', key, expires)
        except Exception as e:
            logger.error(f"生成预签名URL失败 {key}: {e}")
            return self.get_public_url(key)

# 为了保持向后兼容，创建一个别名
StorageClient = OSSClient