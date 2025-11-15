"""
WebSocket处理器框架
提供实时数据推送和消息管理功能
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

import structlog
from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

from ...config import settings
from ...adapters.base import MarketData, OrderBook, Trade
from ...utils.exceptions import WebSocketError, handle_exception

logger = structlog.get_logger()


class ConnectionType(Enum):
    """连接类型"""
    MARKET_DATA = "market_data"
    TRADING = "trading"
    USER = "user"
    SYSTEM = "system"


class MessageType(Enum):
    """消息类型"""
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    DATA = "data"
    ERROR = "error"
    ORDER_UPDATE = "order_update"
    TRADE_UPDATE = "trade_update"


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接管理
        self.connections: Dict[str, WebSocketConnection] = {}
        self.connection_counter = 0
        
        # 订阅管理
        self.market_subscriptions: Dict[str, Set[WebSocketConnection]] = {}
        self.trading_subscriptions: Dict[str, Set[WebSocketConnection]] = {}
        self.user_subscriptions: Dict[int, Set[WebSocketConnection]] = {}
        
        # 任务管理
        self.running_tasks: Set[asyncio.Task] = set()
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocket管理器初始化完成")
    
    def _generate_connection_id(self) -> str:
        """生成连接ID"""
        self.connection_counter += 1
        return f"ws_{self.connection_counter}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    async def connect(self, websocket: WebSocket, connection_type: ConnectionType) -> str:
        """接受WebSocket连接"""
        try:
            await websocket.accept()
            connection_id = self._generate_connection_id()
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                connection_type=connection_type,
                manager=self
            )
            
            self.connections[connection_id] = connection
            
            logger.info(
                "WebSocket连接建立",
                connection_id=connection_id,
                connection_type=connection_type.value,
                client_ip=websocket.client.host if websocket.client else "unknown"
            )
            
            # 启动连接的心跳检查
            self.running_tasks.add(
                asyncio.create_task(connection._heartbeat_loop())
            )
            
            return connection_id
            
        except Exception as e:
            logger.error(f"WebSocket连接建立失败: {e}")
            raise WebSocketError(f"连接建立失败: {str(e)}")
    
    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # 清理订阅
        await self._unsubscribe_all(connection)
        
        # 移除连接
        del self.connections[connection_id]
        
        # 记录断开
        logger.info(
            "WebSocket连接断开",
            connection_id=connection_id,
            connection_type=connection.connection_type.value
        )
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """发送消息到指定连接"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        await connection.send_message(message)
    
    async def broadcast_message(self, message: Dict[str, Any], 
                              subscription_type: str = None, 
                              subscription_key: str = None):
        """广播消息到指定订阅组"""
        target_connections = set()
        
        if subscription_type == "market_data":
            if subscription_key in self.market_subscriptions:
                target_connections = self.market_subscriptions[subscription_key].copy()
        elif subscription_type == "trading":
            if subscription_key in self.trading_subscriptions:
                target_connections = self.trading_subscriptions[subscription_key].copy()
        elif subscription_type == "user":
            try:
                user_id = int(subscription_key)
                if user_id in self.user_subscriptions:
                    target_connections = self.user_subscriptions[user_id].copy()
            except ValueError:
                pass
        else:
            # 广播到所有连接
            target_connections = set(self.connections.values())
        
        # 发送消息
        for connection in target_connections:
            try:
                await connection.send_message(message)
            except Exception as e:
                logger.warning(
                    "发送消息失败",
                    connection_id=connection.connection_id,
                    error=str(e)
                )
    
    async def subscribe_market_data(self, connection_id: str, symbol: str, exchange: str):
        """订阅市场数据"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        subscription_key = f"{exchange}:{symbol}"
        
        if subscription_key not in self.market_subscriptions:
            self.market_subscriptions[subscription_key] = set()
        
        self.market_subscriptions[subscription_key].add(connection)
        
        logger.debug(
            "订阅市场数据",
            connection_id=connection_id,
            subscription_key=subscription_key
        )
    
    async def subscribe_trading(self, connection_id: str, symbol: str):
        """订阅交易数据"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        if symbol not in self.trading_subscriptions:
            self.trading_subscriptions[symbol] = set()
        
        self.trading_subscriptions[symbol].add(connection)
        
        logger.debug(
            "订阅交易数据", 
            connection_id=connection_id,
            symbol=symbol
        )
    
    async def subscribe_user(self, connection_id: str, user_id: int):
        """订阅用户数据"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        
        self.user_subscriptions[user_id].add(connection)
        
        logger.debug(
            "订阅用户数据",
            connection_id=connection_id,
            user_id=user_id
        )
    
    async def _unsubscribe_all(self, connection):
        """取消所有订阅"""
        # 从市场数据订阅中移除
        for subscription_key in list(self.market_subscriptions.keys()):
            if connection in self.market_subscriptions[subscription_key]:
                self.market_subscriptions[subscription_key].discard(connection)
                if not self.market_subscriptions[subscription_key]:
                    del self.market_subscriptions[subscription_key]
        
        # 从交易数据订阅中移除
        for symbol in list(self.trading_subscriptions.keys()):
            if connection in self.trading_subscriptions[symbol]:
                self.trading_subscriptions[symbol].discard(connection)
                if not self.trading_subscriptions[symbol]:
                    del self.trading_subscriptions[symbol]
        
        # 从用户数据订阅中移除
        for user_id in list(self.user_subscriptions.keys()):
            if connection in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].discard(connection)
                if not self.user_subscriptions[user_id]:
                    del self.user_subscriptions[user_id]
    
    async def start_heartbeat(self):
        """启动全局心跳任务"""
        if self.heartbeat_task:
            return
        
        self.heartbeat_task = asyncio.create_task(self._global_heartbeat_loop())
        logger.info("WebSocket心跳任务启动")
    
    async def stop_heartbeat(self):
        """停止心跳任务"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
            logger.info("WebSocket心跳任务停止")
    
    async def _global_heartbeat_loop(self):
        """全局心跳循环"""
        while True:
            try:
                # 广播心跳消息
                heartbeat_message = {
                    "type": MessageType.HEARTBEAT.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "server_time": datetime.utcnow().isoformat()
                }
                
                await self.broadcast_message(heartbeat_message)
                
                # 等待30秒后发送下一次心跳
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳任务错误: {e}")
                await asyncio.sleep(10)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取WebSocket统计信息"""
        return {
            "active_connections": len(self.connections),
            "market_subscriptions": len(self.market_subscriptions),
            "trading_subscriptions": len(self.trading_subscriptions),
            "user_subscriptions": len(self.user_subscriptions),
            "running_tasks": len(self.running_tasks),
            "heartbeat_active": self.heartbeat_task is not None and not self.heartbeat_task.done()
        }


class WebSocketConnection:
    """WebSocket连接包装器"""
    
    def __init__(self, connection_id: str, websocket: WebSocket, 
                 connection_type: ConnectionType, manager: WebSocketManager):
        self.connection_id = connection_id
        self.websocket = websocket
        self.connection_type = connection_type
        self.manager = manager
        self.last_activity = datetime.utcnow()
        self.message_count = 0
        
        logger.info(
            "WebSocket连接包装器创建",
            connection_id=connection_id,
            connection_type=connection_type.value
        )
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if self.websocket.state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_json(message)
                self.last_activity = datetime.utcnow()
                self.message_count += 1
                
            except Exception as e:
                logger.error(
                    "WebSocket发送消息失败",
                    connection_id=self.connection_id,
                    error=str(e)
                )
                await self.manager.disconnect(self.connection_id)
        else:
            logger.warning(
                "WebSocket连接已断开，无法发送消息",
                connection_id=self.connection_id
            )
    
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """接收消息"""
        if self.websocket.state == WebSocketState.CONNECTED:
            try:
                message = await self.websocket.receive_json()
                self.last_activity = datetime.utcnow()
                return message
                
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket客户端断开",
                    connection_id=self.connection_id
                )
                await self.manager.disconnect(self.connection_id)
                return None
            except json.JSONDecodeError:
                logger.warning(
                    "WebSocket收到无效JSON",
                    connection_id=self.connection_id
                )
                await self.send_error("无效的JSON格式")
                return None
            except Exception as e:
                logger.error(
                    "WebSocket接收消息错误",
                    connection_id=self.connection_id,
                    error=str(e)
                )
                return None
        return None
    
    async def send_error(self, error_message: str, error_code: str = "WS_ERROR"):
        """发送错误消息"""
        error_msg = {
            "type": MessageType.ERROR.value,
            "error": {
                "code": error_code,
                "message": error_message
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_message(error_msg)
    
    async def _heartbeat_loop(self):
        """单个连接的心跳检查"""
        while True:
            try:
                # 检查连接健康状态
                if self.websocket.state == WebSocketState.DISCONNECTED:
                    break
                
                # 检查长时间无活动（5分钟）
                time_since_activity = (datetime.utcnow() - self.last_activity).total_seconds()
                if time_since_activity > 300:  # 5分钟
                    logger.warning(
                        "WebSocket连接超时",
                        connection_id=self.connection_id,
                        last_activity=self.last_activity.isoformat()
                    )
                    break
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "连接心跳检查错误",
                    connection_id=self.connection_id,
                    error=str(e)
                )
                break
        
        # 清理连接
        await self.manager.disconnect(self.connection_id)


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()


async def get_ws_manager() -> WebSocketManager:
    """获取WebSocket管理器依赖"""
    return ws_manager


# 市场数据推送函数
async def broadcast_market_data(market_data: MarketData, exchange: str, connection_type: ConnectionType):
    """广播市场数据"""
    message = {
        "type": MessageType.DATA.value,
        "data_type": "market_data",
        "data": {
            "symbol": market_data.symbol,
            "exchange": exchange,
            "price": float(market_data.current_price),
            "change": float(market_data.price_change_percent),
            "volume": float(market_data.volume_24h),
            "timestamp": market_data.timestamp.isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    subscription_key = f"{exchange}:{market_data.symbol}"
    await ws_manager.broadcast_message(message, "market_data", subscription_key)


async def broadcast_trade_update(trade: Trade, order_update: Dict[str, Any] = None):
    """广播交易更新"""
    message = {
        "type": MessageType.TRADE_UPDATE.value,
        "data": {
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "price": float(trade.price),
            "quantity": float(trade.quantity),
            "side": trade.side.value,
            "timestamp": trade.timestamp.isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if order_update:
        message["data"]["order_update"] = order_update
    
    await ws_manager.broadcast_message(message, "trading", trade.symbol)


# 订阅管理函数
async def handle_subscribe_message(connection_id: str, message: Dict[str, Any]):
    """处理订阅消息"""
    try:
        data = message.get("data", {})
        subscription_type = data.get("type")
        
        if subscription_type == "market_data":
            symbol = data.get("symbol")
            exchange = data.get("exchange", "binance")
            
            if symbol:
                await ws_manager.subscribe_market_data(connection_id, symbol, exchange)
                
        elif subscription_type == "trading":
            symbol = data.get("symbol")
            
            if symbol:
                await ws_manager.subscribe_trading(connection_id, symbol)
                
        elif subscription_type == "user":
            user_id = data.get("user_id")
            
            if user_id:
                await ws_manager.subscribe_user(connection_id, user_id)
        
    except Exception as e:
        logger.error(f"处理订阅消息失败: {e}")


if __name__ == "__main__":
    # 测试WebSocket管理器
    import asyncio
    
    async def test_ws_manager():
        print("测试WebSocket管理器...")
        
        stats = ws_manager.get_stats()
        print(f"初始状态: {stats}")
        
        await ws_manager.start_heartbeat()
        print("心跳任务已启动")
        
        # 模拟推送市场数据
        market_data = MarketData(
            symbol="BTCUSDT",
            current_price=50000.0,
            previous_close=49000.0,
            high_24h=51000.0,
            low_24h=48000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            volume_24h=1000000.0,
            quote_volume_24h=50000000.0,
            timestamp=datetime.utcnow()
        )
        
        await broadcast_market_data(market_data, "binance", ConnectionType.MARKET_DATA)
        print("市场数据已广播")
        
        # 等待几秒后停止
        await asyncio.sleep(5)
        await ws_manager.stop_heartbeat()
        print("测试完成")
    
    asyncio.run(test_ws_manager())