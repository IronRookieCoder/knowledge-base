"""
搜索引擎实现
基于Whoosh的中文搜索支持
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import jieba
from whoosh import fields, index
from whoosh.analysis import StandardAnalyzer, Token, Analyzer
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import Query
from whoosh.searching import Results

from ..knowledge_common.config import settings
from ..knowledge_common.logging import get_logger
from ..knowledge_common.utils import ensure_directory

logger = get_logger(__name__)


class ChineseAnalyzer(Analyzer):
    """中文分析器"""

    def __init__(self):
        # 加载自定义词典
        custom_dict_path = Path("config/custom_dict.txt")
        if custom_dict_path.exists():
            jieba.load_userdict(str(custom_dict_path))

    def __call__(self, text, **kwargs):
        """分析文本"""
        # 使用jieba进行中文分词
        words = jieba.cut_for_search(text)
        tokens = []
        pos = 0

        for word in words:
            word = word.strip()
            if len(word) >= settings.min_word_len:
                token = Token(
                    text=word,
                    pos=pos,
                    startchar=pos,
                    endchar=pos + len(word)
                )
                tokens.append(token)
                pos += len(word)

        return tokens


class SearchEngine:
    """搜索引擎"""

    def __init__(self):
        self.index_path = Path(settings.search_index_path)
        ensure_directory(self.index_path)
        self.analyzer = ChineseAnalyzer() if settings.chinese_analyzer else StandardAnalyzer()
        self.schema = self._create_schema()
        self._index = None

    def _create_schema(self):
        """创建索引结构"""
        return fields.Schema(
            id=fields.ID(stored=True),
            title=fields.TEXT(stored=True, analyzer=self.analyzer),
            content=fields.TEXT(analyzer=self.analyzer),
            category=fields.ID(stored=True),
            source_type=fields.ID(stored=True),
            author=fields.TEXT(stored=True),
            file_path=fields.TEXT(stored=True),
            created_at=fields.DATETIME(stored=True),
            updated_at=fields.DATETIME(stored=True)
        )

    @property
    def idx(self):
        """获取索引实例"""
        if self._index is None:
            if index.exists_in(str(self.index_path)):
                self._index = index.open_dir(str(self.index_path))
            else:
                self._index = index.create_in(str(self.index_path), self.schema)
        return self._index

    async def add_document(self, document: Dict[str, Any]) -> None:
        """添加文档到索引"""
        writer = self.idx.writer()
        try:
            writer.add_document(
                id=str(document["id"]),
                title=document["title"],
                content=document["content"],
                category=document.get("category", ""),
                source_type=document["source_type"],
                author=document.get("author", ""),
                file_path=document["file_path"],
                created_at=document["created_at"],
                updated_at=document["updated_at"]
            )
            writer.commit()
            logger.info("Document added to search index", document_id=document["id"])
        except Exception as e:
            writer.cancel()
            logger.error("Failed to add document to index", document_id=document["id"], error=str(e))
            raise

    async def update_document(self, document: Dict[str, Any]) -> None:
        """更新索引中的文档"""
        writer = self.idx.writer()
        try:
            writer.update_document(
                id=str(document["id"]),
                title=document["title"],
                content=document["content"],
                category=document.get("category", ""),
                source_type=document["source_type"],
                author=document.get("author", ""),
                file_path=document["file_path"],
                created_at=document["created_at"],
                updated_at=document["updated_at"]
            )
            writer.commit()
            logger.info("Document updated in search index", document_id=document["id"])
        except Exception as e:
            writer.cancel()
            logger.error("Failed to update document in index", document_id=document["id"], error=str(e))
            raise

    async def delete_document(self, document_id: int) -> None:
        """从索引中删除文档"""
        writer = self.idx.writer()
        try:
            writer.delete_by_term("id", str(document_id))
            writer.commit()
            logger.info("Document deleted from search index", document_id=document_id)
        except Exception as e:
            writer.cancel()
            logger.error("Failed to delete document from index", document_id=document_id, error=str(e))
            raise

    async def search(
        self,
        query_str: str,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """搜索文档"""
        try:
            with self.idx.searcher() as searcher:
                # 构建查询
                query = self._build_query(query_str, category, source_type)

                # 执行搜索
                results = searcher.search(query, limit=limit + offset)

                # 提取结果
                documents = []
                for hit in results[offset:offset + limit]:
                    documents.append({
                        "id": int(hit["id"]),
                        "title": hit["title"],
                        "file_path": hit["file_path"],
                        "category": hit["category"],
                        "source_type": hit["source_type"],
                        "author": hit["author"],
                        "updated_at": hit["updated_at"],
                        "score": hit.score,
                        "excerpt": self._generate_excerpt(hit, query_str)
                    })

                return documents, len(results)

        except Exception as e:
            logger.error("Search failed", query=query_str, error=str(e))
            return [], 0

    def _build_query(
        self,
        query_str: str,
        category: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Query:
        """构建搜索查询"""
        # 多字段搜索
        parser = MultifieldParser(["title", "content"], self.idx.schema)
        query = parser.parse(query_str)

        # 添加过滤条件
        filters = []
        if category:
            from whoosh.query import Term
            filters.append(Term("category", category))

        if source_type:
            from whoosh.query import Term
            filters.append(Term("source_type", source_type))

        # 组合查询
        if filters:
            from whoosh.query import And
            return And([query] + filters)

        return query

    def _generate_excerpt(self, hit, query_str: str, max_length: int = 200) -> str:
        """生成搜索结果摘要"""
        try:
            content = hit.get("content", "")
            if not content:
                return ""

            # 简单的摘要生成：查找关键词周围的文本
            words = jieba.cut(query_str) if settings.chinese_analyzer else query_str.split()

            for word in words:
                word = word.strip()
                if word and word in content:
                    # 找到关键词位置
                    pos = content.find(word)
                    if pos != -1:
                        # 提取关键词前后的文本
                        start = max(0, pos - max_length // 2)
                        end = min(len(content), pos + max_length // 2)
                        excerpt = content[start:end].strip()

                        # 高亮关键词
                        excerpt = excerpt.replace(word, f"**{word}**")

                        if start > 0:
                            excerpt = "..." + excerpt
                        if end < len(content):
                            excerpt = excerpt + "..."

                        return excerpt

            # 如果没有找到关键词，返回内容开头
            if len(content) <= max_length:
                return content
            else:
                return content[:max_length] + "..."

        except Exception as e:
            logger.warning("Failed to generate excerpt", error=str(e))
            return ""

    async def rebuild_index(self, documents: List[Dict[str, Any]]) -> None:
        """重建索引"""
        try:
            # 删除现有索引
            if self._index:
                self._index.close()
                self._index = None

            # 删除索引文件
            import shutil
            if self.index_path.exists():
                shutil.rmtree(self.index_path)

            ensure_directory(self.index_path)

            # 创建新索引
            self._index = index.create_in(str(self.index_path), self.schema)

            # 批量添加文档
            writer = self.idx.writer()
            try:
                for doc in documents:
                    writer.add_document(
                        id=str(doc["id"]),
                        title=doc["title"],
                        content=doc["content"],
                        category=doc.get("category", ""),
                        source_type=doc["source_type"],
                        author=doc.get("author", ""),
                        file_path=doc["file_path"],
                        created_at=doc["created_at"],
                        updated_at=doc["updated_at"]
                    )

                writer.commit()
                logger.info("Search index rebuilt", document_count=len(documents))

            except Exception as e:
                writer.cancel()
                raise

        except Exception as e:
            logger.error("Failed to rebuild index", error=str(e))
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            with self.idx.searcher() as searcher:
                doc_count = searcher.doc_count()

                # 统计各分类的文档数量
                categories = {}
                sources = {}

                for doc in searcher.all_docs():
                    category = doc.get("category", "unknown")
                    source_type = doc.get("source_type", "unknown")

                    categories[category] = categories.get(category, 0) + 1
                    sources[source_type] = sources.get(source_type, 0) + 1

                return {
                    "total_documents": doc_count,
                    "categories": categories,
                    "sources": sources
                }

        except Exception as e:
            logger.error("Failed to get search stats", error=str(e))
            return {
                "total_documents": 0,
                "categories": {},
                "sources": {}
            }


# 全局搜索引擎实例
search_engine = SearchEngine()