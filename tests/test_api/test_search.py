"""
搜索引擎测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import tempfile
from pathlib import Path

from packages.knowledge_api.search import SearchEngine, ChineseAnalyzer


class TestChineseAnalyzer:
    """中文分析器测试"""

    def test_chinese_tokenization(self):
        """测试中文分词"""
        analyzer = ChineseAnalyzer()

        # 测试中文文本
        tokens = list(analyzer("这是一个测试文档"))
        token_texts = [token.text for token in tokens]

        assert len(token_texts) > 0
        assert "测试" in token_texts or "文档" in token_texts

    def test_english_tokenization(self):
        """测试英文分词"""
        analyzer = ChineseAnalyzer()

        tokens = list(analyzer("This is a test document"))
        token_texts = [token.text for token in tokens]

        assert "test" in token_texts
        assert "document" in token_texts

    def test_mixed_language_tokenization(self):
        """测试中英文混合分词"""
        analyzer = ChineseAnalyzer()

        tokens = list(analyzer("这是API文档"))
        token_texts = [token.text for token in tokens]

        assert "API" in token_texts


class TestSearchEngine:
    """搜索引擎测试"""

    @pytest.fixture
    def temp_search_engine(self):
        """创建临时搜索引擎"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('packages.knowledge_api.search.settings') as mock_settings:
                mock_settings.search.index_path = temp_dir
                mock_settings.search.chinese_analyzer = True
                mock_settings.search.min_word_len = 1

                engine = SearchEngine()
                yield engine

    @pytest.mark.asyncio
    async def test_add_document(self, temp_search_engine, sample_document_data):
        """测试添加文档到索引"""
        doc_data = sample_document_data.copy()
        doc_data["id"] = 1
        doc_data["created_at"] = "2024-01-01T00:00:00"
        doc_data["updated_at"] = "2024-01-01T00:00:00"

        await temp_search_engine.add_document(doc_data)

        # 验证文档已添加
        stats = await temp_search_engine.get_stats()
        assert stats["total_documents"] == 1

    @pytest.mark.asyncio
    async def test_search_documents(self, temp_search_engine, sample_documents_data):
        """测试文档搜索"""
        # 添加测试文档
        for i, doc_data in enumerate(sample_documents_data):
            doc_data["id"] = i + 1
            doc_data["created_at"] = "2024-01-01T00:00:00"
            doc_data["updated_at"] = "2024-01-01T00:00:00"
            await temp_search_engine.add_document(doc_data)

        # 测试搜索
        documents, total = await temp_search_engine.search("API")

        assert total > 0
        assert len(documents) > 0

        # 验证搜索结果包含相关文档
        found_titles = [doc["title"] for doc in documents]
        assert any("API" in title for title in found_titles)

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, temp_search_engine, sample_documents_data):
        """测试带分类过滤的搜索"""
        # 添加测试文档
        for i, doc_data in enumerate(sample_documents_data):
            doc_data["id"] = i + 1
            doc_data["created_at"] = "2024-01-01T00:00:00"
            doc_data["updated_at"] = "2024-01-01T00:00:00"
            await temp_search_engine.add_document(doc_data)

        # 测试分类过滤
        documents, total = await temp_search_engine.search(
            "部署",
            category="deployment"
        )

        assert total > 0
        for doc in documents:
            assert doc["category"] == "deployment"

    @pytest.mark.asyncio
    async def test_search_chinese_content(self, temp_search_engine):
        """测试中文内容搜索"""
        doc_data = {
            "id": 1,
            "title": "中文测试文档",
            "content": "这个文档包含中文内容，用于测试中文搜索功能。包括分词和全文检索。",
            "category": "test",
            "source_type": "test",
            "author": "测试员",
            "file_path": "test.md",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

        await temp_search_engine.add_document(doc_data)

        # 测试中文搜索
        documents, total = await temp_search_engine.search("中文搜索")

        assert total > 0
        assert len(documents) > 0

    @pytest.mark.asyncio
    async def test_update_document(self, temp_search_engine, sample_document_data):
        """测试更新文档"""
        doc_data = sample_document_data.copy()
        doc_data["id"] = 1
        doc_data["created_at"] = "2024-01-01T00:00:00"
        doc_data["updated_at"] = "2024-01-01T00:00:00"

        # 添加文档
        await temp_search_engine.add_document(doc_data)

        # 更新文档
        doc_data["title"] = "更新后的标题"
        doc_data["content"] = "更新后的内容"
        await temp_search_engine.update_document(doc_data)

        # 搜索验证更新
        documents, total = await temp_search_engine.search("更新后")
        assert total > 0

    @pytest.mark.asyncio
    async def test_delete_document(self, temp_search_engine, sample_document_data):
        """测试删除文档"""
        doc_data = sample_document_data.copy()
        doc_data["id"] = 1
        doc_data["created_at"] = "2024-01-01T00:00:00"
        doc_data["updated_at"] = "2024-01-01T00:00:00"

        # 添加文档
        await temp_search_engine.add_document(doc_data)

        # 验证文档存在
        stats = await temp_search_engine.get_stats()
        assert stats["total_documents"] == 1

        # 删除文档
        await temp_search_engine.delete_document(1)

        # 验证文档已删除
        stats = await temp_search_engine.get_stats()
        assert stats["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_rebuild_index(self, temp_search_engine, sample_documents_data):
        """测试重建索引"""
        # 准备文档数据
        for i, doc_data in enumerate(sample_documents_data):
            doc_data["id"] = i + 1
            doc_data["created_at"] = "2024-01-01T00:00:00"
            doc_data["updated_at"] = "2024-01-01T00:00:00"

        # 重建索引
        await temp_search_engine.rebuild_index(sample_documents_data)

        # 验证索引
        stats = await temp_search_engine.get_stats()
        assert stats["total_documents"] == len(sample_documents_data)

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_search_engine, sample_documents_data):
        """测试获取统计信息"""
        # 添加测试文档
        for i, doc_data in enumerate(sample_documents_data):
            doc_data["id"] = i + 1
            doc_data["created_at"] = "2024-01-01T00:00:00"
            doc_data["updated_at"] = "2024-01-01T00:00:00"
            await temp_search_engine.add_document(doc_data)

        # 获取统计信息
        stats = await temp_search_engine.get_stats()

        assert stats["total_documents"] == len(sample_documents_data)
        assert len(stats["categories"]) > 0
        assert len(stats["sources"]) > 0

    def test_generate_excerpt(self, temp_search_engine):
        """测试摘要生成"""
        hit = Mock()
        hit.get.return_value = "这是一个很长的文档内容，包含API接口的详细说明和使用示例。"

        excerpt = temp_search_engine._generate_excerpt(hit, "API")

        assert "API" in excerpt
        assert len(excerpt) <= 200 + 20  # 允许一些格式化字符