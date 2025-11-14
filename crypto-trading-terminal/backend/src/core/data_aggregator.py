"""
数据聚合器
负责从多个交易所获取数据并统一处理
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set, AsyncGenerator, Any, Callable
from contextlib import asynccontextmanager
import weakref

import structlog

from ..adapters.base import (
    BaseExchangeAdapter, MarketData, OrderBook, Trade, ExchangeAdapterFactory,
    MarketType, Exchange
)
from ..storage.redis_cache import get_market_cache, MarketDataCache
from ..storage.models import MarketData as MarketDataModel
from ..utils.exceptions import DataAggregationError, ExchangeConnectionError

logger = structlog.get_logger(__name__)


class DataAggregator:
    """数据聚合器"""
    
    def __init__(self):
        self.adapters: Dict[str, BaseExchangeAdapter] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.data_cache: Dict[str, MarketData] = {}
        self.is_running = False
        self.cache_manager = get_market_cache()
        
        # 数据更新统计
        self.update_stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None
        }
    
    async def initialize(self) -> None:
        """初始化数据聚合器"""
        try:
            logger.info("初始化数据聚合器...")
            
            # 创建交易所适配器实例
            await self._initialize_adapters()
            
            # 建立连接测试
            await self._test_connections()
            
            self.is_running = True
            logger.info("数据聚合器初始化完成")
            
        except Exception as e:
            logger.error(f"数据聚合器初始化失败: {e}")
            raise DataAggregationError(f"初始化失败: {e}")
    
    async def _initialize_adapters(self) -> None:
        """初始化交易所适配器"""
        supported_exchanges = ExchangeAdapterFactory.get_supported_exchanges()
        
        for exchange_type in supported_exchanges:
            try:
                adapter = ExchangeAdapterFactory.create_adapter(
                    exchange_type, 
                    is_testnet=True
                )
                
                self.adapters[exchange_type] = adapter
                logger.info(f"已初始化 {exchange_type} 适配器")
                
            except Exception as e:
                logger.warning(f"初始化 {exchange_type} 适配器失败: {e}")
    
    async def _test_connections(self) -> None:
        """测试交易所连接"""
        connection_results = {}
        
        for exchange_type, adapter in self.adapters.items():
            try:
                connected = await adapter.connect()
                connection_results[exchange_type] = connected
                
                if connected:
                    logger.info(f"✅ {exchange_type} 连接成功")
                else:
                    logger.warning(f"❌ {exchange_type} 连接失败")
                    
            except Exception as e:
                logger.error(f"{exchange_type} 连接测试异常: {e}")
                connection_results[exchange_type] = False
        
        # 检查是否有可用连接
        available_connections = [k for k, v in connection_results.items() if v]
        
        if not available_connections:
            raise DataAggregationError("没有可用的交易所连接")
        
        logger.info(f"可用交易所连接: {available_connections}")
    
    async def get_market_data(self, exchange: str, market_type: str, symbol: str) -> Optional[MarketData]:
        """获取市场数据"""
        try:
            exchange_key = f"{exchange}_{market_type}"
            
            # 检查缓存
            cache_key = f"{exchange_key}:{symbol}"
            cached_data = self.data_cache.get(cache_key)
            
            if cached_data:
                logger.debug(f"使用缓存数据: {cache_key}")
                return cached_data
            
            # 从适配器获取数据
            if exchange_key not in self.adapters:
                raise DataAggregationError(f"不支持的交易所: {exchange_key}")
            
            adapter = self.adapters[exchange_key]
            
            if market_type.lower() == "spot":
                data = await adapter.get_spot_ticker(symbol)
            elif market_type.lower() == "futures":
                data = await adapter.get_futures_ticker(symbol)
            else:
                raise DataAggregationError(f"不支持的市场类型: {market_type}")
            
            # 缓存数据
            self.data_cache[cache_key] = data
            
            # 更新Redis缓存
            if self.cache_manager:
                await self.cache_manager.cache_market_data(
                    exchange, market_type, symbol, self._market_data_to_dict(data)
                )
            
            logger.debug(f"获取市场数据成功: {exchange_key}:{symbol}")
            return data
            
        except Exception as e:
            logger.error(f"获取市场数据失败 {exchange}:{market_type}:{symbol}: {e}")
            raise DataAggregationError(f"数据获取失败: {e}")
    
    async def get_multiple_market_data(
        self, 
        exchange: str, 
        market_type: str, 
        symbols: List[str]
    ) -> Dict[str, Optional[MarketData]]:
        """批量获取市场数据"""
        results = {}
        
        for symbol in symbols:
            try:
                data = await self.get_market_data(exchange, market_type, symbol)
                results[symbol] = data
            except Exception as e:
                logger.warning(f"批量获取 {symbol} 数据失败: {e}")
                results[symbol] = None
        
        return results
    
    async def get_all_supported_symbols(self) -> Dict[str, List[str]]:
        """获取所有支持的交易对"""
        symbols_dict = {}
        
        for exchange_key, adapter in self.adapters.items():
            try:
                # 获取适配器支持的交易对
                if hasattr(adapter, '_supported_symbols'):
                    symbols = adapter._supported_symbols
                else:
                    # 如果适配器没有缓存，使用默认列表
                    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
                
                symbols_dict[exchange_key] = symbols
                logger.info(f"{exchange_key} 支持 {len(symbols)} 个交易对")
                
            except Exception as e:
                logger.warning(f"获取 {exchange_key} 支持的交易对失败: {e}")
                symbols_dict[exchange_key] = []
        
        return symbols_dict
    
    async def subscribe_market_data(
        self, 
        exchange: str, 
        market_type: str, 
        symbol: str, 
        callback: Callable[[MarketData], None]
    ) -> None:
        """订阅实时市场数据"""
        subscription_key = f"{exchange}_{market_type}_{symbol}"
        
        if subscription_key not in self.subscribers:
            self.subscribers[subscription_key] = []
            # 启动订阅
            asyncio.create_task(self._start_subscription(subscription_key, exchange, market_type, symbol))
        
        self.subscribers[subscription_key].append(callback)
        logger.info(f"已订阅市场数据: {subscription_key}")
    
    async def unsubscribe_market_data(
        self, 
        exchange: str, 
        market_type: str, 
        symbol: str, 
        callback: Callable[[MarketData], None]
    ) -> None:
        """取消订阅市场数据"""
        subscription_key = f"{exchange}_{market_type}_{symbol}"
        
        if subscription_key in self.subscribers and callback in self.subscribers[subscription_key]:
            self.subscribers[subscription_key].remove(callback)
            
            # 如果没有订阅者，停止订阅
            if not self.subscribers[subscription_key]:
                del self.subscribers[subscription_key]
                logger.info(f"已取消订阅: {subscription_key}")
    
    async def _start_subscription(
        self, 
        subscription_key: str, 
        exchange: str, 
        market_type: str, 
        symbol: str
    ) -> None:
        """启动数据订阅"""
        try:
            exchange_key = f"{exchange}_{market_type}"
            
            if exchange_key not in self.adapters:
                return
            
            adapter = self.adapters[exchange_key]
            
            # 根据市场类型选择订阅方法
            if market_type.lower() == "spot":
                stream = adapter.subscribe_spot_ticker(symbol)
            elif market_type.lower() == "futures":
                stream = adapter.subscribe_futures_ticker(symbol)
            else:
                return
            
            logger.info(f"开始订阅 {subscription_key}")
            
            async for data in stream:
                # 更新缓存
                self.data_cache[f"{exchange_key}:{symbol}"] = data
                
                # 更新Redis缓存
                if self.cache_manager:
                    await self.cache_manager.cache_market_data(
                        exchange, market_type, symbol, self._market_data_to_dict(data)
                    )
                
                # 通知订阅者
                if subscription_key in self.subscribers:
                    for callback in self.subscribers[subscription_key]:
                        try:
                            await self._safe_callback(callback, data)
                        except Exception as e:
                            logger.warning(f"订阅者回调执行失败: {e}")
                
                # 更新统计
                self.update_stats["total_updates"] += 1
                self.update_stats["successful_updates"] += 1
                self.update_stats["last_update_time"] = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"订阅 {subscription_key} 失败: {e}")
            self.update_stats["total_updates"] += 1
            self.update_stats["failed_updates"] += 1
    
    async def _safe_callback(self, callback: Callable, data: MarketData) -> None:
        """安全执行回调函数"""
        if asyncio.iscoroutinefunction(callback):
            await callback(data)
        else:
            callback(data)
    
    def _market_data_to_dict(self, market_data: MarketData) -> Dict[str, Any]:
        """将MarketData对象转换为字典"""
        return {
            "symbol": market_data.symbol,
            "current_price": float(market_data.current_price),
            "previous_close": float(market_data.previous_close),
            "high_24h": float(market_data.high_24h),
            "low_24h": float(market_data.low_24h),
            "price_change": float(market_data.price_change),
            "price_change_percent": float(market_data.price_change_percent),
            "volume_24h": float(market_data.volume_24h),
            "quote_volume_24h": float(market_data.quote_volume_24h),
            "timestamp": market_data.timestamp.isoformat(),
            "exchange": getattr(market_data, 'exchange', 'unknown'),
            "market_type": getattr(market_data, 'market_type', 'unknown')
        }
    
    async def get_aggregated_data(
        self, 
        market_type: str, 
        symbols: List[str]
    ) -> Dict[str, Dict[str, Optional[MarketData]]]:
        """聚合多交易所数据"""
        aggregated = {}
        
        for symbol in symbols:
            symbol_data = {}
            
            for exchange_key in self.adapters.keys():
                exchange, _ = exchange_key.split('_', 1)
                
                try:
                    data = await self.get_market_data(exchange, market_type, symbol)
                    symbol_data[exchange] = data
                except Exception as e:
                    logger.warning(f"聚合数据失败 {exchange}:{symbol}: {e}")
                    symbol_data[exchange] = None
            
            aggregated[symbol] = symbol_data
        
        return aggregated
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy" if self.is_running else "stopped",
            "adapters": {},
            "subscriptions": len(self.subscribers),
            "cache_size": len(self.data_cache),
            "stats": self.update_stats
        }
        
        for exchange_key, adapter in self.adapters.items():
            try:
                is_healthy = await adapter.is_healthy()
                health_status["adapters"][exchange_key] = {
                    "healthy": is_healthy,
                    "status": "online" if is_healthy else "offline"
                }
            except Exception as e:
                health_status["adapters"][exchange_key] = {
                    "healthy": False,
                    "status": "error",
                    "error": str(e)
                }
        
        return health_status
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("清理数据聚合器资源...")
            
            # 关闭所有适配器连接
            for adapter in self.adapters.values():
                await adapter.disconnect()
            
            # 清理缓存
            self.data_cache.clear()
            self.subscribers.clear()
            
            self.is_running = False
            logger.info("数据聚合器清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")


# 全局数据聚合器实例
_data_aggregator: Optional[DataAggregator] = None


async def get_data_aggregator() -> DataAggregator:
    """获取全局数据聚合器实例"""
    global _data_aggregator
    
    if _data_aggregator is None:
        _data_aggregator = DataAggregator()
        await _data_aggregator.initialize()
    
    return _data_aggregator


async def shutdown_data_aggregator():
    """关闭数据聚合器"""
    global _data_aggregator
    
    if _data_aggregator:
        await _data_aggregator.cleanup()
        _data_aggregator = None


if __name__ == "__main__":
    # 测试数据聚合器
    import asyncio
    
    async def test_data_aggregator():
        print("测试数据聚合器...")
        
        try:
            aggregator = await get_data_aggregator()
            
            # 测试获取市场数据
            btc_data = await aggregator.get_market_data("binance", "spot", "BTCUSDT")
            if btc_data:
                print(f"✅ BTC价格: ${btc_data.current_price}")
                print(f"   24h涨跌: {btc_data.price_change_percent}%")
            
            # 测试健康检查
            health = await aggregator.health_check()
            print(f"✅ 健康状态: {health['status']}")
            print(f"   适配器数量: {len(health['adapters'])}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        finally:
            await shutdown_data_aggregator()
    
    asyncio.run(test_data_aggregator())
