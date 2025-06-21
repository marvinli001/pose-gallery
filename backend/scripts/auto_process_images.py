#!/usr/bin/env python3
"""
自动化图片处理脚本
功能：
1. 扫描OSS中的新图片
2. 调用OpenAI API进行图片分析
3. 自动写入数据库
4. 支持批量处理和错误重试

使用方法：
python scripts/auto_process_images.py --scan-oss    # 扫描OSS中的新图片
python scripts/auto_process_images.py --process-pending  # 处理数据库中待分析的图片
python scripts/auto_process_images.py --upload /path/to/images  # 批量上传并分析
python scripts/auto_process_images.py --retry-failed  # 重试失败的图片
"""

import os
import sys
import argparse
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db, engine
from app.models import Pose, Tag, PoseTag
from app.utils.storage_client import OSSClient
from app.services.ai_analyzer import AIAnalyzer
from app.config import settings
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text

# 确保日志目录存在
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ImageProcessor:
    """图片自动化处理器"""
    
    def __init__(self):
        self.oss_client = OSSClient()
        self.ai_analyzer = AIAnalyzer()
        self.db = next(get_db())
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
    def scan_and_process_oss_images(self):
        """扫描OSS并处理新图片"""
        logger.info("开始扫描OSS中的图片...")
        
        try:
            # 获取OSS中的所有图片
            oss_images = self.oss_client.list_images()
            logger.info(f"OSS中发现 {len(oss_images)} 张图片")
            
            # 获取数据库中已有的图片
            existing_keys = set()
            existing_poses = self.db.query(Pose.oss_key).all()
            for pose in existing_poses:
                existing_keys.add(pose.oss_key)
                
            logger.info(f"数据库中已有 {len(existing_keys)} 条记录")
            
            # 找出需要处理的新图片
            new_images = [img for img in oss_images if img not in existing_keys]
            logger.info(f"需要处理 {len(new_images)} 张新图片")
            
            if not new_images:
                logger.info("没有新图片需要处理")
                return
                
            self.stats['total'] = len(new_images)
            
            # 并发处理图片（控制并发数量）
            with ThreadPoolExecutor(max_workers=settings.max_concurrent_requests) as executor:
                futures = []
                for oss_key in new_images:
                    future = executor.submit(self.process_single_image_from_oss, oss_key)
                    futures.append(future)
                    
                # 处理结果
                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        result = future.result()
                        if result:
                            self.stats['success'] += 1
                            logger.info(f"[{i}/{len(new_images)}] 处理成功")
                        else:
                            self.stats['failed'] += 1
                            logger.error(f"[{i}/{len(new_images)}] 处理失败")
                    except Exception as e:
                        self.stats['failed'] += 1
                        logger.error(f"[{i}/{len(new_images)}] 处理异常: {e}")
                        
                    # 避免API限制，添加延迟
                    if i % 5 == 0:
                        time.sleep(settings.processing_delay)
                        
        except Exception as e:
            logger.error(f"扫描OSS失败: {e}")
            
        finally:
            self.print_stats()
            
    def process_single_image_from_oss(self, oss_key: str) -> bool:
        """处理OSS中的单张图片 - 每个线程使用独立的数据库会话"""
        # 创建独立的数据库会话
        db = SessionLocal()
        try:
            logger.info(f"处理图片: {oss_key}")
            
            # 生成URL
            oss_url = self.oss_client.get_public_url(oss_key)
            thumbnail_url = self.oss_client.get_thumbnail_url(oss_key)
            
            # 从文件名提取基本信息
            filename = Path(oss_key).stem
            
            # 先插入基础记录
            pose_data = {
                'oss_key': oss_key,
                'oss_url': oss_url,
                'thumbnail_url': thumbnail_url,
                'title': f'摄影姿势 - {filename}',
                'description': 'OSS自动导入的图片，待AI分析',
                'processing_status': 'processing',
                'status': 'active',
                'created_at': datetime.now(timezone.utc)
            }
            
            pose = Pose(**pose_data)
            db.add(pose)
            db.commit()
            
            logger.info(f"图片基础信息已入库，ID: {pose.id}")
            
            # AI分析
            logger.info(f"开始AI分析...")
            analysis = self.ai_analyzer.analyze_pose_image(oss_url)
            
            if analysis:
                # 更新AI分析结果
                updated_data = {
                    'title': analysis.get('title', pose_data['title']),
                    'description': analysis.get('description', ''),
                    'scene_category': analysis.get('scene_category'),
                    'angle': analysis.get('angle'),
                    'shooting_tips': analysis.get('shooting_tips', ''),
                    'ai_tags': ','.join(analysis.get('tags', [])),
                    'processing_status': 'completed',
                    'ai_analyzed_at': datetime.now(timezone.utc),
                    'ai_confidence': analysis.get('confidence', 0.8)
                }
                
                # 更新pose记录
                for key, value in updated_data.items():
                    setattr(pose, key, value)
                    
                # 处理标签
                self.process_tags_with_session(db, pose, analysis.get('tags', []))
                
                # 处理道具（如果有）
                if analysis.get('props'):
                    pose.props = json.dumps(analysis['props'], ensure_ascii=False)
                
                db.commit()
                
                logger.info(f"✅ AI分析完成: {updated_data['title']}")
                logger.info(f"   场景: {updated_data['scene_category']}")
                logger.info(f"   角度: {updated_data['angle']}")
                logger.info(f"   标签: {updated_data['ai_tags']}")
                
                return True
            else:
                # AI分析失败，标记为失败状态
                pose.processing_status = 'failed'
                pose.error_message = 'AI分析失败'
                db.commit()
                
                logger.error(f"❌ AI分析失败: {oss_key}")
                return False
                
        except Exception as e:
            logger.error(f"处理图片失败 {oss_key}: {e}")
            try:
                db.rollback()
                if 'pose' in locals():
                    pose.processing_status = 'failed'
                    pose.error_message = str(e)
                    db.commit()
            except Exception as rollback_error:
                logger.error(f"回滚失败: {rollback_error}")
            return False
        finally:
            db.close()
            
    def process_tags_with_session(self, db: Session, pose: Pose, tags: List[str]):
        """处理图片标签 - 使用指定的数据库会话"""
        for tag_name in tags:
            if not tag_name.strip():
                continue
                
            tag_name = tag_name.strip()
            
            # 查找或创建标签
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                # 分类标签类型
                tag_category = self.classify_tag(tag_name)
                tag = Tag(
                    name=tag_name,
                    category=tag_category,
                    usage_count=0
                )
                db.add(tag)
                db.flush()  # 获取tag.id
                
            # 创建关联关系
            pose_tag = db.query(PoseTag).filter(
                PoseTag.pose_id == pose.id,
                PoseTag.tag_id == tag.id
            ).first()
            
            if not pose_tag:
                pose_tag = PoseTag(
                    pose_id=pose.id,
                    tag_id=tag.id,
                    confidence=0.9
                )
                db.add(pose_tag)
                
                # 更新标签使用次数
                tag.usage_count += 1

    def process_tags(self, pose: Pose, tags: List[str]):
        """处理图片标签 - 使用默认会话"""
        self.process_tags_with_session(self.db, pose, tags)
                
    def classify_tag(self, tag_name: str) -> str:
        """分类标签类型"""
        # 场景标签
        scene_keywords = ['室内', '户外', '咖啡厅', '海边', '森林', '城市', '办公室', '学校']
        if any(keyword in tag_name for keyword in scene_keywords):
            return 'scene'
            
        # 情绪标签
        mood_keywords = ['清新', '文艺', '性感', '可爱', '优雅', '温柔', '活泼', '安静']
        if any(keyword in tag_name for keyword in mood_keywords):
            return 'mood'
            
        # 姿势标签
        pose_keywords = ['坐姿', '站立', '躺下', '行走', '倚靠', '蹲着']
        if any(keyword in tag_name for keyword in pose_keywords):
            return 'pose'
            
        # 风格标签
        style_keywords = ['日系', '韩系', '复古', '现代', '简约', '欧美']
        if any(keyword in tag_name for keyword in style_keywords):
            return 'style'
            
        # 角度标签
        angle_keywords = ['正面', '侧面', '背面', '俯视', '仰视', '斜角']
        if any(keyword in tag_name for keyword in angle_keywords):
            return 'angle'
            
        # 道具标签
        prop_keywords = ['咖啡', '书', '花', '帽子', '眼镜', '包']
        if any(keyword in tag_name for keyword in prop_keywords):
            return 'prop'
            
        return 'other'
        
    def process_pending_images(self):
        """处理数据库中待分析的图片"""
        logger.info("查找待处理的图片...")
        
        pending_poses = self.db.query(Pose).filter(
            Pose.processing_status == 'pending'
        ).all()
        
        logger.info(f"找到 {len(pending_poses)} 张待处理图片")
        
        if not pending_poses:
            logger.info("没有待处理的图片")
            return
            
        self.stats['total'] = len(pending_poses)
        
        for i, pose in enumerate(pending_poses, 1):
            logger.info(f"[{i}/{len(pending_poses)}] 处理图片 ID: {pose.id}")
            
            try:
                # 更新状态为处理中
                pose.processing_status = 'processing'
                self.db.commit()
                
                # AI分析
                analysis = self.ai_analyzer.analyze_pose_image(pose.oss_url)
                
                if analysis:
                    # 更新分析结果
                    pose.title = analysis.get('title', pose.title)
                    pose.description = analysis.get('description', '')
                    pose.scene_category = analysis.get('scene_category')
                    pose.angle = analysis.get('angle')
                    pose.shooting_tips = analysis.get('shooting_tips', '')
                    pose.ai_tags = ','.join(analysis.get('tags', []))
                    pose.processing_status = 'completed'
                    pose.ai_analyzed_at = datetime.now(timezone.utc)
                    pose.ai_confidence = analysis.get('confidence', 0.8)
                    
                    # 处理标签
                    self.process_tags(pose, analysis.get('tags', []))
                    
                    # 处理道具
                    if analysis.get('props'):
                        pose.props = json.dumps(analysis['props'], ensure_ascii=False)
                    
                    self.db.commit()
                    
                    self.stats['success'] += 1
                    logger.info(f"✅ 处理成功: {pose.title}")
                    
                else:
                    pose.processing_status = 'failed'
                    pose.error_message = 'AI分析失败'
                    self.db.commit()
                    
                    self.stats['failed'] += 1
                    logger.error(f"❌ AI分析失败")
                    
            except Exception as e:
                pose.processing_status = 'failed'
                pose.error_message = str(e)
                self.db.commit()
                
                self.stats['failed'] += 1
                logger.error(f"❌ 处理异常: {e}")
                
            # 避免API限制
            if i % 5 == 0:
                time.sleep(settings.processing_delay)
                
        self.print_stats()
        
    def retry_failed_images(self):
        """重试失败的图片"""
        logger.info("查找处理失败的图片...")
        
        failed_poses = self.db.query(Pose).filter(
            Pose.processing_status == 'failed'
        ).all()
        
        logger.info(f"找到 {len(failed_poses)} 张失败图片")
        
        if not failed_poses:
            logger.info("没有失败的图片")
            return
            
        self.stats['total'] = len(failed_poses)
        
        for i, pose in enumerate(failed_poses, 1):
            logger.info(f"[{i}/{len(failed_poses)}] 重试图片 ID: {pose.id}")
            logger.info(f"  原因: {pose.error_message}")
            
            try:
                # 重置状态
                pose.processing_status = 'processing'
                pose.error_message = None
                self.db.commit()
                
                # AI分析
                analysis = self.ai_analyzer.analyze_pose_image(pose.oss_url)
                
                if analysis:
                    # 更新分析结果
                    pose.title = analysis.get('title', pose.title)
                    pose.description = analysis.get('description', '')
                    pose.scene_category = analysis.get('scene_category')
                    pose.angle = analysis.get('angle')
                    pose.shooting_tips = analysis.get('shooting_tips', '')
                    pose.ai_tags = ','.join(analysis.get('tags', []))
                    pose.processing_status = 'completed'
                    pose.ai_analyzed_at = datetime.now(timezone.utc)
                    pose.ai_confidence = analysis.get('confidence', 0.8)
                    
                    # 处理标签
                    self.process_tags(pose, analysis.get('tags', []))
                    
                    self.db.commit()
                    
                    self.stats['success'] += 1
                    logger.info(f"✅ 重试成功: {pose.title}")
                    
                else:
                    pose.processing_status = 'failed'
                    pose.error_message = 'AI分析失败（重试后）'
                    self.db.commit()
                    
                    self.stats['failed'] += 1
                    logger.error(f"❌ 重试仍失败")
                    
            except Exception as e:
                pose.processing_status = 'failed'
                pose.error_message = f"重试异常: {str(e)}"
                self.db.commit()
                
                self.stats['failed'] += 1
                logger.error(f"❌ 重试异常: {e}")
                
            # 避免API限制
            time.sleep(settings.processing_delay * 2)  # 重试时间间隔更长
                
        self.print_stats()
        
    def upload_and_process_folder(self, folder_path: str):
        """上传文件夹并处理"""
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"文件夹不存在: {folder_path}")
            return
            
        # 支持的图片格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(folder.glob(f"*{ext}"))
            image_files.extend(folder.glob(f"*{ext.upper()}"))
            
        if not image_files:
            logger.error(f"在 {folder_path} 中未找到图片文件")
            return
            
        logger.info(f"找到 {len(image_files)} 张图片")
        self.stats['total'] = len(image_files)
        
        for i, image_path in enumerate(image_files, 1):
            logger.info(f"[{i}/{len(image_files)}] 上传: {image_path.name}")
            
            try:
                # 生成OSS key
                file_ext = image_path.suffix.lower()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                random_id = str(uuid.uuid4())[:8]
                oss_key = f"poses/{timestamp}_{random_id}{file_ext}"
                
                # 上传到OSS
                with open(image_path, 'rb') as f:
                    self.oss_client.bucket.put_object(oss_key, f)
                
                logger.info(f"  ✅ 上传成功: {oss_key}")
                
                # 处理图片
                if self.process_single_image_from_oss(oss_key):
                    self.stats['success'] += 1
                    logger.info(f"  ✅ 处理成功")
                else:
                    self.stats['failed'] += 1
                    logger.error(f"  ❌ 处理失败")
                    
            except Exception as e:
                self.stats['failed'] += 1
                logger.error(f"  ❌ 上传失败: {e}")
                
            # 避免API限制
            if i % 3 == 0:
                time.sleep(settings.processing_delay)
                
        self.print_stats()
        
    def print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("处理统计")
        logger.info("=" * 60)
        logger.info(f"总数: {self.stats['total']}")
        logger.info(f"成功: {self.stats['success']}")
        logger.info(f"失败: {self.stats['failed']}")
        logger.info(f"跳过: {self.stats['skipped']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100
            logger.info(f"成功率: {success_rate:.1f}%")
            
        logger.info("=" * 60)
        
    def show_status(self):
        """显示当前系统状态"""
        logger.info("=" * 60)
        logger.info("系统状态")
        logger.info("=" * 60)
        
        # 统计数据库中的图片状态
        total_poses = self.db.query(Pose).count()
        pending_poses = self.db.query(Pose).filter(Pose.processing_status == 'pending').count()
        processing_poses = self.db.query(Pose).filter(Pose.processing_status == 'processing').count()
        completed_poses = self.db.query(Pose).filter(Pose.processing_status == 'completed').count()
        failed_poses = self.db.query(Pose).filter(Pose.processing_status == 'failed').count()
        
        logger.info(f"总图片数: {total_poses}")
        logger.info(f"待处理: {pending_poses}")
        logger.info(f"处理中: {processing_poses}")
        logger.info(f"已完成: {completed_poses}")
        logger.info(f"处理失败: {failed_poses}")
        
        # 统计场景分类
        scene_stats = self.db.execute(
            text("""
                SELECT scene_category, COUNT(*) as count
                FROM poses 
                WHERE status = 'active' AND scene_category IS NOT NULL
                GROUP BY scene_category
                ORDER BY count DESC
            """)
        ).fetchall()
        
        if scene_stats:
            logger.info("\n场景分类统计:")
            for scene, count in scene_stats:
                logger.info(f"  {scene}: {count}")
                
        logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='自动化图片处理工具')
    parser.add_argument('--scan-oss', action='store_true', help='扫描OSS中的新图片')
    parser.add_argument('--process-pending', action='store_true', help='处理待分析的图片')
    parser.add_argument('--retry-failed', action='store_true', help='重试失败的图片')
    parser.add_argument('--upload', type=str, help='上传文件夹中的图片')
    parser.add_argument('--status', action='store_true', help='显示系统状态')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
        
    processor = ImageProcessor()
    
    try:
        if args.scan_oss:
            processor.scan_and_process_oss_images()
        elif args.process_pending:
            processor.process_pending_images()
        elif args.retry_failed:
            processor.retry_failed_images()
        elif args.upload:
            processor.upload_and_process_folder(args.upload)
        elif args.status:
            processor.show_status()
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"执行失败: {e}")
    finally:
        processor.db.close()

if __name__ == "__main__":
    main()