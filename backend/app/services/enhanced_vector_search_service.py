import json
import os
from typing import List, Tuple, Optional, Dict
import logging
import numpy as np
import openai
from openai import OpenAI
import faiss
from ..config import settings

logger = logging.getLogger(__name__)

class EnhancedVectorSearchService:
    """增强版向量搜索服务 - 支持多阶段检索和GPT重排序"""
    
    def __init__(self, index_path: str, id_map_path: str):
        self.index_path = index_path
        self.id_map_path = id_map_path
        self.index = None
        self.id_map = None
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.available = False
        self._load_index()
    
    def _load_index(self):
        """加载索引和ID映射"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.id_map_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.id_map_path, "r", encoding="utf-8") as f:
                    self.id_map = json.load(f)
                self.available = True
                logger.info("增强版向量索引加载成功")
            else:
                logger.warning(f"向量索引文件未找到: {self.index_path} 或 {self.id_map_path}")
                logger.warning("增强版向量搜索功能将不可用")
        except Exception as e:
            logger.error(f"增强版索引加载失败: {e}")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.available
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """基础向量搜索"""
        if not self.available:
            return []
        
        try:
            # 生成查询向量
            query_vec = self._embed(query)
            if query_vec is None:
                return []
            
            # 向量搜索
            distances, indices = self.index.search(query_vec.reshape(1, -1), top_k)
            
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0 or str(idx) not in self.id_map:
                    continue
                
                pose_id = self.id_map[str(idx)]
                similarity = self._distance_to_similarity(dist)
                results.append((pose_id, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"基础向量搜索失败: {e}")
            return []
    
    def multi_stage_search(self, query: str, final_k: int = 10, 
                          stage1_k: int = 50, min_similarity: float = 0.3) -> List[Tuple[int, float]]:
        """多阶段搜索：向量召回 + GPT重排序"""
        
        # 阶段1：向量召回更多候选
        stage1_results = self._vector_recall(query, stage1_k)
        
        if not stage1_results:
            return []
        
        # 阶段2：GPT重排序
        stage2_results = self._gpt_rerank(query, stage1_results, final_k)
        
        # 阶段3：最终质量过滤
        final_results = self._quality_filter(stage2_results, min_similarity)
        
        return final_results
    
    def _vector_recall(self, query: str, top_k: int) -> List[Tuple[int, float, str]]:
        """阶段1：向量召回"""
        if not self.available:
            return []
        
        try:
            # 生成查询向量
            query_vec = self._embed(query)
            if query_vec is None:
                return []
            
            # 向量搜索
            distances, indices = self.index.search(query_vec.reshape(1, -1), top_k)
            
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0 or str(idx) not in self.id_map:
                    continue
                
                pose_id = self.id_map[str(idx)]
                similarity = self._distance_to_similarity(dist)
                
                # 获取原始文本（用于重排序）
                original_text = self._get_pose_text(pose_id)
                results.append((pose_id, similarity, original_text))
            
            return results
            
        except Exception as e:
            logger.error(f"向量召回失败: {e}")
            return []
    
    def _gpt_rerank(self, query: str, candidates: List[Tuple[int, float, str]], 
                   final_k: int) -> List[Tuple[int, float]]:
        """阶段2：GPT重排序"""
        if not candidates:
            return []
        
        try:
            # 构建重排序prompt
            prompt = self._build_rerank_prompt(query, candidates)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 使用更快的模型做重排序
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            
            # 解析重排序结果
            reranked_results = self._parse_rerank_result(response.choices[0].message.content, candidates)
            
            return reranked_results[:final_k]
            
        except Exception as e:
            logger.error(f"GPT重排序失败: {e}")
            # 降级到原始排序
            return [(pose_id, score) for pose_id, score, _ in candidates[:final_k]]
    
    def _build_rerank_prompt(self, query: str, candidates: List[Tuple[int, float, str]]) -> str:
        """构建重排序prompt"""
        candidates_text = ""
        for i, (pose_id, score, text) in enumerate(candidates):
            candidates_text += f"\n{i+1}. ID:{pose_id} (向量相似度:{score:.3f})\n内容: {text[:200]}...\n"
        
        return f"""
你是一个专业的图片搜索排序专家。用户搜索: "{query}"

以下是候选结果：
{candidates_text}

请根据用户查询的意图，对这些结果进行重新排序，只返回最相关的结果。

评分标准：
1. 语义相关性：内容是否与查询意图匹配
2. 关键词匹配：是否包含查询的关键词
3. 上下文理解：是否理解查询的隐含含义
4. 质量评估：描述是否详细准确

请按以下JSON格式返回排序结果：
{{
    "reranked_results": [
        {{"id": 123, "score": 0.95, "reason": "完全匹配用户查询意图"}},
        {{"id": 456, "score": 0.85, "reason": "部分匹配但相关性高"}}
    ],
    "filtered_count": 2
}}

只返回相关性分数 > 0.6 的结果，最多返回10个。
"""
    
    def _parse_rerank_result(self, result_text: str, candidates: List[Tuple[int, float, str]]) -> List[Tuple[int, float]]:
        """解析重排序结果"""
        try:
            # 提取JSON
            if '```json' in result_text:
                json_str = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                json_str = result_text.split('```')[1]
            else:
                json_str = result_text
            
            result = json.loads(json_str.strip())
            reranked = []
            
            for item in result.get('reranked_results', []):
                pose_id = item.get('id')
                score = item.get('score', 0.0)
                if score > 0.6:  # 质量阈值
                    reranked.append((pose_id, score))
            
            return reranked
            
        except Exception as e:
            logger.error(f"重排序结果解析失败: {e}")
            # 降级处理
            return [(pose_id, score) for pose_id, score, _ in candidates]
    
    def _quality_filter(self, results: List[Tuple[int, float]], min_similarity: float) -> List[Tuple[int, float]]:
        """阶段3：最终质量过滤"""
        if not results:
            return []
        
        # 动态阈值调整
        scores = [score for _, score in results]
        avg_score = sum(scores) / len(scores)
        
        # 如果平均分很低，说明查询质量不好，提高阈值
        dynamic_threshold = max(min_similarity, avg_score * 0.8)
        
        filtered = [(pose_id, score) for pose_id, score in results if score >= dynamic_threshold]
        
        logger.info(f"质量过滤: {len(results)} -> {len(filtered)} (阈值: {dynamic_threshold:.3f})")
        return filtered
    
    def _embed(self, text: str) -> Optional[np.ndarray]:
        """生成向量"""
        try:
            resp = self.client.embeddings.create(input=[text], model="text-embedding-3-small")
            return np.array(resp.data[0].embedding, dtype="float32")
        except Exception as e:
            logger.error(f"向量生成失败: {e}")
            return None
    
    def _distance_to_similarity(self, distance: float) -> float:
        """转换距离为相似度"""
        return max(0.0, 1.0 - distance / 2.0)
    
    def _get_pose_text(self, pose_id: int) -> str:
        """获取pose的原始文本（需要从数据库查询）"""
        # 这里需要实现从数据库获取文本的逻辑
        # 目前返回占位符
        return f"pose_{pose_id}_text"
    
# 在现有的 EnhancedVectorSearchService 类中添加以下方法：

def search_with_pagination(self, query: str, page: int = 1, page_size: int = 10, 
                          similarity_threshold: float = 1.5) -> Dict:
    """
    分页向量搜索
    
    Args:
        query: 搜索查询
        page: 页码（从1开始）
        page_size: 每页数量
        similarity_threshold: 相似度阈值
    
    Returns:
        {
            'results': [(pose_id, similarity_score), ...],
            'total': 总数量,
            'page': 当前页,
            'has_next': 是否有下一页
        }
    """
    if not self.available:
        return {'results': [], 'total': 0, 'page': page, 'has_next': False}
    
    try:
        # 搜索更大的候选集
        search_k = min(page * page_size * 5, 1000)  # 最多搜索1000个候选
        
        query_vec = self._embed(query)
        if query_vec is None:
            return {'results': [], 'total': 0, 'page': page, 'has_next': False}
        
        distances, indices = self.index.search(query_vec.reshape(1, -1), search_k)
        
        # 过滤和排序所有结果
        all_results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or str(idx) not in self.id_map:
                continue
                
            # 应用相似度阈值过滤
            if dist > similarity_threshold:
                continue
                
            pose_id = self.id_map[str(idx)]
            similarity = self._distance_to_similarity(dist)
            all_results.append((pose_id, similarity))
        
        # 按相似度排序
        all_results.sort(key=lambda x: x[1], reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = all_results[start_idx:end_idx]
        
        logger.info(f"分页搜索: 总数={len(all_results)}, 页码={page}, 页大小={page_size}")
        
        return {
            'results': page_results,
            'total': len(all_results),
            'page': page,
            'has_next': end_idx < len(all_results)
        }
        
    except Exception as e:
        logger.error(f"分页搜索失败: {e}")
        return {'results': [], 'total': 0, 'page': page, 'has_next': False}

def search_with_dynamic_threshold(self, query: str, target_count: int = 20, 
                                 min_similarity: float = 0.3) -> List[Tuple[int, float]]:
    """
    动态阈值搜索，确保返回足够多的相关结果
    
    Args:
        query: 搜索查询
        target_count: 目标返回数量
        min_similarity: 最低相似度要求
    """
    if not self.available:
        return []
    
    try:
        query_vec = self._embed(query)
        if query_vec is None:
            return []
        
        # 搜索更大的候选集
        search_k = min(target_count * 10, 1000)
        distances, indices = self.index.search(query_vec.reshape(1, -1), search_k)
        
        # 收集所有有效结果
        valid_results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or str(idx) not in self.id_map:
                continue
            
            similarity = self._distance_to_similarity(dist)
            if similarity >= min_similarity:
                pose_id = self.id_map[str(idx)]
                valid_results.append((pose_id, similarity, dist))
        
        if not valid_results:
            return []
        
        # 按相似度排序
        valid_results.sort(key=lambda x: x[1], reverse=True)
        
        # 动态确定阈值
        if len(valid_results) >= target_count:
            # 如果结果够多，使用更严格的阈值
            threshold_similarity = valid_results[target_count - 1][1]
            # 确保阈值不会过于严格
            threshold_similarity = max(threshold_similarity, min_similarity)
        else:
            # 如果结果不够，使用最低阈值
            threshold_similarity = min_similarity
        
        # 应用动态阈值
        final_results = [
            (pose_id, similarity) 
            for pose_id, similarity, _ in valid_results 
            if similarity >= threshold_similarity
        ]
        
        logger.info(f"动态阈值搜索: 候选={len(valid_results)}, 最终={len(final_results)}, 阈值={threshold_similarity:.3f}")
        
        return final_results[:target_count]
        
    except Exception as e:
        logger.error(f"动态阈值搜索失败: {e}")
        return []

def multi_tier_search(self, query: str, target_count: int = 20) -> List[Tuple[int, float]]:
    """
    多层次搜索：先严格后宽松
    """
    # 第一层：严格搜索
    strict_results = self.search(query, top_k=target_count)
    
    if len(strict_results) >= target_count:
        logger.info(f"严格搜索满足需求: {len(strict_results)} 个结果")
        return strict_results[:target_count]
    
    # 第二层：动态阈值搜索
    logger.info(f"严格搜索结果不足({len(strict_results)}个)，启用动态阈值搜索")
    dynamic_results = self.search_with_dynamic_threshold(query, target_count, min_similarity=0.2)
    
    if len(dynamic_results) >= target_count:
        logger.info(f"动态搜索满足需求: {len(dynamic_results)} 个结果")
        return dynamic_results[:target_count]
    
    # 第三层：宽松搜索
    logger.info(f"动态搜索结果仍不足({len(dynamic_results)}个)，启用宽松搜索")
    try:
        query_vec = self._embed(query)
        if query_vec is None:
            return dynamic_results
        
        # 使用更大的搜索范围和更宽松的条件
        search_k = min(target_count * 20, 2000)
        distances, indices = self.index.search(query_vec.reshape(1, -1), search_k)
        
        loose_results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or str(idx) not in self.id_map:
                continue
            
            similarity = self._distance_to_similarity(dist)
            if similarity >= 0.1:  # 非常宽松的阈值
                pose_id = self.id_map[str(idx)]
                loose_results.append((pose_id, similarity))
        
        # 按相似度排序
        loose_results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"宽松搜索完成: {len(loose_results)} 个结果")
        return loose_results[:target_count]
        
    except Exception as e:
        logger.error(f"宽松搜索失败: {e}")
        return dynamic_results

def multi_tier_search(self, query: str, target_count: int = 20) -> List[Tuple[int, float]]:
    """
    多层次搜索：先严格后宽松
    """
    # 第一层：严格搜索
    strict_results = self.search(query, top_k=target_count)
    
    if len(strict_results) >= target_count:
        logger.info(f"严格搜索满足需求: {len(strict_results)} 个结果")
        return strict_results[:target_count]
    
    # 第二层：使用动态阈值搜索
    dynamic_results = self.search_with_dynamic_threshold(
        query, target_count=target_count, min_similarity=0.2
    )
    
    if len(dynamic_results) >= target_count:
        logger.info(f"动态搜索满足需求: {len(dynamic_results)} 个结果")
        return dynamic_results[:target_count]
    
    # 第三层：最宽松搜索
    try:
        query_vec = self._embed(query)
        if query_vec is None:
            return dynamic_results
        
        search_k = min(target_count * 15, 1500)
        distances, indices = self.index.search(query_vec.reshape(1, -1), search_k)
        
        loose_results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or str(idx) not in self.id_map:
                continue
            
            similarity = self._distance_to_similarity(dist)
            if similarity >= 0.1:  # 非常宽松的阈值
                pose_id = self.id_map[str(idx)]
                loose_results.append((pose_id, similarity))
        
        loose_results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"宽松搜索完成: {len(loose_results)} 个结果")
        return loose_results[:target_count]
        
    except Exception as e:
        logger.error(f"宽松搜索失败: {e}")
        return dynamic_results