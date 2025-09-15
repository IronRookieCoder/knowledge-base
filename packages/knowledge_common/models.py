"""数据库模型定义"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship, Mapped

from .database import Base


class BaseModel(Base):
    """基础模型类"""
    __abstract__ = True

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class CategoryModel(BaseModel):
    """文档分类模型"""
    __tablename__ = "categories"

    name: Mapped[str] = Column(String(100), nullable=False, index=True)
    slug: Mapped[str] = Column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text)
    parent_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = Column(Integer, default=0, nullable=False)

    # 关系
    parent = relationship("CategoryModel", remote_side="CategoryModel.id", backref="children")
    documents = relationship("DocumentModel", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class DocumentModel(BaseModel):
    """文档模型"""
    __tablename__ = "documents"

    title: Mapped[str] = Column(String(200), nullable=False, index=True)
    slug: Mapped[str] = Column(String(200), unique=True, nullable=False, index=True)
    content: Mapped[str] = Column(Text, nullable=False)
    summary: Mapped[Optional[str]] = Column(Text)
    file_path: Mapped[str] = Column(String(500), nullable=False, index=True)
    source_type: Mapped[str] = Column(String(50), nullable=False, index=True)  # gitlab, confluence, local
    source_id: Mapped[Optional[str]] = Column(String(100), index=True)
    source_url: Mapped[Optional[str]] = Column(String(500))
    category_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    author: Mapped[Optional[str]] = Column(String(100))
    language: Mapped[str] = Column(String(10), default="zh", nullable=False)
    tags: Mapped[Optional[List[str]]] = Column(JSON)
    doc_metadata: Mapped[Optional[dict]] = Column(JSON)
    is_published: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    version: Mapped[str] = Column(String(50), default="1.0", nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = Column(DateTime)
    view_count: Mapped[int] = Column(Integer, default=0, nullable=False)

    # 关系
    category = relationship("CategoryModel", back_populates="documents")

    # 索引
    __table_args__ = (
        Index("idx_document_source", "source_type", "source_id"),
        Index("idx_document_category", "category_id", "is_published"),
        Index("idx_document_title_content", "title"),  # 全文搜索会使用专门的搜索引擎
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', source_type='{self.source_type}')>"


class SyncLogModel(BaseModel):
    """同步日志模型"""
    __tablename__ = "sync_logs"

    source_type: Mapped[str] = Column(String(50), nullable=False, index=True)
    source_name: Mapped[str] = Column(String(100), nullable=False)
    status: Mapped[str] = Column(String(20), nullable=False, index=True)  # success, error, running
    message: Mapped[Optional[str]] = Column(Text)
    documents_synced: Mapped[int] = Column(Integer, default=0, nullable=False)
    documents_added: Mapped[int] = Column(Integer, default=0, nullable=False)
    documents_updated: Mapped[int] = Column(Integer, default=0, nullable=False)
    documents_deleted: Mapped[int] = Column(Integer, default=0, nullable=False)
    sync_duration: Mapped[Optional[float]] = Column(String(20))  # 同步耗时(秒)
    sync_metadata: Mapped[Optional[dict]] = Column(JSON)

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, source_type='{self.source_type}', status='{self.status}')>"


class SearchIndexModel(BaseModel):
    """搜索索引状态模型"""
    __tablename__ = "search_indexes"

    document_id: Mapped[int] = Column(
        Integer, ForeignKey("documents.id"), nullable=False, unique=True
    )
    indexed_at: Mapped[datetime] = Column(DateTime, nullable=False)
    index_version: Mapped[str] = Column(String(20), default="1.0", nullable=False)
    word_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    keywords: Mapped[Optional[List[str]]] = Column(JSON)

    # 关系
    document = relationship("DocumentModel")

    def __repr__(self) -> str:
        return f"<SearchIndex(document_id={self.document_id}, indexed_at={self.indexed_at})>"


class ApiKeyModel(BaseModel):
    """API密钥模型"""
    __tablename__ = "api_keys"

    name: Mapped[str] = Column(String(100), nullable=False)
    key_hash: Mapped[str] = Column(String(256), unique=True, nullable=False, index=True)
    permissions: Mapped[List[str]] = Column(JSON, default=list)  # ["read", "write", "admin"]
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = Column(DateTime)
    last_used_at: Mapped[Optional[datetime]] = Column(DateTime)
    request_count: Mapped[int] = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name='{self.name}', is_active={self.is_active})>"