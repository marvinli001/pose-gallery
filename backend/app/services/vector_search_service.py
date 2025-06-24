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

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """向量搜索"""
        if not self.available:
            raise RuntimeError("向量搜索服务不可用，索引文件未找到")
        
        try:
            vec = self._embed(query)
            if vec is None:
                return []
                
            D, I = self.index.search(vec.reshape(1, -1), top_k)
            ids_scores = []
            for idx, dist in zip(I[0], D[0]):
                if idx < 0:
                    continue
                if str(idx) in self.id_map:  # 确保索引存在
                    pose_id = self.id_map[str(idx)]
                    score = float(dist)
                    ids_scores.append((pose_id, score))
            return ids_scores
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []