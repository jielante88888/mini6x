"""
交易所状态管理系统
实时跟踪和管理所有交易所的连接状态、性能指标和健康状况
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import weakref

import structlog

from ..adapters.base import BaseExchangeAdapter
from ..core.market_analyzer import HealthStatus, HealthCheckResult, PerformanceMetrics, AlertEvent, AlertLevel
from ..storage.redis_cache import get_market_cache

logger = structlog.get_logger(__name__)


class ConnectionStatus(Enum):
    """连接状态"""
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class ExchangeStatus(Enum):
    """交易所状态"""
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class ExchangeConnectionInfo:
    """交易所连接信息"""
    exchange: str
    market_type: str
    connection_status: ConnectionStatus
    api_status: Dict[str, str]  # spot_api, futures_api, websocket
    connection_time: datetime
    last_heartbeat: Optional[datetime] = None
    reconnect_attempts: int = 0
    last_error: Optional[str] = None
    latency_ms: float = 0.0
    error_count: int = 0


@dataclass
class ExchangeStatusSummary:
    """交易所状态摘要"""
    exchange: str
    overall_status: ExchangeStatus
    spot_status: ExchangeStatus
    futures_status: ExchangeStatus
    last_update: datetime
    uptime_percentage: float
    error_count: int
    performance_score: float
    active_connections: int


class ExchangeStatusManager:
    """交易所状态管理器"""
    
    def __init__(self):
        self.connections: Dict[str, ExchangeConnectionInfo] = {}
        self.status_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alert_handlers: List[Callable] = []
        self.status_subscribers: Set[Callable] = set()
        
        # 状态监控配置
        self.heartbeat_interval = 30  # 秒
        self.status_check_interval = 10  # 秒
        self.connection_timeout = 30  # 秒
        self.reconnect_delay = 5  # 秒
        
        # 统计信息
        self.total_connection_time = defaultdict(float)
        self.uptime_statistics = defaultdict(lambda: {'total_time': 0, 'up_time': 0})
        
        # 缓存管理器
        self.cache_manager = get_market_cache()
        
        # 监控任务
        self.monitoring_active = False
        self.monitor_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("交易所状态管理器初始化完成")
    
    async def start_monitoring(self, adapters: Dict[str, BaseExchangeAdapter]):
        """开始状态监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # 初始化连接状态
        for adapter_key, adapter in adapters.items():
            exchange, market_type = adapter_key.split('_', 1)
            await self._initialize_connection(exchange, market_type, adapter)
        
        # 启动监控任务
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        status_task = asyncio.create_task(self._status_check_loop())
        
        self.monitor_tasks['heartbeat'] = heartbeat_task
        self.monitor_tasks['status'] = status_task
        
        logger.info("交易所状态监控已启动")
    
    async def stop_monitoring(self):
        """停止状态监控"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        # 取消监控任务
        for task in self.monitor_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.monitor_tasks.clear()
        
        logger.info("交易所状态监控已停止")
    
    async def _initialize_connection(self, exchange: str, market_type: str, adapter: BaseExchangeAdapter):
        """初始化连接状态"""
        connection_key = f"{exchange}_{market_type}"
        
        # 测试连接
        try:
            connection_status = ConnectionStatus.CONNECTING
            
            if await adapter.is_healthy():
                connection_status = ConnectionStatus.CONNECTED
            else:
                connection_status = ConnectionStatus.DISCONNECTED
            
            connection_info = ExchangeConnectionInfo(
                exchange=exchange,
                market_type=market_type,
                connection_status=connection_status,
                api_status={
                    'spot_api': 'connected' if market_type == 'spot' else 'disconnected',
                    'futures_api': 'connected' if market_type == 'futures' else 'disconnected',
                    'websocket': 'connected'  # 默认连接
                },
                connection_time=datetime.now(timezone.utc),
                last_heartbeat=datetime.now(timezone.utc)
            )
            
            self.connections[connection_key] = connection_info
            
            # 记录连接状态历史
            self._record_status_change(connection_key, connection_status)
            
            logger.info(f"交易所连接状态初始化: {connection_key} - {connection_status.value}")
            
        except Exception as e:
            logger.error(f"初始化连接失败 {connection_key}: {e}")
            
            connection_info = ExchangeConnectionInfo(
                exchange=exchange,
                market_type=market_type,
                connection_status=ConnectionStatus.FAILED,
                api_status={'error': str(e)},
                connection_time=datetime.now(timezone.utc)
            )
            
            self.connections[connection_key] = connection_info
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.monitoring_active:
                await self._send_heartbeats()
                await asyncio.sleep(self.heartbeat_interval)
                
        except asyncio.CancelledError:
            logger.info("心跳任务已取消")
        except Exception as e:
            logger.error(f"心跳循环错误: {e}")
    
    async def _status_check_loop(self):
        """状态检查循环"""
        try:
            while self.monitoring_active:
                await self._check_connection_status()
                await asyncio.sleep(self.status_check_interval)
                
        except asyncio.CancelledError:
            logger.info("状态检查任务已取消")
        except Exception as e:
            logger.error(f"状态检查循环错误: {e}")
    
    async def _send_heartbeats(self):
        """发送心跳"""
        for connection_key, connection_info in self.connections.items():
            try:
                # 模拟心跳发送
                connection_info.last_heartbeat = datetime.now(timezone.utc)
                
                # 检查心跳超时
                heartbeat_age = (datetime.now(timezone.utc) - connection_info.last_heartbeat).total_seconds()
                if heartbeat_age > self.connection_timeout:
                    await self._handle_heartbeat_timeout(connection_key, connection_info)
                
            except Exception as e:
                logger.error(f"心跳发送失败 {connection_key}: {e}")
    
    async def _handle_heartbeat_timeout(self, connection_key: str, connection_info: ExchangeConnectionInfo):
        """处理心跳超时"""
        if connection_info.connection_status != ConnectionStatus.DISCONNECTED:
            logger.warning(f"心跳超时: {connection_key}")
            
            # 更新连接状态
            await self._update_connection_status(connection_key, ConnectionStatus.DISCONNECTED, "心跳超时")
            
            # 尝试重连
            if connection_info.reconnect_attempts < 5:
                asyncio.create_task(self._attempt_reconnection(connection_key))
    
    async def _check_connection_status(self):
        """检查连接状态"""
        for connection_key, connection_info in self.connections.items():
            try:
                # 检查连接有效性
                is_healthy = await self._check_connection_health(connection_key)
                
                if not is_healthy and connection_info.connection_status == ConnectionStatus.CONNECTED:
                    await self._update_connection_status(connection_key, ConnectionStatus.DISCONNECTED, "连接健康检查失败")
                
                # 更新统计信息
                self._update_uptime_statistics(connection_key, connection_info.connection_status)
                
            except Exception as e:
                logger.error(f"连接状态检查失败 {connection_key}: {e}")
    
    async def _check_connection_health(self, connection_key: str) -> bool:
        """检查连接健康状态"""
        try:
            # 这里应该实现实际的健康检查逻辑
            # 目前返回模拟数据
            connection_info = self.connections[connection_key]
            
            # 检查是否有最近的心跳
            if connection_info.last_heartbeat:
                heartbeat_age = (datetime.now(timezone.utc) - connection_info.last_heartbeat).total_seconds()
                if heartbeat_age > self.connection_timeout:
                    return False
            
            # 检查错误次数
            if connection_info.error_count > 10:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _attempt_reconnection(self, connection_key: str):
        """尝试重连"""
        connection_info = self.connections.get(connection_key)
        if not connection_info:
            return
        
        logger.info(f"尝试重连: {connection_key} (第{connection_info.reconnect_attempts + 1}次)")
        
        try:
            # 更新重连尝试次数
            connection_info.reconnect_attempts += 1
            await self._update_connection_status(connection_key, ConnectionStatus.RECONNECTING, f"重连尝试 {connection_info.reconnect_attempts}")
            
            # 等待重连延迟
            await asyncio.sleep(self.reconnect_delay)
            
            # 尝试连接
            # 这里应该调用实际的适配器连接逻辑
            # connection_success = await adapter.connect()
            
            # 模拟连接成功
            connection_success = True
            
            if connection_success:
                await self._update_connection_status(connection_key, ConnectionStatus.CONNECTED, "重连成功")
                connection_info.reconnect_attempts = 0
                connection_info.error_count = 0
                logger.info(f"重连成功: {connection_key}")
            else:
                await self._update_connection_status(connection_key, ConnectionStatus.FAILED, "重连失败")
                logger.warning(f"重连失败: {connection_key}")
                
        except Exception as e:
            await self._update_connection_status(connection_key, ConnectionStatus.FAILED, f"重连异常: {e}")
            logger.error(f"重连异常 {connection_key}: {e}")
    
    async def _update_connection_status(self, connection_key: str, status: ConnectionStatus, reason: str = ""):
        """更新连接状态"""
        connection_info = self.connections.get(connection_key)
        if not connection_info:
            return
        
        old_status = connection_info.connection_status
        connection_info.connection_status = status
        
        if reason:
            connection_info.last_error = reason
        
        # 记录状态变化
        self._record_status_change(connection_key, status)
        
        # 通知状态变化监听器
        await self._notify_status_subscribers(connection_key, old_status, status)
        
        # 触发状态变化事件
        if old_status != status:
            logger.info(f"连接状态变化: {connection_key} {old_status.value} -> {status.value} ({reason})")
    
    def _record_status_change(self, connection_key: str, status: ConnectionStatus):
        """记录状态变化历史"""
        timestamp = datetime.now(timezone.utc)
        self.status_history[connection_key].append({
            'timestamp': timestamp,
            'status': status.value,
            'connection_time': time.time()
        })
    
    async def _notify_status_subscribers(self, connection_key: str, old_status: ConnectionStatus, new_status: ConnectionStatus):
        """通知状态变化监听器"""
        for subscriber in self.status_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(connection_key, old_status, new_status)
                else:
                    subscriber(connection_key, old_status, new_status)
            except Exception as e:
                logger.error(f"状态变化通知失败: {e}")
    
    def _update_uptime_statistics(self, connection_key: str, status: ConnectionStatus):
        """更新运行时间统计"""
        stats = self.uptime_statistics[connection_key]
        current_time = time.time()
        
        # 如果状态已连接，记录运行时间
        if status == ConnectionStatus.CONNECTED:
            if not hasattr(stats, 'last_update_time'):
                stats['last_update_time'] = current_time
            
            time_delta = current_time - stats['last_update_time']
            stats['up_time'] += time_delta
        
        stats['total_time'] += self.status_check_interval
        stats['last_update_time'] = current_time
    
    async def get_connection_status(self, exchange: str, market_type: str) -> Optional[ExchangeConnectionInfo]:
        """获取连接状态"""
        connection_key = f"{exchange}_{market_type}"
        return self.connections.get(connection_key)
    
    async def get_all_connection_status(self) -> Dict[str, ExchangeConnectionInfo]:
        """获取所有连接状态"""
        return dict(self.connections)
    
    def get_exchange_status_summary(self, exchange: str) -> Optional[ExchangeStatusSummary]:
        """获取交易所状态摘要"""
        # 获取现货和期货连接状态
        spot_connection = self.connections.get(f"{exchange}_spot")
        futures_connection = self.connections.get(f"{exchange}_futures")
        
        if not spot_connection and not futures_connection:
            return None
        
        # 计算整体状态
        status_scores = []
        if spot_connection:
            spot_score = self._calculate_status_score(spot_connection.connection_status)
            status_scores.append(spot_score)
        
        if futures_connection:
            futures_score = self._calculate_status_score(futures_connection.connection_status)
            status_scores.append(futures_score)
        
        overall_score = sum(status_scores) / len(status_scores) if status_scores else 0
        overall_status = self._score_to_status(overall_score)
        
        # 计算现货状态
        spot_status = ExchangeStatus.ONLINE if spot_connection and spot_connection.connection_status == ConnectionStatus.CONNECTED else ExchangeStatus.OFFLINE
        if spot_connection and spot_connection.connection_status == ConnectionStatus.DISCONNECTED:
            spot_status = ExchangeStatus.DEGRADED
        elif spot_connection and spot_connection.connection_status == ConnectionStatus.FAILED:
            spot_status = ExchangeStatus.ERROR
        
        # 计算期货状态
        futures_status = ExchangeStatus.ONLINE if futures_connection and futures_connection.connection_status == ConnectionStatus.CONNECTED else ExchangeStatus.OFFLINE
        if futures_connection and futures_connection.connection_status == ConnectionStatus.DISCONNECTED:
            futures_status = ExchangeStatus.DEGRADED
        elif futures_connection and futures_connection.connection_status == ConnectionStatus.FAILED:
            futures_status = ExchangeStatus.ERROR
        
        # 计算运行时间百分比
        uptime_percentages = []
        for connection_key in [f"{exchange}_spot", f"{exchange}_futures"]:
            stats = self.uptime_statistics.get(connection_key)
            if stats and stats['total_time'] > 0:
                uptime = (stats['up_time'] / stats['total_time']) * 100
                uptime_percentages.append(uptime)
        
        avg_uptime = sum(uptime_percentages) / len(uptime_percentages) if uptime_percentages else 0
        
        # 计算错误总数
        total_errors = 0
        if spot_connection:
            total_errors += spot_connection.error_count
        if futures_connection:
            total_errors += futures_connection.error_count
        
        # 计算性能得分
        performance_score = max(0, 1 - (total_errors / 100))  # 简单的性能计算
        
        return ExchangeStatusSummary(
            exchange=exchange,
            overall_status=overall_status,
            spot_status=spot_status,
            futures_status=futures_status,
            last_update=datetime.now(timezone.utc),
            uptime_percentage=avg_uptime,
            error_count=total_errors,
            performance_score=performance_score,
            active_connections=sum(1 for conn in self.connections.values() if conn.connection_status == ConnectionStatus.CONNECTED)
        )
    
    def _calculate_status_score(self, status: ConnectionStatus) -> float:
        """计算状态得分"""
        score_map = {
            ConnectionStatus.CONNECTED: 1.0,
            ConnectionStatus.CONNECTING: 0.7,
            ConnectionStatus.RECONNECTING: 0.5,
            ConnectionStatus.DISCONNECTED: 0.3,
            ConnectionStatus.FAILED: 0.1,
            ConnectionStatus.MAINTENANCE: 0.0
        }
        return score_map.get(status, 0.0)
    
    def _score_to_status(self, score: float) -> ExchangeStatus:
        """将得分转换为状态"""
        if score >= 0.8:
            return ExchangeStatus.ONLINE
        elif score >= 0.5:
            return ExchangeStatus.DEGRADED
        elif score >= 0.2:
            return ExchangeStatus.OFFLINE
        else:
            return ExchangeStatus.ERROR
    
    async def get_all_exchanges_status(self) -> Dict[str, ExchangeStatusSummary]:
        """获取所有交易所状态"""
        exchanges = set()
        for connection_key in self.connections.keys():
            exchange, _ = connection_key.split('_', 1)
            exchanges.add(exchange)
        
        status_summaries = {}
        for exchange in exchanges:
            summary = self.get_exchange_status_summary(exchange)
            if summary:
                status_summaries[exchange] = summary
        
        return status_summaries
    
    def add_status_subscriber(self, subscriber: Callable[[str, ConnectionStatus, ConnectionStatus], None]):
        """添加状态变化监听器"""
        self.status_subscribers.add(subscriber)
    
    def remove_status_subscriber(self, subscriber: Callable[[str, ConnectionStatus, ConnectionStatus], None]):
        """移除状态变化监听器"""
        self.status_subscribers.discard(subscriber)
    
    async def force_reconnection(self, exchange: str, market_type: str) -> bool:
        """强制重连"""
        connection_key = f"{exchange}_{market_type}"
        connection_info = self.connections.get(connection_key)
        
        if not connection_info:
            return False
        
        # 如果已经在重连中，跳过
        if connection_info.connection_status == ConnectionStatus.RECONNECTING:
            return False
        
        logger.info(f"强制重连: {connection_key}")
        
        # 启动重连任务
        asyncio.create_task(self._attempt_reconnection(connection_key))
        
        return True
    
    async def get_connection_statistics(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        total_connections = len(self.connections)
        connected_count = sum(1 for conn in self.connections.values() if conn.connection_status == ConnectionStatus.CONNECTED)
        disconnected_count = sum(1 for conn in self.connections.values() if conn.connection_status == ConnectionStatus.DISCONNECTED)
        failed_count = sum(1 for conn in self.connections.values() if conn.connection_status == ConnectionStatus.FAILED)
        
        avg_uptime = 0
        if self.uptime_statistics:
            uptimes = []
            for stats in self.uptime_statistics.values():
                if stats['total_time'] > 0:
                    uptime = (stats['up_time'] / stats['total_time']) * 100
                    uptimes.append(uptime)
            avg_uptime = sum(uptimes) / len(uptimes) if uptimes else 0
        
        total_errors = sum(conn.error_count for conn in self.connections.values())
        
        return {
            "total_connections": total_connections,
            "connected_count": connected_count,
            "disconnected_count": disconnected_count,
            "failed_count": failed_count,
            "connection_rate": (connected_count / total_connections * 100) if total_connections > 0 else 0,
            "average_uptime_percentage": avg_uptime,
            "total_errors": total_errors,
            "monitoring_active": self.monitoring_active,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    def get_status_history(self, exchange: str, market_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取状态历史"""
        connection_key = f"{exchange}_{market_type}"
        history = self.status_history.get(connection_key, [])
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 过滤时间范围内的记录
        filtered_history = [
            record for record in history
            if record['timestamp'] >= cutoff_time
        ]
        
        return [asdict(record) if hasattr(record, '__dict__') else record for record in filtered_history]


# 全局实例
_status_manager: Optional[ExchangeStatusManager] = None


async def get_status_manager() -> ExchangeStatusManager:
    """获取全局状态管理器实例"""
    global _status_manager
    
    if _status_manager is None:
        _status_manager = ExchangeStatusManager()
    
    return _status_manager


async def shutdown_status_manager():
    """关闭状态管理器"""
    global _status_manager
    
    if _status_manager:
        await _status_manager.stop_monitoring()
        _status_manager = None


if __name__ == "__main__":
    # 测试状态管理器
    import asyncio
    
    async def test_status_manager():
        print("测试状态管理器...")
        
        try:
            manager = await get_status_manager()
            
            # 获取统计信息
            stats = await manager.get_connection_statistics()
            print(f"连接统计: {json.dumps(stats, indent=2, default=str)}")
            
        except Exception as e:
            print(f"测试失败: {e}")
        finally:
            await shutdown_status_manager()
    
    asyncio.run(test_status_manager())