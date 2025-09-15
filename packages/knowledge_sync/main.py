"""
同步服务主入口
"""

import asyncio
import yaml
from pathlib import Path
from typing import Dict, Any

import click

from ..knowledge_common.config import settings
from ..knowledge_common.database import db_manager
from ..knowledge_common.logging import get_logger
from .gitlab_syncer import GitLabSyncer
from .confluence_syncer import ConfluenceSyncer
from .local_syncer import LocalSyncer

logger = get_logger(__name__)


class SyncService:
    """同步服务"""

    def __init__(self):
        self.gitlab_syncer = GitLabSyncer()
        self.confluence_syncer = ConfluenceSyncer()
        self.local_syncer = LocalSyncer()

    async def sync_all(self) -> None:
        """同步所有配置的源"""
        try:
            # 初始化数据库
            await db_manager.create_tables()

            # 加载同步配置
            config = await self._load_sync_config()

            # 同步GitLab项目
            gitlab_projects = config.get("sources", {}).get("gitlab", [])
            if gitlab_projects:
                logger.info("Starting GitLab sync", project_count=len(gitlab_projects))
                await self.gitlab_syncer.sync_projects(gitlab_projects)

            # 同步Confluence空间
            confluence_spaces = config.get("sources", {}).get("confluence", [])
            if confluence_spaces:
                logger.info("Starting Confluence sync", space_count=len(confluence_spaces))
                await self.confluence_syncer.sync_spaces(confluence_spaces)

            # 同步本地文档
            local_config = config.get("sources", {}).get("local", {})
            if local_config:
                logger.info("Starting local docs sync")
                await self.local_syncer.sync_local_docs(local_config)

            # 更新导航（如果启用）
            if settings.sync.auto_update_nav:
                await self._update_navigation()

            logger.info("Sync completed successfully")

        except Exception as e:
            logger.error("Sync failed", error=str(e))
            raise

    async def _load_sync_config(self) -> Dict[str, Any]:
        """加载同步配置"""
        config_file = Path("config/sources.yml")
        if not config_file.exists():
            logger.warning("Sync config file not found, using default config")
            return self._get_default_config()

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error("Failed to load sync config", error=str(e))
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "sources": {
                "gitlab": [],
                "confluence": [],
                "local": {
                    "docs_dir": "packages/docs/docs",
                    "category": "docs"
                }
            }
        }

    async def _update_navigation(self) -> None:
        """更新导航"""
        try:
            nav_script = Path(settings.sync.nav_script_path)
            if nav_script.exists():
                logger.info("Updating navigation")
                import subprocess
                result = subprocess.run(
                    ["python", str(nav_script)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.info("Navigation updated successfully")
                else:
                    logger.warning(
                        "Navigation update failed",
                        stderr=result.stderr
                    )
            else:
                logger.warning("Navigation script not found", script_path=str(nav_script))
        except Exception as e:
            logger.error("Failed to update navigation", error=str(e))


@click.group()
def cli():
    """知识库同步服务"""
    pass


@cli.command()
@click.option("--config", "-c", help="配置文件路径")
def sync(config):
    """执行同步"""
    async def run_sync():
        service = SyncService()
        await service.sync_all()

    asyncio.run(run_sync())


@cli.command()
@click.option("--project-id", required=True, type=int, help="GitLab项目ID")
@click.option("--docs-path", default="docs/", help="文档目录路径")
@click.option("--branch", default="main", help="分支名称")
@click.option("--target-path", help="目标路径")
@click.option("--category", default="general", help="文档分类")
def sync_gitlab(project_id, docs_path, branch, target_path, category):
    """同步单个GitLab项目"""
    async def run_gitlab_sync():
        syncer = GitLabSyncer()
        project_config = {
            "project_id": project_id,
            "docs_path": docs_path,
            "branch": branch,
            "target_path": target_path or f"project-{project_id}/",
            "category": category
        }
        await syncer.sync_projects([project_config])

    asyncio.run(run_gitlab_sync())


@cli.command()
@click.option("--space-key", required=True, help="Confluence空间键")
@click.option("--space-name", help="空间名称")
@click.option("--target-path", help="目标路径")
@click.option("--category", default="confluence", help="文档分类")
@click.option("--include-attachments", is_flag=True, help="包含附件")
def sync_confluence(space_key, space_name, target_path, category, include_attachments):
    """同步单个Confluence空间"""
    async def run_confluence_sync():
        syncer = ConfluenceSyncer()
        space_config = {
            "key": space_key,
            "name": space_name or space_key,
            "target_path": target_path or f"confluence-{space_key}/",
            "category": category,
            "include_attachments": include_attachments
        }
        await syncer.sync_spaces([space_config])

    asyncio.run(run_confluence_sync())


@cli.command()
def init_db():
    """初始化数据库"""
    async def run_init():
        await db_manager.create_tables()
        logger.info("Database initialized successfully")

    asyncio.run(run_init())


def main():
    """主入口函数"""
    cli()


if __name__ == "__main__":
    main()