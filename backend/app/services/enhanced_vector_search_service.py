import os
import json
import faiss
import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional
from openai import OpenAI
from sqlalchemy.orm import Session

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
                
                # 获取姿势描述信息用于重排序
                pose_info = self._get_pose_description(pose_id)
                results.append((pose_id, similarity, pose_info))
            
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
            # 构建重排序提示
            candidate_texts = []
            for i, (pose_id, similarity, description) in enumerate(candidates):
                candidate_texts.append(f"{i}: {description}")
            
            candidates_text = "\n".join(candidate_texts)
            
            prompt = f"""
你是一个专业的摄影姿势推荐专家。用户查询："{query}"

请从以下候选姿势中选择最相关的{final_k}个，并按相关性排序（最相关的排在前面）：

{candidates_text}

只返回选中的候选编号，用逗号分隔，例如：0,3,7,2,9
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            # 解析GPT响应
            selected_indices = []
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                try:
                    indices = [int(x.strip()) for x in content.split(',')]
                    selected_indices = [i for i in indices if 0 <= i < len(candidates)][:final_k]
                except ValueError:
                    logger.warning(f"GPT重排序响应解析失败: {content}")
            
            # 如果GPT失败，使用原始顺序
            if not selected_indices:
                selected_indices = list(range(min(final_k, len(candidates))))
            
            # 构建最终结果
            results = []
            for i, idx in enumerate(selected_indices):
                pose_id, original_similarity, _ = candidates[idx]
                # 结合原始相似度和GPT排序位置计算新分数
                gpt_score = 1.0 - (i * 0.1)  # GPT排序越靠前分数越高
                final_score = original_similarity * 0.7 + gpt_score * 0.3
                results.append((pose_id, final_score))
            
            return results
            
        except Exception as e:
            logger.error(f"GPT重排序失败: {e}")
            # 降级到基础排序
            return [(pose_id, similarity) for pose_id, similarity, _ in candidates[:final_k]]
    
    def _quality_filter(self, results: List[Tuple[int, float]], 
                       min_similarity: float) -> List[Tuple[int, float]]:
        """阶段3：质量过滤"""
        filtered = [(pose_id, score) for pose_id, score in results if score >= min_similarity]
        return sorted(filtered, key=lambda x: x[1], reverse=True)
    
    def _embed(self, text: str) -> np.ndarray:
        """生成文本嵌入向量"""
        try:
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            return None
    
    def _distance_to_similarity(self, distance: float) -> float:
        """将距离转换为相似度分数 (0-1)"""
        # 使用指数衰减函数，距离越小相似度越高
        return np.exp(-distance)
    
    def _get_pose_description(self, pose_id: int) -> str:
        """获取姿势描述信息"""
        # 这里应该从数据库获取姿势的描述信息
        # 暂时返回简单的占位符
        return f"姿势 {pose_id} 的描述信息"
    
    def search_with_pagination(self, query: str, page: int = 1, page_size: int = 20, 
                              similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """分页搜索"""
        if not self.available:
            return {'results': [], 'total': 0, 'page': page, 'has_next': False}
        
        try:
            query_vec = self._embed(query)
            if query_vec is None:
                return {'results': [], 'total': 0, 'page': page, 'has_next': False}
            
            # 搜索大量候选结果
            search_k = min(page * page_size * 5, 2000)  # 搜索足够多的候选
            distances, indices = self.index.search(query_vec.reshape(1, -1), search_k)
            
            # 过滤有效结果
            valid_results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0 or str(idx) not in self.id_map:
                    continue
                
                if dist <= similarity_threshold:  # 距离越小越相似
                    pose_id = self.id_map[str(idx)]
                    similarity = self._distance_to_similarity(dist)
                    valid_results.append((pose_id, similarity))
            
            # 排序
            valid_results.sort(key=lambda x: x[1], reverse=True)
            
            # 分页
            total = len(valid_results)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            page_results = valid_results[start_idx:end_idx]
            has_next = end_idx < total
            
            logger.info(f"分页搜索: 第{page}页, 每页{page_size}条, 总计{total}条, 返回{len(page_results)}条")
            
            return {
                'results': page_results,
                'total': total,
                'page': page,
                'has_next': has_next
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
            logger.info(f"动态阈值搜索满足需求: {len(dynamic_results)} 个结果")
            return dynamic_results[:target_count]
        
        # 第三层：最宽松搜索
        logger.info(f"动态搜索结果仍不足({len(dynamic_results)}个)，启用最宽松搜索")
        relaxed_results = self.search_with_dynamic_threshold(query, target_count, min_similarity=0.1)
        
        logger.info(f"最终多层次搜索结果: {len(relaxed_results)} 个结果")
        return relaxed_results[:target_count]