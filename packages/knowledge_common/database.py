"""数据库管理模块"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, select, update, delete
from sqlalchemy.exc import IntegrityError

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy基础模型类"""
    metadata = MetaData()


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """初始化数据库连接"""
        if self._is_initialized:
            return

        try:
            # 创建异步引擎
            self.engine = create_async_engine(
                self.database_url,
                echo=settings.debug,
                future=True,
            )

            # 创建会话工厂
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # 创建所有表
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._is_initialized = True
            logger.info(f"数据库初始化成功: {self.database_url}")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    async def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            self._is_initialized = False
            logger.info("数据库连接已关闭")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器"""
        if not self._is_initialized:
            await self.initialize()

        if not self.session_factory:
            raise RuntimeError("数据库未正确初始化")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def check_connection(self) -> bool:
        """检查数据库连接状态"""
        try:
            if not self._is_initialized:
                await self.initialize()

            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False

    async def create_tables(self) -> None:
        """创建数据库表（用于同步服务）"""
        if not self._is_initialized:
            await self.initialize()

    # 文档相关方法
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        async with self.get_session() as session:
            from .models import DocumentModel
            result = await session.execute(
                select(DocumentModel).where(DocumentModel.slug == doc_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                return {
                    'id': doc.slug,
                    'title': doc.title,
                    'content': doc.content,
                    'content_hash': doc.doc_metadata.get('content_hash') if doc.doc_metadata else None,
                    'file_path': doc.file_path,
                    'source_type': doc.source_type,
                    'source_id': doc.source_id,
                    'category': doc.category.slug if doc.category else None,
                    'author': doc.author,
                    'created_at': doc.created_at,
                    'updated_at': doc.updated_at,
                    'metadata': doc.doc_metadata
                }
            return None

    async def create_document(self, doc_data: Dict[str, Any]) -> None:
        """创建文档"""
        async with self.get_session() as session:
            from .models import DocumentModel, CategoryModel

            # 获取或创建分类
            category = None
            if doc_data.get('category'):
                category_result = await session.execute(
                    select(CategoryModel).where(CategoryModel.slug == doc_data['category'])
                )
                category = category_result.scalar_one_or_none()

                if not category:
                    category = CategoryModel(
                        name=doc_data['category'].title(),
                        slug=doc_data['category'],
                        description=f"Auto-created category for {doc_data['category']}"
                    )
                    session.add(category)
                    await session.flush()

            # 创建文档
            document = DocumentModel(
                title=doc_data['title'],
                slug=doc_data['id'],
                content=doc_data['content'],
                summary=doc_data.get('metadata', {}).get('description'),
                file_path=doc_data['file_path'],
                source_type=doc_data['source_type'],
                source_id=doc_data.get('source_id'),
                category_id=category.id if category else None,
                author=doc_data.get('author'),
                tags=doc_data.get('metadata', {}).get('tags', []),
                doc_metadata=doc_data.get('metadata', {}),
                last_sync_at=doc_data.get('synced_at', datetime.now())
            )

            # 添加content_hash到metadata
            if doc_data.get('content_hash'):
                if not document.doc_metadata:
                    document.doc_metadata = {}
                document.doc_metadata['content_hash'] = doc_data['content_hash']

            session.add(document)

    async def update_document(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        """更新文档"""
        async with self.get_session() as session:
            from .models import DocumentModel, CategoryModel

            # 获取现有文档
            result = await session.execute(
                select(DocumentModel).where(DocumentModel.slug == doc_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                await self.create_document(doc_data)
                return

            # 获取或创建分类
            category = None
            if doc_data.get('category'):
                category_result = await session.execute(
                    select(CategoryModel).where(CategoryModel.slug == doc_data['category'])
                )
                category = category_result.scalar_one_or_none()

                if not category:
                    category = CategoryModel(
                        name=doc_data['category'].title(),
                        slug=doc_data['category'],
                        description=f"Auto-created category for {doc_data['category']}"
                    )
                    session.add(category)
                    await session.flush()

            # 更新文档字段
            document.title = doc_data['title']
            document.content = doc_data['content']
            document.summary = doc_data.get('metadata', {}).get('description')
            document.file_path = doc_data['file_path']
            document.source_type = doc_data['source_type']
            document.source_id = doc_data.get('source_id')
            document.category_id = category.id if category else None
            document.author = doc_data.get('author')
            document.tags = doc_data.get('metadata', {}).get('tags', [])
            document.doc_metadata = doc_data.get('metadata', {})
            document.last_sync_at = doc_data.get('synced_at', datetime.now())
            document.updated_at = datetime.now()

            # 添加content_hash到metadata
            if doc_data.get('content_hash'):
                if not document.doc_metadata:
                    document.doc_metadata = {}
                document.doc_metadata['content_hash'] = doc_data['content_hash']

    async def create_sync_log(self, log_data: Dict[str, Any]) -> None:
        """创建同步日志"""
        async with self.get_session() as session:
            from .models import SyncLogModel

            sync_log = SyncLogModel(
                source_type=log_data['source_type'],
                source_name=log_data.get('source_id', log_data['source_type']),
                status=log_data['status'],
                message=log_data.get('message'),
                documents_synced=log_data.get('documents_synced', 0),
                documents_added=log_data.get('documents_added', 1 if log_data['action'] == 'create' else 0),
                documents_updated=log_data.get('documents_updated', 1 if log_data['action'] == 'update' else 0),
                sync_metadata=log_data.get('metadata')
            )

            session.add(sync_log)


# 全局数据库管理器实例
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖项：获取数据库会话"""
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """初始化数据库（用于应用启动）"""
    await db_manager.initialize()


async def close_database() -> None:
    """关闭数据库（用于应用关闭）"""
    await db_manager.close()


async def check_sqlite_database() -> dict:
    """检查SQLite数据库状态"""
    try:
        is_connected = await db_manager.check_connection()
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "database_url": settings.database_url,
            "type": "SQLite",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_url": settings.database_url,
            "type": "SQLite",
        }