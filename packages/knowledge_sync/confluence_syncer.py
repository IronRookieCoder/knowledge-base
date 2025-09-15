"""
Confluence文档同步器
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import html2text
from atlassian import Confluence
from sqlalchemy.ext.asyncio import AsyncSession

from ..knowledge_common.config import settings
from ..knowledge_common.database import db_manager
from ..knowledge_common.logging import get_logger
from ..knowledge_common.utils import (
    ensure_directory,
    get_file_hash,
    extract_markdown_metadata,
    clean_markdown_content
)
from ..knowledge_common.models import DocumentModel, SyncLogModel

logger = get_logger(__name__)


class ConfluenceSyncer:
    """Confluence文档同步器"""

    def __init__(self):
        self.confluence = Confluence(
            url=settings.confluence.url,
            username=settings.confluence.username,
            password=settings.confluence.token,
            cloud=True
        )
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # 不限制行宽

        self.output_dir = Path(settings.sync.docs_output_dir)
        ensure_directory(self.output_dir)

    async def sync_spaces(self, spaces_config: List[Dict[str, Any]]) -> None:
        """同步多个Confluence空间"""
        for space_config in spaces_config:
            try:
                await self._sync_single_space(space_config)
            except Exception as e:
                logger.error(
                    "Failed to sync space",
                    space_key=space_config.get("key"),
                    error=str(e)
                )
                await self._log_sync_error(space_config, str(e))

    async def _sync_single_space(self, space_config: Dict[str, Any]) -> None:
        """同步单个Confluence空间"""
        space_key = space_config["key"]
        space_name = space_config.get("name", space_key)
        target_path = space_config.get("target_path", f"confluence-{space_key}/")
        include_attachments = space_config.get("include_attachments", False)
        category = space_config.get("category", "confluence")

        logger.info(
            "Starting sync for Confluence space",
            space_key=space_key,
            space_name=space_name,
            target_path=target_path
        )

        try:
            # 获取空间页面列表
            pages = await self._get_space_pages(space_key)

            # 处理页面
            synced_count = 0
            for page in pages:
                try:
                    document = await self._process_page(
                        page,
                        space_key,
                        category,
                        include_attachments
                    )
                    if document:
                        await self._save_document(document, target_path)
                        synced_count += 1

                except Exception as e:
                    logger.warning(
                        "Failed to process page",
                        page_id=page.get("id"),
                        page_title=page.get("title"),
                        error=str(e)
                    )

            logger.info(
                "Sync completed for space",
                space_key=space_key,
                synced_documents=synced_count
            )

            await self._log_sync_success(space_config, synced_count)

        except Exception as e:
            logger.error(
                "Error syncing space",
                space_key=space_key,
                error=str(e)
            )
            raise

    async def _get_space_pages(self, space_key: str) -> List[Dict[str, Any]]:
        """获取空间的所有页面"""
        try:
            # 使用同步方法获取页面，然后在异步上下文中处理
            pages = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.confluence.get_all_pages_from_space(
                    space_key,
                    start=0,
                    limit=500,
                    status="current",
                    expand="body.storage,version,ancestors"
                )
            )
            return pages
        except Exception as e:
            logger.error(
                "Failed to get pages from space",
                space_key=space_key,
                error=str(e)
            )
            return []

    async def _process_page(
        self,
        page: Dict[str, Any],
        space_key: str,
        category: str,
        include_attachments: bool
    ) -> Optional[Dict[str, Any]]:
        """处理单个页面"""
        page_id = page["id"]
        title = page["title"]

        try:
            # 获取页面内容
            html_content = page.get("body", {}).get("storage", {}).get("value", "")
            if not html_content:
                logger.warning(
                    "Page has no content",
                    page_id=page_id,
                    title=title
                )
                return None

            # 转换HTML为Markdown
            markdown_content = await self._convert_html_to_markdown(
                html_content,
                page_id,
                include_attachments
            )

            # 生成文件路径
            file_path = await self._generate_file_path(page, space_key)

            # 获取页面元数据
            version = page.get("version", {}).get("number", 1)
            updated_date = page.get("version", {}).get("when")
            updated_at = datetime.fromisoformat(
                updated_date.replace("Z", "+00:00")
            ) if updated_date else datetime.utcnow()

            document = {
                "title": title,
                "content": markdown_content,
                "file_path": file_path,
                "source_type": "confluence",
                "source_id": f"{space_key}:{page_id}",
                "category": category,
                "author": page.get("version", {}).get("by", {}).get("displayName"),
                "version": str(version),
                "file_hash": get_file_hash(None),  # 将在保存时计算
                "updated_at": updated_at
            }

            return document

        except Exception as e:
            logger.error(
                "Failed to process page",
                page_id=page_id,
                title=title,
                error=str(e)
            )
            return None

    async def _convert_html_to_markdown(
        self,
        html_content: str,
        page_id: str,
        include_attachments: bool
    ) -> str:
        """将HTML内容转换为Markdown"""
        try:
            # 处理Confluence特有的宏和标记
            processed_html = await self._process_confluence_macros(html_content)

            # 如果需要处理附件，下载并本地化链接
            if include_attachments:
                processed_html = await self._process_attachments(
                    processed_html,
                    page_id
                )

            # 转换为Markdown
            markdown = self.html_converter.handle(processed_html)

            # 清理Markdown内容
            return clean_markdown_content(markdown)

        except Exception as e:
            logger.warning(
                "Failed to convert HTML to Markdown",
                page_id=page_id,
                error=str(e)
            )
            return ""

    async def _process_confluence_macros(self, html_content: str) -> str:
        """处理Confluence特有的宏"""
        # 处理代码块宏
        import re

        # 处理代码宏
        code_pattern = r'<ac:structured-macro ac:name="code"[^>]*>(.*?)</ac:structured-macro>'
        def replace_code_macro(match):
            content = match.group(1)
            # 提取代码内容
            plain_text_pattern = r'<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>'
            code_match = re.search(plain_text_pattern, content, re.DOTALL)
            if code_match:
                code_content = code_match.group(1)
                return f'<pre><code>{code_content}</code></pre>'
            return match.group(0)

        html_content = re.sub(code_pattern, replace_code_macro, html_content, flags=re.DOTALL)

        # 处理信息宏
        info_pattern = r'<ac:structured-macro ac:name="info"[^>]*>(.*?)</ac:structured-macro>'
        def replace_info_macro(match):
            content = match.group(1)
            # 提取信息内容
            body_pattern = r'<ac:rich-text-body>(.*?)</ac:rich-text-body>'
            body_match = re.search(body_pattern, content, re.DOTALL)
            if body_match:
                info_content = body_match.group(1)
                return f'<blockquote><strong>ℹ️ 信息</strong><br/>{info_content}</blockquote>'
            return match.group(0)

        html_content = re.sub(info_pattern, replace_info_macro, html_content, flags=re.DOTALL)

        # 处理警告宏
        warning_pattern = r'<ac:structured-macro ac:name="warning"[^>]*>(.*?)</ac:structured-macro>'
        def replace_warning_macro(match):
            content = match.group(1)
            body_pattern = r'<ac:rich-text-body>(.*?)</ac:rich-text-body>'
            body_match = re.search(body_pattern, content, re.DOTALL)
            if body_match:
                warning_content = body_match.group(1)
                return f'<blockquote><strong>⚠️ 警告</strong><br/>{warning_content}</blockquote>'
            return match.group(0)

        html_content = re.sub(warning_pattern, replace_warning_macro, html_content, flags=re.DOTALL)

        return html_content

    async def _process_attachments(self, html_content: str, page_id: str) -> str:
        """处理附件，下载并本地化链接"""
        import re

        # 匹配附件链接
        attachment_pattern = r'<ac:image[^>]*><ri:attachment ri:filename="([^"]+)"[^>]*></ri:attachment></ac:image>'

        def replace_attachment(match):
            filename = match.group(1)
            try:
                # 下载附件
                local_path = self._download_attachment(page_id, filename)
                if local_path:
                    return f'![{filename}]({local_path})'
                else:
                    return f'![{filename}](attachment:{filename})'
            except Exception as e:
                logger.warning(
                    "Failed to download attachment",
                    page_id=page_id,
                    filename=filename,
                    error=str(e)
                )
                return f'![{filename}](attachment:{filename})'

        return re.sub(attachment_pattern, replace_attachment, html_content)

    def _download_attachment(self, page_id: str, filename: str) -> Optional[str]:
        """下载附件到本地"""
        try:
            # 创建附件目录
            attachments_dir = self.output_dir / "attachments" / page_id
            ensure_directory(attachments_dir)

            # 下载附件
            attachment_content = self.confluence.download_attachment(page_id, filename)
            if attachment_content:
                local_file = attachments_dir / filename
                local_file.write_bytes(attachment_content)
                return f"attachments/{page_id}/{filename}"

        except Exception as e:
            logger.warning(
                "Failed to download attachment",
                page_id=page_id,
                filename=filename,
                error=str(e)
            )

        return None

    async def _generate_file_path(self, page: Dict[str, Any], space_key: str) -> str:
        """生成文件路径"""
        title = page["title"]

        # 清理标题作为文件名
        safe_title = "".join(
            c for c in title if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        safe_title = safe_title.replace(' ', '-')

        # 处理页面层级
        ancestors = page.get("ancestors", [])
        path_parts = []

        for ancestor in ancestors:
            ancestor_title = ancestor.get("title", "")
            safe_ancestor = "".join(
                c for c in ancestor_title if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            safe_ancestor = safe_ancestor.replace(' ', '-')
            if safe_ancestor:
                path_parts.append(safe_ancestor)

        path_parts.append(safe_title)

        # 构建完整路径
        file_path = "/".join(path_parts) + ".md"
        return file_path

    async def _save_document(
        self,
        doc_data: Dict[str, Any],
        target_path: str
    ) -> None:
        """保存文档到数据库和文件系统"""
        async with db_manager.get_session() as session:
            try:
                # 计算文件哈希
                doc_data["file_hash"] = get_file_hash(None)  # 基于内容计算

                # 检查文档是否已存在
                existing_doc = await self._find_existing_document(
                    session,
                    doc_data["source_id"]
                )

                if existing_doc:
                    # 检查是否需要更新
                    if existing_doc.file_hash != doc_data["file_hash"]:
                        await self._update_document(session, existing_doc, doc_data)
                else:
                    # 创建新文档
                    await self._create_document(session, doc_data)

                # 保存文件到文件系统
                await self._save_document_file(doc_data, target_path)

                await session.commit()

            except Exception as e:
                logger.error(
                    "Failed to save document",
                    source_id=doc_data["source_id"],
                    error=str(e)
                )
                await session.rollback()
                raise

    async def _find_existing_document(
        self,
        session: AsyncSession,
        source_id: str
    ) -> Optional[Document]:
        """查找已存在的文档"""
        from sqlalchemy import select

        result = await session.execute(
            select(Document).where(Document.source_id == source_id)
        )
        return result.scalar_one_or_none()

    async def _create_document(
        self,
        session: AsyncSession,
        doc_data: Dict[str, Any]
    ) -> Document:
        """创建新文档"""
        document = Document(
            title=doc_data["title"],
            content=doc_data["content"],
            file_path=doc_data["file_path"],
            source_type=doc_data["source_type"],
            source_id=doc_data["source_id"],
            category=doc_data["category"],
            author=doc_data.get("author"),
            version=doc_data.get("version"),
            file_hash=doc_data["file_hash"],
            updated_at=doc_data.get("updated_at", datetime.utcnow())
        )

        session.add(document)
        await session.flush()

        logger.info(
            "Created new document",
            document_id=document.id,
            title=document.title,
            source_id=document.source_id
        )

        return document

    async def _update_document(
        self,
        session: AsyncSession,
        document: Document,
        doc_data: Dict[str, Any]
    ) -> None:
        """更新文档"""
        document.title = doc_data["title"]
        document.content = doc_data["content"]
        document.author = doc_data.get("author")
        document.version = doc_data.get("version")
        document.file_hash = doc_data["file_hash"]
        document.updated_at = doc_data.get("updated_at", datetime.utcnow())
        document.synced_at = datetime.utcnow()

        logger.info(
            "Updated document",
            document_id=document.id,
            title=document.title,
            source_id=document.source_id
        )

    async def _save_document_file(
        self,
        doc_data: Dict[str, Any],
        target_path: str
    ) -> None:
        """保存文档文件到文件系统"""
        target_dir = self.output_dir / target_path
        ensure_directory(target_dir)

        target_file = target_dir / doc_data["file_path"]
        ensure_directory(target_file.parent)

        # 保存文件
        target_file.write_text(
            doc_data["content"],
            encoding="utf-8"
        )

    async def _log_sync_success(
        self,
        space_config: Dict[str, Any],
        documents_count: int
    ) -> None:
        """记录同步成功日志"""
        async with db_manager.get_session() as session:
            log_entry = SyncLog(
                source_type="confluence",
                source_id=space_config["key"],
                operation="sync",
                status="success",
                message=f"Successfully synced {documents_count} documents",
                documents_count=documents_count
            )
            session.add(log_entry)
            await session.commit()

    async def _log_sync_error(
        self,
        space_config: Dict[str, Any],
        error_message: str
    ) -> None:
        """记录同步错误日志"""
        async with db_manager.get_session() as session:
            log_entry = SyncLog(
                source_type="confluence",
                source_id=space_config.get("key", "unknown"),
                operation="sync",
                status="error",
                message=error_message,
                documents_count=0
            )
            session.add(log_entry)
            await session.commit()