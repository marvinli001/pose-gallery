import json
import os
from typing import List, Tuple

import numpy as np
import openai
import faiss

EMBED_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", "backend/vector_index/faiss.index")
ID_MAP_PATH = os.getenv("VECTOR_ID_MAP_PATH", "backend/vector_index/id_map.json")


class VectorSearchService:
    def __init__(self, index_path: str = INDEX_PATH, id_map_path: str = ID_MAP_PATH):
        if not os.path.exists(index_path) or not os.path.exists(id_map_path):
            raise RuntimeError("Vector index not found. Run build_vector_index.py first")
        self.index = faiss.read_index(index_path)
        with open(id_map_path, "r", encoding="utf-8") as f:
            self.id_map = json.load(f)

    def _embed(self, text: str) -> np.ndarray:
        resp = openai.embeddings.create(input=[text], model=EMBED_MODEL)
        vec = np.array(resp.data[0].embedding, dtype="float32")
        return vec

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        vec = self._embed(query)
        D, I = self.index.search(vec.reshape(1, -1), top_k)
        ids_scores = []
        for idx, dist in zip(I[0], D[0]):
            if idx < 0:
                continue
            pose_id = self.id_map[idx]
            score = float(dist)
            ids_scores.append((pose_id, score))
        return ids_scores
