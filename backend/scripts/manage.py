#!/usr/bin/env python3
"""
管理工具脚本
用法：
    python scripts/manage.py stats
    python scripts/manage.py clean-cache
    python scripts/manage.py check-failed
    python scripts/manage.py reprocess --pose-id 123
"""

import sys
import argparse
from pathlib import Path
from tabulate import tabulate

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import SessionLocal
from app.models.pose import Pose
from app.models.tag import Tag, PoseTag
from app.models.search_history import SearchHistory
from app.utils.redis_client import RedisClient
from app.services.pose_service import PoseService
from app.services.ai_analyzer import AIAnalyzer
from sqlalchemy import text, func
import json

class ManagementTool:
    """管理工具"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.redis_client = RedisClient()
        self.pose_service = PoseService()
        self.ai_analyzer = AIAnalyzer()
    
    def show_stats(self):
        """显示统计信息"""
        print("=" * 60)
        print("系统统计信息")
        print("=" * 60)
        
        # 姿势统计
        total_poses = self.db.query(Pose).count()
        active_poses = self.db.query(Pose).filter(Pose.status == 'active').count()
        pending_poses = self.db.query(Pose).filter(Pose.processing_status == 'pending').count()
        processing_poses = self.db.query(Pose).filter(Pose.processing_status == 'processing').count()
        completed_poses = self.db.query(Pose).filter(Pose.processing_status == 'completed').count()
        failed_poses = self.db.query(Pose).filter(Pose.processing_status == 'failed').count()
        
        pose_stats = [
            ["总图片数", total_poses],
            ["活跃图片", active_poses],
            ["待处理", pending_poses],
            ["处理中", processing_poses],
            ["已完成", completed_poses],
            ["处理失败", failed_poses]
        ]
        
        print("\n图片处理状态:")
        print(tabulate(pose_stats, headers=["状态", "数量"], tablefmt="grid"))
        
        # 分类统计
        category_stats = self.db.execute(
            text("""
                SELECT scene_category, COUNT(*) as count
                FROM poses 
                WHERE status = 'active' AND scene_category IS NOT NULL
                GROUP BY scene_category
                ORDER BY count DESC
                LIMIT 10
            """)
        ).fetchall()
        
        if category_stats:
            print("\n场景分类统计:")
            print(tabulate(category_stats, headers=["分类", "数量"], tablefmt="grid"))
        
        # 标签统计
        tag_stats = self.db.execute(
            text("""
                SELECT t.name, t.usage_count, t.category
                FROM tags t
                ORDER BY t.usage_count DESC
                LIMIT 10
            """)
        ).fetchall()
        
        if tag_stats:
            print("\n热门标签:")
            print(tabulate(tag_stats, headers=["标签", "使用次数", "分类"], tablefmt="grid"))
        
        # 搜索统计
        search_stats = self.db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT normalized_query) as unique_queries,
                    AVG(response_time_ms) as avg_response_time
                FROM search_history 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
        ).fetchone()
        
        if search_stats:
            search_data = [
                ["7天内搜索总数", search_stats[0] or 0],
                ["唯一搜索词数", search_stats[1] or 0],
                ["平均响应时间(ms)", round(search_stats[2] or 0, 2)]
            ]
            print("\n搜索统计:")
            print(tabulate(search_data, headers=["指标", "值"], tablefmt="grid"))
    
    def check_failed(self):
        """检查失败的处理"""
        print("=" * 60)
        print("处理失败的图片")
        print("=" * 60)
        
        failed_poses = self.db.query(Pose).filter(
            Pose.processing_status == 'failed'
        ).limit(20).all()
        
        if not failed_poses:
            print("没有处理失败的图片")
            return
        
        failed_data = []
        for pose in failed_poses:
            failed_data.append([
                pose.id,
                pose.oss_key[:50] + "..." if len(pose.oss_key) > 50 else pose.oss_key,
                pose.error_message[:50] + "..." if pose.error_message and len(pose.error_message) > 50 else pose.error_message,
                pose.updated_at.strftime('%Y-%m-%d %H:%M:%S') if pose.updated_at else ""
            ])
        
        print(tabulate(failed_data, headers=["ID", "OSS Key", "错误信息", "更新时间"], tablefmt="grid"))
    
    def clean_cache(self):
        """清理缓存"""
        print("开始清理Redis缓存...")
        
        # 清理搜索缓存
        search_keys = self.redis_client.keys("search:*")
        if search_keys:
            for key in search_keys:
                self.redis_client.delete(key)
            print(f"清理了 {len(search_keys)} 个搜索缓存")
        
        # 清理姿势缓存
        pose_keys = self.redis_client.keys("pose:*")
        if pose_keys:
            for key in pose_keys:
                self.redis_client.delete(key)
            print(f"清理了 {len(pose_keys)} 个姿势缓存")
        
        # 清理处理锁
        processing_keys = self.redis_client.keys("processing:*")
        if processing_keys:
            for key in processing_keys:
                self.redis_client.delete(key)
            print(f"清理了 {len(processing_keys)} 个处理锁")
        
        print("缓存清理完成")
    
    def reprocess_pose(self, pose_id: int):
        """重新处理指定图片"""
        print(f"重新处理图片 ID: {pose_id}")
        
        pose = self.db.query(Pose).filter(Pose.id == pose_id).first()
        if not pose:
            print(f"未找到图片 ID: {pose_id}")
            return
        
        print(f"图片信息: {pose.oss_key}")
        print(f"当前状态: {pose.processing_status}")
        
        try:
            # 重新分析
            image_url = pose.oss_url
            analysis = self.ai_analyzer.analyze_pose_image(image_url)
            
            if analysis:
                # 保存结果
                updated_pose = self.pose_service.save_analyzed_pose(
                    self.db, pose.oss_key, analysis
                )
                if updated_pose:
                    print(f"✅ 重新处理成功: {updated_pose.title}")
                else:
                    print("❌ 保存失败")
            else:
                print("❌ AI分析失败")
                
        except Exception as e:
            print(f"❌ 重新处理失败: {e}")
    
    def export_data(self, output_file: str):
        """导出数据"""
        print(f"导出数据到: {output_file}")
        
        # 导出姿势数据
        poses = self.db.query(Pose).filter(Pose.status == 'active').all()
        
        export_data = []
        for pose in poses:
            # 获取标签
            tags = self.db.execute(
                text("""
                    SELECT t.name FROM tags t
                    JOIN pose_tags pt ON t.id = pt.tag_id
                    WHERE pt.pose_id = :pose_id
                """),
                {"pose_id": pose.id}
            ).fetchall()
            
            tag_names = [tag[0] for tag in tags]
            
            export_data.append({
                "id": pose.id,
                "oss_key": pose.oss_key,
                "title": pose.title,
                "description": pose.description,
                "scene_category": pose.scene_category,
                "angle": pose.angle,
                "tags": tag_names,
                "props": json.loads(pose.props) if pose.props else [],
                "shooting_tips": pose.shooting_tips,
                "view_count": pose.view_count,
                "created_at": pose.created_at.isoformat() if pose.created_at else None
            })
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"导出完成，共 {len(export_data)} 条记录")
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'db'):
            self.db.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # stats命令
    subparsers.add_parser('stats', help='显示统计信息')
    
    # check-failed命令
    subparsers.add_parser('check-failed', help='检查处理失败的图片')
    
    # clean-cache命令
    subparsers.add_parser('clean-cache', help='清理Redis缓存')
    
    # reprocess命令
    reprocess_parser = subparsers.add_parser('reprocess', help='重新处理指定图片')
    reprocess_parser.add_argument('--pose-id', type=int, required=True, help='图片ID')
    
    # export命令
    export_parser = subparsers.add_parser('export', help='导出数据')
    export_parser.add_argument('--output', type=str, required=True, help='输出文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tool = ManagementTool()
    
    try:
        if args.command == 'stats':
            tool.show_stats()
        elif args.command == 'check-failed':
            tool.check_failed()
        elif args.command == 'clean-cache':
            tool.clean_cache()
        elif args.command == 'reprocess':
            tool.reprocess_pose(args.pose_id)
        elif args.command == 'export':
            tool.export_data(args.output)
    except Exception as e:
        print(f"执行命令失败: {e}")
    finally:
        del tool

if __name__ == "__main__":
    main()