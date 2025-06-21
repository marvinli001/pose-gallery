import pymysql
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

def init_database():
    # 连接MySQL服务器（不指定数据库）
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 读取SQL文件
            with open('../migrations/init_database.sql', 'r', encoding='utf-8') as f:
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
    init_database()
