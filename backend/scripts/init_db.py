import pymysql
from dotenv import load_dotenv
import os
import sys

# 确保能找到 .env 文件
# 先尝试当前目录，再尝试上级目录
env_paths = ['.env', '../.env', '../../.env']
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"加载环境变量文件: {env_path}")
        break
else:
    print("警告: 未找到 .env 文件")

def test_connection():
    """测试数据库连接"""
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', '3306'))
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASS', '')
    
    print(f"尝试连接到: {host}:{port}")
    print(f"用户: {user}")
    print(f"密码: {'*' * len(password) if password else '(空)'}")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4',
            connect_timeout=10  # 添加连接超时
        )
        print("✅ 数据库连接成功！")
        connection.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def init_database():
    # 首先测试连接
    if not test_connection():
        print("请检查数据库配置和网络连接")
        return
    
    # 连接MySQL服务器（不指定数据库）
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),  # 添加端口配置
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        charset='utf8mb4',
        connect_timeout=10
    )
    
    try:
        with connection.cursor() as cursor:
            # 读取SQL文件
            sql_file_path = '../migrations/init_database.sql'
            if not os.path.exists(sql_file_path):
                sql_file_path = 'migrations/init_database.sql'
            
            if not os.path.exists(sql_file_path):
                print(f"错误: 找不到 SQL 文件 {sql_file_path}")
                return
                
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_commands = f.read().split(';')
            
            # 执行每个SQL命令
            for command in sql_commands:
                if command.strip():
                    cursor.execute(command)
                    print(f"执行成功: {command[:50]}...")
            
            connection.commit()
            print("数据库初始化完成！")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    print("=== 数据库初始化工具 ===")
    
    # 显示当前环境变量
    print("\n当前环境变量:")
    print(f"DB_HOST: {os.getenv('DB_HOST', '未设置')}")
    print(f"DB_PORT: {os.getenv('DB_PORT', '未设置')}")
    print(f"DB_USER: {os.getenv('DB_USER', '未设置')}")
    print(f"DB_PASS: {'已设置' if os.getenv('DB_PASS') else '未设置'}")
    print()
    
    init_database()