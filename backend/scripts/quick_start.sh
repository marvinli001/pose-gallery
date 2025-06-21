#!/bin/bash

echo "🚀 摄影姿势库自动化处理 - 快速启动"
echo "================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查配置
echo "检查配置..."
python scripts/check_config.py

if [ $? -ne 0 ]; then
    echo "❌ 配置检查失败，请检查.env文件"
    exit 1
fi

# 检查数据库连接
echo "检查数据库连接..."
python scripts/check_connections.py

# 显示使用说明
echo ""
echo "🎉 环境准备完成！"
echo ""
echo "📋 可用命令："
echo "  python scripts/auto_process_images.py --scan-oss      # 扫描OSS新图片"
echo "  python scripts/auto_process_images.py --process-pending  # 处理待分析图片"  
echo "  python scripts/auto_process_images.py --upload /path/to/images  # 批量上传"
echo "  python scripts/auto_process_images.py --retry-failed  # 重试失败图片"
echo "  python scripts/auto_process_images.py --status        # 查看系统状态"
echo ""
echo "🔧 管理命令："
echo "  python scripts/manage.py stats     # 查看统计信息"
echo "  python scripts/manage.py failed    # 查看失败图片"
echo ""