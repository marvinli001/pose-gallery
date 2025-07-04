#!/usr/bin/env python3
"""
自动化图片处理脚本 - 最终修复版本
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db, engine
from app.models import Pose, Tag, PoseTag
from app.utils.storage_client import OSSClient
from app.services.ai_analyzer import AIAnalyzer
from app.config import settings
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# 确保日志目录存在
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 修复Windows编码问题的日志配置
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # 替换可能导致编码问题的字符
            msg = msg.replace('❌', '[ERROR]').replace('✅', '[SUCCESS]').replace('⚠️', '[WARNING]')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_process.log', encoding='utf-8'),
        SafeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 全局锁，避免标签处理时的并发冲突
tag_processing_lock = threading.Lock()

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
            
            # 减少并发数，避免数据库死锁
            max_workers = 1  # 暂时使用单线程处理，避免死锁
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                        
                    # 增加延迟，避免API限制
                    time.sleep(3)  # 每次处理后等待3秒
                        
        except Exception as e:
            logger.error(f"扫描OSS失败: {e}")
            
        finally:
            self.print_stats()
            
    def process_single_image_from_oss(self, oss_key: str) -> bool:
        """处理OSS中的单张图片 - 优化数据库操作"""
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
                    
                # 处理道具（如果有）
                if analysis.get('props'):
                    pose.props = json.dumps(analysis['props'], ensure_ascii=False)
                
                # 先提交pose更新
                db.commit()
                
                # 处理标签（使用锁避免并发冲突）
                self.process_tags_with_session_safe(db, pose, analysis.get('tags', []))
                
                logger.info(f"[SUCCESS] AI分析完成: {updated_data['title']}")
                logger.info(f"   场景: {updated_data['scene_category']}")
                logger.info(f"   角度: {updated_data['angle']}")
                logger.info(f"   标签: {updated_data['ai_tags']}")
                
                return True
            else:
                # AI分析失败，标记为失败状态
                pose.processing_status = 'failed'
                pose.error_message = 'AI分析失败'
                db.commit()
                
                logger.error(f"[ERROR] AI分析失败: {oss_key}")
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
    
    def process_tags_with_session_safe(self, db: Session, pose: Pose, tags: List[str]):
        """安全地处理图片标签 - 避免死锁"""
        with tag_processing_lock:  # 使用全局锁
            for tag_name in tags:
                if not tag_name.strip():
                    continue
                    
                tag_name = tag_name.strip()
                max_retries = 3
                
                for retry in range(max_retries):
                    try:
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
                            try:
                                db.commit()  # 立即提交标签
                            except IntegrityError:
                                # 如果标签已经存在（并发创建），回滚后重新查询
                                db.rollback()
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    continue  # 如果还是没找到，跳过这个标签
                            
                        # 创建关联关系
                        existing_pose_tag = db.query(PoseTag).filter(
                            PoseTag.pose_id == pose.id,
                            PoseTag.tag_id == tag.id
                        ).first()
                        
                        if not existing_pose_tag:
                            pose_tag = PoseTag(
                                pose_id=pose.id,
                                tag_id=tag.id,
                                confidence=0.9
                            )
                            db.add(pose_tag)
                            
                            # 更新标签使用次数
                            tag.usage_count += 1
                            
                            try:
                                db.commit()
                                break  # 成功处理，跳出重试循环
                            except IntegrityError:
                                # 关联关系已存在，回滚继续
                                db.rollback()
                                break
                                
                    except Exception as e:
                        logger.warning(f"处理标签 '{tag_name}' 失败 (第{retry+1}次): {e}")
                        db.rollback()
                        if retry == max_retries - 1:
                            logger.error(f"标签 '{tag_name}' 处理最终失败")
                        else:
                            time.sleep(0.1 * (retry + 1))  # 递增延迟
    
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
            
            # 创建新的数据库会话
            db = SessionLocal()
            try:
                # 重新查询pose对象
                pose = db.query(Pose).filter(Pose.id == pose.id).first()
                if not pose:
                    continue
                
                # 重置状态
                pose.processing_status = 'processing'
                pose.error_message = None
                db.commit()
                
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
                    
                    # 处理道具
                    if analysis.get('props'):
                        pose.props = json.dumps(analysis['props'], ensure_ascii=False)
                    
                    db.commit()
                    
                    # 处理标签
                    self.process_tags_with_session_safe(db, pose, analysis.get('tags', []))
                    
                    self.stats['success'] += 1
                    logger.info(f"[SUCCESS] 重试成功: {pose.title}")
                    
                else:
                    pose.processing_status = 'failed'
                    pose.error_message = 'AI分析失败（重试后）'
                    db.commit()
                    
                    self.stats['failed'] += 1
                    logger.error(f"[ERROR] 重试仍失败")
                    
            except Exception as e:
                pose.processing_status = 'failed'
                pose.error_message = f"重试异常: {str(e)}"
                db.commit()
                
                self.stats['failed'] += 1
                logger.error(f"[ERROR] 重试异常: {e}")
            finally:
                db.close()
                
            # 避免API限制
            time.sleep(5)  # 重试时间间隔更长
                
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

def main():
    parser = argparse.ArgumentParser(description='自动化图片处理工具 - 最终版本')
    parser.add_argument('--scan-oss', action='store_true', help='扫描OSS中的新图片')
    parser.add_argument('--retry-failed', action='store_true', help='重试失败的图片')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
        
    processor = ImageProcessor()
    
    try:
        if args.scan_oss:
            processor.scan_and_process_oss_images()
        elif args.retry_failed:
            processor.retry_failed_images()
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"执行失败: {e}")
    finally:
        processor.db.close()

if __name__ == "__main__":
    main()