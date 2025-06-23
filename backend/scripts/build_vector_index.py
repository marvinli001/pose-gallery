import json
import os
from typing import List

import numpy as np
import openai
import faiss
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal

# Embedding model name can be configured via OPENAI_MODEL env var
EMBED_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", "backend/vector_index/faiss.index")
ID_MAP_PATH = os.getenv("VECTOR_ID_MAP_PATH", "backend/vector_index/id_map.json")


def get_all_pose_text(db: Session) -> List[tuple[int, str]]:
    sql = text(
        """
        SELECT p.id, p.title, p.description,
               GROUP_CONCAT(t.name SEPARATOR ' ') as tags
        FROM poses p
        LEFT JOIN pose_tags pt ON p.id = pt.pose_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.status = 'active'
        GROUP BY p.id
        """
    )
    rows = db.execute(sql).fetchall()
    results = []
    for row in rows:
        combined = " ".join(filter(None, [row[1], row[2], row[3]]))
        results.append((row[0], combined.strip()))
    return results


def embed_text(texts: List[str]) -> List[List[float]]:
    resp = openai.embeddings.create(input=texts, model=EMBED_MODEL)
    return [d.embedding for d in resp.data]


def build_index():
    db = SessionLocal()
    try:
        data = get_all_pose_text(db)
        if not data:
            print("No poses found")
            return
        ids, texts = zip(*data)
        embeddings = embed_text(list(texts))
        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings, dtype="float32"))
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        faiss.write_index(index, INDEX_PATH)
        with open(ID_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(list(ids), f)
        print(f"Index built with {len(ids)} entries")
    finally:
        db.close()


if __name__ == "__main__":
    build_index()
