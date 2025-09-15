"""
MCP服务器测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from packages.knowledge_mcp.server import KnowledgeBaseMCPServer


class TestKnowledgeBaseMCPServer:
    """MCP服务器测试"""

    @pytest.fixture
    def mcp_server(self):
        """创建MCP服务器实例"""
        with patch('packages.knowledge_mcp.server.db_manager'):
            server = KnowledgeBaseMCPServer()
            return server

    @pytest.mark.asyncio
    async def test_search_knowledge(self, mcp_server):
        """测试知识搜索工具"""
        # 模拟搜索引擎
        with patch('packages.knowledge_mcp.server.search_engine') as mock_search:
            mock_search.search.return_value = (
                [{
                    "id": 1,
                    "title": "测试文档",
                    "file_path": "test.md",
                    "category": "test",
                    "source_type": "gitlab",
                    "author": "测试员",
                    "updated_at": "2024-01-01T00:00:00",
                    "excerpt": "这是测试摘要"
                }],
                1
            )

            result = await mcp_server._search_knowledge({"query": "测试"})

            assert len(result) == 1
            assert "测试文档" in result[0].text
            assert "gitlab" in result[0].text

    @pytest.mark.asyncio
    async def test_search_knowledge_empty_query(self, mcp_server):
        """测试空查询的搜索"""
        result = await mcp_server._search_knowledge({"query": ""})

        assert len(result) == 1
        assert "不能为空" in result[0].text

    @pytest.mark.asyncio
    async def test_search_knowledge_no_results(self, mcp_server):
        """测试无结果的搜索"""
        with patch('packages.knowledge_mcp.server.search_engine') as mock_search:
            mock_search.search.return_value = ([], 0)

            result = await mcp_server._search_knowledge({"query": "不存在的内容"})

            assert len(result) == 1
            assert "未找到" in result[0].text

    @pytest.mark.asyncio
    async def test_get_document(self, mcp_server, test_session, sample_document_data):
        """测试获取文档工具"""
        from packages.knowledge_common.models import Document

        # 创建测试文档
        document = Document(**sample_document_data)
        test_session.add(document)
        await test_session.commit()

        with patch('packages.knowledge_mcp.server.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            result = await mcp_server._get_document({"document_id": document.id})

            assert len(result) == 1
            assert sample_document_data["title"] in result[0].text
            assert sample_document_data["content"] in result[0].text

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mcp_server, test_session):
        """测试获取不存在的文档"""
        with patch('packages.knowledge_mcp.server.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            result = await mcp_server._get_document({"document_id": 999})

            assert len(result) == 1
            assert "未找到" in result[0].text

    @pytest.mark.asyncio
    async def test_get_categories(self, mcp_server):
        """测试获取分类工具"""
        mock_categories = [
            {"name": "API", "count": 5},
            {"name": "部署", "count": 3}
        ]

        with patch.object(mcp_server, '_get_categories_data', return_value=mock_categories):
            result = await mcp_server._get_categories({})

            assert len(result) == 1
            assert "API" in result[0].text
            assert "部署" in result[0].text
            assert "5" in result[0].text

    @pytest.mark.asyncio
    async def test_get_stats(self, mcp_server):
        """测试获取统计信息工具"""
        mock_stats = {
            "total_documents": 10,
            "categories": {"API": 5, "部署": 3},
            "sources": {"gitlab": 7, "confluence": 3}
        }

        with patch.object(mcp_server, '_get_stats_data', return_value=mock_stats):
            result = await mcp_server._get_stats({})

            assert len(result) == 1
            assert "10" in result[0].text
            assert "API" in result[0].text
            assert "gitlab" in result[0].text

    @pytest.mark.asyncio
    async def test_get_categories_data(self, mcp_server, test_session, sample_documents_data):
        """测试获取分类数据"""
        from packages.knowledge_common.models import Document

        # 添加测试文档
        for i, doc_data in enumerate(sample_documents_data):
            document = Document(**doc_data)
            test_session.add(document)

        await test_session.commit()

        with patch('packages.knowledge_mcp.server.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            categories = await mcp_server._get_categories_data()

            assert len(categories) > 0
            category_names = [cat["name"] for cat in categories]
            assert "api" in category_names

    @pytest.mark.asyncio
    async def test_get_stats_data(self, mcp_server, test_session, sample_documents_data):
        """测试获取统计数据"""
        from packages.knowledge_common.models import Document

        # 添加测试文档
        for i, doc_data in enumerate(sample_documents_data):
            document = Document(**doc_data)
            test_session.add(document)

        await test_session.commit()

        with patch('packages.knowledge_mcp.server.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            stats = await mcp_server._get_stats_data()

            assert stats["total_documents"] == len(sample_documents_data)
            assert len(stats["categories"]) > 0
            assert len(stats["sources"]) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """测试错误处理"""
        with patch('packages.knowledge_mcp.server.search_engine') as mock_search:
            mock_search.search.side_effect = Exception("搜索错误")

            result = await mcp_server._search_knowledge({"query": "测试"})

            assert len(result) == 1
            assert "搜索错误" in result[0].text