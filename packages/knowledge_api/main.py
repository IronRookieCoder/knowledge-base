"""
API服务主入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ..knowledge_common.config import settings
from ..knowledge_common.database import db_manager, get_db
from ..knowledge_common.logging import get_logger
from ..knowledge_common.models import DocumentModel
from .models import ErrorResponse
from .routers import documents, health
from sqlalchemy import select

logger = get_logger(__name__)


async def rebuild_search_index():
    """从数据库重建搜索索引"""
    try:
        logger.info("开始重建搜索索引...")

        # 获取搜索引擎
        from .search import search_engine

        # 获取所有已发布的文档
        async for session in get_db():
            query = select(DocumentModel).where(DocumentModel.is_published == True)
            result = await session.execute(query)
            documents = result.scalars().all()

            logger.info(f"找到 {len(documents)} 个文档")

            # 转换为搜索引擎格式
            search_docs = []
            for doc in documents:
                search_doc = {
                    "id": str(doc.id),
                    "title": doc.title or "",
                    "content": doc.content or "",
                    "category": "docs",
                    "source_type": doc.source_type or "local",
                    "author": doc.author or "Unknown",
                    "file_path": doc.file_path or "",
                    "created_at": doc.created_at.strftime("%Y%m%d%H%M%S") if doc.created_at else "20240101000000",
                    "updated_at": doc.updated_at.strftime("%Y%m%d%H%M%S") if doc.updated_at else "20240101000000"
                }
                search_docs.append(search_doc)

            # 重建索引
            await search_engine.rebuild_index(search_docs)
            logger.info("搜索索引重建完成")
            break  # 只需要一次会话

    except Exception as e:
        logger.error("重建搜索索引失败", error=str(e))
        # 不抛出异常，允许服务继续启动


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("Starting API service")

    try:
        # 初始化数据库
        await db_manager.initialize()
        logger.info("Database initialized")

        # 初始化搜索索引并从数据库重建
        from .search import search_engine
        await rebuild_search_index()
        logger.info("Search engine initialized and index rebuilt")

        yield

    except Exception as e:
        logger.error("Failed to initialize service", error=str(e))
        raise

    finally:
        # 关闭时清理
        logger.info("Shutting down API service")
        await db_manager.close()


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Knowledge Base API",
        description="企业知识库管理系统API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 配置受信任主机
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*"]
        )

    # 注册路由
    app.include_router(health.router)
    app.include_router(documents.router, prefix="/api")

    # 全局异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP_ERROR",
                message=exc.detail,
                code=str(exc.status_code)
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Internal server error"
            ).model_dump()
        )

    return app


app = create_app()


def main():
    """主入口函数"""
    uvicorn.run(
        "packages.knowledge_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development(),
        log_level="info" if settings.is_production() else "debug"
    )


if __name__ == "__main__":
    main()