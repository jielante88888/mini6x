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
        
        # 期货数据聚合器
        self.futures_aggregator = FuturesDataAggregator(self)
        
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
            
            # 清理期货数据聚合器
            if hasattr(self, 'futures_aggregator'):
                await self.futures_aggregator.cleanup()
            
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


class FuturesDataAggregator:
    """期货数据聚合器 - 专门处理期货市场的数据聚合"""
    
    def __init__(self, main_aggregator: DataAggregator):
        self.main_aggregator = main_aggregator
        
        # 期货专用缓存
        self.futures_data_cache: Dict[str, MarketData] = {}
        self.funding_rate_cache: Dict[str, Dict] = {}
        self.open_interest_cache: Dict[str, Dict] = {}
        
        # 期货市场监控
        self.active_futures_subscriptions: Set[str] = set()
        self.futures_monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("期货数据聚合器初始化完成")
    
    async def get_futures_market_data(
        self, 
        exchange: str, 
        symbol: str
    ) -> Optional[MarketData]:
        """获取期货市场数据"""
        try:
            # 检查期货缓存
            cache_key = f"{exchange}:futures:{symbol}"
            
            if cache_key in self.futures_data_cache:
                cached_data = self.futures_data_cache[cache_key]
                # 检查缓存是否仍然有效（5分钟内）
                if (datetime.now(timezone.utc) - cached_data.timestamp).total_seconds() < 300:
                    logger.debug(f"期货数据缓存命中: {cache_key}")
                    return cached_data
            
            # 从主聚合器获取数据
            futures_data = await self.main_aggregator.get_market_data(
                exchange, "futures", symbol
            )
            
            if futures_data:
                # 验证期货特有字段
                if futures_data.funding_rate is None:
                    # 获取资金费率
                    funding_rate_data = await self.get_funding_rate_data(exchange, symbol)
                    if funding_rate_data:
                        futures_data = futures_data.copy_with(
                            funding_rate=funding_rate_data.get('last_funding_rate')
                        )
                
                if futures_data.open_interest is None:
                    # 获取持仓量
                    oi_data = await self.get_open_interest_data(exchange, symbol)
                    if oi_data:
                        futures_data = futures_data.copy_with(
                            open_interest=oi_data.get('open_interest')
                        )
                
                # 缓存期货数据
                self.futures_data_cache[cache_key] = futures_data
                
                logger.debug(f"获取期货数据成功: {cache_key}")
                return futures_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取期货数据失败 {exchange}:{symbol}: {e}")
            return None
    
    async def get_funding_rate_data(
        self, 
        exchange: str, 
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """获取资金费率数据"""
        try:
            cache_key = f"{exchange}:futures:{symbol}"
            
            if cache_key in self.funding_rate_cache:
                return self.funding_rate_cache[cache_key]
            
            # 获取适配器
            exchange_key = f"{exchange}_futures"
            if exchange_key not in self.main_aggregator.adapters:
                raise DataAggregationError(f"不支持的期货交易所: {exchange_key}")
            
            adapter = self.main_aggregator.adapters[exchange_key]
            
            # 获取资金费率
            if hasattr(adapter, 'get_funding_rate'):
                funding_rate_data = await adapter.get_funding_rate(symbol)
                if funding_rate_data:
                    self.funding_rate_cache[cache_key] = funding_rate_data
                    return funding_rate_data
            
            return None
            
        except Exception as e:
            logger.debug(f"获取资金费率失败 {exchange}:{symbol}: {e}")
            return None
    
    async def get_open_interest_data(
        self, 
        exchange: str, 
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """获取持仓量数据"""
        try:
            cache_key = f"{exchange}:futures:{symbol}"
            
            if cache_key in self.open_interest_cache:
                return self.open_interest_cache[cache_key]
            
            # 获取适配器
            exchange_key = f"{exchange}_futures"
            if exchange_key not in self.main_aggregator.adapters:
                raise DataAggregationError(f"不支持的期货交易所: {exchange_key}")
            
            adapter = self.main_aggregator.adapters[exchange_key]
            
            # 获取持仓量
            if hasattr(adapter, 'get_open_interest'):
                oi_data = await adapter.get_open_interest(symbol)
                if oi_data:
                    self.open_interest_cache[cache_key] = oi_data
                    return oi_data
            
            return None
            
        except Exception as e:
            logger.debug(f"获取持仓量失败 {exchange}:{symbol}: {e}")
            return None
    
    async def monitor_futures_market(
        self, 
        exchange: str, 
        symbols: List[str],
        update_interval: float = 5.0
    ) -> AsyncGenerator[MarketData, None]:
        """监控期货市场数据"""
        try:
            # 启动监控任务
            for symbol in symbols:
                subscription_key = f"{exchange}:{symbol}"
                if subscription_key not in self.active_futures_subscriptions:
                    self.active_futures_subscriptions.add(subscription_key)
                    
                    # 启动单独的数据更新任务
                    task = asyncio.create_task(
                        self._futures_monitoring_loop(
                            exchange, symbol, update_interval
                        )
                    )
                    self.futures_monitoring_tasks[subscription_key] = task
            
            # 生成数据流
            while True:
                for symbol in symbols:
                    cache_key = f"{exchange}:futures:{symbol}"
                    if cache_key in self.futures_data_cache:
                        yield self.futures_data_cache[cache_key]
                
                await asyncio.sleep(update_interval)
                
        except asyncio.CancelledError:
            logger.info("期货市场监控已取消")
            raise
        except Exception as e:
            logger.error(f"期货市场监控错误: {e}")
            raise
    
    async def _futures_monitoring_loop(
        self, 
        exchange: str, 
        symbol: str, 
        interval: float
    ):
        """期货市场监控循环"""
        try:
            while True:
                try:
                    # 获取最新数据
                    futures_data = await self.get_futures_market_data(exchange, symbol)
                    
                    if futures_data:
                        logger.debug(f"期货数据更新: {exchange}:{symbol}")
                    
                    await asyncio.sleep(interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"期货监控循环错误 {exchange}:{symbol}: {e}")
                    await asyncio.sleep(interval * 2)  # 出错时延长间隔
        
        finally:
            # 清理资源
            subscription_key = f"{exchange}:{symbol}"
            self.active_futures_subscriptions.discard(subscription_key)
            self.futures_monitoring_tasks.pop(subscription_key, None)
    
    async def stop_monitoring(
        self, 
        exchange: str, 
        symbol: str
    ):
        """停止监控指定期货交易对"""
        subscription_key = f"{exchange}:{symbol}"
        
        # 取消监控任务
        if subscription_key in self.futures_monitoring_tasks:
            task = self.futures_monitoring_tasks[subscription_key]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.futures_monitoring_tasks[subscription_key]
        
        # 清理订阅
        self.active_futures_subscriptions.discard(subscription_key)
        
        logger.info(f"停止期货监控: {subscription_key}")
    
    async def get_futures_summary(
        self, 
        exchange: str, 
        symbols: List[str]
    ) -> Dict[str, Any]:
        """获取期货市场摘要"""
        try:
            futures_data_list = []
            funding_rates = []
            open_interests = []
            
            for symbol in symbols:
                # 获取期货数据
                futures_data = await self.get_futures_market_data(exchange, symbol)
                if futures_data:
                    futures_data_list.append(futures_data)
                    
                    # 收集资金费率
                    if futures_data.funding_rate is not None:
                        funding_rates.append(futures_data.funding_rate)
                    
                    # 收集持仓量
                    if futures_data.open_interest is not None:
                        open_interests.append(futures_data.open_interest)
            
            # 计算统计信息
            summary = {
                "exchange": exchange,
                "symbols_count": len(futures_data_list),
                "total_volume": sum(data.volume_24h for data in futures_data_list),
                "avg_price": sum(data.current_price for data in futures_data_list) / len(futures_data_list) if futures_data_list else 0,
                "price_range": {
                    "highest": max(data.high_24h for data in futures_data_list) if futures_data_list else 0,
                    "lowest": min(data.low_24h for data in futures_data_list) if futures_data_list else 0
                },
                "funding_rates": {
                    "average": sum(funding_rates) / len(funding_rates) if funding_rates else 0,
                    "highest": max(funding_rates) if funding_rates else 0,
                    "lowest": min(funding_rates) if funding_rates else 0
                },
                "open_interests": {
                    "total": sum(open_interests),
                    "average": sum(open_interests) / len(open_interests) if open_interests else 0
                },
                "update_time": datetime.now(timezone.utc)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取期货摘要失败 {exchange}: {e}")
            raise DataAggregationError(f"期货摘要获取失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "futures_data_cache_size": len(self.futures_data_cache),
            "funding_rate_cache_size": len(self.funding_rate_cache),
            "open_interest_cache_size": len(self.open_interest_cache),
            "active_subscriptions": len(self.active_futures_subscriptions),
            "monitoring_tasks": len(self.futures_monitoring_tasks)
        }
    
    async def cleanup(self):
        """清理资源"""
        # 取消所有监控任务
        for task in self.futures_monitoring_tasks.values():
            task.cancel()
        
        # 等待任务完成
        if self.futures_monitoring_tasks:
            await asyncio.gather(
                *self.futures_monitoring_tasks.values(),
                return_exceptions=True
            )
        
        # 清理缓存
        self.futures_data_cache.clear()
        self.funding_rate_cache.clear()
        self.open_interest_cache.clear()
        self.active_futures_subscriptions.clear()
        self.futures_monitoring_tasks.clear()
        
        logger.info("期货数据聚合器已清理")


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
            
            # 测试期货数据聚合器
            if hasattr(aggregator, 'futures_aggregator'):
                futures_data = await aggregator.futures_aggregator.get_futures_market_data("binance", "BTCUSDT-PERP")
                if futures_data:
                    print(f"✅ BTC期货价格: ${futures_data.current_price}")
                    print(f"   资金费率: {futures_data.funding_rate}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        finally:
            await shutdown_data_aggregator()
    
    asyncio.run(test_data_aggregator())
