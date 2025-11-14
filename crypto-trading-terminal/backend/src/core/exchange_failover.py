"""
交易所故障转移管理器
实现当主交易所故障时自动切换到备用交易所的机制
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import weakref

import structlog

from ..adapters.base import BaseExchangeAdapter, MarketData
from ..core.market_analyzer import HealthStatus, HealthCheckResult
from ..core.exchange_priority import ExchangePriorityManager
from ..utils.exceptions import ExchangeConnectionError, FailoverError

logger = structlog.get_logger(__name__)


class FailoverMode(Enum):
    """故障转移模式"""
    ACTIVE_PASSIVE = "active_passive"  # 主备模式
    LOAD_BALANCING = "load_balancing"  # 负载均衡模式
    PRIORITY_BASED = "priority_based"  # 基于优先级


class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"    # 正常状态
    OPEN = "open"        # 断开状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class FailoverEvent:
    """故障转移事件"""
    id: str
    market_type: str
    from_exchange: str
    to_exchange: str
    reason: str
    timestamp: datetime
    duration_ms: float
    success: bool = True


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 3
    timeout_seconds: int = 30
    success_threshold: int = 2
    monitor_window_seconds: int = 60


class CircuitBreaker:
    """断路器实现"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # 检查超时
            if self.last_failure_time and self.last_failure_time < datetime.now(timezone.utc) - timedelta(seconds=self.config.timeout_seconds):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("断路器状态变更为半开")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """记录成功"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("断路器状态变更为关闭")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"断路器开启，失败次数: {self.failure_count}")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("断路器在半开状态下重新开启")
    
    def is_closed(self) -> bool:
        """检查是否关闭"""
        return self.state == CircuitBreakerState.CLOSED
    
    def is_open(self) -> bool:
        """检查是否开启"""
        return self.state == CircuitBreakerState.OPEN
    
    def reset(self):
        """重置断路器"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        logger.info("断路器已重置")


class ExchangeFailoverManager:
    """交易所故障转移管理器"""
    
    def __init__(self, data_aggregator):
        self.data_aggregator = data_aggregator
        self.priority_manager = ExchangePriorityManager()
        
        # 故障转移配置
        self.failover_mode = FailoverMode.PRIORITY_BASED
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_interval = 5  # 秒
        
        # 状态跟踪
        self.active_exchanges: Dict[str, str] = {}  # market_type -> exchange
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.failover_events: deque = deque(maxlen=1000)
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # 统计信息
        self.total_failover_events = 0
        self.successful_failovers = 0
        self.failed_failovers = 0
        self.failover_latency_samples = deque(maxlen=100)
        
        # 事件处理器
        self.failover_handlers: List[Callable] = []
        
        # 默认断路器配置
        default_config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=30,
            success_threshold=2
        )
        
        self.circuit_breaker_configs = {
            'spot': default_config,
            'futures': default_config
        }
        
        logger.info("交易所故障转移管理器初始化完成")
    
    async def start_monitoring(self):
        """开始故障转移监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # 启动监控任务
        for market_type in ['spot', 'futures']:
            task = asyncio.create_task(self._monitor_market_type(market_type))
            self.monitoring_tasks[market_type] = task
        
        logger.info("故障转移监控已启动")
    
    async def stop_monitoring(self):
        """停止故障转移监控"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        # 取消监控任务
        for task in self.monitoring_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.monitoring_tasks.clear()
        
        logger.info("故障转移监控已停止")
    
    async def _monitor_market_type(self, market_type: str):
        """监控特定市场类型"""
        try:
            while self.monitoring_active:
                await self._check_and_handle_failover(market_type)
                await asyncio.sleep(self.monitor_interval)
                
        except asyncio.CancelledError:
            logger.info(f"{market_type} 市场监控任务已取消")
        except Exception as e:
            logger.error(f"{market_type} 市场监控错误: {e}")
    
    async def _check_and_handle_failover(self, market_type: str):
        """检查并处理故障转移"""
        current_exchange = self.active_exchanges.get(market_type)
        
        if not current_exchange:
            # 首次选择交易所
            selected_exchange = await self._select_initial_exchange(market_type)
            if selected_exchange:
                self.active_exchanges[market_type] = selected_exchange
            return
        
        # 检查当前交易所健康状态
        health_result = self._get_exchange_health(current_exchange, market_type)
        
        if health_result and health_result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            # 交易所健康，记录成功
            self._record_success(current_exchange, market_type)
            
            # 检查是否可以恢复主交易所
            await self._check_main_recovery(market_type)
        else:
            # 交易所不健康，触发故障转移
            await self._trigger_failover(market_type, current_exchange, health_result)
    
    async def _select_initial_exchange(self, market_type: str) -> Optional[str]:
        """选择初始交易所"""
        # 使用优先级管理器选择最优交易所
        selected_exchange = self.priority_manager.get_optimal_exchange(market_type)
        
        if selected_exchange:
            # 检查交易所健康状态
            health_result = self._get_exchange_health(selected_exchange, market_type)
            
            if health_result and health_result.status != HealthStatus.CRITICAL:
                logger.info(f"选择初始交易所: {selected_exchange} ({market_type})")
                return selected_exchange
            else:
                # 如果首选不健康，尝试其他交易所
                for exchange in self.priority_manager.market_priorities.get(market_type, {}).keys():
                    if exchange != selected_exchange:
                        health_result = self._get_exchange_health(exchange, market_type)
                        if health_result and health_result.status != HealthStatus.CRITICAL:
                            logger.info(f"主交易所不可用，选择备用交易所: {exchange} ({market_type})")
                            return exchange
        
        return None
    
    async def _trigger_failover(self, market_type: str, failed_exchange: str, health_result: Optional[HealthCheckResult]):
        """触发故障转移"""
        failover_start_time = time.time()
        
        try:
            # 选择备用交易所
            backup_exchange = await self._select_backup_exchange(market_type, failed_exchange)
            
            if not backup_exchange:
                logger.error(f"没有可用的备用交易所: {market_type}")
                self.failed_failovers += 1
                return
            
            # 执行故障转移
            old_exchange = self.active_exchanges.get(market_type)
            self.active_exchanges[market_type] = backup_exchange
            
            # 记录故障转移事件
            failover_duration = (time.time() - failover_start_time) * 1000
            self.total_failover_events += 1
            self.successful_failovers += 1
            self.failover_latency_samples.append(failover_duration)
            
            event = FailoverEvent(
                id=f"{market_type}_{int(time.time())}",
                market_type=market_type,
                from_exchange=failed_exchange,
                to_exchange=backup_exchange,
                reason=health_result.error_message if health_result else "健康检查失败",
                timestamp=datetime.now(timezone.utc),
                duration_ms=failover_duration,
                success=True
            )
            
            self.failover_events.append(event)
            
            # 触发故障转移处理器
            await self._notify_failover_handlers(event)
            
            logger.info(
                f"故障转移完成: {market_type} {failed_exchange} -> {backup_exchange} "
                f"({failover_duration:.2f}ms)"
            )
            
        except Exception as e:
            logger.error(f"故障转移失败: {e}")
            self.failed_failovers += 1
            
            event = FailoverEvent(
                id=f"{market_type}_{int(time.time())}",
                market_type=market_type,
                from_exchange=failed_exchange,
                to_exchange="unknown",
                reason=str(e),
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - failover_start_time) * 1000,
                success=False
            )
            
            self.failover_events.append(event)
    
    async def _select_backup_exchange(self, market_type: str, excluded_exchange: str) -> Optional[str]:
        """选择备用交易所"""
        # 获取所有可用的交易所
        available_exchanges = []
        
        for exchange in self.priority_manager.market_priorities.get(market_type, {}).keys():
            if exchange != excluded_exchange:
                health_result = self._get_exchange_health(exchange, market_type)
                
                if health_result and health_result.status != HealthStatus.CRITICAL:
                    # 检查断路器状态
                    circuit_breaker = self.circuit_breakers.get(f"{exchange}_{market_type}")
                    if not circuit_breaker or circuit_breaker.can_execute():
                        available_exchanges.append((exchange, health_result.performance_score))
        
        if available_exchanges:
            # 按性能得分排序，选择最佳的备用交易所
            available_exchanges.sort(key=lambda x: x[1], reverse=True)
            return available_exchanges[0][0]
        
        return None
    
    def _get_exchange_health(self, exchange: str, market_type: str) -> Optional[HealthCheckResult]:
        """获取交易所健康状态"""
        # 这里应该从健康监控器获取实际健康状态
        # 暂时返回模拟数据
        return None
    
    def _record_success(self, exchange: str, market_type: str):
        """记录成功"""
        circuit_breaker_key = f"{exchange}_{market_type}"
        if circuit_breaker_key in self.circuit_breakers:
            self.circuit_breakers[circuit_breaker_key].record_success()
    
    async def _check_main_recovery(self, market_type: str):
        """检查主交易所是否恢复"""
        current_exchange = self.active_exchanges.get(market_type)
        
        # 获取优先级配置
        priorities = self.priority_manager.market_priorities.get(market_type, {})
        
        # 按优先级排序交易所
        sorted_exchanges = sorted(
            priorities.items(),
            key=lambda x: x[1].priority
        )
        
        # 检查是否有更高优先级的交易所可用
        for exchange, config in sorted_exchanges:
            if exchange == current_exchange:
                break
            
            health_result = self._get_exchange_health(exchange, market_type)
            circuit_breaker_key = f"{exchange}_{market_type}"
            
            if (health_result and 
                health_result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED] and
                (circuit_breaker_key not in self.circuit_breakers or 
                 self.circuit_breakers[circuit_breaker_key].is_closed())):
                
                logger.info(f"主交易所恢复，重新选择: {market_type} {current_exchange} -> {exchange}")
                
                # 执行恢复
                self.active_exchanges[market_type] = exchange
                break
    
    async def get_active_exchange(self, market_type: str) -> Optional[str]:
        """获取当前活跃的交易所"""
        if market_type not in self.active_exchanges:
            # 初始化选择
            selected_exchange = await self._select_initial_exchange(market_type)
            if selected_exchange:
                self.active_exchanges[market_type] = selected_exchange
        
        return self.active_exchanges.get(market_type)
    
    async def wait_for_failover(self, market_type: str, timeout: float = 10.0) -> bool:
        """等待故障转移完成"""
        start_time = time.time()
        original_exchange = await self.get_active_exchange(market_type)
        
        while time.time() - start_time < timeout:
            current_exchange = await self.get_active_exchange(market_type)
            
            if current_exchange != original_exchange:
                return True
            
            await asyncio.sleep(0.1)
        
        return False
    
    async def wait_for_recovery(self, market_type: str, timeout: float = 10.0) -> bool:
        """等待恢复完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查是否有更高优先级的交易所可用
            current_exchange = await self.get_active_exchange(market_type)
            priorities = self.priority_manager.market_priorities.get(market_type, {})
            
            if priorities:
                # 获取优先级最高的可用交易所
                for exchange, config in sorted(priorities.items(), key=lambda x: x[1].priority):
                    health_result = self._get_exchange_health(exchange, market_type)
                    
                    if (exchange != current_exchange and 
                        health_result and 
                        health_result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]):
                        
                        logger.info(f"等待恢复完成: {market_type} 当前 {current_exchange} -> {exchange}")
                        return True
            
            await asyncio.sleep(0.1)
        
        return False
    
    async def get_market_data_with_failover(self, market_type: str, symbol: str) -> Optional[MarketData]:
        """带故障转移的市场数据获取"""
        exchange = await self.get_active_exchange(market_type)
        
        if not exchange:
            raise FailoverError("没有可用的交易所")
        
        try:
            # 从数据聚合器获取数据
            market_data = await self.data_aggregator.get_market_data(exchange, market_type, symbol)
            
            # 记录学习数据
            self.priority_manager.record_learning_data(market_type, exchange, True, 0)
            
            return market_data
            
        except Exception as e:
            # 记录学习数据
            self.priority_manager.record_learning_data(market_type, exchange, False, 0, 1)
            
            # 触发故障转移
            circuit_breaker_key = f"{exchange}_{market_type}"
            if circuit_breaker_key not in self.circuit_breakers:
                config = self.circuit_breaker_configs.get(market_type, CircuitBreakerConfig())
                self.circuit_breakers[circuit_breaker_key] = CircuitBreaker(config)
            
            self.circuit_breakers[circuit_breaker_key].record_failure()
            
            raise e
    
    def set_failover_mode(self, mode: FailoverMode):
        """设置故障转移模式"""
        self.failover_mode = mode
        logger.info(f"故障转移模式已设置为: {mode.value}")
    
    def set_circuit_breaker_threshold(self, market_type: str, failure_count: int, timeout_seconds: int):
        """设置断路器阈值"""
        self.circuit_breaker_configs[market_type] = CircuitBreakerConfig(
            failure_threshold=failure_count,
            timeout_seconds=timeout_seconds
        )
        logger.info(f"已设置 {market_type} 市场断路器阈值: {failure_count} 失败, {timeout_seconds}秒超时")
    
    def add_failover_handler(self, handler: Callable[[FailoverEvent], None]):
        """添加故障转移事件处理器"""
        self.failover_handlers.append(handler)
    
    async def _notify_failover_handlers(self, event: FailoverEvent):
        """通知故障转移处理器"""
        for handler in self.failover_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"故障转移处理器执行失败: {e}")
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """获取故障转移统计信息"""
        avg_latency = sum(self.failover_latency_samples) / len(self.failover_latency_samples) if self.failover_latency_samples else 0
        
        return {
            "total_failover_events": self.total_failover_events,
            "successful_failovers": self.successful_failovers,
            "failed_failovers": self.failed_failovers,
            "success_rate": (self.successful_failovers / self.total_failover_events * 100) if self.total_failover_events > 0 else 0,
            "avg_failover_latency_ms": avg_latency,
            "last_failover_time": self.failover_events[-1].timestamp.isoformat() if self.failover_events else None,
            "market_failover_counts": {
                event.market_type: sum(1 for e in self.failover_events if e.market_type == event.market_type)
                for event in self.failover_events
            },
            "active_exchanges": dict(self.active_exchanges),
            "circuit_breaker_states": {
                key: breaker.state.value
                for key, breaker in self.circuit_breakers.items()
            }
        }


# 全局实例
_failover_manager: Optional[ExchangeFailoverManager] = None


async def get_failover_manager(data_aggregator) -> ExchangeFailoverManager:
    """获取全局故障转移管理器实例"""
    global _failover_manager
    
    if _failover_manager is None:
        _failover_manager = ExchangeFailoverManager(data_aggregator)
    
    return _failover_manager


async def shutdown_failover_manager():
    """关闭故障转移管理器"""
    global _failover_manager
    
    if _failover_manager:
        await _failover_manager.stop_monitoring()
        _failover_manager = None


if __name__ == "__main__":
    # 测试故障转移管理器
    import asyncio
    
    async def test_failover_manager():
        print("测试故障转移管理器...")
        
        try:
            # 模拟数据聚合器
            data_aggregator = Mock()
            
            manager = await get_failover_manager(data_aggregator)
            
            # 获取统计信息
            stats = manager.get_failover_statistics()
            print(f"故障转移统计: {json.dumps(stats, indent=2, default=str)}")
            
        except Exception as e:
            print(f"测试失败: {e}")
        finally:
            await shutdown_failover_manager()
    
    asyncio.run(test_failover_manager())