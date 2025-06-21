from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func, desc
from typing import List, Tuple, Optional
import re
import time
from ..models.pose import Pose
from ..models.tag import Tag, PoseTag
from ..models.search_history import SearchHistory

class SearchService:
    def __init__(self):
        self.synonym_cache = {}
        self._load_synonyms()
    
    def _load_synonyms(self):
        """加载同义词缓存"""
        # 这里可以从数据库加载同义词，暂时硬编码一些
        self.synonym_cache = {
            '写真': ['拍照', '摄影', '人像'],
            '美女': ['女生', '女孩', '女性'],
            '室内': ['屋内', '房间内'],
            '户外': ['室外', '外景'],
            '咖啡厅': ['咖啡馆', '咖啡店'],
            '坐姿': ['坐着', '坐下'],
            '站姿': ['站着', '站立'],
        }
    
    def _expand_query(self, query: str) -> List[str]:
        """扩展搜索词（同义词）"""
        words = [query]
        for word, synonyms in self.synonym_cache.items():
            if word in query:
                for synonym in synonyms:
                    words.append(query.replace(word, synonym))
        return list(set(words))
    
    def _normalize_query(self, query: str) -> str:
        """标准化搜索词"""
        # 去除特殊字符，转换为小写
        return re.sub(r'[^\w\s]', '', query.lower().strip())
    
    def search_poses(
        self, 
        db: Session, 
        query: str, 
        category: Optional[str] = None,
        angle: Optional[str] = None,
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List[Pose], int]:
        """搜索姿势图片"""
        start_time = time.time()
        
        # 标准化查询
        normalized_query = self._normalize_query(query)
        expanded_queries = self._expand_query(query)
        
        # 构建基础查询
        base_query = db.query(Pose).filter(Pose.status == 'active')
        
        # 全文搜索条件
        search_conditions = []
        for q in expanded_queries:
            search_conditions.append(
                text("MATCH(title, description, ai_tags) AGAINST(:query IN NATURAL LANGUAGE MODE)")
                .params(query=q)
            )
        
        # 标签搜索条件
        tag_conditions = []
        for q in expanded_queries:
            tag_subquery = (
                db.query(PoseTag.pose_id)
                .join(Tag, PoseTag.tag_id == Tag.id)
                .filter(Tag.name.like(f"%{q}%"))
                .subquery()
            )
            tag_conditions.append(Pose.id.in_(tag_subquery))
        
        # 组合搜索条件
        if search_conditions or tag_conditions:
            all_conditions = search_conditions + tag_conditions
            base_query = base_query.filter(or_(*all_conditions))
        
        # 分类筛选
        if category:
            base_query = base_query.filter(Pose.scene_category == category)
        
        # 角度筛选
        if angle:
            base_query = base_query.filter(Pose.angle == angle)
        
        # 获取总数
        total = base_query.count()
        
        # 分页和排序
        poses = (
            base_query
            .order_by(desc(Pose.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        
        # 记录搜索历史
        response_time = int((time.time() - start_time) * 1000)
        self._record_search_history(
            db, query, normalized_query, total, response_time, category
        )
        
        # 更新搜索计数
        if poses:
            pose_ids = [pose.id for pose in poses]
            db.execute(
                text("UPDATE poses SET search_count = search_count + 1 WHERE id IN :ids"),
                {"ids": pose_ids}
            )
            db.commit()
        
        return poses, total
    
    def _record_search_history(
        self, 
        db: Session, 
        query: str, 
        normalized_query: str,
        results_count: int, 
        response_time: int,
        category: Optional[str] = None
    ):
        """记录搜索历史"""
        try:
            history = SearchHistory(
                query=query,
                normalized_query=normalized_query,
                results_count=results_count,
                response_time_ms=response_time,
                filter_category=category
            )
            db.add(history)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"记录搜索历史失败: {e}")
    
    def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        # 这里可以基于搜索历史、标签等生成建议
        # 暂时返回一些基础建议
        suggestions = []
        
        # 基于常见搜索词
        common_terms = [
            '室内写真', '户外拍照', '咖啡厅', '街头', '森系',
            '文艺', '清新', '复古', '性感', '可爱',
            '坐姿', '站姿', '躺姿', '背影', '侧面'
        ]
        
        for term in common_terms:
            if prefix.lower() in term.lower():
                suggestions.append(term)
        
        return suggestions[:limit]
    
    def get_popular_searches(self, db: Session, limit: int = 10) -> List[dict]:
        """获取热门搜索"""
        result = db.execute(
            text("""
                SELECT normalized_query, COUNT(*) as count
                FROM search_history 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY normalized_query
                ORDER BY count DESC
                LIMIT :limit
            """),
            {"limit": limit}
        ).fetchall()
        
        return [{"query": row[0], "count": row[1]} for row in result]
    
    def get_categories_with_count(self, db: Session) -> List[dict]:
        """获取分类及数量"""
        result = db.execute(
            text("""
                SELECT scene_category, COUNT(*) as count 
                FROM poses 
                WHERE status = 'active' AND scene_category IS NOT NULL
                GROUP BY scene_category
                ORDER BY count DESC
            """)
        ).fetchall()
        
        return [{"name": row[0], "count": row[1]} for row in result]
    
    def get_angles_with_count(self, db: Session) -> List[dict]:
        """获取角度及数量"""
        result = db.execute(
            text("""
                SELECT angle, COUNT(*) as count 
                FROM poses 
                WHERE status = 'active' AND angle IS NOT NULL
                GROUP BY angle
                ORDER BY count DESC
            """)
        ).fetchall()
        
        return [{"name": row[0], "count": row[1]} for row in result]