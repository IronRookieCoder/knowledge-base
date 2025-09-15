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
        from whoosh.query import Or, And, Term, Wildcard, FuzzyTerm

        # 预处理查询字符串
        query_terms = []
        if settings.chinese_analyzer:
            # 使用jieba分词
            words = list(jieba.cut_for_search(query_str))
            query_terms.extend([word.strip() for word in words if len(word.strip()) >= settings.min_word_len])
        else:
            # 英文分词
            query_terms = [word.strip() for word in query_str.split() if len(word.strip()) > 0]

        if not query_terms:
            query_terms = [query_str]

        # 构建多字段查询
        title_queries = []
        content_queries = []

        for term in query_terms:
            # 标题字段查询（权重更高）
            title_queries.append(Term("title", term))
            title_queries.append(Wildcard("title", f"*{term}*"))
            if len(term) >= 2:
                title_queries.append(FuzzyTerm("title", term, maxdist=1))

            # 内容字段查询
            content_queries.append(Term("content", term))
            content_queries.append(Wildcard("content", f"*{term}*"))
            if len(term) >= 2:
                content_queries.append(FuzzyTerm("content", term, maxdist=1))

        # 组合标题和内容查询
        title_query = Or(title_queries) if title_queries else None
        content_query = Or(content_queries) if content_queries else None

        # 标题匹配权重更高
        main_queries = []
        if title_query:
            main_queries.append(title_query.with_boost(2.0))
        if content_query:
            main_queries.append(content_query)

        main_query = Or(main_queries) if main_queries else Term("title", query_str)

        # 添加过滤条件
        filters = []
        if category:
            filters.append(Term("category", category))

        if source_type:
            filters.append(Term("source_type", source_type))

        # 组合查询
        if filters:
            return And([main_query] + filters)

        return main_query

    def _generate_excerpt(self, hit, query_str: str, max_length: int = 200) -> str:
        """生成搜索结果摘要"""
        try:
            # 尝试从不同来源获取内容
            content = ""
            if hasattr(hit, 'get'):
                content = hit.get("content", "")
            else:
                # 如果hit是Whoosh的Hit对象，尝试不同的方式访问内容
                try:
                    content = hit["content"] if "content" in hit else ""
                except:
                    try:
                        content = str(hit.get("content", ""))
                    except:
                        pass

            if not content:
                # 如果没有内容，尝试从标题生成摘要
                title = ""
                if hasattr(hit, 'get'):
                    title = hit.get("title", "")
                else:
                    try:
                        title = hit["title"] if "title" in hit else ""
                    except:
                        try:
                            title = str(hit.get("title", ""))
                        except:
                            pass
                return title[:max_length] if title else ""

            # 预处理查询词
            query_terms = []
            if settings.chinese_analyzer:
                words = list(jieba.cut(query_str))
                query_terms = [word.strip() for word in words if len(word.strip()) >= settings.min_word_len]
            else:
                query_terms = [word.strip() for word in query_str.split() if len(word.strip()) > 0]

            # 查找最佳匹配位置
            best_pos = -1
            best_score = 0

            for term in query_terms:
                if term in content:
                    pos = content.find(term)
                    # 计算此位置的得分（匹配词的长度）
                    score = len(term)
                    if score > best_score:
                        best_score = score
                        best_pos = pos

            if best_pos != -1:
                # 以最佳匹配位置为中心生成摘要
                start = max(0, best_pos - max_length // 2)
                end = min(len(content), best_pos + max_length // 2)

                # 尝试在句子边界调整
                if start > 0:
                    # 向前查找句子开始
                    for i in range(start, max(0, start - 50), -1):
                        if content[i] in '。！？\n':
                            start = i + 1
                            break

                if end < len(content):
                    # 向后查找句子结束
                    for i in range(end, min(len(content), end + 50)):
                        if content[i] in '。！？\n':
                            end = i + 1
                            break

                excerpt = content[start:end].strip()

                # 高亮关键词
                for term in query_terms:
                    if term in excerpt:
                        excerpt = excerpt.replace(term, f"**{term}**")

                # 添加省略号
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(content):
                    excerpt = excerpt + "..."

                return excerpt

            # 如果没有找到关键词，返回内容开头
            if len(content) <= max_length:
                return content.strip()
            else:
                # 尝试在句子边界截断
                excerpt = content[:max_length]
                last_sentence = excerpt.rfind('。')
                if last_sentence > max_length // 2:
                    excerpt = excerpt[:last_sentence + 1]
                else:
                    excerpt = excerpt + "..."

                return excerpt.strip()

        except Exception as e:
            logger.warning("Failed to generate excerpt", error=str(e), query=query_str)
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