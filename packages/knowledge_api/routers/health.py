"""
健康检查API路由
"""

from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import text

from ...knowledge_common.config import settings
from ...knowledge_common.database import db_manager
from ...knowledge_common.logging import get_logger
from ..models import HealthResponse

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    services = {}

    # 检查数据库连接
    try:
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))
        services["database"] = "unhealthy"

    # 检查GitLab连接
    try:
        if settings.gitlab.token and settings.gitlab.url:
            import gitlab
            gl = gitlab.Gitlab(settings.gitlab.url, private_token=settings.gitlab.token)
            gl.auth()
            services["gitlab"] = "healthy"
        else:
            services["gitlab"] = "not_configured"
    except Exception as e:
        logger.warning("GitLab health check failed", error=str(e))
        services["gitlab"] = "unhealthy"

    # 检查Confluence连接
    try:
        if settings.confluence.token and settings.confluence.url:
            from atlassian import Confluence
            confluence = Confluence(
                url=settings.confluence.url,
                username=settings.confluence.username,
                password=settings.confluence.token,
                cloud=True
            )
            # 简单的连接测试
            confluence.get_all_spaces(start=0, limit=1)
            services["confluence"] = "healthy"
        else:
            services["confluence"] = "not_configured"
    except Exception as e:
        logger.warning("Confluence health check failed", error=str(e))
        services["confluence"] = "unhealthy"

    # 检查搜索引擎
    try:
        from ..search import search_engine
        stats = await search_engine.get_stats()
        services["search"] = "healthy"
    except Exception as e:
        logger.warning("Search engine health check failed", error=str(e))
        services["search"] = "unhealthy"

    # 确定整体状态
    overall_status = "healthy"
    if any(status == "unhealthy" for status in services.values()):
        overall_status = "unhealthy"
    elif any(status == "not_configured" for status in services.values()):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services
    )


@router.get("/")
async def root():
    """根路径"""
    return {
        "message": "Knowledge Base API",
        "version": "1.0.0",
        "docs": "/docs"
    }