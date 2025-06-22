from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func, desc
from typing import List, Tuple, Optional, Dict, Set
import re
import time
import jieba
import jieba.posseg as pseg
from fuzzywuzzy import fuzz, process
from collections import defaultdict, Counter
import json
import redis
from ..models.pose import Pose
from ..models.tag import Tag, PoseTag
from ..models.search_history import SearchHistory

class EnhancedSearchService:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.synonym_cache = {}
        self.spelling_corrections = {}
        self.popular_terms_cache = {}
        self._load_dictionaries()
        
        # 初始化 jieba 分词
        jieba.initialize()
        
        # 设置搜索缓存过期时间
        self.cache_expire = 3600  # 1小时
    
    def _load_dictionaries(self):
        """加载词典和同义词库"""
        # 扩展的同义词库
        self.synonym_cache = {
            # 拍摄风格
            '写真': ['拍照', '摄影', '人像', '肖像'],
            '美女': ['女生', '女孩', '女性', '美眉', '女士'],
            '帅哥': ['男生', '男孩', '男性', '型男', '男士'],
            '清新': ['小清新', '清爽', '自然', '淡雅'],
            '文艺': ['文青', '艺术', '复古', '怀旧'],
            '性感': ['魅惑', '妩媚', '诱人', '迷人'],
            '可爱': ['萌', '甜美', '俏皮', '活泼'],
            '温柔': ['柔美', '恬静', '优雅', '淑女'],
            
            # 场景地点
            '室内': ['屋内', '房间内', '室内环境'],
            '户外': ['室外', '外景', '野外', '户外环境'],
            '咖啡厅': ['咖啡馆', '咖啡店', '咖啡屋'],
            '海边': ['海滩', '沙滩', '海岸', '海景'],
            '公园': ['花园', '园林', '绿地'],
            '街头': ['街道', '马路', '城市', '都市'],
            '森林': ['树林', '山林', '丛林'],
            '校园': ['学校', '大学', '校园'],
            
            # 姿势动作
            '坐姿': ['坐着', '坐下', '坐位'],
            '站姿': ['站着', '站立', '站位'],
            '躺姿': ['躺着', '卧姿', '平躺'],
            '蹲姿': ['蹲着', '蹲下', '下蹲'],
            '跳跃': ['跳起', '腾空', '跳动'],
            '背影': ['背面', '后背', '背部'],
            '侧面': ['侧脸', '侧身', '半身'],
            
            # 情绪表达
            '开心': ['快乐', '高兴', '愉快', '欢乐'],
            '忧郁': ['忧伤', '忧愁', '沉思', '深沉'],
            '活泼': ['欢快', '生动', '活跃', '跳跃'],
            '安静': ['宁静', '平静', '沉默', '静谧'],
        }
        
        # 常见拼写错误纠正
        self.spelling_corrections = {
            '咖非厅': '咖啡厅',
            '俏比': '俏皮',
            '可爱': '可爱',
            '写真': '写真',
            '摄影': '摄影',
            '户外': '户外',
            '室内': '室内',
        }
    
    def _segment_and_analyze(self, query: str) -> Dict:
        """分词和词性分析"""
        # 分词
        words = jieba.lcut(query)
        
        # 词性标注
        pos_tags = list(pseg.cut(query))
        
        # 提取关键词（名词、形容词、动词）
        keywords = []
        for word, flag in pos_tags:
            if flag.startswith(('n', 'a', 'v')) and len(word) > 1:
                keywords.append(word)
        
        return {
            'words': words,
            'keywords': keywords,
            'pos_tags': pos_tags
        }
    
    def _expand_query_smart(self, query: str) -> List[str]:
        """智能查询扩展"""
        expanded_queries = [query]
        
        # 分词分析
        analysis = self._segment_and_analyze(query)
        keywords = analysis['keywords']
        
        # 同义词扩展
        for keyword in keywords:
            if keyword in self.synonym_cache:
                for synonym in self.synonym_cache[keyword]:
                    # 替换关键词生成新查询
                    new_query = query.replace(keyword, synonym)
                    expanded_queries.append(new_query)
        
        # 部分匹配扩展（去掉一些字符）
        if len(query) > 2:
            # 前缀匹配
            expanded_queries.append(query[:-1])
            # 后缀匹配
            expanded_queries.append(query[1:])
        
        return list(set(expanded_queries))
    
    def _fuzzy_match_correction(self, query: str, available_terms: List[str]) -> List[str]:
        """模糊匹配和拼写纠正"""
        corrections = []
        
        # 直接拼写纠正
        if query in self.spelling_corrections:
            corrections.append(self.spelling_corrections[query])
        
        # 模糊匹配
        matches = process.extract(query, available_terms, limit=3, scorer=fuzz.ratio)
        for match, score in matches:
            if score > 70:  # 相似度阈值
                corrections.append(match)
        
        return corrections
    
    def _get_available_terms(self, db: Session) -> List[str]:
        """获取可用的搜索词汇"""
        cache_key = "search_available_terms"
        
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # 从数据库获取
        terms = set()
        
        # 从标题和描述提取
        result = db.execute(
            text("SELECT title, description FROM poses WHERE status = 'active'")
        ).fetchall()
        
        for row in result:
            if row[0]:  # title
                terms.update(jieba.lcut(row[0]))
            if row[1]:  # description
                terms.update(jieba.lcut(row[1]))
        
        # 从标签获取
        tags = db.query(Tag.name).all()
        for tag in tags:
            terms.add(tag[0])
        
        # 过滤短词和无意义词
        filtered_terms = [term for term in terms if len(term) > 1 and term.isalpha()]
        
        # 缓存结果
        if self.redis_client:
            self.redis_client.setex(
                cache_key, 
                self.cache_expire, 
                json.dumps(filtered_terms, ensure_ascii=False)
            )
        
        return filtered_terms
    
    def search_poses_enhanced(
        self, 
        db: Session, 
        query: str, 
        category: Optional[str] = None,
        angle: Optional[str] = None,
        page: int = 1, 
        per_page: int = 20,
        enable_fuzzy: bool = True
    ) -> Tuple[List[Pose], int, Dict]:
        """增强的搜索功能"""
        start_time = time.time()
        search_info = {
            'original_query': query,
            'corrected_query': None,
            'expanded_queries': [],
            'suggestions': []
        }
        
        # 标准化查询
        normalized_query = self._normalize_query(query)
        
        # 拼写纠正和模糊匹配
        available_terms = self._get_available_terms(db)
        corrections = self._fuzzy_match_correction(query, available_terms)
        
        if corrections and enable_fuzzy:
            corrected_query = corrections[0]
            search_info['corrected_query'] = corrected_query
            query = corrected_query
        
        # 智能查询扩展
        expanded_queries = self._expand_query_smart(query)
        search_info['expanded_queries'] = expanded_queries
        
        # 构建搜索查询
        base_query = db.query(Pose).filter(Pose.status == 'active')
        
        # 多重搜索策略
        search_conditions = []
        
        # 1. 精确匹配（权重最高）
        for q in expanded_queries:
            search_conditions.append(
                text("MATCH(title, description) AGAINST(:query IN BOOLEAN MODE)")
                .params(query=f'"{q}"')
            )
        
        # 2. 自然语言匹配
        for q in expanded_queries:
            search_conditions.append(
                text("MATCH(title, description, ai_tags) AGAINST(:query IN NATURAL LANGUAGE MODE)")
                .params(query=q)
            )
        
        # 3. LIKE 模糊匹配（兜底策略）
        for q in expanded_queries:
            search_conditions.extend([
                Pose.title.like(f"%{q}%"),
                Pose.description.like(f"%{q}%"),
                Pose.ai_tags.like(f"%{q}%")
            ])
        
        # 4. 标签搜索
        tag_conditions = []
        for q in expanded_queries:
            tag_subquery = (
                db.query(PoseTag.pose_id)
                .join(Tag, PoseTag.tag_id == Tag.id)
                .filter(Tag.name.like(f"%{q}%"))
                .subquery()
            )
            tag_conditions.append(Pose.id.in_(tag_subquery))
        
        # 组合所有搜索条件
        all_conditions = search_conditions + tag_conditions
        if all_conditions:
            base_query = base_query.filter(or_(*all_conditions))
        
        # 分类和角度筛选
        if category:
            base_query = base_query.filter(Pose.scene_category == category)
        if angle:
            base_query = base_query.filter(Pose.angle == angle)
        
        # 获取总数
        total = base_query.count()
        
        # 排序：优先显示更相关的结果
        poses = (
            base_query
            .order_by(
                desc(Pose.view_count),  # 浏览量
                desc(Pose.created_at)   # 创建时间
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        
        # 记录搜索历史
        response_time = int((time.time() - start_time) * 1000)
        self._record_search_history(
            db, search_info['original_query'], normalized_query, 
            total, response_time, category
        )
        
        return poses, total, search_info
    
    def get_smart_suggestions(self, db: Session, prefix: str, limit: int = 10) -> List[Dict]:
        """智能搜索建议"""
        suggestions = []
        
        if len(prefix) < 1:
            return []
        
        # 1. 基于搜索历史的建议
        history_suggestions = self._get_history_suggestions(db, prefix, limit // 2)
        suggestions.extend(history_suggestions)
        
        # 2. 基于标签的建议
        tag_suggestions = self._get_tag_suggestions(db, prefix, limit // 2)
        suggestions.extend(tag_suggestions)
        
        # 3. 基于同义词的建议
        synonym_suggestions = self._get_synonym_suggestions(prefix, limit // 2)
        suggestions.extend(synonym_suggestions)
        
        # 去重并排序
        unique_suggestions = {}
        for suggestion in suggestions:
            text = suggestion['text']
            if text not in unique_suggestions:
                unique_suggestions[text] = suggestion
            else:
                # 合并权重
                unique_suggestions[text]['weight'] += suggestion['weight']
        
        # 按权重排序
        sorted_suggestions = sorted(
            unique_suggestions.values(), 
            key=lambda x: x['weight'], 
            reverse=True
        )
        
        return sorted_suggestions[:limit]
    
    def _get_history_suggestions(self, db: Session, prefix: str, limit: int) -> List[Dict]:
        """基于搜索历史的建议"""
        result = db.execute(
            text("""
                SELECT normalized_query, COUNT(*) as count
                FROM search_history 
                WHERE normalized_query LIKE :prefix
                AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY normalized_query
                ORDER BY count DESC
                LIMIT :limit
            """),
            {"prefix": f"{prefix}%", "limit": limit}
        ).fetchall()
        
        return [
            {
                'text': row[0],
                'type': 'history',
                'weight': row[1] * 10
            }
            for row in result
        ]
    
    def _get_tag_suggestions(self, db: Session, prefix: str, limit: int) -> List[Dict]:
        """基于标签的建议"""
        result = db.execute(
            text("""
                SELECT t.name, COUNT(pt.pose_id) as usage_count
                FROM tags t
                LEFT JOIN pose_tags pt ON t.id = pt.tag_id
                WHERE t.name LIKE :prefix
                GROUP BY t.id, t.name
                ORDER BY usage_count DESC
                LIMIT :limit
            """),
            {"prefix": f"%{prefix}%", "limit": limit}
        ).fetchall()
        
        return [
            {
                'text': row[0],
                'type': 'tag',
                'weight': row[1] * 5
            }
            for row in result
        ]
    
    def _get_synonym_suggestions(self, prefix: str, limit: int) -> List[Dict]:
        """基于同义词的建议"""
        suggestions = []
        
        for word, synonyms in self.synonym_cache.items():
            if prefix.lower() in word.lower():
                suggestions.append({
                    'text': word,
                    'type': 'synonym',
                    'weight': 3
                })
            
            for synonym in synonyms:
                if prefix.lower() in synonym.lower():
                    suggestions.append({
                        'text': synonym,
                        'type': 'synonym',
                        'weight': 2
                    })
        
        return suggestions[:limit]
    
    def _normalize_query(self, query: str) -> str:
        """标准化搜索词"""
        # 去除特殊字符，保留中文、英文和数字
        normalized = re.sub(r'[^\w\s\u4e00-\u9fff]', '', query.strip())
        return normalized.lower()
    
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
    
    def get_search_analytics(self, db: Session, days: int = 7) -> Dict:
        """获取搜索分析数据"""
        result = db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT normalized_query) as unique_queries,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(results_count) as avg_results,
                    COUNT(CASE WHEN results_count = 0 THEN 1 END) as zero_results
                FROM search_history 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            """),
            {"days": days}
        ).fetchone()
        
        # 获取热门搜索词
        popular_queries = db.execute(
            text("""
                SELECT normalized_query, COUNT(*) as count
                FROM search_history 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY normalized_query
                ORDER BY count DESC
                LIMIT 10
            """),
            {"days": days}
        ).fetchall()
        
        return {
            "total_searches": result[0] or 0,
            "unique_queries": result[1] or 0,
            "avg_response_time_ms": round(result[2] or 0, 2),
            "avg_results": round(result[3] or 0, 2),
            "zero_results_rate": round((result[4] or 0) / max(result[0] or 1, 1) * 100, 2),
            "popular_queries": [{"query": row[0], "count": row[1]} for row in popular_queries]
        }