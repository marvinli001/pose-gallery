"""
修正的PoseService - 专门处理姿势相关的数据库操作
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json
import logging

from ..models import Pose, Tag, PoseTag
from ..database import get_db

logger = logging.getLogger(__name__)

class PoseService:
    """姿势服务类 - 处理姿势相关的数据库操作"""
    
    def save_analyzed_pose(self, db: Session, oss_key: str, analysis: Dict) -> Optional[Pose]:
        """保存AI分析后的姿势数据"""
        try:
            # 查找现有记录
            pose = db.query(Pose).filter(Pose.oss_key == oss_key).first()
            
            if not pose:
                logger.error(f"未找到OSS key对应的记录: {oss_key}")
                return None
                
            # 更新AI分析结果
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
            
            # 处理标签关联
            self._process_pose_tags(db, pose, analysis.get('tags', []))
            
            db.commit()
            logger.info(f"姿势数据保存成功: {pose.title}")
            return pose
            
        except Exception as e:
            logger.error(f"保存姿势数据失败: {e}")
            db.rollback()
            return None
            
    def _process_pose_tags(self, db: Session, pose: Pose, tags: List[str]):
        """处理姿势标签关联"""
        # 清除现有标签关联
        db.query(PoseTag).filter(PoseTag.pose_id == pose.id).delete()
        
        for tag_name in tags:
            if not tag_name.strip():
                continue
                
            tag_name = tag_name.strip()
            
            # 查找或创建标签
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag_category = self._classify_tag(tag_name)
                tag = Tag(
                    name=tag_name,
                    category=tag_category,
                    usage_count=1
                )
                db.add(tag)
                db.flush()  # 获取tag.id
            else:
                tag.usage_count += 1
                
            # 创建关联
            pose_tag = PoseTag(
                pose_id=pose.id,
                tag_id=tag.id,
                confidence=0.9
            )
            db.add(pose_tag)
            
    def _classify_tag(self, tag_name: str) -> str:
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
        
    def create_pose_from_oss(self, db: Session, oss_key: str, oss_url: str, thumbnail_url: Optional[str] = None) -> Pose:
        """从OSS信息创建姿势记录"""
        pose_data = {
            'oss_key': oss_key,
            'oss_url': oss_url,
            'thumbnail_url': thumbnail_url,
            'title': f'摄影姿势 - {oss_key.split("/")[-1]}',
            'description': '待AI分析',
            'processing_status': 'pending',
            'status': 'active',
            'created_at': datetime.now(timezone.utc)
        }
        
        pose = Pose(**pose_data)
        db.add(pose)
        db.commit()
        
        logger.info(f"创建姿势记录: {pose.id}")
        return pose
        
    def get_poses_by_status(self, db: Session, status: str, limit: int = 100) -> List[Pose]:
        """根据处理状态获取姿势列表"""
        return db.query(Pose).filter(
            Pose.processing_status == status
        ).limit(limit).all()
        
    def update_pose_status(self, db: Session, pose_id: int, status: str, error_message: Optional[str] = None):
        """更新姿势处理状态"""
        pose = db.query(Pose).filter(Pose.id == pose_id).first()
        if pose:
            pose.processing_status = status
            if error_message:
                pose.error_message = error_message
            db.commit()
            
    def get_statistics(self, db: Session) -> Dict:
        """获取统计信息"""
        stats = {}
        
        # 基础统计
        stats['total'] = db.query(Pose).count()
        stats['active'] = db.query(Pose).filter(Pose.status == 'active').count()
        stats['pending'] = db.query(Pose).filter(Pose.processing_status == 'pending').count()
        stats['processing'] = db.query(Pose).filter(Pose.processing_status == 'processing').count()
        stats['completed'] = db.query(Pose).filter(Pose.processing_status == 'completed').count()
        stats['failed'] = db.query(Pose).filter(Pose.processing_status == 'failed').count()
        
        # 场景分类统计
        scene_stats = db.execute(
            text("""
                SELECT scene_category, COUNT(*) as count
                FROM poses 
                WHERE status = 'active' AND scene_category IS NOT NULL
                GROUP BY scene_category
                ORDER BY count DESC
            """)
        ).fetchall()
        
        stats['scenes'] = {scene: count for scene, count in scene_stats}
        
        return stats