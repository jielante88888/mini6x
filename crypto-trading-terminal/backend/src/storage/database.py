"""
数据库连接和会话管理
支持SQLite和PostgreSQL的动态配置
"""

from typing import Generator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from ..config import settings
from .models import Base

# 同步引擎
_engine = None
_session_factory = None

# 异步引擎
_async_engine = None
_async_session_factory = None


def get_engine():
    """获取数据库引擎"""
    global _engine, _session_factory
    
    if _engine is not None:
        return _engine
    
    # 根据DATABASE_URL决定使用哪个数据库
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite配置
        _engine = create_engine(
            settings.DATABASE_URL,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
            echo=False,
        )
    elif settings.DATABASE_URL.startswith("postgresql"):
        # PostgreSQL配置
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=False,
        )
    else:
        # 默认使用SQLite
        _engine = create_engine("sqlite:///./crypto_trading.db")
    
    _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    return _engine


def get_async_engine():
    """获取异步数据库引擎"""
    global _async_engine, _async_session_factory
    
    if _async_engine is not None:
        return _async_engine
    
    # 转换同步URL为异步URL
    sync_url = settings.DATABASE_URL
    
    if sync_url.startswith("sqlite"):
        # SQLite异步URL
        async_url = sync_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        connect_args = {"check_same_thread": False}
    elif sync_url.startswith("postgresql"):
        # PostgreSQL异步URL
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        connect_args = {}
    else:
        # 默认异步URL
        async_url = "sqlite+aiosqlite:///./crypto_trading.db"
        connect_args = {"check_same_thread": False}
    
    try:
        _async_engine = create_async_engine(
            async_url,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            pool_pre_ping=True,
            connect_args=connect_args,
            echo=False,
        )
        _async_session_factory = async_sessionmaker(
            bind=_async_engine, class_=AsyncSession, expire_on_commit=False
        )
    except ImportError:
        # 如果异步驱动不可用，回退到同步
        print("警告: 异步数据库驱动不可用，使用同步模式")
        _async_engine = None
        _async_session_factory = None
    
    return _async_engine


def create_tables():
    """创建所有表"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def create_tables_async():
    """异步创建所有表"""
    engine = get_async_engine()
    if engine is not None:
        import asyncio
        asyncio.run(_create_tables_async())


async def _create_tables_async():
    """实际异步创建表的实现"""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> Generator:
    """获取数据库会话"""
    factory = _session_factory or get_engine()._session_factory
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Generator:
    """获取数据库会话的别名"""
    return get_session()


@asynccontextmanager
async def get_async_session():
    """获取异步数据库会话"""
    factory = _async_session_factory or get_async_engine()._session_factory
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# 数据库事件监听器
@event.listens_for(get_engine() or object, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """为SQLite设置性能优化参数"""
    if hasattr(dbapi_connection, 'cursor'):
        cursor = dbapi_connection.cursor()
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys=ON")
        # 启用WAL模式以提高并发性能
        cursor.execute("PRAGMA journal_mode=WAL")
        # 增加缓存大小
        cursor.execute("PRAGMA cache_size=10000")
        cursor.close()


@event.listens_for(get_engine() or object, "connect")
def set_postgres_pragma(dbapi_connection, connection_record):
    """为PostgreSQL设置性能优化参数"""
    if hasattr(dbapi_connection, 'cursor'):
        cursor = dbapi_connection.cursor()
        # 设置时区
        cursor.execute("SET timezone = 'UTC'")
        cursor.close()


# 初始化函数
def init_database():
    """初始化数据库连接"""
    engine = get_engine()
    
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    print(f"数据库初始化完成: {settings.DATABASE_URL}")


def close_database():
    """关闭数据库连接"""
    if _engine is not None:
        _engine.dispose()
    
    if _async_engine is not None:
        import asyncio
        asyncio.run(_async_engine.dispose())


if __name__ == "__main__":
    # 测试数据库连接
    from ..config import settings
    
    print("测试数据库连接...")
    print(f"数据库URL: {settings.DATABASE_URL}")
    
    try:
        engine = get_engine()
        connection = engine.connect()
        print("✅ 数据库连接成功")
        connection.close()
        
        # 测试表创建
        create_tables()
        print("✅ 数据库表创建成功")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")