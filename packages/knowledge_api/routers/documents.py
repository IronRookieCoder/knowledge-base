"""
文档相关API路由
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ...knowledge_common.database import db_manager
from ...knowledge_common.models import DocumentModel
from ...knowledge_common.logging import get_logger
from ..models import (
    DocumentResponse,
    DocumentSummary,
    SearchRequest,
    SearchResponse,
    CategoryResponse,
    StatsResponse
)
from ..search import search_engine

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with db_manager.get_session() as session:
        yield session


@router.get("/", response_model=List[DocumentSummary])
async def list_documents(
    category: Optional[str] = Query(None, description="分类过滤"),
    source_type: Optional[str] = Query(None, description="来源类型过滤"),
    limit: int = Query(20, description="返回数量", ge=1, le=100),
    offset: int = Query(0, description="偏移量", ge=0),
    db: AsyncSession = Depends(get_db)
):
    """获取文档列表"""
    try:
        # 构建查询
        query = select(DocumentModel).where(DocumentModel.is_active == True)

        if category:
            query = query.where(DocumentModel.category == category)

        if source_type:
            query = query.where(DocumentModel.source_type == source_type)

        query = query.order_by(desc(DocumentModel.updated_at)).offset(offset).limit(limit)

        # 执行查询
        result = await db.execute(query)
        documents = result.scalars().all()

        # 转换为响应模型
        return [
            DocumentSummary(
                id=doc.id,
                title=doc.title,
                file_path=doc.file_path,
                source_type=doc.source_type,
                category=doc.category,
                author=doc.author,
                updated_at=doc.updated_at,
                excerpt=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            )
            for doc in documents
        ]

    except Exception as e:
        logger.error("Failed to list documents", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取单个文档"""
    try:
        query = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.is_active == True
        )
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="DocumentModel not found")

        return DocumentResponse.model_validate(document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """搜索文档"""
    start_time = datetime.now()

    try:
        # 执行搜索
        documents, total = await search_engine.search(
            query_str=request.query,
            category=request.category,
            source_type=request.source_type,
            limit=request.limit,
            offset=request.offset
        )

        # 计算耗时
        took = (datetime.now() - start_time).total_seconds()

        # 转换为响应模型
        document_summaries = [
            DocumentSummary(
                id=doc["id"],
                title=doc["title"],
                file_path=doc["file_path"],
                source_type=doc["source_type"],
                category=doc["category"],
                author=doc["author"],
                updated_at=doc["updated_at"],
                excerpt=doc["excerpt"]
            )
            for doc in documents
        ]

        return SearchResponse(
            total=total,
            documents=document_summaries,
            query=request.query,
            took=took
        )

    except Exception as e:
        logger.error("Search failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/categories/", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """获取文档分类统计"""
    try:
        query = select(
            DocumentModel.category,
            func.count(DocumentModel.id).label("count")
        ).where(
            DocumentModel.is_active == True,
            DocumentModel.category.isnot(None)
        ).group_by(DocumentModel.category)

        result = await db.execute(query)
        categories = result.fetchall()

        return [
            CategoryResponse(
                name=category or "未分类",
                count=count,
                description=f"{category}类别文档"
            )
            for category, count in categories
        ]

    except Exception as e:
        logger.error("Failed to get categories", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get categories")


@router.get("/stats/", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取文档统计信息"""
    try:
        # 获取总文档数
        total_query = select(func.count(DocumentModel.id)).where(DocumentModel.is_active == True)
        total_result = await db.execute(total_query)
        total_documents = total_result.scalar()

        # 获取分类统计
        category_query = select(
            DocumentModel.category,
            func.count(DocumentModel.id).label("count")
        ).where(
            DocumentModel.is_active == True
        ).group_by(DocumentModel.category)

        category_result = await db.execute(category_query)
        categories = [
            CategoryResponse(
                name=category or "未分类",
                count=count
            )
            for category, count in category_result.fetchall()
        ]

        # 获取来源统计
        source_query = select(
            DocumentModel.source_type,
            func.count(DocumentModel.id).label("count")
        ).where(
            DocumentModel.is_active == True
        ).group_by(DocumentModel.source_type)

        source_result = await db.execute(source_query)
        sources = {
            source_type: count
            for source_type, count in source_result.fetchall()
        }

        # 获取最后同步时间
        last_sync_query = select(func.max(DocumentModel.synced_at)).where(DocumentModel.is_active == True)
        last_sync_result = await db.execute(last_sync_query)
        last_sync = last_sync_result.scalar()

        return StatsResponse(
            total_documents=total_documents,
            categories=categories,
            sources=sources,
            last_sync=last_sync
        )

    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get stats")