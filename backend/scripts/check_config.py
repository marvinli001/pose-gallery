#!/usr/bin/env python3
"""
配置检查脚本 - 验证所有必要的配置是否正确
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_database_config():
    """检查数据库配置"""
    print("检查数据库配置...")
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME']
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ 缺少环境变量: {var}")
            return False
        else:
            # 隐藏密码
            display_value = '***' if 'PASS' in var else value
            print(f"✅ {var}: {display_value}")
    
    return True

def check_openai_config():
    """检查OpenAI配置"""
    print("\n检查OpenAI配置...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 缺少 OPENAI_API_KEY")
        return False
    else:
        print(f"✅ OPENAI_API_KEY: {api_key[:10]}...")
    
    model = os.getenv('OPENAI_MODEL', 'gpt-4-vision-preview')
    print(f"✅ OPENAI_MODEL: {model}")
    
    return True

def check_oss_config():
    """检查OSS配置"""
    print("\n检查OSS配置...")
    required_vars = ['OSS_ENDPOINT', 'OSS_ACCESS_KEY', 'OSS_SECRET_KEY', 'OSS_BUCKET']
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ 缺少环境变量: {var}")
            return False
        else:
            # 隐藏敏感信息
            if 'KEY' in var:
                display_value = f"{value[:8]}..."
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    return True

def check_redis_config():
    """检查Redis配置"""
    print("\n检查Redis配置...")
    
    host = os.getenv('REDIS_HOST', 'localhost')
    port = os.getenv('REDIS_PORT', '6379')
    password = os.getenv('REDIS_PASSWORD', '')
    
    print(f"✅ REDIS_HOST: {host}")
    print(f"✅ REDIS_PORT: {port}")
    print(f"✅ REDIS_PASSWORD: {'已设置' if password else '未设置'}")
    
    return True

def main():
    print("=" * 60)
    print("配置检查工具")
    print("=" * 60)
    
    checks = [
        check_database_config(),
        check_openai_config(), 
        check_oss_config(),
        check_redis_config()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ 所有配置检查通过！")
        print("可以开始使用自动化处理脚本。")
    else:
        print("❌ 部分配置有问题，请检查后再运行。")
        
    print("=" * 60)

if __name__ == "__main__":
    main()