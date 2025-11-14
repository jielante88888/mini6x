"""
Redis缓存管理器
提供连接池、缓存管理和数据序列化功能
"""

import json
import asyncio
from typing import Optional, Any, Union, Dict, List
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.exceptions import ConnectionError, TimeoutError

from ..config import settings
import structlog

logger = structlog.get_logger()

# 全局Redis连接实例
_redis_client: Optional[Redis] = None
_connection_pool: Optional[redis.ConnectionPool] = None


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.key_prefix = "crypto_trading:"
        self.default_ttl = 300  # 5分钟默认TTL
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键"""
        return f"{self.key_prefix}{key}"
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        json_encode: bool = True
    ) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)
            json_encode: 是否使用JSON编码
        """
        try:
            redis_key = self._make_key(key)
            
            if json_encode and value is not None:
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized_value = str(value)
            
            if ttl:
                await self.redis.setex(redis_key, ttl, serialized_value)
            else:
                await self.redis.set(redis_key, serialized_value)
            
            logger.debug(f"缓存设置成功: {key}")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {key} - {e}")
            return False
        except Exception as e:
            logger.error(f"Redis设置错误: {key} - {e}")
            return False
    
    async def get(
        self, 
        key: str, 
        default: Any = None,
        json_decode: bool = True
    ) -> Any:
        """获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            json_decode: 是否使用JSON解码
        """
        try:
            redis_key = self._make_key(key)
            value = await self.redis.get(redis_key)
            
            if value is None:
                logger.debug(f"缓存未找到: {key}")
                return default
            
            if json_decode:
                try:
                    decoded_value = json.loads(value.decode('utf-8'))
                    logger.debug(f"缓存获取成功: {key}")
                    return decoded_value
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 如果JSON解码失败，返回原始字符串
                    return value.decode('utf-8') if isinstance(value, bytes) else str(value)
            else:
                return value.decode('utf-8') if isinstance(value, bytes) else str(value)
                
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {key} - {e}")
            return default
        except Exception as e:
            logger.error(f"Redis获取错误: {key} - {e}")
            return default
    
    async def delete(self, *keys: str) -> int:
        """删除缓存键"""
        try:
            redis_keys = [self._make_key(key) for key in keys]
            deleted_count = await self.redis.delete(*redis_keys)
            logger.debug(f"缓存删除成功: {len(redis_keys)} 个键")
            return deleted_count
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {e}")
            return 0
        except Exception as e:
            logger.error(f"Redis删除错误: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        try:
            redis_key = self._make_key(key)
            exists = await self.redis.exists(redis_key)
            logger.debug(f"缓存检查: {key} - {'存在' if exists else '不存在'}")
            return bool(exists)
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {key} - {e}")
            return False
        except Exception as e:
            logger.error(f"Redis检查错误: {key} - {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间"""
        try:
            redis_key = self._make_key(key)
            result = await self.redis.expire(redis_key, ttl)
            logger.debug(f"缓存过期时间设置: {key} - {ttl}秒")
            return result
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {key} - {e}")
            return False
        except Exception as e:
            logger.error(f"Redis过期时间设置错误: {key} - {e}")
            return False
    
    async def ping(self) -> bool:
        """测试Redis连接"""
        try:
            result = await self.redis.ping()
            logger.debug("Redis连接测试: ping成功")
            return result
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接测试失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis ping错误: {e}")
            return False
    
    # 批量操作
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存"""
        try:
            redis_mapping = {}
            for key, value in mapping.items():
                redis_key = self._make_key(key)
                if value is not None:
                    redis_mapping[redis_key] = json.dumps(value, ensure_ascii=False, default=str)
                else:
                    redis_mapping[redis_key] = str(value)
            
            if ttl:
                # 如果有TTL，使用pipeline执行
                pipeline = self.redis.pipeline()
                for key, value in redis_mapping.items():
                    pipeline.setex(key, ttl, value)
                await pipeline.execute()
            else:
                await self.redis.mset(redis_mapping)
            
            logger.debug(f"批量缓存设置成功: {len(mapping)} 个键")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis批量设置错误: {e}")
            return False
    
    async def mget(self, keys: List[str], default: Any = None) -> Dict[str, Any]:
        """批量获取缓存"""
        try:
            redis_keys = [self._make_key(key) for key in keys]
            values = await self.redis.mget(redis_keys)
            
            result = {}
            for i, key in enumerate(keys):
                if i < len(values) and values[i] is not None:
                    try:
                        decoded_value = json.loads(values[i].decode('utf-8'))
                        result[key] = decoded_value
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result[key] = values[i].decode('utf-8') if isinstance(values[i], bytes) else str(values[i])
                else:
                    result[key] = default
            
            logger.debug(f"批量缓存获取成功: {len(result)} 个键")
            return result
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis连接错误: {e}")
            return {key: default for key in keys}
        except Exception as e:
            logger.error(f"Redis批量获取错误: {e}")
            return {key: default for key in keys}


class MarketDataCache:
    """市场数据专用缓存管理器"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.market_prefix = "market_data:"
    
    async def cache_market_data(self, exchange: str, market_type: str, symbol: str, data: Dict[str, Any]) -> bool:
        """缓存市场数据"""
        key = f"{self.market_prefix}{exchange}:{market_type}:{symbol}"
        return await self.cache.set(key, data, ttl=30)  # 30秒缓存
    
    async def get_market_data(self, exchange: str, market_type: str, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据缓存"""
        key = f"{self.market_prefix}{exchange}:{market_type}:{symbol}"
        return await self.cache.get(key)
    
    async def cache_klines(self, exchange: str, symbol: str, interval: str, klines: List[Dict[str, Any]]) -> bool:
        """缓存K线数据"""
        key = f"klines:{exchange}:{symbol}:{interval}"
        return await self.cache.set(key, klines, ttl=300)  # 5分钟缓存
    
    async def get_klines(self, exchange: str, symbol: str, interval: str) -> Optional[List[Dict[str, Any]]]:
        """获取K线数据缓存"""
        key = f"klines:{exchange}:{symbol}:{interval}"
        return await self.cache.get(key)


class UserSessionCache:
    """用户会话缓存管理器"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.session_prefix = "session:"
    
    async def cache_user_session(self, user_id: int, session_data: Dict[str, Any]) -> bool:
        """缓存用户会话"""
        key = f"{self.session_prefix}user:{user_id}"
        return await self.cache.set(key, session_data, ttl=3600)  # 1小时缓存
    
    async def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户会话"""
        key = f"{self.session_prefix}user:{user_id}"
        return await self.cache.get(key)
    
    async def clear_user_session(self, user_id: int) -> bool:
        """清除用户会话"""
        key = f"{self.session_prefix}user:{user_id}"
        return await self.cache.delete(key)


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None
_market_cache: Optional[MarketDataCache] = None
_session_cache: Optional[UserSessionCache] = None


def get_cache_manager() -> Optional[CacheManager]:
    """获取全局缓存管理器"""
    return _cache_manager


def get_market_cache() -> Optional[MarketDataCache]:
    """获取市场数据缓存管理器"""
    return _market_cache


def get_session_cache() -> Optional[UserSessionCache]:
    """获取用户会话缓存管理器"""
    return _session_cache


async def init_redis() -> bool:
    """初始化Redis连接"""
    global _redis_client, _connection_pool, _cache_manager, _market_cache, _session_cache
    
    try:
        # 创建连接池
        redis_url = settings.REDIS_URL
        _connection_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            retry_on_timeout=True,
            socket_timeout=30,
            socket_connect_timeout=30,
        )
        
        # 创建Redis客户端
        _redis_client = redis.Redis(
            connection_pool=_connection_pool,
            decode_responses=False,  # 我们手动处理解码
        )
        
        # 测试连接
        if await _redis_client.ping():
            logger.info("Redis连接成功")
            
            # 创建缓存管理器
            _cache_manager = CacheManager(_redis_client)
            _market_cache = MarketDataCache(_cache_manager)
            _session_cache = UserSessionCache(_cache_manager)
            
            logger.info("Redis缓存管理器初始化完成")
            return True
        else:
            logger.error("Redis ping失败")
            return False
            
    except Exception as e:
        logger.error(f"Redis初始化失败: {e}")
        return False


async def close_redis():
    """关闭Redis连接"""
    global _redis_client, _connection_pool
    
    try:
        if _redis_client:
            await _redis_client.close()
        
        if _connection_pool:
            await _connection_pool.disconnect()
        
        logger.info("Redis连接已关闭")
        
    except Exception as e:
        logger.error(f"Redis连接关闭错误: {e}")


@asynccontextmanager
async def redis_context():
    """Redis上下文管理器"""
    try:
        if not _redis_client or not await _redis_client.ping():
            await init_redis()
        
        yield _redis_client
        
    except Exception as e:
        logger.error(f"Redis上下文错误: {e}")
        raise


if __name__ == "__main__":
    # 测试Redis连接
    import asyncio
    
    async def test_redis():
        print("测试Redis连接...")
        
        # 测试初始化
        success = await init_redis()
        if not success:
            print("❌ Redis初始化失败")
            return
        
        # 测试基本操作
        cache = get_cache_manager()
        if cache:
            # 测试设置和获取
            await cache.set("test_key", {"message": "Hello Redis!", "timestamp": "2025-11-14"})
            value = await cache.get("test_key")
            print(f"✅ 测试数据: {value}")
            
            # 测试市场数据缓存
            market_cache = get_market_cache()
            if market_cache:
                market_data = {
                    "symbol": "BTCUSDT",
                    "price": 43250.00,
                    "change": 1.25,
                    "volume": 1500000
                }
                await market_cache.cache_market_data("binance", "spot", "BTCUSDT", market_data)
                cached_data = await market_cache.get_market_data("binance", "spot", "BTCUSDT")
                print(f"✅ 市场数据: {cached_data}")
        
        await close_redis()
        print("✅ Redis测试完成")
    
    asyncio.run(test_redis())