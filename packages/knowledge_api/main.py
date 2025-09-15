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
from ..knowledge_common.database import db_manager
from ..knowledge_common.logging import get_logger
from .models import ErrorResponse
from .routers import documents, health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("Starting API service")

    try:
        # 初始化数据库
        await db_manager.initialize()
        logger.info("Database initialized")

        # 初始化搜索索引
        from .search import search_engine
        logger.info("Search engine initialized")

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