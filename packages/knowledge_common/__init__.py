"""知识库共享模块"""

__version__ = "1.0.0"

from .config import settings, AppConfig
from .database import DatabaseManager, get_db
from .logging import setup_logging, get_logger
from .models import BaseModel, DocumentModel, CategoryModel

__all__ = [
    "settings",
    "AppConfig",
    "DatabaseManager",
    "get_db",
    "setup_logging",
    "get_logger",
    "BaseModel",
    "DocumentModel",
    "CategoryModel",
]