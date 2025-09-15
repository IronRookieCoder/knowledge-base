"""
本地文档同步器
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..knowledge_common.config import settings
from ..knowledge_common.database import db_manager
from ..knowledge_common.logging import get_logger

logger = get_logger(__name__)


class LocalSyncer:
    """本地文档同步器"""

    def __init__(self):
        self.db = db_manager
        self.search_engine = None

    def _get_search_engine(self):
        """延迟加载搜索引擎"""
        if self.search_engine is None:
            try:
                from ..knowledge_api.search import search_engine
                self.search_engine = search_engine
            except ImportError:
                logger.warning("Search engine not available")
                self.search_engine = None
        return self.search_engine

    async def sync_local_docs(self, config: Dict[str, Any]) -> None:
        """同步本地文档"""
        docs_dir = Path(config.get("docs_dir", settings.docs_output_dir))
        category = config.get("category", settings.default_category)

        if not docs_dir.exists():
            logger.warning(f"Local docs directory not found: {docs_dir}")
            return

        logger.info(f"Starting local docs sync from: {docs_dir}")

        # 扫描本地文档
        markdown_files = list(docs_dir.rglob("*.md"))
        logger.info(f"Found {len(markdown_files)} markdown files")

        synced_count = 0
        for md_file in markdown_files:
            try:
                await self._sync_file(md_file, docs_dir, category)
                synced_count += 1
            except Exception as e:
                logger.error(f"Failed to sync file {md_file}: {e}")

        logger.info(f"Local sync completed: {synced_count}/{len(markdown_files)} files synced")

    async def _sync_file(self, file_path: Path, docs_dir: Path, category: str) -> None:
        """同步单个文档文件"""
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取文档元数据
            metadata = self._extract_metadata(content, file_path)

            # 计算文件哈希
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            # 生成相对路径作为文档ID
            relative_path = file_path.relative_to(docs_dir)
            doc_id = str(relative_path).replace('\\', '/')

            # 获取文件统计信息
            stat = file_path.stat()

            # 检查文档是否已存在且内容未变化
            existing_doc = await self.db.get_document_by_id(doc_id)
            if existing_doc and existing_doc.get('content_hash') == file_hash:
                logger.debug(f"Document unchanged, skipping: {doc_id}")
                return

            # 准备文档数据
            doc_data = {
                'id': doc_id,
                'title': metadata['title'],
                'content': content,
                'content_hash': file_hash,
                'file_path': str(file_path),
                'relative_path': str(relative_path),
                'category': category,
                'source_type': 'local',
                'source_id': str(file_path),
                'author': metadata.get('author', 'Unknown'),
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'updated_at': datetime.fromtimestamp(stat.st_mtime),
                'synced_at': datetime.now(),
                'metadata': metadata
            }

            # 保存到数据库
            if existing_doc:
                await self.db.update_document(doc_id, doc_data)
                logger.info(f"Updated document: {doc_id}")
            else:
                await self.db.create_document(doc_data)
                logger.info(f"Created document: {doc_id}")

            # 更新搜索索引
            await self._update_search_index(doc_data, existing_doc is not None)

            # 记录同步日志
            await self.db.create_sync_log({
                'source_type': 'local',
                'source_id': str(file_path),
                'action': 'update' if existing_doc else 'create',
                'document_id': doc_id,
                'status': 'success',
                'message': f"Synced local file: {relative_path}",
                'synced_at': datetime.now()
            })

        except Exception as e:
            logger.error(f"Failed to sync file {file_path}: {e}")
            # 记录错误日志
            await self.db.create_sync_log({
                'source_type': 'local',
                'source_id': str(file_path),
                'action': 'sync',
                'document_id': doc_id if 'doc_id' in locals() else None,
                'status': 'error',
                'message': f"Failed to sync: {str(e)}",
                'synced_at': datetime.now()
            })
            raise

    def _extract_metadata(self, content: str, file_path: Path) -> Dict[str, Any]:
        """提取文档元数据"""
        metadata = {}

        # 提取标题（第一个 # 标题或文件名）
        lines = content.split('\n')
        title = None

        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                break

        if not title:
            title = file_path.stem.replace('_', ' ').replace('-', ' ').title()

        metadata['title'] = title

        # 尝试提取 YAML front matter
        if content.startswith('---'):
            try:
                end_index = content.find('---', 3)
                if end_index > 0:
                    front_matter = content[3:end_index].strip()
                    import yaml
                    fm_data = yaml.safe_load(front_matter)
                    if isinstance(fm_data, dict):
                        metadata.update(fm_data)
            except Exception as e:
                logger.debug(f"Failed to parse front matter: {e}")

        # 提取其他元数据
        metadata.setdefault('author', 'Unknown')
        metadata.setdefault('description', self._extract_description(content))
        metadata.setdefault('tags', self._extract_tags(content))

        return metadata

    def _extract_description(self, content: str) -> str:
        """提取文档描述"""
        lines = content.split('\n')
        description = ""

        # 跳过标题和空行，获取第一段文本
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                description = line
                break

        # 限制描述长度
        if len(description) > 200:
            description = description[:200] + "..."

        return description

    def _extract_tags(self, content: str) -> List[str]:
        """提取文档标签"""
        tags = []

        # 从内容中提取可能的标签
        lines = content.split('\n')
        for line in lines:
            line = line.strip().lower()
            if 'tags:' in line or 'tag:' in line:
                # 简单的标签提取逻辑
                try:
                    tag_part = line.split(':', 1)[1].strip()
                    if tag_part:
                        # 移除方括号和引号
                        tag_part = tag_part.strip('[]"\'')
                        tags.extend([tag.strip() for tag in tag_part.split(',')])
                except:
                    pass

        return list(set(tags))  # 去重

    async def _update_search_index(self, doc_data: Dict[str, Any], is_update: bool) -> None:
        """更新搜索索引"""
        try:
            search_engine = self._get_search_engine()
            if search_engine is None:
                logger.debug("Search engine not available, skipping index update")
                return

            # 准备搜索索引数据
            search_doc = {
                "id": doc_data['id'],
                "title": doc_data['title'],
                "content": doc_data['content'],
                "category": doc_data['category'],
                "source_type": doc_data['source_type'],
                "author": doc_data['author'],
                "file_path": doc_data['file_path'],
                "created_at": doc_data['created_at'],
                "updated_at": doc_data['updated_at']
            }

            # 使用整数ID（如果有的话）
            try:
                # 从数据库获取数据库生成的ID
                existing_doc = await self.db.get_document_by_id(doc_data['id'])
                if existing_doc and 'id' in existing_doc:
                    search_doc["id"] = existing_doc['id']
            except:
                # 如果获取失败，使用原ID的哈希值作为数字ID
                search_doc["id"] = abs(hash(doc_data['id'])) % (10**9)

            if is_update:
                await search_engine.update_document(search_doc)
                logger.debug(f"Updated search index for document: {doc_data['id']}")
            else:
                await search_engine.add_document(search_doc)
                logger.debug(f"Added to search index: {doc_data['id']}")

        except Exception as e:
            logger.warning(f"Failed to update search index for {doc_data['id']}: {e}")
            # 不要抛出异常，避免影响文档同步