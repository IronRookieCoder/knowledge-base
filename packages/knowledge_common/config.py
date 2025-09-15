"""配置管理模块"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """应用配置类"""

    # 环境配置
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")

    # 数据库配置
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/knowledge_base.db",
        description="数据库连接URL"
    )

    # GitLab配置
    gitlab_url: str = Field(default="", description="GitLab服务器URL")
    gitlab_token: str = Field(default="", description="GitLab访问令牌")

    # Confluence配置
    confluence_url: str = Field(default="", description="Confluence服务器URL")
    confluence_username: str = Field(default="", description="Confluence用户名")
    confluence_token: str = Field(default="", description="Confluence访问令牌")

    # 同步配置
    docs_output_dir: str = Field(
        default="packages/docs/docs",
        description="文档输出目录"
    )
    auto_update_nav: bool = Field(default=True, description="自动更新导航")
    sync_interval: int = Field(default=3600, description="同步间隔(秒)")
    nav_script_path: str = Field(
        default="packages/docs/scripts/update_nav.py",
        description="导航更新脚本路径"
    )

    # API配置
    api_host: str = Field(default="0.0.0.0", description="API服务监听地址")
    api_port: int = Field(default=8080, description="API服务端口")
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS允许的源"
    )
    rate_limit: str = Field(default="100/minute", description="API限流配置")

    # MCP配置
    mcp_host: str = Field(default="0.0.0.0", description="MCP服务监听地址")
    mcp_port: int = Field(default=9000, description="MCP服务端口")
    mcp_max_connections: int = Field(default=100, description="MCP最大连接数")

    # 搜索配置
    search_index_path: str = Field(
        default="data/search_index",
        description="搜索索引存储路径"
    )
    chinese_analyzer: bool = Field(default=True, description="启用中文分析器")
    min_word_len: int = Field(default=1, description="最小单词长度")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[str] = Field(default=None, description="日志文件路径")

    # 文件存储配置
    data_dir: str = Field(default="data", description="数据存储目录")
    upload_dir: str = Field(default="data/uploads", description="上传文件目录")
    max_file_size: int = Field(default=10*1024*1024, description="最大文件大小(字节)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"


# 全局配置实例
settings = AppConfig()


def ensure_data_dirs() -> None:
    """确保数据目录存在"""
    dirs_to_create = [
        settings.data_dir,
        settings.upload_dir,
        settings.docs_output_dir,
        settings.search_index_path,
        os.path.dirname(settings.database_url.replace("sqlite+aiosqlite:///", "")),
    ]

    for dir_path in dirs_to_create:
        if dir_path:
            Path(dir_path).mkdir(parents=True, exist_ok=True)