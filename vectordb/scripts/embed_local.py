"""
本地 Embedding 服务封装
支持 BGE-large-zh (主选) 和 Ollama (备选)
"""
import os
import json
import requests
from typing import List, Optional
from config import EMBEDDING_MODEL, EMBEDDING_DEVICE, OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

class LocalEmbedding:
    """本地Embedding服务"""

    def __init__(self, use_bge: bool = True):
        self.use_bge = use_bge
        self.bge_model = None
        self.dimension = 1024

        if use_bge:
            self._init_bge()

    def _init_bge(self):
        """初始化BGE模型"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"加载 BGE 模型: {EMBEDDING_MODEL}")
            self.bge_model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
            self.dimension = 1024
            print(f"✓ BGE 模型加载成功")
        except Exception as e:
            print(f"✗ BGE 加载失败: {e}")
            print(f"切换到 Ollama Embedding")
            self.use_bge = False

    def encode(self, texts: List[str]) -> List[List[float]]:
        """生成文本向量"""
        if self.use_bge and self.bge_model:
            return self._encode_bge(texts)
        else:
            return self._encode_ollama(texts)

    def _encode_bge(self, texts: List[str]) -> List[List[float]]:
        """使用BGE生成向量"""
        embeddings = self.bge_model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def _encode_ollama(self, texts: List[str]) -> List[List[float]]:
        """使用Ollama生成向量"""
        embeddings = []
        for text in texts:
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings.append(data.get("embedding", []))
                else:
                    # 降级：返回零向量
                    embeddings.append([0.0] * self.dimension)
            except Exception as e:
                print(f"Ollama embedding 错误: {e}")
                embeddings.append([0.0] * self.dimension)

        return embeddings

    def get_embedding_function(self):
        """返回ChromaDB兼容的embedding函数"""
        def embedding_func(texts: List[str]) -> List[List[float]]:
            return self.encode(texts)
        return embedding_func

# 用于ChromaDB的embedding函数类
class BGEEmbeddingFunction:
    """ChromaDB兼容的BGE Embedding函数"""

    def __init__(self):
        self.embedder = LocalEmbedding(use_bge=True)

    def __call__(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts)

def get_embedding_function():
    """获取ChromaDB embedding函数"""
    return BGEEmbeddingFunction()

if __name__ == "__main__":
    # 测试
    embedder = LocalEmbedding(use_bge=True)
    test_texts = [
        "这是第一个测试句子",
        "这是第二个测试句子，用于验证embedding功能"
    ]
    embeddings = embedder.encode(test_texts)
    print(f"生成了 {len(embeddings)} 个向量")
    print(f"向量维度: {len(embeddings[0])}")
    print(f"第一个向量前5个值: {embeddings[0][:5]}")