"""
MCP服务器实现
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Prompt,
    Resource
)

from ..knowledge_common.config import settings
from ..knowledge_common.database import db_manager
from ..knowledge_common.logging import get_logger
from ..knowledge_api.search import search_engine

logger = get_logger(__name__)


class KnowledgeBaseMCPServer:
    """知识库MCP服务器"""

    def __init__(self):
        self.server = Server("knowledge-base")
        self._setup_handlers()

    def _setup_handlers(self):
        """设置处理器"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="search_knowledge",
                    description="搜索知识库内容，支持关键词搜索和分类过滤",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "category": {
                                "type": "string",
                                "description": "文档分类过滤，可选"
                            },
                            "source_type": {
                                "type": "string",
                                "description": "来源类型过滤（gitlab/confluence），可选"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回结果数量限制，默认10",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_document",
                    description="根据文档ID获取完整文档内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "integer",
                                "description": "文档ID"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                Tool(
                    name="get_categories",
                    description="获取所有文档分类及其文档数量",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_stats",
                    description="获取知识库统计信息",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """处理工具调用"""
            try:
                if name == "search_knowledge":
                    return await self._search_knowledge(arguments)
                elif name == "get_document":
                    return await self._get_document(arguments)
                elif name == "get_categories":
                    return await self._get_categories(arguments)
                elif name == "get_stats":
                    return await self._get_stats(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error("Tool call failed", tool=name, error=str(e))
                return [TextContent(
                    type="text",
                    text=f"Error executing tool {name}: {str(e)}"
                )]

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """列出可用提示"""
            return [
                Prompt(
                    name="knowledge_search",
                    description="知识库搜索助手提示",
                    arguments=[
                        {
                            "name": "topic",
                            "description": "要搜索的主题",
                            "required": True
                        }
                    ]
                ),
                Prompt(
                    name="document_analysis",
                    description="文档分析提示",
                    arguments=[
                        {
                            "name": "document_id",
                            "description": "要分析的文档ID",
                            "required": True
                        }
                    ]
                )
            ]

        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> str:
            """获取提示内容"""
            if name == "knowledge_search":
                topic = arguments.get("topic", "")
                return f"""你是一个企业知识库搜索助手。用户想了解关于"{topic}"的信息。

请使用search_knowledge工具搜索相关文档，然后：
1. 总结找到的相关信息
2. 如果找到多个相关文档，请提供一个概览
3. 如果需要更详细的信息，可以使用get_document工具获取完整文档内容
4. 提供有用的建议和下一步行动

搜索关键词：{topic}"""

            elif name == "document_analysis":
                doc_id = arguments.get("document_id", "")
                return f"""请分析文档ID为{doc_id}的文档。

使用get_document工具获取文档内容，然后提供：
1. 文档主要内容摘要
2. 关键信息点
3. 文档的适用场景
4. 相关建议或注意事项

文档ID：{doc_id}"""

            return f"Unknown prompt: {name}"

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="knowledge://stats",
                    name="Knowledge Base Statistics",
                    description="知识库统计信息",
                    mimeType="application/json"
                ),
                Resource(
                    uri="knowledge://categories",
                    name="DocumentModel Categories",
                    description="文档分类列表",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取资源"""
            if uri == "knowledge://stats":
                stats = await self._get_stats_data()
                return json.dumps(stats, ensure_ascii=False, indent=2)
            elif uri == "knowledge://categories":
                categories = await self._get_categories_data()
                return json.dumps(categories, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

    async def _search_knowledge(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """搜索知识库"""
        query = arguments.get("query", "")
        category = arguments.get("category")
        source_type = arguments.get("source_type")
        limit = arguments.get("limit", 10)

        if not query:
            return [TextContent(
                type="text",
                text="搜索查询不能为空"
            )]

        try:
            # 执行搜索
            documents, total = await search_engine.search(
                query_str=query,
                category=category,
                source_type=source_type,
                limit=limit,
                offset=0
            )

            if not documents:
                return [TextContent(
                    type="text",
                    text=f"未找到与'{query}'相关的文档"
                )]

            # 格式化结果
            result_text = f"找到 {total} 个相关文档（显示前 {len(documents)} 个）：\n\n"

            for i, doc in enumerate(documents, 1):
                result_text += f"## {i}. {doc['title']}\n"
                result_text += f"**ID**: {doc['id']}\n"
                result_text += f"**分类**: {doc['category']}\n"
                result_text += f"**来源**: {doc['source_type']}\n"
                result_text += f"**路径**: {doc['file_path']}\n"
                if doc['author']:
                    result_text += f"**作者**: {doc['author']}\n"
                result_text += f"**更新时间**: {doc['updated_at']}\n"
                if doc['excerpt']:
                    result_text += f"**内容**: {doc['excerpt']}\n"
                result_text += "\n"

            result_text += f"\n💡 使用 get_document 工具并提供文档ID可获取完整内容"

            return [TextContent(
                type="text",
                text=result_text
            )]

        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            return [TextContent(
                type="text",
                text=f"搜索失败：{str(e)}"
            )]

    async def _get_document(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """获取文档详情"""
        document_id = arguments.get("document_id")

        if not document_id:
            return [TextContent(
                type="text",
                text="文档ID不能为空"
            )]

        try:
            from sqlalchemy import select
            from ..knowledge_common.models import DocumentModel

            async with db_manager.get_session() as session:
                query = select(DocumentModel).where(
                    DocumentModel.id == document_id,
                    DocumentModel.is_active == True
                )
                result = await session.execute(query)
                document = result.scalar_one_or_none()

                if not document:
                    return [TextContent(
                        type="text",
                        text=f"未找到ID为 {document_id} 的文档"
                    )]

                # 格式化文档内容
                content = f"# {document.title}\n\n"
                content += f"**文档ID**: {document.id}\n"
                content += f"**分类**: {document.category}\n"
                content += f"**来源**: {document.source_type}\n"
                content += f"**文件路径**: {document.file_path}\n"
                if document.author:
                    content += f"**作者**: {document.author}\n"
                if document.version:
                    content += f"**版本**: {document.version}\n"
                content += f"**创建时间**: {document.created_at}\n"
                content += f"**更新时间**: {document.updated_at}\n"
                content += f"**同步时间**: {document.synced_at}\n\n"
                content += "---\n\n"
                content += document.content

                return [TextContent(
                    type="text",
                    text=content
                )]

        except Exception as e:
            logger.error("Get document failed", document_id=document_id, error=str(e))
            return [TextContent(
                type="text",
                text=f"获取文档失败：{str(e)}"
            )]

    async def _get_categories(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """获取分类列表"""
        try:
            categories = await self._get_categories_data()

            if not categories:
                return [TextContent(
                    type="text",
                    text="暂无文档分类"
                )]

            result_text = "## 文档分类统计\n\n"
            for category in categories:
                result_text += f"- **{category['name']}**: {category['count']} 个文档\n"

            return [TextContent(
                type="text",
                text=result_text
            )]

        except Exception as e:
            logger.error("Get categories failed", error=str(e))
            return [TextContent(
                type="text",
                text=f"获取分类失败：{str(e)}"
            )]

    async def _get_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """获取统计信息"""
        try:
            stats = await self._get_stats_data()

            result_text = "## 知识库统计信息\n\n"
            result_text += f"**总文档数**: {stats['total_documents']}\n\n"

            if stats['categories']:
                result_text += "### 分类统计\n"
                for name, count in stats['categories'].items():
                    result_text += f"- {name}: {count} 个文档\n"
                result_text += "\n"

            if stats['sources']:
                result_text += "### 来源统计\n"
                for source, count in stats['sources'].items():
                    result_text += f"- {source}: {count} 个文档\n"

            return [TextContent(
                type="text",
                text=result_text
            )]

        except Exception as e:
            logger.error("Get stats failed", error=str(e))
            return [TextContent(
                type="text",
                text=f"获取统计信息失败：{str(e)}"
            )]

    async def _get_categories_data(self) -> List[Dict[str, Any]]:
        """获取分类数据"""
        from sqlalchemy import select, func
        from ..knowledge_common.models import DocumentModel, CategoryModel

        async with db_manager.get_session() as session:
            # 查询有分类的文档统计
            categorized_query = select(
                CategoryModel.name,
                func.count(DocumentModel.id).label("count")
            ).select_from(
                CategoryModel.__table__.join(
                    DocumentModel.__table__,
                    CategoryModel.id == DocumentModel.category_id
                )
            ).where(
                DocumentModel.is_active == True
            ).group_by(CategoryModel.name)

            categorized_result = await session.execute(categorized_query)
            categories_data = []

            for name, count in categorized_result.fetchall():
                categories_data.append({
                    "name": name,
                    "count": count
                })

            # 查询未分类文档数量
            uncategorized_query = select(func.count(DocumentModel.id)).where(
                DocumentModel.is_active == True,
                DocumentModel.category_id.is_(None)
            )
            uncategorized_result = await session.execute(uncategorized_query)
            uncategorized_count = uncategorized_result.scalar() or 0

            if uncategorized_count > 0:
                categories_data.append({
                    "name": "未分类",
                    "count": uncategorized_count
                })

            return categories_data

    async def _get_stats_data(self) -> Dict[str, Any]:
        """获取统计数据"""
        from sqlalchemy import select, func
        from ..knowledge_common.models import DocumentModel, CategoryModel

        async with db_manager.get_session() as session:
            # 总文档数
            total_query = select(func.count(DocumentModel.id)).where(DocumentModel.is_active == True)
            total_result = await session.execute(total_query)
            total_documents = total_result.scalar()

            # 分类统计
            categorized_query = select(
                CategoryModel.name,
                func.count(DocumentModel.id).label("count")
            ).select_from(
                CategoryModel.__table__.join(
                    DocumentModel.__table__,
                    CategoryModel.id == DocumentModel.category_id
                )
            ).where(
                DocumentModel.is_active == True
            ).group_by(CategoryModel.name)

            categorized_result = await session.execute(categorized_query)
            categories = {}

            for name, count in categorized_result.fetchall():
                categories[name] = count

            # 未分类文档统计
            uncategorized_query = select(func.count(DocumentModel.id)).where(
                DocumentModel.is_active == True,
                DocumentModel.category_id.is_(None)
            )
            uncategorized_result = await session.execute(uncategorized_query)
            uncategorized_count = uncategorized_result.scalar() or 0

            if uncategorized_count > 0:
                categories["未分类"] = uncategorized_count

            # 来源统计
            source_query = select(
                DocumentModel.source_type,
                func.count(DocumentModel.id).label("count")
            ).where(
                DocumentModel.is_active == True
            ).group_by(DocumentModel.source_type)

            source_result = await session.execute(source_query)
            sources = {
                source_type: count
                for source_type, count in source_result.fetchall()
            }

            return {
                "total_documents": total_documents,
                "categories": categories,
                "sources": sources
            }

    async def run(self):
        """运行MCP服务器"""
        logger.info("Starting MCP server")

        # 初始化数据库
        await db_manager.create_tables()

        async with stdio_server() as streams:
            await self.server.run(
                streams[0],  # read stream
                streams[1],  # write stream
                self.server.create_initialization_options()
            )


async def main():
    """主入口函数"""
    server = KnowledgeBaseMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())