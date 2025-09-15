"""日志配置模块"""

import sys
import logging
import io
from pathlib import Path
from typing import Optional
import structlog
from structlog.stdlib import LoggerFactory

from .config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    service_name: Optional[str] = None,
) -> None:
    """设置结构化日志"""
    level = log_level or settings.log_level
    file_path = log_file or settings.log_file

    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.environment == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 配置标准logging - 解决Windows中文编码问题
    # 确保stdout使用UTF-8编码
    if sys.platform.startswith('win'):
        # Windows系统需要特殊处理编码
        stdout_handler = logging.StreamHandler(
            io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        )
    else:
        stdout_handler = logging.StreamHandler(sys.stdout)

    stdout_handler.setLevel(getattr(logging, level.upper()))
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))

    # 清除现有handler避免重复
    logging.getLogger().handlers.clear()
    logging.getLogger().addHandler(stdout_handler)
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    # 配置文件日志
    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))

        if settings.environment == "production":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

    # 添加服务名称到日志上下文
    if service_name:
        structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取结构化日志器"""
    return structlog.get_logger(name)


# 默认设置日志
setup_logging()

# 导出默认日志器
logger = get_logger(__name__)