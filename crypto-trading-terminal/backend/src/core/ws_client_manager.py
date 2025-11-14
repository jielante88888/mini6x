"""
WebSocket客户端管理器
负责管理与外部交易所的WebSocket连接
"""

import asyncio
import json
import weakref
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Callable, Any, AsyncGenerator
from contextlib import asynccontextmanager

import structlog
import websockets
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, InvalidStatusCode, TimeoutError

from ..adapters.base import MarketData, OrderBook, Trade, Exchange
from ..utils.exceptions import WebSocketError

logger = structlog.get_logger(__name__)


class WebSocketClientManager:
    """WebSocket客户端管理器"""
    
    def __init__(self):
        # WebSocket连接池
        self.connections: Dict[str, WebSocketConnection] = {}
        
        # 订阅管理
        self.subscriptions: Dict[str, SubscriptionConfig] = {}
        
        # 回调函数
        self.data_callbacks: Dict[str, List[Callable]] = {}
        
        # 期货专用WebSocket管理器
        self.futures_ws_manager = FuturesWebSocketManager(self)
        
        # 连接统计
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages": 0,
            "failed_connections": 0,
            "reconnected_count": 0
        }
    
    async def subscribe_market_data(
        self,
        exchange: str,
        market_type: str,
        symbol: str,
        data_type: str,
        callback: Callable[[Dict[str, Any]], None],
        reconnect: bool = True
    ) -> str:
        """订阅市场数据"""
        
        subscription_id = f"{exchange}_{market_type}_{symbol}_{data_type}"
        
        # 创建订阅配置
        subscription = SubscriptionConfig(
            exchange=exchange,
            market_type=market_type,
            symbol=symbol,
            data_type=data_type,
            callback=callback,
            auto_reconnect=reconnect
        )
        
        self.subscriptions[subscription_id] = subscription
        
        # 初始化回调列表
        if subscription_id not in self.data_callbacks:
            self.data_callbacks[subscription_id] = []
        self.data_callbacks[subscription_id].append(callback)
        
        # 开始连接
        await self._start_subscription(subscription_id, subscription)
        
        logger.info(f"开始订阅: {subscription_id}")
        return subscription_id
    
    async def unsubscribe_market_data(
        self,
        subscription_id: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """取消订阅市场数据"""
        
        if subscription_id not in self.subscriptions:
            logger.warning(f"订阅不存在: {subscription_id}")
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        # 移除回调
        if callback and subscription_id in self.data_callbacks:
            callbacks = self.data_callbacks[subscription_id]
            if callback in callbacks:
                callbacks.remove(callback)
                logger.info(f"移除回调: {subscription_id}")
        
        # 如果没有更多回调，关闭连接
        if subscription_id not in self.data_callbacks or not self.data_callbacks[subscription_id]:
            await self._close_subscription(subscription_id)
            del self.subscriptions[subscription_id]
            
            if subscription_id in self.data_callbacks:
                del self.data_callbacks[subscription_id]
            
            logger.info(f"取消订阅: {subscription_id}")
            return True
        
        return True
    
    async def _start_subscription(self, subscription_id: str, subscription: 'SubscriptionConfig'):
        """启动订阅"""
        
        try:
            # 获取连接URL
            ws_url = self._get_websocket_url(
                subscription.exchange, 
                subscription.market_type, 
                subscription.symbol, 
                subscription.data_type
            )
            
            # 创建WebSocket连接
            connection = WebSocketConnection(
                subscription_id=subscription_id,
                ws_url=ws_url,
                auto_reconnect=subscription.auto_reconnect,
                data_callbacks=self.data_callbacks.get(subscription_id, [])
            )
            
            self.connections[subscription_id] = connection
            
            # 启动连接
            asyncio.create_task(connection.start())
            
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            logger.info(f"连接启动: {subscription_id} -> {ws_url}")
            
        except Exception as e:
            logger.error(f"启动订阅失败 {subscription_id}: {e}")
            raise WebSocketError(f"订阅启动失败: {e}")
    
    async def _close_subscription(self, subscription_id: str):
        """关闭订阅"""
        
        if subscription_id in self.connections:
            connection = self.connections[subscription_id]
            await connection.stop()
            del self.connections[subscription_id]
            
            self.stats["active_connections"] -= 1
            logger.info(f"连接已关闭: {subscription_id}")
    
    def _get_websocket_url(
        self, 
        exchange: str, 
        market_type: str, 
        symbol: str, 
        data_type: str
    ) -> str:
        """获取WebSocket URL"""
        
        symbol_lower = symbol.lower()
        
        # 币安现货WebSocket
        if exchange.lower() == "binance":
            if data_type == "ticker":
                return f"wss://stream.binance.com:9443/ws/{symbol_lower}@ticker"
            elif data_type == "depth":
                return f"wss://stream.binance.com:9443/ws/{symbol_lower}@depth"
            elif data_type == "trades":
                return f"wss://stream.binance.com:9443/ws/{symbol_lower}@trade"
            elif data_type == "klines_1m":
                return f"wss://stream.binance.com:9443/ws/{symbol_lower}@kline_1m"
            else:
                return f"wss://stream.binance.com:9443/ws/{symbol_lower}@ticker"
        
        # OKX现货WebSocket  
        elif exchange.lower() == "okx":
            if data_type == "ticker":
                return f"wss://ws.okx.com:8443/ws/v5/public"
            elif data_type == "depth":
                return f"wss://ws.okx.com:8443/ws/v5/public"
            elif data_type == "trades":
                return f"wss://ws.okx.com:8443/ws/v5/public"
            else:
                return f"wss://ws.okx.com:8443/ws/v5/public"
        
        # 默认测试网URL
        else:
            return f"wss://testnet.binance.vision/ws/{symbol_lower}@ticker"
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        status = {
            "total_subscriptions": len(self.subscriptions),
            "active_connections": len(self.connections),
            "stats": self.stats.copy()
        }
        
        # 详细连接状态
        status["connections"] = {}
        for subscription_id, connection in self.connections.items():
            status["connections"][subscription_id] = {
                "connected": connection.is_connected,
                "url": connection.ws_url,
                "last_message": connection.last_message_time.isoformat() if connection.last_message_time else None,
                "message_count": connection.message_count,
                "error_count": connection.error_count
            }
        
        return status
    
    async def reconnect_all(self):
        """重新连接所有订阅"""
        
        logger.info("开始重新连接所有订阅...")
        reconnected = 0
        
        for subscription_id, subscription in self.subscriptions.items():
            if subscription_id not in self.connections:
                try:
                    await self._start_subscription(subscription_id, subscription)
                    reconnected += 1
                except Exception as e:
                    logger.error(f"重连失败 {subscription_id}: {e}")
        
        self.stats["reconnected_count"] += reconnected
        logger.info(f"重新连接完成: {reconnected}个订阅")
    
    async def cleanup(self):
        """清理资源"""
        
        logger.info("清理WebSocket客户端管理器...")
        
        # 关闭所有连接
        for connection in self.connections.values():
            await connection.stop()
        
        self.connections.clear()
        self.subscriptions.clear()
        self.data_callbacks.clear()
        
        logger.info("WebSocket客户端管理器清理完成")


class SubscriptionConfig:
    """订阅配置"""
    
    def __init__(
        self,
        exchange: str,
        market_type: str,
        symbol: str,
        data_type: str,
        callback: Callable,
        auto_reconnect: bool = True
    ):
        self.exchange = exchange
        self.market_type = market_type
        self.symbol = symbol
        self.data_type = data_type
        self.callback = callback
        self.auto_reconnect = auto_reconnect
        self.created_at = datetime.utcnow()


class WebSocketConnection:
    """WebSocket连接"""
    
    def __init__(
        self,
        subscription_id: str,
        ws_url: str,
        data_callbacks: List[Callable],
        auto_reconnect: bool = True
    ):
        self.subscription_id = subscription_id
        self.ws_url = ws_url
        self.data_callbacks = data_callbacks
        self.auto_reconnect = auto_reconnect
        
        # 连接状态
        self.is_connected = False
        self.websocket = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # 统计
        self.message_count = 0
        self.error_count = 0
        self.last_message_time: Optional[datetime] = None
        
        # 速率限制
        self.message_times: List[datetime] = []
        self.max_messages_per_second = 50
    
    async def start(self):
        """启动连接"""
        
        logger.info(f"启动WebSocket连接: {self.subscription_id}")
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self._connect()
                break
            except Exception as e:
                self.reconnect_attempts += 1
                logger.warning(f"连接失败 {self.subscription_id} (尝试 {self.reconnect_attempts}): {e}")
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error(f"达到最大重连次数: {self.subscription_id}")
                    break
                
                await asyncio.sleep(2 ** self.reconnect_attempts)  # 指数退避
    
    async def _connect(self):
        """建立连接"""
        
        try:
            self.websocket = await ws_connect(
                self.ws_url,
                close_timeout=5,
                ping_timeout=5,
                ping_interval=20
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info(f"WebSocket连接成功: {self.subscription_id}")
            
            # 开始消息处理
            await self._listen()
            
        except ConnectionClosed:
            logger.warning(f"WebSocket连接关闭: {self.subscription_id}")
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"WebSocket连接异常 {self.subscription_id}: {e}")
            self.is_connected = False
            raise
    
    async def _listen(self):
        """监听消息"""
        
        try:
            async for message in self.websocket:
                try:
                    await self._process_message(message)
                except Exception as e:
                    self.error_count += 1
                    logger.warning(f"处理消息失败: {e}")
                    continue
                    
        except ConnectionClosed:
            logger.info(f"WebSocket监听结束: {self.subscription_id}")
            self.is_connected = False
            
            # 自动重连
            if self.auto_reconnect:
                await asyncio.sleep(1)
                await self._reconnect()
        except Exception as e:
            logger.error(f"WebSocket监听异常 {self.subscription_id}: {e}")
            self.is_connected = False
            raise
    
    async def _process_message(self, message: str):
        """处理消息"""
        
        try:
            # 解析JSON消息
            data = json.loads(message)
            
            # 更新统计
            self.message_count += 1
            self.last_message_time = datetime.utcnow()
            
            # 速率限制检查
            if not self._check_rate_limit():
                logger.warning(f"达到速率限制: {self.subscription_id}")
                return
            
            # 解析数据
            processed_data = self._parse_message_data(data)
            
            if processed_data:
                # 通知回调函数
                await self._notify_callbacks(processed_data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {message[:100]}... 错误: {e}")
            self.error_count += 1
    
    def _check_rate_limit(self) -> bool:
        """检查速率限制"""
        now = datetime.utcnow()
        
        # 清理超过1秒的消息时间
        self.message_times = [
            msg_time for msg_time in self.message_times 
            if (now - msg_time).total_seconds() < 1.0
        ]
        
        # 检查是否超过限制
        return len(self.message_times) < self.max_messages_per_second
    
    def _parse_message_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析消息数据"""
        
        try:
            # 币安现货数据格式
            if "s" in data and "c" in data:  # 币安ticker格式
                return {
                    "type": "ticker",
                    "symbol": data.get("s"),
                    "price": float(data.get("c", 0)),
                    "volume": float(data.get("v", 0)),
                    "change": float(data.get("p", 0)),
                    "change_percent": float(data.get("P", 0)),
                    "timestamp": data.get("E", 0),
                    "high": float(data.get("h", 0)),
                    "low": float(data.get("l", 0))
                }
            
            # 订单簿数据
            elif "b" in data and "a" in data:  # 币安orderbook格式
                return {
                    "type": "orderbook",
                    "symbol": data.get("s"),
                    "bids": [[float(p), float(q)] for p, q in data.get("b", [])],
                    "asks": [[float(p), float(q)] for p, q in data.get("a", [])],
                    "timestamp": data.get("E", 0)
                }
            
            # 交易数据
            elif "t" in data and "p" in data and "q" in data:  # 币安trade格式
                return {
                    "type": "trade",
                    "symbol": data.get("s"),
                    "price": float(data.get("p", 0)),
                    "quantity": float(data.get("q", 0)),
                    "timestamp": data.get("T", 0),
                    "is_buyer_maker": data.get("m", False)
                }
            
            else:
                logger.debug(f"未识别的数据格式: {data}")
                return data
            
        except (ValueError, TypeError) as e:
            logger.warning(f"数据解析失败: {e}")
            return None
    
    async def _notify_callbacks(self, data: Dict[str, Any]):
        """通知回调函数"""
        
        for callback in self.data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.warning(f"回调函数执行失败: {e}")
    
    async def _reconnect(self):
        """重新连接"""
        
        logger.info(f"开始重连: {self.subscription_id}")
        
        try:
            await self._connect()
        except Exception as e:
            logger.error(f"重连失败 {self.subscription_id}: {e}")
            raise
    
    async def stop(self):
        """停止连接"""
        
        logger.info(f"停止WebSocket连接: {self.subscription_id}")
        
        self.is_connected = False
        self.auto_reconnect = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"关闭连接失败: {e}")


# 全局WebSocket客户端管理器实例
_ws_client_manager: Optional[WebSocketClientManager] = None


async def get_ws_client_manager() -> WebSocketClientManager:
    """获取全局WebSocket客户端管理器"""
    global _ws_client_manager
    
    if _ws_client_manager is None:
        _ws_client_manager = WebSocketClientManager()
    
    return _ws_client_manager


async def shutdown_ws_client_manager():
    """关闭WebSocket客户端管理器"""
    global _ws_client_manager
    
    if _ws_client_manager:
        await _ws_client_manager.cleanup()
        _ws_client_manager = None


if __name__ == "__main__":
    # 测试WebSocket客户端管理器
    import asyncio
    
    async def test_ws_client_manager():
class FuturesWebSocketManager:
    """期货专用WebSocket管理器 - 专门处理期货市场的实时数据连接"""
    
    def __init__(self, main_manager: WebSocketClientManager):
        self.main_manager = main_manager
        
        # 期货专用连接管理
        self.futures_connections: Dict[str, WebSocketConnection] = {}
        self.futures_subscriptions: Dict[str, SubscriptionConfig] = {}
        
        # 期货特有数据处理
        self.funding_rate_callbacks: Dict[str, Callable] = {}
        self.open_interest_callbacks: Dict[str, Callable] = {}
        
        # 期货市场监控
        self.futures_monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.funding_rate_queues: Dict[str, asyncio.Queue] = {}
        
        logger.info("期货专用WebSocket管理器初始化完成")
    
    async def subscribe_futures_market_data(
        self,
        exchange: str,
        symbol: str,
        callback: Callable[[Dict], None],
        market_data_types: List[str] = None
    ) -> str:
        """订阅期货市场数据"""
        try:
            if market_data_types is None:
                market_data_types = ["ticker", "orderbook", "trades"]
            
            subscription_id = f"futures:{exchange}:{symbol}:{','.join(market_data_types)}"
            
            # 创建订阅配置
            config = SubscriptionConfig(
                subscription_id=subscription_id,
                exchange=exchange,
                market_type="futures",
                symbol=symbol,
                data_types=market_data_types,
                callback=callback,
                auto_reconnect=True,
                max_retries=5
            )
            
            self.futures_subscriptions[subscription_id] = config
            
            # 建立WebSocket连接
            connection_id = await self._create_futures_connection(exchange, symbol)
            config.connection_id = connection_id
            
            # 发送订阅消息
            await self._send_subscription_messages(connection_id, market_data_types, symbol)
            
            # 启动数据监控
            await self._start_futures_monitoring(exchange, symbol, config)
            
            logger.info(f"期货市场数据订阅成功: {subscription_id}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"期货市场数据订阅失败: {e}")
            raise WebSocketError(f"期货数据订阅失败: {e}")
    
    async def _create_futures_connection(
        self,
        exchange: str,
        symbol: str
    ) -> str:
        """创建期货专用WebSocket连接"""
        try:
            # 构建期货WebSocket URL
            ws_url = self._get_futures_ws_url(exchange, symbol)
            
            connection_id = f"futures_{exchange}_{symbol}_{int(asyncio.get_event_loop().time())}"
            
            # 创建WebSocket连接
            connection = WebSocketConnection(
                connection_id=connection_id,
                exchange=exchange,
                market_type="futures",
                symbol=symbol,
                ws_url=ws_url,
                auto_reconnect=True,
                reconnect_interval=5.0,
                max_reconnect_attempts=10
            )
            
            self.futures_connections[connection_id] = connection
            await connection.connect()
            
            logger.info(f"期货WebSocket连接建立: {connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"期货WebSocket连接失败: {e}")
            raise WebSocketError(f"期货连接失败: {e}")
    
    def _get_futures_ws_url(self, exchange: str, symbol: str) -> str:
        """获取期货WebSocket URL"""
        if exchange.lower() == "binance":
            # 币安期货WebSocket
            symbol_lower = symbol.lower().replace("-usdt-perp", "usdt")
            return f"wss://fstream.binance.com/ws/{symbol_lower}@ticker"
        elif exchange.lower() == "okx":
            # OKX期货WebSocket
            return f"wss://ws.okx.com:8443/ws/v5/public"
        else:
            raise ValueError(f"不支持的期货交易所: {exchange}")
    
    async def _send_subscription_messages(
        self,
        connection_id: str,
        data_types: List[str],
        symbol: str
    ):
        """发送订阅消息"""
        connection = self.futures_connections.get(connection_id)
        if not connection:
            return
        
        if connection.exchange == "binance":
            # 币安期货订阅格式
            for data_type in data_types:
                if data_type == "ticker":
                    subscribe_msg = {
                        "method": "SUBSCRIBE",
                        "params": [f"{symbol.lower().replace('-usdt-perp', 'usdt')}@ticker"],
                        "id": int(asyncio.get_event_loop().time())
                    }
                    await connection.send_message(subscribe_msg)
        
        elif connection.exchange == "okx":
            # OKX期货订阅格式
            subscribe_msg = {
                "op": "subscribe",
                "args": [
                    {
                        "channel": "tickers",
                        "instId": symbol
                    }
                ]
            }
            await connection.send_message(subscribe_msg)
    
    async def _start_futures_monitoring(
        self,
        exchange: str,
        symbol: str,
        config: SubscriptionConfig
    ):
        """启动期货市场监控"""
        try:
            # 创建数据处理任务
            task = asyncio.create_task(
                self._futures_data_processing_loop(exchange, symbol, config)
            )
            
            monitoring_key = f"{exchange}:{symbol}"
            self.futures_monitoring_tasks[monitoring_key] = task
            
        except Exception as e:
            logger.error(f"期货市场监控启动失败: {e}")
    
    async def _futures_data_processing_loop(
        self,
        exchange: str,
        symbol: str,
        config: SubscriptionConfig
    ):
        """期货数据处理循环"""
        try:
            connection_id = config.connection_id
            connection = self.futures_connections.get(connection_id)
            
            if not connection:
                return
            
            async for message in connection.message_stream:
                try:
                    # 解析期货数据
                    futures_data = self._parse_futures_message(message, exchange)
                    
                    if futures_data:
                        # 调用回调函数
                        config.callback(futures_data)
                        
                        # 处理期货特有数据
                        await self._process_futures_specific_data(futures_data, exchange, symbol)
                
                except Exception as e:
                    logger.error(f"期货数据处理错误: {e}")
        
        except asyncio.CancelledError:
            logger.info(f"期货数据处理循环已取消: {exchange}:{symbol}")
        except Exception as e:
            logger.error(f"期货数据处理循环错误: {exchange}:{symbol}: {e}")
        finally:
            # 清理任务
            monitoring_key = f"{exchange}:{symbol}"
            self.futures_monitoring_tasks.pop(monitoring_key, None)
    
    def _parse_futures_message(
        self,
        message: str,
        exchange: str
    ) -> Optional[Dict]:
        """解析期货WebSocket消息"""
        try:
            data = json.loads(message)
            
            if exchange.lower() == "binance":
                return self._parse_binance_futures_data(data)
            elif exchange.lower() == "okx":
                return self._parse_okx_futures_data(data)
            
            return None
            
        except Exception as e:
            logger.error(f"期货消息解析失败: {e}")
            return None
    
    def _parse_binance_futures_data(self, data: Dict) -> Optional[Dict]:
        """解析币安期货数据"""
        if 'e' in data and data['e'] == '24hrTicker':
            return {
                "symbol": data['s'],
                "price": float(data['c']),
                "price_change": float(data['p']),
                "price_change_percent": float(data['P']),
                "volume": float(data['v']),
                "high_24h": float(data['h']),
                "low_24h": float(data['l']),
                "funding_rate": float(data.get('F', 0)),
                "open_interest": float(data.get('o', 0)),
                "mark_price": float(data.get('c', 0)),
                "index_price": float(data.get('i', 0)),
                "timestamp": datetime.utcnow(),
                "exchange": "binance",
                "market_type": "futures"
            }
        
        return None
    
    def _parse_okx_futures_data(self, data: Dict) -> Optional[Dict]:
        """解析OKX期货数据"""
        if 'data' in data and data['data']:
            ticker_data = data['data'][0]
            if 'instId' in ticker_data:
                return {
                    "symbol": ticker_data['instId'],
                    "price": float(ticker_data['last']),
                    "price_change": float(ticker_data.get('ch', 0)),
                    "price_change_percent": float(ticker_data.get('chUsd', 0)),
                    "volume": float(ticker_data['vol24h']),
                    "high_24h": float(ticker_data['high24h']),
                    "low_24h": float(ticker_data['low24h']),
                    "funding_rate": float(ticker_data.get('fundingRate', 0)),
                    "open_interest": float(ticker_data.get('oi', 0)),
                    "mark_price": float(ticker_data.get('markPrice', ticker_data['last'])),
                    "index_price": float(ticker_data.get('indexPrice', ticker_data['last'])),
                    "timestamp": datetime.utcnow(),
                    "exchange": "okx",
                    "market_type": "futures"
                }
        
        return None
    
    async def _process_futures_specific_data(
        self,
        data: Dict,
        exchange: str,
        symbol: str
    ):
        """处理期货特有数据"""
        try:
            # 处理资金费率数据
            if 'funding_rate' in data and data['funding_rate'] != 0:
                funding_key = f"{exchange}:{symbol}"
                if funding_key in self.funding_rate_callbacks:
                    self.funding_rate_callbacks[funding_key]({
                        "symbol": symbol,
                        "funding_rate": data['funding_rate'],
                        "timestamp": data['timestamp'],
                        "exchange": exchange
                    })
            
            # 处理持仓量数据
            if 'open_interest' in data and data['open_interest'] != 0:
                oi_key = f"{exchange}:{symbol}"
                if oi_key in self.open_interest_callbacks:
                    self.open_interest_callbacks[oi_key]({
                        "symbol": symbol,
                        "open_interest": data['open_interest'],
                        "timestamp": data['timestamp'],
                        "exchange": exchange
                    })
        
        except Exception as e:
            logger.error(f"期货特有数据处理错误: {e}")
    
    async def subscribe_funding_rate(
        self,
        exchange: str,
        symbol: str,
        callback: Callable[[Dict], None]
    ) -> str:
        """订阅资金费率数据"""
        funding_key = f"{exchange}:{symbol}"
        self.funding_rate_callbacks[funding_key] = callback
        
        logger.info(f"资金费率订阅成功: {funding_key}")
        return funding_key
    
    async def subscribe_open_interest(
        self,
        exchange: str,
        symbol: str,
        callback: Callable[[Dict], None]
    ) -> str:
        """订阅持仓量数据"""
        oi_key = f"{exchange}:{symbol}"
        self.open_interest_callbacks[oi_key] = callback
        
        logger.info(f"持仓量订阅成功: {oi_key}")
        return oi_key
    
    async def unsubscribe_futures_data(
        self,
        exchange: str,
        symbol: str
    ):
        """取消期货数据订阅"""
        try:
            # 查找并取消订阅
            subscription_id = f"futures:{exchange}:{symbol}:ticker"
            
            if subscription_id in self.futures_subscriptions:
                config = self.futures_subscriptions[subscription_id]
                
                # 取消监控任务
                monitoring_key = f"{exchange}:{symbol}"
                if monitoring_key in self.futures_monitoring_tasks:
                    task = self.futures_monitoring_tasks[monitoring_key]
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    del self.futures_monitoring_tasks[monitoring_key]
                
                # 关闭连接
                if config.connection_id in self.futures_connections:
                    connection = self.futures_connections[config.connection_id]
                    await connection.disconnect()
                    del self.futures_connections[config.connection_id]
                
                # 清理订阅
                del self.futures_subscriptions[subscription_id]
                
                logger.info(f"期货数据订阅已取消: {subscription_id}")
            
        except Exception as e:
            logger.error(f"取消期货数据订阅失败: {e}")
    
    async def get_futures_connection_status(self) -> Dict[str, Any]:
        """获取期货连接状态"""
        status = {
            "total_connections": len(self.futures_connections),
            "active_subscriptions": len(self.futures_subscriptions),
            "monitoring_tasks": len(self.futures_monitoring_tasks),
            "funding_rate_subscriptions": len(self.funding_rate_callbacks),
            "open_interest_subscriptions": len(self.open_interest_callbacks),
            "connections": {}
        }
        
        for connection_id, connection in self.futures_connections.items():
            status["connections"][connection_id] = {
                "exchange": connection.exchange,
                "symbol": connection.symbol,
                "is_connected": connection.is_connected,
                "last_message": connection.last_message_time
            }
        
        return status
    
    async def cleanup(self):
        """清理期货WebSocket资源"""
        try:
            # 取消所有监控任务
            for task in self.futures_monitoring_tasks.values():
                task.cancel()
            
            # 等待任务完成
            if self.futures_monitoring_tasks:
                await asyncio.gather(
                    *self.futures_monitoring_tasks.values(),
                    return_exceptions=True
                )
            
            # 关闭所有连接
            for connection in self.futures_connections.values():
                await connection.disconnect()
            
            # 清理缓存
            self.futures_connections.clear()
            self.futures_subscriptions.clear()
            self.funding_rate_callbacks.clear()
            self.open_interest_callbacks.clear()
            self.futures_monitoring_tasks.clear()
            
            logger.info("期货WebSocket管理器清理完成")
            
        except Exception as e:
            logger.error(f"期货WebSocket管理器清理失败: {e}")


# 更新主管理器的cleanup方法
def _add_futures_cleanup_to_main_manager():
    """为主管理器添加期货清理功能"""
    original_cleanup = WebSocketClientManager.cleanup
    
    async def enhanced_cleanup(self):
        """增强的清理方法，包含期货管理器的清理"""
        if hasattr(self, 'futures_ws_manager'):
            await self.futures_ws_manager.cleanup()
        
        # 调用原始清理方法
        if hasattr(original_cleanup, '__call__'):
            await original_cleanup()
    
    WebSocketClientManager.cleanup = enhanced_cleanup


# 应用增强
_add_futures_cleanup_to_main_manager()


# 更新测试代码
if __name__ == "__main__":
    print("测试WebSocket客户端管理器...")
        
        try:
            manager = await get_ws_client_manager()
            
            # 测试订阅
            def market_data_handler(data):
                print(f"收到市场数据: {data.get('symbol', 'unknown')} - ${data.get('price', 0)}")
            
            subscription_id = await manager.subscribe_market_data(
                "binance",
                "spot", 
                "BTCUSDT",
                "ticker",
                market_data_handler
            )
            
            print(f"订阅ID: {subscription_id}")
            
            # 等待一段时间
            await asyncio.sleep(10)
            
            # 获取连接状态
            status = await manager.get_connection_status()
            print(f"连接状态: {status}")
            
        except Exception as e:
            print(f"测试失败: {e}")
        finally:
            await shutdown_ws_client_manager()
    
    asyncio.run(test_ws_client_manager())
