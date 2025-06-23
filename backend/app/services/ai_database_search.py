from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from ..models.pose import Pose
from ..models.tag import Tag, PoseTag
from .ai_analyzer import AIAnalyzer
import json
import logging

logger = logging.getLogger(__name__)

class AIDatabaseSearchService:
    """AI数据库搜索服务"""
    
    def __init__(self):
        self.ai_analyzer = AIAnalyzer()
    
    def ai_search_database(self, db: Session, user_query: str) -> Dict:
        """使用AI理解用户查询，生成精确的数据库查询"""
        try:
            # 第一步：分析用户查询意图
            search_intent = self._analyze_search_intent(user_query)
            
            # 第二步：生成数据库查询
            sql_conditions = self._generate_sql_conditions(search_intent)
            
            # 第三步：执行搜索
            poses = self._execute_smart_search(db, sql_conditions)
            
            # 第四步：AI相关性排序
            ranked_poses = self._ai_relevance_ranking(poses, user_query, search_intent)
            
            return {
                "poses": ranked_poses,
                "total": len(ranked_poses),
                "search_intent": search_intent,
                "sql_conditions": sql_conditions,
                "ai_explanation": search_intent.get("explanation", "")
            }
            
        except Exception as e:
            logger.error(f"AI数据库搜索失败: {e}")
            # 回退到传统搜索
            return self._fallback_search(db, user_query)
    
    def _analyze_search_intent(self, user_query: str) -> Dict:
        """分析用户搜索意图"""
        prompt = f"""
分析以下摄影姿势搜索查询，提取搜索意图和条件：

用户查询："{user_query}"

请以JSON格式返回分析结果：
{{
    "intent_type": "specific_pose|scene_based|mood_based|style_based|mixed",
    "scene_category": "室内|户外|咖啡厅|商场|学校|办公室|海边|森林|城市|其他|null",
    "angle": "正面|侧面|背面|俯视|仰视|斜角|null", 
    "mood_tags": ["情绪标签1", "情绪标签2"],
    "pose_tags": ["姿势标签1", "姿势标签2"],
    "style_tags": ["风格标签1", "风格标签2"],
    "prop_tags": ["道具标签1", "道具标签2"],
    "keywords": ["关键词1", "关键词2"],
    "filters": {{
        "title_contains": ["标题包含词"],
        "description_contains": ["描述包含词"]
    }},
    "explanation": "搜索意图解释"
}}

分析说明：
1. 识别查询类型（具体姿势、场景、情绪、风格等）
2. 提取数据库字段匹配条件
3. 分类标签类型用于精确匹配
4. 提供搜索逻辑解释

示例：
- "咖啡厅拍照姿势" → scene_category: "咖啡厅", pose_tags: ["拍照", "坐姿"]
- "俏皮可爱的女生" → mood_tags: ["俏皮", "可爱"], keywords: ["女生"]
- "侧面站立写真" → angle: "侧面", pose_tags: ["站立", "写真"]
"""
        
        try:
            response = self.ai_analyzer.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": "你是专业的摄影搜索分析师，精通数据库查询优化。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            return self._parse_intent_result(result_text)
            
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "intent_type": "mixed",
                "keywords": [user_query],
                "explanation": "AI分析失败，使用关键词搜索"
            }
    
    def _parse_intent_result(self, result_text: str) -> Dict:
        """解析AI意图分析结果"""
        try:
            # 提取JSON
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.rfind("```")
                result_text = result_text[json_start:json_end].strip()
            
            result = json.loads(result_text)
            
            # 清理空值
            for key, value in result.items():
                if value == "null" or value == "None":
                    result[key] = None
                elif isinstance(value, list):
                    result[key] = [v for v in value if v and v != "null"]
            
            return result
            
        except Exception as e:
            logger.error(f"解析意图结果失败: {e}")
            return {"intent_type": "mixed", "keywords": ["搜索"]}
    
    def _generate_sql_conditions(self, search_intent: Dict) -> Dict:
        """根据搜索意图生成SQL查询条件"""
        conditions = {
            "where_clauses": [],
            "join_clauses": [],
            "having_clauses": [],
            "order_by": []
        }
        
        # 基础条件
        conditions["where_clauses"].append("p.status = 'active'")
        
        # 场景分类条件
        if search_intent.get("scene_category"):
            conditions["where_clauses"].append(
                f"p.scene_category = '{search_intent['scene_category']}'"
            )
        
        # 角度条件
        if search_intent.get("angle"):
            conditions["where_clauses"].append(
                f"p.angle = '{search_intent['angle']}'"
            )
        
        # 标签条件
        tag_conditions = []
        all_tags = (
            search_intent.get("mood_tags", []) + 
            search_intent.get("pose_tags", []) + 
            search_intent.get("style_tags", []) + 
            search_intent.get("prop_tags", [])
        )
        
        if all_tags:
            # 需要JOIN标签表
            conditions["join_clauses"].append(
                "LEFT JOIN pose_tags pt ON p.id = pt.pose_id"
            )
            conditions["join_clauses"].append(
                "LEFT JOIN tags t ON pt.tag_id = t.id"
            )
            
            # 标签匹配条件
            tag_like_conditions = []
            for tag in all_tags:
                tag_like_conditions.append(f"t.name LIKE '%{tag}%'")
            
            if tag_like_conditions:
                conditions["where_clauses"].append(
                    f"({' OR '.join(tag_like_conditions)})"
                )
        
        # 关键词条件（全文搜索）
        keywords = search_intent.get("keywords", [])
        title_contains = search_intent.get("filters", {}).get("title_contains", [])
        desc_contains = search_intent.get("filters", {}).get("description_contains", [])
        
        fulltext_terms = keywords + title_contains + desc_contains
        
        if fulltext_terms:
            fulltext_conditions = []
            for term in fulltext_terms:
                fulltext_conditions.extend([
                    f"MATCH(p.title, p.description, p.ai_tags) AGAINST('{term}' IN NATURAL LANGUAGE MODE)",
                    f"p.title LIKE '%{term}%'",
                    f"p.description LIKE '%{term}%'",
                    f"p.ai_tags LIKE '%{term}%'"
                ])
            
            if fulltext_conditions:
                conditions["where_clauses"].append(
                    f"({' OR '.join(fulltext_conditions)})"
                )
        
        # 排序：相关性 + 浏览量 + 时间
        conditions["order_by"] = [
            "p.view_count DESC",
            "p.created_at DESC"
        ]
        
        return conditions
    
    def _execute_smart_search(self, db: Session, sql_conditions: Dict) -> List[Pose]:
        """执行智能搜索"""
        try:
            # 构建基础查询
            base_select = "SELECT DISTINCT p.*"
            base_from = "FROM poses p"
            
            # 添加JOIN
            joins = " ".join(sql_conditions.get("join_clauses", []))
            
            # 添加WHERE条件
            where_clause = ""
            if sql_conditions.get("where_clauses"):
                where_clause = "WHERE " + " AND ".join(sql_conditions["where_clauses"])
            
            # 添加排序
            order_clause = ""
            if sql_conditions.get("order_by"):
                order_clause = "ORDER BY " + ", ".join(sql_conditions["order_by"])
            
            # 限制结果数量
            limit_clause = "LIMIT 50"
            
            # 完整SQL
            sql_query = f"""
            {base_select}
            {base_from}
            {joins}
            {where_clause}
            {order_clause}
            {limit_clause}
            """
            
            logger.info(f"执行AI生成的SQL查询: {sql_query}")
            
            # 执行查询
            result = db.execute(text(sql_query))
            pose_data = result.fetchall()
            
            # 转换为Pose对象
            poses = []
            for row in pose_data:
                pose = db.query(Pose).filter(Pose.id == row.id).first()
                if pose:
                    poses.append(pose)
            
            return poses
            
        except Exception as e:
            logger.error(f"执行智能搜索失败: {e}")
            # 回退到简单查询
            return db.query(Pose).filter(Pose.status == 'active').limit(20).all()
    
    def _ai_relevance_ranking(self, poses: List[Pose], user_query: str, search_intent: Dict) -> List[Dict]:
        """使用AI对搜索结果进行相关性排序"""
        try:
            if not poses:
                return []
            
            # 准备姿势信息用于AI排序
            pose_info = []
            for pose in poses[:20]:  # 限制数量以控制AI调用成本
                pose_info.append({
                    "id": pose.id,
                    "title": pose.title or "",
                    "description": pose.description or "",
                    "scene_category": pose.scene_category or "",
                    "angle": pose.angle or "",
                    "ai_tags": pose.ai_tags or "",
                    "view_count": pose.view_count
                })
            
            # AI相关性评分
            ranking_prompt = f"""
根据用户查询对以下摄影姿势进行相关性排序：

用户查询："{user_query}"
搜索意图：{search_intent.get('explanation', '')}

姿势列表：
{json.dumps(pose_info, ensure_ascii=False, indent=2)}

请返回按相关性排序的姿势ID列表：
{{
    "ranked_ids": [1, 3, 2, ...],
    "explanations": {{
        "1": "最相关原因",
        "3": "次相关原因"
    }}
}}

排序规则：
1. 与查询意图的匹配度
2. 标题和描述的相关性
3. 场景和角度的匹配
4. 标签的相关性
5. 流行度（浏览量）
"""
            
            response = self.ai_analyzer.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": "你是专业的搜索相关性分析师。"},
                    {"role": "user", "content": ranking_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            ranking_result = self._parse_ranking_result(result_text)
            
            # 根据AI排序重新排列结果
            ranked_poses = []
            pose_dict = {pose.id: pose for pose in poses}
            
            for pose_id in ranking_result.get("ranked_ids", []):
                if pose_id in pose_dict:
                    pose = pose_dict[pose_id]
                    ranked_poses.append({
                        "id": pose.id,
                        "oss_url": pose.oss_url,
                        "thumbnail_url": pose.thumbnail_url,
                        "title": pose.title,
                        "description": pose.description,
                        "scene_category": pose.scene_category,
                        "angle": pose.angle,
                        "view_count": pose.view_count,
                        "created_at": pose.created_at.isoformat() if pose.created_at else None,
                        "ai_relevance_explanation": ranking_result.get("explanations", {}).get(str(pose_id), "")
                    })
            
            # 添加未被AI排序的结果
            ranked_ids = set(ranking_result.get("ranked_ids", []))
            for pose in poses:
                if pose.id not in ranked_ids:
                    ranked_poses.append({
                        "id": pose.id,
                        "oss_url": pose.oss_url,
                        "thumbnail_url": pose.thumbnail_url,
                        "title": pose.title,
                        "description": pose.description,
                        "scene_category": pose.scene_category,
                        "angle": pose.angle,
                        "view_count": pose.view_count,
                        "created_at": pose.created_at.isoformat() if pose.created_at else None,
                        "ai_relevance_explanation": "标准匹配"
                    })
            
            return ranked_poses
            
        except Exception as e:
            logger.error(f"AI相关性排序失败: {e}")
            # 回退到原始结果
            return [
                {
                    "id": pose.id,
                    "oss_url": pose.oss_url,
                    "thumbnail_url": pose.thumbnail_url,
                    "title": pose.title,
                    "description": pose.description,
                    "scene_category": pose.scene_category,
                    "angle": pose.angle,
                    "view_count": pose.view_count,
                    "created_at": pose.created_at.isoformat() if pose.created_at else None,
                    "ai_relevance_explanation": "默认排序"
                } for pose in poses
            ]
    
    def _parse_ranking_result(self, result_text: str) -> Dict:
        """解析AI排序结果"""
        try:
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.rfind("```")
                result_text = result_text[json_start:json_end].strip()
            
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            logger.error(f"解析排序结果失败: {e}")
            return {"ranked_ids": [], "explanations": {}}
    
    def _fallback_search(self, db: Session, user_query: str) -> Dict:
        """回退搜索方法"""
        poses = db.query(Pose).filter(
            Pose.status == 'active'
        ).filter(
            or_(
                Pose.title.like(f"%{user_query}%"),
                Pose.description.like(f"%{user_query}%"),
                Pose.ai_tags.like(f"%{user_query}%")
            )
        ).limit(20).all()
        
        return {
            "poses": [
                {
                    "id": pose.id,
                    "oss_url": pose.oss_url,
                    "thumbnail_url": pose.thumbnail_url,
                    "title": pose.title,
                    "description": pose.description,
                    "scene_category": pose.scene_category,
                    "angle": pose.angle,
                    "view_count": pose.view_count,
                    "created_at": pose.created_at.isoformat() if pose.created_at else None,
                    "ai_relevance_explanation": "关键词匹配"
                } for pose in poses
            ],
            "total": len(poses),
            "search_intent": {"intent_type": "fallback"},
            "ai_explanation": "使用传统关键词搜索"
        }