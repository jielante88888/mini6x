"""
FastAPI应用程序的核心模块
包含应用初始化、配置和主要功能模块
"""

from .config import settings
from .main import app, lifespan
from .storage.database import get_db_session, init_database, close_database
from .storage.redis_cache import init_redis, close_redis, get_cache_manager
from .utils.exceptions import (
    BaseAPIException, 
    ValidationError, 
    AuthenticationError,
    handle_exception
)

__all__ = [
    "settings",
    "app", 
    "lifespan",
    "get_db_session",
    "init_database", 
    "close_database",
    "init_redis",
    "close_redis",
    "get_cache_manager",
    "BaseAPIException",
    "ValidationError",
    "AuthenticationError",
    "handle_exception"
]