"""
Pytest配置文件
"""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from packages.knowledge_common.database import Base
from packages.knowledge_common.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_settings():
    """测试设置"""
    original_env = settings.environment
    settings.environment = "test"
    settings.debug = True
    yield settings
    settings.environment = original_env


@pytest.fixture
def sample_document_data():
    """示例文档数据"""
    return {
        "title": "测试文档",
        "content": "这是一个测试文档的内容。包含一些关键信息和示例代码。",
        "file_path": "test/sample.md",
        "source_type": "gitlab",
        "source_id": "test:1",
        "category": "test",
        "author": "测试用户",
        "version": "1.0",
        "file_hash": "abc123"
    }


@pytest.fixture
def sample_documents_data():
    """多个示例文档数据"""
    return [
        {
            "title": "API文档",
            "content": "RESTful API设计指南和最佳实践。包含认证、错误处理等内容。",
            "file_path": "api/rest-api.md",
            "source_type": "gitlab",
            "source_id": "api:1",
            "category": "api",
            "author": "开发团队",
            "version": "2.0",
            "file_hash": "def456"
        },
        {
            "title": "部署指南",
            "content": "应用部署的详细步骤，包含Docker和Kubernetes配置。",
            "file_path": "deployment/guide.md",
            "source_type": "confluence",
            "source_id": "deploy:1",
            "category": "deployment",
            "author": "运维团队",
            "version": "1.5",
            "file_hash": "ghi789"
        },
        {
            "title": "开发规范",
            "content": "代码开发规范和最佳实践，包含代码审查流程。",
            "file_path": "dev/standards.md",
            "source_type": "gitlab",
            "source_id": "dev:1",
            "category": "development",
            "author": "架构师",
            "version": "3.0",
            "file_hash": "jkl012"
        }
    ]