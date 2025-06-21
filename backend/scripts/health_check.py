#!/usr/bin/env python3
"""
系统健康检查脚本
用法：
    python scripts/health_check.py
    python scripts/health_check.py --verbose
"""

import sys
import argparse
from pathlib import Path
import time
import requests

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import SessionLocal
from app.utils.redis_client import RedisClient
from app.utils.storage_client import OSSClient
from app.services.ai_analyzer import AIAnalyzer
from sqlalchemy import text

class HealthChecker:
    """系统健康检查"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {}
    
    def check_database(self):
        """检查数据库连接"""
        print("检查数据库连接...", end="")
        try:
            db = SessionLocal()
            result = db.execute(text("SELECT 1")).fetchone()
            db.close()
            if result:
                print(" ✅")
                self.results['database'] = True
                if self.verbose:
                    print(f"  数据库连接成功: {settings.database_url}")
            else:
                print(" ❌")
                self.results['database'] = False
        except Exception as e:
            print(" ❌")
            self.results['database'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def check_redis(self):
        """检查Redis连接"""
        print("检查Redis连接...", end="")
        try:
            redis_client = RedisClient()
            redis_client.client.ping()
            print(" ✅")
            self.results['redis'] = True
            if self.verbose:
                print(f"  Redis连接成功: {settings.redis_url}")
        except Exception as e:
            print(" ❌")
            self.results['redis'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def check_oss(self):
        """检查OSS连接"""
        print("检查OSS连接...", end="")
        try:
            oss_client = OSSClient()
            # 尝试列出少量对象
            images = oss_client.list_images(max_keys=1)
            print(" ✅")
            self.results['oss'] = True
            if self.verbose:
                print(f"  OSS连接成功，桶: {settings.oss_bucket}")
                print(f"  自定义域名: {settings.oss_custom_domain or '未设置'}")
        except Exception as e:
            print(" ❌")
            self.results['oss'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def check_openai(self):
        """检查OpenAI API"""
        print("检查OpenAI API...", end="")
        try:
            ai_analyzer = AIAnalyzer()
            # 简单的API测试
            response = ai_analyzer.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            if response.choices:
                print(" ✅")
                self.results['openai'] = True
                if self.verbose:
                    print(f"  OpenAI API连接成功")
            else:
                print(" ❌")
                self.results['openai'] = False
        except Exception as e:
            print(" ❌")
            self.results['openai'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def check_disk_space(self):
        """检查磁盘空间"""
        print("检查磁盘空间...", end="")
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024**3)
            if free_gb > 5:  # 至少5GB空闲空间
                print(" ✅")
                self.results['disk'] = True
                if self.verbose:
                    print(f"  可用空间: {free_gb}GB")
            else:
                print(" ⚠️")
                self.results['disk'] = False
                if self.verbose:
                    print(f"  可用空间不足: {free_gb}GB")
        except Exception as e:
            print(" ❌")
            self.results['disk'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def check_log_files(self):
        """检查日志文件"""
        print("检查日志文件...", end="")
        try:
            log_file = Path(settings.log_file)
            if log_file.parent.exists():
                print(" ✅")
                self.results['logs'] = True
                if self.verbose:
                    print(f"  日志目录存在: {log_file.parent}")
                    if log_file.exists():
                        size_mb = log_file.stat().st_size / (1024*1024)
                        print(f"  当前日志大小: {size_mb:.1f}MB")
            else:
                print(" ❌")
                self.results['logs'] = False
                if self.verbose:
                    print(f"  日志目录不存在: {log_file.parent}")
        except Exception as e:
            print(" ❌")
            self.results['logs'] = False
            if self.verbose:
                print(f"  错误: {e}")
    
    def run_all_checks(self):
        """运行所有检查"""
        print("=" * 50)
        print("系统健康检查")
        print("=" * 50)
        
        self.check_database()
        self.check_redis()
        self.check_oss()
        self.check_openai()
        self.check_disk_space()
        self.check_log_files()
        
        print("\n" + "=" * 50)
        print("检查结果汇总")
        print("=" * 50)
        
        all_passed = True
        for service, status in self.results.items():
            status_icon = "✅" if status else "❌"
            print(f"{service:12}: {status_icon}")
            if not status:
                all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ 所有检查通过，系统健康")
            return 0
        else:
            print("❌ 部分检查失败，请检查相关配置")
            return 1

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='系统健康检查')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    checker = HealthChecker(verbose=args.verbose)
    exit_code = checker.run_all_checks()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()