import json
import os
import sys
import time
from typing import List, Tuple
from pathlib import Path

import numpy as np
import openai
from openai import OpenAI
import faiss
from sqlalchemy import text
from sqlalchemy.orm import Session

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal

# 配置参数
EMBED_MODEL = "text-embedding-3-small"
INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", "backend/vector_index/faiss.index")
ID_MAP_PATH = os.getenv("VECTOR_ID_MAP_PATH", "backend/vector_index/id_map.json")
BATCH_SIZE = 100  # OpenAI API批量处理限制
MAX_RETRIES = 3  # 重试次数


def get_all_pose_text(db: Session) -> List[Tuple[int, str]]:
    """获取所有姿势的文本数据"""
    sql = text(
        """
        SELECT p.id, p.title, p.description, p.scene_category, 
               p.angle, p.shooting_tips, p.ai_tags,
               GROUP_CONCAT(t.name SEPARATOR ' ') as tags
        FROM poses p
        LEFT JOIN pose_tags pt ON p.id = pt.pose_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.status = 'active'
        GROUP BY p.id, p.title, p.description, p.scene_category, 
                 p.angle, p.shooting_tips, p.ai_tags
        """
    )
    
    try:
        rows = db.execute(sql).fetchall()
        results = []
        
        for row in rows:
            # 合并所有文本字段
            text_parts = []
            for field in row[1:]:  # 跳过ID字段
                if field and str(field).strip():
                    text_parts.append(str(field).strip())
            
            combined_text = " ".join(text_parts)
            if combined_text.strip():  # 只保留有内容的记录
                results.append((row[0], combined_text.strip()))
        
        print(f"找到 {len(results)} 个有效姿势记录")
        return results
        
    except Exception as e:
        print(f"获取姿势数据失败: {e}")
        return []


def embed_text_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """批量生成文本嵌入向量，带重试机制"""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"正在生成 {len(texts)} 个文本的嵌入向量...")
            resp = client.embeddings.create(input=texts, model=EMBED_MODEL)
            embeddings = [d.embedding for d in resp.data]
            print(f"成功生成 {len(embeddings)} 个向量")
            return embeddings
            
        except Exception as e:
            print(f"嵌入向量生成失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise e


def build_index():
    """构建向量索引"""
    print("开始构建向量索引...")
    
    # 检查OpenAI API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置 OPENAI_API_KEY 环境变量")
        return False
    
    # 初始化OpenAI客户端
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI客户端初始化成功")
    except Exception as e:
        print(f"❌ OpenAI客户端初始化失败: {e}")
        return False
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 获取所有姿势文本数据
        data = get_all_pose_text(db)
        if not data:
            print("❌ 没有找到有效的姿势数据")
            return False
        
        ids, texts = zip(*data)
        print(f"准备处理 {len(texts)} 个文本记录")
        
        # 分批处理文本嵌入
        all_embeddings = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            print(f"处理批次 {batch_num}/{total_batches} ({len(batch_texts)} 个文本)")
            
            try:
                batch_embeddings = embed_text_batch(list(batch_texts), client)
                all_embeddings.extend(batch_embeddings)
                
                # 添加延迟避免API限流
                if i + BATCH_SIZE < len(texts):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ 批次 {batch_num} 处理失败: {e}")
                return False
        
        if len(all_embeddings) != len(texts):
            print(f"❌ 嵌入向量数量不匹配: 期望 {len(texts)}, 实际 {len(all_embeddings)}")
            return False
        
        print(f"✅ 成功生成 {len(all_embeddings)} 个嵌入向量")
        
        # 构建FAISS索引
        print("构建FAISS索引...")
        embeddings_array = np.array(all_embeddings, dtype="float32")
        dimension = embeddings_array.shape[1]
        
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        print(f"FAISS索引创建完成，维度: {dimension}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        
        # 保存FAISS索引
        faiss.write_index(index, INDEX_PATH)
        print(f"✅ FAISS索引已保存到: {INDEX_PATH}")
        
        # 保存ID映射（使用字符串键以匹配vector_search_service.py）
        id_map = {str(i): pose_id for i, pose_id in enumerate(ids)}
        with open(ID_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(id_map, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ID映射已保存到: {ID_MAP_PATH}")
        print(f"✅ 向量索引构建完成! 包含 {len(ids)} 条记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 构建索引过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


def verify_index():
    """验证构建的索引"""
    print("\n验证索引文件...")
    
    try:
        if not os.path.exists(INDEX_PATH):
            print(f"❌ 索引文件不存在: {INDEX_PATH}")
            return False
            
        if not os.path.exists(ID_MAP_PATH):
            print(f"❌ ID映射文件不存在: {ID_MAP_PATH}")
            return False
        
        # 验证FAISS索引
        index = faiss.read_index(INDEX_PATH)
        print(f"✅ FAISS索引: {index.ntotal} 个向量, 维度 {index.d}")
        
        # 验证ID映射
        with open(ID_MAP_PATH, "r", encoding="utf-8") as f:
            id_map = json.load(f)
        print(f"✅ ID映射: {len(id_map)} 个条目")
        
        if index.ntotal != len(id_map):
            print(f"⚠️  警告: 索引向量数量 ({index.ntotal}) 与ID映射数量 ({len(id_map)}) 不匹配")
        
        return True
        
    except Exception as e:
        print(f"❌ 索引验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=== 向量索引构建工具 ===")
    print(f"嵌入模型: {EMBED_MODEL}")
    print(f"索引路径: {INDEX_PATH}")
    print(f"映射路径: {ID_MAP_PATH}")
    print(f"批次大小: {BATCH_SIZE}")
    print()
    
    # 构建索引
    success = build_index()
    
    if success:
        # 验证索引
        verify_success = verify_index()
        if verify_success:
            print("\n🎉 向量索引构建和验证完成!")
            return 0
        else:
            print("\n❌ 索引验证失败")
            return 1
    else:
        print("\n❌ 向量索引构建失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)