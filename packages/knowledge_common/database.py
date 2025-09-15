"""数据库管理模块"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

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