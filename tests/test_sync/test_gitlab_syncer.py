"""
GitLab同步器测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from packages.knowledge_sync.gitlab_syncer import GitLabSyncer
from packages.knowledge_common.models import Document


class TestGitLabSyncer:
    """GitLab同步器测试类"""

    @pytest.fixture
    def gitlab_syncer(self):
        """创建GitLab同步器实例"""
        with patch('packages.knowledge_sync.gitlab_syncer.gitlab.Gitlab'):
            syncer = GitLabSyncer()
            syncer.gitlab_client = Mock()
            return syncer

    @pytest.mark.asyncio
    async def test_scan_documents(self, gitlab_syncer, tmp_path):
        """测试文档扫描功能"""
        # 创建测试文档
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        test_file = docs_dir / "test.md"
        test_file.write_text("""# 测试文档

这是一个测试文档。

## 功能介绍

测试功能的详细说明。
""", encoding="utf-8")

        # 模拟项目对象
        mock_project = Mock()
        mock_project.id = 123

        # 执行扫描
        documents = await gitlab_syncer._scan_documents(docs_dir, mock_project, "test")

        # 验证结果
        assert len(documents) == 1
        doc = documents[0]
        assert doc["title"] == "测试文档"
        assert doc["category"] == "test"
        assert doc["source_type"] == "gitlab"
        assert "测试功能" in doc["content"]

    @pytest.mark.asyncio
    async def test_process_documents(self, gitlab_syncer, test_session, sample_document_data):
        """测试文档处理功能"""
        documents = [sample_document_data]

        # 模拟数据库会话
        with patch('packages.knowledge_sync.gitlab_syncer.db_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            # 模拟复制文件操作
            with patch.object(gitlab_syncer, '_copy_document_file', new_callable=AsyncMock):
                count = await gitlab_syncer._process_documents(documents, "test/", 123, "test")

        assert count == 1

    def test_get_file_hash(self, tmp_path):
        """测试文件哈希计算"""
        from packages.knowledge_common.utils import get_file_hash

        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容", encoding="utf-8")

        hash1 = get_file_hash(test_file)
        hash2 = get_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5哈希长度

    @pytest.mark.asyncio
    async def test_sync_projects_empty_config(self, gitlab_syncer):
        """测试空配置的项目同步"""
        await gitlab_syncer.sync_projects([])
        # 应该不会抛出异常

    @pytest.mark.asyncio
    async def test_sync_projects_error_handling(self, gitlab_syncer):
        """测试项目同步错误处理"""
        # 模拟配置错误的项目
        projects_config = [{"project_id": "invalid"}]

        with patch.object(gitlab_syncer, '_log_sync_error', new_callable=AsyncMock) as mock_log_error:
            await gitlab_syncer.sync_projects(projects_config)
            mock_log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_existing_document(self, gitlab_syncer, test_session, sample_document_data):
        """测试查找已存在文档"""
        # 创建文档
        document = Document(**sample_document_data)
        test_session.add(document)
        await test_session.commit()

        # 查找文档
        found_doc = await gitlab_syncer._find_existing_document(test_session, "test:1")

        assert found_doc is not None
        assert found_doc.title == "测试文档"

    @pytest.mark.asyncio
    async def test_create_document(self, gitlab_syncer, test_session, sample_document_data):
        """测试创建新文档"""
        document = await gitlab_syncer._create_document(test_session, sample_document_data)

        assert document.id is not None
        assert document.title == "测试文档"
        assert document.source_type == "gitlab"

    @pytest.mark.asyncio
    async def test_update_document(self, gitlab_syncer, test_session, sample_document_data):
        """测试更新文档"""
        # 创建原始文档
        document = Document(**sample_document_data)
        test_session.add(document)
        await test_session.commit()

        # 更新数据
        updated_data = sample_document_data.copy()
        updated_data["title"] = "更新后的标题"
        updated_data["content"] = "更新后的内容"

        # 执行更新
        await gitlab_syncer._update_document(test_session, document, updated_data)

        assert document.title == "更新后的标题"
        assert document.content == "更新后的内容"