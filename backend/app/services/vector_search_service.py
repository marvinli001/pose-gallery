import json
import os
from typing import List, Tuple, Optional
import logging

import numpy as np
import openai
import faiss

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", "backend/vector_index/faiss.index")
ID_MAP_PATH = os.getenv("VECTOR_ID_MAP_PATH", "backend/vector_index/id_map.json")


class VectorSearchService:
    def __init__(self, index_path: str = INDEX_PATH, id_map_path: str = ID_MAP_PATH):
        self.index = None
        self.id_map = None
        self.available = False
        
        try:
            if os.path.exists(index_path) and os.path.exists(id_map_path):
                self.index = faiss.read_index(index_path)
                with open(id_map_path, "r", encoding="utf-8") as f:
                    self.id_map = json.load(f)
                self.available = True
                logger.info("向量搜索服务初始化成功")
            else:
                logger.warning(f"向量索引文件未找到: {index_path} 或 {id_map_path}")
                logger.warning("向量搜索功能将不可用，请运行 build_vector_index.py 生成索引")
        except Exception as e:
            logger.error(f"向量搜索服务初始化失败: {e}")

    def is_available(self) -> bool:
        """检查向量搜索服务是否可用"""
        return self.available

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """获取文本向量表示"""
        try:
            resp = openai.embeddings.create(input=[text], model=EMBED_MODEL)
            vec = np.array(resp.data[0].embedding, dtype="float32")
            return vec
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            return None

    def search(self, query: str, top_k: int = 10, similarity_threshold: float = 1.5) -> List[Tuple[int, float]]:
        """
        向量搜索
        
        Args:
            query: 搜索查询
            top_k: 最大返回数量
            similarity_threshold: 相似度阈值（L2距离，越小越相似）
        
        Returns:
            [(pose_id, similarity_score), ...] 按相似度排序
        """
        if not self.available:
            raise RuntimeError("向量搜索服务不可用，索引文件未找到")
        
        try:
            vec = self._embed(query)
            if vec is None:
                return []
                
            # 搜索更多候选结果以便过滤
            search_k = min(top_k * 3, 100)  # 搜索3倍数量的候选
            D, I = self.index.search(vec.reshape(1, -1), search_k)
            
            ids_scores = []
            distances = D[0]
            indices = I[0]
            
            logger.info(f"向量搜索原始结果距离范围: {distances.min():.3f} - {distances.max():.3f}")
            
            for idx, dist in zip(indices, distances):
                if idx < 0:  # 无效索引
                    continue
                    
                # 应用相似度阈值过滤
                if dist > similarity_threshold:
                    logger.debug(f"跳过低相似度结果: 距离={dist:.3f} > 阈值={similarity_threshold}")
                    continue
                    
                if str(idx) in self.id_map:
                    pose_id = self.id_map[str(idx)]
                    # 转换距离为相似度分数（越小的距离 = 越高的相似度）
                    similarity_score = self._distance_to_similarity(dist)
                    ids_scores.append((pose_id, similarity_score))
            
            # 按相似度排序并限制数量
            ids_scores.sort(key=lambda x: x[1], reverse=True)
            result = ids_scores[:top_k]
            
            logger.info(f"向量搜索完成: 找到 {len(result)} 个相关结果（相似度阈值: {similarity_threshold}）")
            
            # 记录前几个结果的分数
            if result:
                top_scores = [score for _, score in result[:5]]
                logger.info(f"前5个结果相似度分数: {top_scores}")
            
            return result
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def _distance_to_similarity(self, distance: float) -> float:
        """
        将L2距离转换为相似度分数 (0-1)
        距离越小，相似度越高
        """
        # 使用负指数函数将距离转换为相似度
        # 距离0 -> 相似度1.0，距离增大相似度指数衰减
        return np.exp(-distance / 2.0)
    
    def search_with_adaptive_threshold(self, query: str, top_k: int = 10, 
                                     min_results: int = 3) -> List[Tuple[int, float]]:
        """
        自适应阈值搜索：动态调整阈值确保返回合适数量的结果
        
        Args:
            query: 搜索查询
            top_k: 期望返回数量
            min_results: 最少返回数量
        """
        if not self.available:
            raise RuntimeError("向量搜索服务不可用，索引文件未找到")
        
        # 尝试不同的阈值
        thresholds = [0.8, 1.2, 1.5, 2.0, 2.5]
        
        for threshold in thresholds:
            results = self.search(query, top_k * 2, threshold)
            
            if len(results) >= min_results:
                logger.info(f"使用阈值 {threshold}，找到 {len(results)} 个结果")
                return results[:top_k]
        
        # 如果所有阈值都无法找到足够结果，使用最宽松的阈值
        logger.warning(f"无法找到足够的相关结果，使用宽松阈值")
        return self.search(query, top_k, 3.0)