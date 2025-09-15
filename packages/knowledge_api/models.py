"""
API数据模型
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    title: str
    content: str
    file_path: str
    source_type: str
    source_id: str
    category: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    synced_at: datetime

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    """文档摘要模型"""
    id: int
    title: str
    file_path: str
    source_type: str
    category: Optional[str] = None
    author: Optional[str] = None
    updated_at: datetime
    excerpt: Optional[str] = None  # 内容摘要

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=200)
    category: Optional[str] = Field(None, description="文档分类过滤")
    source_type: Optional[str] = Field(None, description="来源类型过滤")
    limit: int = Field(20, description="返回结果数量", ge=1, le=100)
    offset: int = Field(0, description="结果偏移量", ge=0)


class SearchResponse(BaseModel):
    """搜索响应模型"""
    total: int = Field(..., description="总结果数")
    documents: List[DocumentSummary] = Field(..., description="文档列表")
    query: str = Field(..., description="搜索查询")
    took: float = Field(..., description="搜索耗时(秒)")


class CategoryResponse(BaseModel):
    """分类响应模型"""
    name: str
    count: int
    description: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应模型"""
    total_documents: int
    categories: List[CategoryResponse]
    sources: Dict[str, int]
    last_sync: Optional[datetime] = None


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    message: str
    code: Optional[str] = None