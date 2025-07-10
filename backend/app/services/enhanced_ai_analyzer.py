import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedAIAnalyzer:
    """增强版AI分析器 - 用于查询分析和内容理解"""
    
    def __init__(self):
        self.available = True
        self.scene_keywords = {
            "室内": ["室内", "房间", "卧室", "客厅", "书房", "办公室", "家里"],
            "咖啡馆": ["咖啡馆", "咖啡店", "café", "cafe", "星巴克", "咖啡厅"],
            "街头": ["街头", "街道", "马路", "城市", "都市", "街拍"],
            "户外": ["户外", "公园", "草地", "自然", "花园", "海边", "山上"],
            "商务": ["商务", "办公", "职场", "正式", "西装", "会议"],
            "创意": ["创意", "艺术", "抽象", "时尚", "个性", "独特"]
        }
        
        self.pose_keywords = {
            "坐姿": ["坐", "坐着", "坐姿", "椅子", "沙发", "凳子"],
            "站立": ["站", "站着", "站立", "站姿", "直立"],
            "行走": ["走", "行走", "走路", "漫步", "步行"],
            "躺卧": ["躺", "躺着", "卧", "平躺", "侧躺"],
            "蹲下": ["蹲", "蹲下", "蹲姿", "半蹲"],
            "靠墙": ["靠", "靠墙", "倚靠", "依靠"]
        }
        
        self.angle_keywords = {
            "全身": ["全身", "全身照", "整体", "全貌", "完整"],
            "半身": ["半身", "半身照", "上半身", "腰部以上"],
            "特写": ["特写", "近景", "面部", "脸部", "头像"],
            "侧面": ["侧面", "侧脸", "侧身", "侧向"],
            "背面": ["背面", "背影", "后面", "背部"],
            "正面": ["正面", "正脸", "正向", "面对"]
        }
        
        self.style_keywords = {
            "文艺": ["文艺", "清新", "简约", "素雅", "淡雅"],
            "时尚": ["时尚", "潮流", "个性", "酷炫", "前卫"],
            "优雅": ["优雅", "端庄", "气质", "知性", "温柔"],
            "活泼": ["活泼", "青春", "可爱", "俏皮", "生动"],
            "商务": ["商务", "正式", "职业", "专业", "严肃"],
            "休闲": ["休闲", "随意", "自然", "舒适", "轻松"]
        }
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.available
    
    def analyze_search_query(self, query: str) -> Dict[str, Any]:
        """分析搜索查询，提取意图和关键词"""
        try:
            query_lower = query.lower().strip()
            
            # 提取关键词
            scene_related = self._extract_keywords(query_lower, self.scene_keywords)
            pose_related = self._extract_keywords(query_lower, self.pose_keywords)
            angle_related = self._extract_keywords(query_lower, self.angle_keywords)
            style_related = self._extract_keywords(query_lower, self.style_keywords)
            
            # 分析查询意图
            intent = self._analyze_intent(query_lower, scene_related, pose_related, angle_related, style_related)
            
            # 生成增强查询
            enhanced_query = self._generate_enhanced_query(
                query, scene_related, pose_related, angle_related, style_related
            )
            
            # 计算置信度
            confidence = self._calculate_confidence(scene_related, pose_related, angle_related, style_related)
            
            return {
                "analysis": {
                    "intent": intent,
                    "confidence": confidence,
                    "scene_related": scene_related,
                    "pose_related": pose_related,
                    "angle_related": angle_related,
                    "style_related": style_related,
                    "keywords_count": len(scene_related) + len(pose_related) + len(angle_related) + len(style_related)
                },
                "enhanced_query": enhanced_query,
                "suggestions": self._generate_suggestions(intent, scene_related, pose_related, angle_related, style_related)
            }
            
        except Exception as e:
            logger.error(f"查询分析失败: {e}")
            return {
                "analysis": {
                    "intent": "未知",
                    "confidence": 0.0,
                    "scene_related": [],
                    "pose_related": [],
                    "angle_related": [],
                    "style_related": [],
                    "keywords_count": 0
                },
                "enhanced_query": query,
                "suggestions": ["请尝试使用更具体的关键词"]
            }
    
    def _extract_keywords(self, query: str, keyword_dict: Dict[str, List[str]]) -> List[str]:
        """从查询中提取相关关键词"""
        found_keywords = []
        for category, keywords in keyword_dict.items():
            for keyword in keywords:
                if keyword in query:
                    found_keywords.append(category)
                    break
        return found_keywords
    
    def _analyze_intent(self, query: str, scene_related: List[str], pose_related: List[str], 
                       angle_related: List[str], style_related: List[str]) -> str:
        """分析查询意图"""
        if scene_related and not pose_related and not angle_related:
            return "场景搜索"
        elif pose_related and not scene_related:
            return "姿势搜索"
        elif angle_related:
            return "角度搜索"
        elif style_related:
            return "风格搜索"
        elif scene_related and pose_related:
            return "综合搜索"
        else:
            return "通用搜索"
    
    def _generate_enhanced_query(self, original_query: str, scene_related: List[str], 
                               pose_related: List[str], angle_related: List[str], 
                               style_related: List[str]) -> str:
        """生成增强查询"""
        # 如果已经很具体，直接返回
        if len(scene_related) + len(pose_related) + len(angle_related) + len(style_related) >= 3:
            return original_query
        
        # 添加同义词和相关词
        enhanced_parts = [original_query]
        
        # 添加场景相关词
        if scene_related:
            for scene in scene_related:
                if scene in self.scene_keywords:
                    enhanced_parts.extend(self.scene_keywords[scene][:2])
        
        # 添加姿势相关词
        if pose_related:
            for pose in pose_related:
                if pose in self.pose_keywords:
                    enhanced_parts.extend(self.pose_keywords[pose][:2])
        
        return " ".join(set(enhanced_parts))
    
    def _calculate_confidence(self, scene_related: List[str], pose_related: List[str], 
                            angle_related: List[str], style_related: List[str]) -> float:
        """计算分析置信度"""
        keyword_count = len(scene_related) + len(pose_related) + len(angle_related) + len(style_related)
        
        if keyword_count == 0:
            return 0.1
        elif keyword_count == 1:
            return 0.4
        elif keyword_count == 2:
            return 0.7
        elif keyword_count >= 3:
            return 0.9
        else:
            return 0.5
    
    def _generate_suggestions(self, intent: str, scene_related: List[str], 
                            pose_related: List[str], angle_related: List[str], 
                            style_related: List[str]) -> List[str]:
        """生成搜索建议"""
        suggestions = []
        
        if intent == "场景搜索":
            suggestions.append("尝试添加具体的拍摄角度，如「全身」「半身」「特写」")
            if not pose_related:
                suggestions.append("可以添加姿势描述，如「坐姿」「站立」「行走」")
        
        elif intent == "姿势搜索":
            suggestions.append("可以结合场景关键词，如「室内坐姿」「户外站立」")
            if not angle_related:
                suggestions.append("建议指定拍摄角度，如「正面」「侧面」「背面」")
        
        elif intent == "角度搜索":
            suggestions.append("可以添加场景或姿势描述，让搜索更精准")
        
        elif intent == "风格搜索":
            suggestions.append("建议添加具体场景，如「文艺咖啡馆」「商务办公室」")
        
        elif intent == "通用搜索":
            suggestions.append("建议使用更具体的描述词汇")
            suggestions.append("可以尝试：场景+姿势+角度的组合")
        
        if not suggestions:
            suggestions.append("搜索结果不理想？尝试使用同义词或更通用的词汇")
        
        return suggestions
    
    def analyze_pose_content(self, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析姿势内容，用于匹配优化"""
        try:
            title = pose_data.get("title", "")
            description = pose_data.get("description", "")
            ai_tags = pose_data.get("ai_tags", "")
            scene_category = pose_data.get("scene_category", "")
            angle = pose_data.get("angle", "")
            
            # 提取内容特征
            content_features = {
                "scene_type": scene_category,
                "angle_type": angle,
                "extracted_scenes": self._extract_keywords(title.lower() + " " + description.lower(), self.scene_keywords),
                "extracted_poses": self._extract_keywords(title.lower() + " " + description.lower(), self.pose_keywords),
                "extracted_angles": self._extract_keywords(title.lower() + " " + description.lower(), self.angle_keywords),
                "extracted_styles": self._extract_keywords(title.lower() + " " + description.lower(), self.style_keywords),
                "tag_count": len(ai_tags.split(",")) if ai_tags else 0
            }
            
            return content_features
            
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            return {}

    def _build_enhanced_analysis_prompt(self) -> str:
        """构建增强版分析提示词 - 针对向量搜索优化"""
        return """
你是一个专业的摄影作品分析专家。请仔细分析这张图片，重点关注以下几个方面来生成高质量的标签和描述，以便用户能够准确搜索到相关内容。

请按照以下JSON格式返回分析结果：

{
    "title": "简洁的标题",
    "description": "详细的姿势描述",
    "scene_category": "场景分类",
    "angle": "拍摄角度",
    "primary_tags": ["核心标签1", "核心标签2"],
    "semantic_tags": ["语义标签1", "语义标签2"],
    "style_tags": ["风格标签1", "风格标签2"],
    "emotion_tags": ["情感标签1", "情感标签2"],
    "clothing_tags": ["服装标签1", "服装标签2"],
    "props": ["道具1", "道具2"],
    "color_scheme": ["主色调1", "主色调2"],
    "lighting": "光线描述",
    "composition": "构图描述",
    "shooting_tips": "拍摄建议",
    "search_keywords": ["搜索关键词1", "搜索关键词2"],
    "confidence": 0.95
}

**详细分析要求：**

1. **title**: 3-8个字，突出最显著特征

2. **description**: 80-150字，包含：
   - 人物状态和动作
   - 环境和背景
   - 整体氛围感受

3. **分层标签系统**：
   - **primary_tags**: 3-5个核心标签，最重要的特征
   - **semantic_tags**: 5-8个语义标签，描述场景含义
   - **style_tags**: 3-5个风格标签（日系、韩系、欧美、复古等）
   - **emotion_tags**: 2-4个情感标签（温柔、活泼、忧郁、俏皮等）
   - **clothing_tags**: 3-6个服装标签（具体服装类型、颜色、风格）

4. **视觉元素**：
   - **color_scheme**: 主要颜色调性
   - **lighting**: 光线类型和效果
   - **composition**: 构图特点

5. **search_keywords**: 10-15个用户可能搜索的关键词，包括：
   - 同义词和近义词
   - 通俗表达
   - 专业术语
   - 相关概念

6. **场景和角度**：严格按照预设选项选择

重点：生成的标签要考虑中文用户的搜索习惯，包含多种表达方式。
"""