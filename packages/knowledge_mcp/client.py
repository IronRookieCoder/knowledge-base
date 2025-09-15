"""
MCP客户端示例
用于测试MCP服务器功能
"""

import asyncio
import json
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..knowledge_common.logging import get_logger

logger = get_logger(__name__)


class KnowledgeBaseMCPClient:
    """知识库MCP客户端"""

    def __init__(self, server_script_path: str = "packages/knowledge_mcp/server.py"):
        self.server_script_path = server_script_path
        self.session: ClientSession = None
        self.stdio_transport = None

    async def connect(self):
        """连接到MCP服务器"""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "packages.knowledge_mcp.server"]
        )

        # 使用异步上下文管理器
        self.stdio_transport = stdio_client(server_params)
        read_stream, write_stream = await self.stdio_transport.__aenter__()
        self.session = ClientSession(read_stream, write_stream)

        await self.session.initialize()
        logger.info("Connected to MCP server")

    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
        if hasattr(self, 'stdio_transport') and self.stdio_transport:
            await self.stdio_transport.__aexit__(None, None, None)
        logger.info("Disconnected from MCP server")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_tools()
        return [tool.model_dump() for tool in result.tools]

    async def search_knowledge(
        self,
        query: str,
        category: str = None,
        source_type: str = None,
        limit: int = 10
    ) -> str:
        """搜索知识库"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        arguments = {"query": query, "limit": limit}
        if category:
            arguments["category"] = category
        if source_type:
            arguments["source_type"] = source_type

        result = await self.session.call_tool("search_knowledge", arguments)
        return result.content[0].text if result.content else ""

    async def get_document(self, document_id: int) -> str:
        """获取文档详情"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.call_tool("get_document", {"document_id": document_id})
        return result.content[0].text if result.content else ""

    async def get_categories(self) -> str:
        """获取分类列表"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.call_tool("get_categories", {})
        return result.content[0].text if result.content else ""

    async def get_stats(self) -> str:
        """获取统计信息"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.call_tool("get_stats", {})
        return result.content[0].text if result.content else ""

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """列出可用提示"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_prompts()
        return [prompt.model_dump() for prompt in result.prompts]

    async def get_prompt(self, name: str, arguments: Dict[str, str] = None) -> str:
        """获取提示内容"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.get_prompt(name, arguments or {})
        return result.content[0].text if result.content else ""

    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出可用资源"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_resources()
        return [resource.model_dump() for resource in result.resources]

    async def read_resource(self, uri: str) -> str:
        """读取资源"""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.read_resource(uri)
        return result.content[0].text if result.content else ""


async def test_client():
    """测试客户端功能"""
    client = KnowledgeBaseMCPClient()

    try:
        await client.connect()

        # 测试工具列表
        print("=== 可用工具 ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")

        print("\n=== 测试搜索 ===")
        search_result = await client.search_knowledge("API")
        print(search_result)

        print("\n=== 获取统计信息 ===")
        stats = await client.get_stats()
        print(stats)

        print("\n=== 获取分类 ===")
        categories = await client.get_categories()
        print(categories)

        print("\n=== 可用提示 ===")
        prompts = await client.list_prompts()
        for prompt in prompts:
            print(f"- {prompt['name']}: {prompt['description']}")

        print("\n=== 可用资源 ===")
        resources = await client.list_resources()
        for resource in resources:
            print(f"- {resource['uri']}: {resource['description']}")

    except Exception as e:
        logger.error("Client test failed", error=str(e))
        print(f"测试失败：{e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_client())