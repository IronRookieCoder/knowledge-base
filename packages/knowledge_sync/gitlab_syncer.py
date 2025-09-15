"""
GitLab文档同步器
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import gitlab
from git import Repo, InvalidGitRepositoryError
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


class GitLabSyncer:
    """GitLab文档同步器"""

    def __init__(self):
        self.gitlab_client = gitlab.Gitlab(
            settings.gitlab.url,
            private_token=settings.gitlab.token
        )
        self.output_dir = Path(settings.sync.docs_output_dir)
        ensure_directory(self.output_dir)

    async def sync_projects(self, projects_config: List[Dict[str, Any]]) -> None:
        """同步多个项目的文档"""
        for project_config in projects_config:
            try:
                await self._sync_single_project(project_config)
            except Exception as e:
                logger.error(
                    "Failed to sync project",
                    project_id=project_config.get("project_id"),
                    error=str(e)
                )
                await self._log_sync_error(project_config, str(e))

    async def _sync_single_project(self, project_config: Dict[str, Any]) -> None:
        """同步单个项目的文档"""
        project_id = project_config["project_id"]
        docs_path = project_config.get("docs_path", "docs/")
        branch = project_config.get("branch", "main")
        target_path = project_config.get("target_path", f"project-{project_id}/")
        category = project_config.get("category", "general")

        logger.info(
            "Starting sync for project",
            project_id=project_id,
            branch=branch,
            target_path=target_path
        )

        try:
            # 获取项目
            project = self.gitlab_client.projects.get(project_id)

            # 克隆或更新仓库
            local_repo_path = await self._clone_or_update_repository(project, branch)

            # 扫描文档目录
            docs_dir = local_repo_path / docs_path
            if not docs_dir.exists():
                logger.warning(
                    "Docs directory not found",
                    project_id=project_id,
                    docs_path=str(docs_dir)
                )
                return

            documents = await self._scan_documents(docs_dir, project, category)

            # 处理文档
            synced_count = await self._process_documents(
                documents,
                target_path,
                project_id,
                category
            )

            logger.info(
                "Sync completed for project",
                project_id=project_id,
                synced_documents=synced_count
            )

            await self._log_sync_success(project_config, synced_count)

        except Exception as e:
            logger.error(
                "Error syncing project",
                project_id=project_id,
                error=str(e)
            )
            raise

    async def _clone_or_update_repository(self, project, branch: str) -> Path:
        """克隆或更新仓库"""
        repo_dir = Path("temp") / "repos" / str(project.id)
        ensure_directory(repo_dir.parent)

        try:
            if repo_dir.exists() and (repo_dir / ".git").exists():
                # 更新现有仓库
                repo = Repo(str(repo_dir))
                origin = repo.remotes.origin
                origin.fetch()

                # 切换到指定分支
                if branch in [ref.name.split('/')[-1] for ref in repo.refs]:
                    repo.git.checkout(branch)
                    origin.pull()
                else:
                    logger.warning(
                        "Branch not found, using default",
                        project_id=project.id,
                        branch=branch
                    )
            else:
                # 克隆新仓库
                if repo_dir.exists():
                    import shutil
                    shutil.rmtree(repo_dir)

                clone_url = project.http_url_to_repo
                if settings.gitlab.token:
                    # 使用token进行身份验证
                    clone_url = clone_url.replace(
                        "https://",
                        f"https://oauth2:{settings.gitlab.token}@"
                    )

                repo = Repo.clone_from(clone_url, str(repo_dir), branch=branch)

            return repo_dir

        except Exception as e:
            logger.error(
                "Failed to clone/update repository",
                project_id=project.id,
                error=str(e)
            )
            raise

    async def _scan_documents(
        self,
        docs_dir: Path,
        project,
        category: str
    ) -> List[Dict[str, Any]]:
        """扫描文档目录"""
        documents = []

        for file_path in docs_dir.rglob("*.md"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    metadata = extract_markdown_metadata(content)
                    clean_content = clean_markdown_content(content)

                    # 获取文件相对路径
                    relative_path = file_path.relative_to(docs_dir)

                    # 获取Git信息
                    git_info = await self._get_git_file_info(file_path, project)

                    document = {
                        "title": metadata.get("title", file_path.stem),
                        "content": clean_content,
                        "file_path": str(relative_path),
                        "source_type": "gitlab",
                        "source_id": f"{project.id}:{relative_path}",
                        "category": category,
                        "author": git_info.get("author"),
                        "version": git_info.get("version"),
                        "file_hash": get_file_hash(file_path),
                        "updated_at": git_info.get("updated_at", datetime.utcnow()),
                        "metadata": metadata,
                        "local_path": file_path
                    }

                    documents.append(document)

                except Exception as e:
                    logger.warning(
                        "Failed to process document",
                        file_path=str(file_path),
                        error=str(e)
                    )

        return documents

    async def _get_git_file_info(self, file_path: Path, project) -> Dict[str, Any]:
        """获取文件的Git信息"""
        try:
            repo = Repo(str(file_path.parents[2]))  # 假设在docs目录下两级

            # 获取文件的最后提交信息
            commits = list(repo.iter_commits(paths=str(file_path), max_count=1))
            if commits:
                commit = commits[0]
                return {
                    "author": commit.author.name,
                    "version": commit.hexsha[:8],
                    "updated_at": datetime.fromtimestamp(commit.committed_date)
                }
        except Exception as e:
            logger.warning(
                "Failed to get git info",
                file_path=str(file_path),
                error=str(e)
            )

        return {}

    async def _process_documents(
        self,
        documents: List[Dict[str, Any]],
        target_path: str,
        project_id: int,
        category: str
    ) -> int:
        """处理文档，保存到数据库和文件系统"""
        synced_count = 0

        async with db_manager.get_session() as session:
            for doc_data in documents:
                try:
                    # 检查文档是否已存在
                    existing_doc = await self._find_existing_document(
                        session,
                        doc_data["source_id"]
                    )

                    if existing_doc:
                        # 检查是否需要更新
                        if existing_doc.file_hash != doc_data["file_hash"]:
                            await self._update_document(session, existing_doc, doc_data)
                            synced_count += 1
                    else:
                        # 创建新文档
                        await self._create_document(session, doc_data)
                        synced_count += 1

                    # 复制文件到目标目录
                    await self._copy_document_file(doc_data, target_path)

                except Exception as e:
                    logger.error(
                        "Failed to process document",
                        source_id=doc_data["source_id"],
                        error=str(e)
                    )

            await session.commit()

        return synced_count

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

    async def _copy_document_file(
        self,
        doc_data: Dict[str, Any],
        target_path: str
    ) -> None:
        """复制文档文件到目标目录"""
        source_file = doc_data["local_path"]
        target_dir = self.output_dir / target_path
        ensure_directory(target_dir)

        target_file = target_dir / doc_data["file_path"]
        ensure_directory(target_file.parent)

        # 复制文件
        target_file.write_text(
            doc_data["content"],
            encoding="utf-8"
        )

    async def _log_sync_success(
        self,
        project_config: Dict[str, Any],
        documents_count: int
    ) -> None:
        """记录同步成功日志"""
        async with db_manager.get_session() as session:
            log_entry = SyncLog(
                source_type="gitlab",
                source_id=str(project_config["project_id"]),
                operation="sync",
                status="success",
                message=f"Successfully synced {documents_count} documents",
                documents_count=documents_count
            )
            session.add(log_entry)
            await session.commit()

    async def _log_sync_error(
        self,
        project_config: Dict[str, Any],
        error_message: str
    ) -> None:
        """记录同步错误日志"""
        async with db_manager.get_session() as session:
            log_entry = SyncLog(
                source_type="gitlab",
                source_id=str(project_config.get("project_id", "unknown")),
                operation="sync",
                status="error",
                message=error_message,
                documents_count=0
            )
            session.add(log_entry)
            await session.commit()