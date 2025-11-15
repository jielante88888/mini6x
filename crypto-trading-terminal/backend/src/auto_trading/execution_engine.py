"""
执行引擎
负责高性能订单执行，包含智能重试、故障转移、并发管理等机制
"""

import asyncio
import logging
import time
import random
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import json

from ..storage.models import (
    Order, Account, ExecutionResultStatus, MarketType,
    OrderType, OrderSide, OrderStatus
)
from ..utils.exceptions import ExchangeException, NetworkException, TimeoutException


logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE_RETRY = "immediate_retry"


@dataclass
class ExecutionConfig:
    """执行配置"""
    max_retries: int = 3
    timeout_seconds: float = 30.0
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    concurrent_limit: int = 10
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_time: float = 300.0  # 5分钟
    enable_failover: bool = True
    failover_exchanges: List[str] = None

    def __post_init__(self):
        if self.failover_exchanges is None:
            self.failover_exchanges = []


@dataclass
class ExecutionRequest:
    """执行请求"""
    order_id: int
    account_id: int
    symbol: str
    order_side: OrderSide
    quantity: Decimal
    order_type: OrderType
    price: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    market_type: MarketType = MarketType.SPOT
    priority: int = 0  # 0-10, 10为最高优先级
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    order_id: int
    exchange_order_id: Optional[str] = None
    filled_quantity: Optional[Decimal] = None
    average_price: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    latency_ms: Optional[float] = None
    retry_count: int = 0
    execution_time: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    exchange_used: Optional[str] = None
    execution_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now()


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_time: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_time:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker 进入半开状态")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        
        return False
    
    def record_success(self):
        """记录成功"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker 恢复到关闭状态")
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker 打开，失败次数: {self.failure_count}")


class ExchangeAdapter:
    """交易所适配器"""
    
    def __init__(self, exchange_name: str, api_key: str = None, api_secret: str = None):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.circuit_breaker = CircuitBreaker()
        self.session = None
    
    async def initialize(self):
        """初始化连接"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
    
    async def place_order(self, request: ExecutionRequest) -> Dict[str, Any]:
        """下单（模拟实现）"""
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(f"Circuit breaker is open for {self.exchange_name}")
        
        try:
            start_time = time.time()
            
            # 模拟网络延迟
            await asyncio.sleep(random.uniform(0.05, 0.2))
            
            # 模拟成功/失败
            if random.random() < 0.85:  # 85%成功率
                execution_time = (time.time() - start_time) * 1000
                
                self.circuit_breaker.record_success()
                
                return {
                    'success': True,
                    'order_id': f"{self.exchange_name}_{request.order_id}_{int(time.time())}",
                    'filled_quantity': float(request.quantity),
                    'average_price': float(request.price or 50000),
                    'commission': float(request.quantity * 0.001),
                    'latency_ms': execution_time,
                    'status': 'filled'
                }
            else:
                self.circuit_breaker.record_failure()
                
                # 随机选择错误类型
                error_types = ['NETWORK_ERROR', 'INSUFFICIENT_BALANCE', 'INVALID_SYMBOL', 'RATE_LIMIT']
                error_type = random.choice(error_types)
                
                raise ExchangeException(f"Exchange error: {error_type}")
                
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise


class CircuitBreakerOpenException(Exception):
    """熔断器开启异常"""
    pass


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        self.exchanges: Dict[str, ExchangeAdapter] = {}
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        self.active_executions: Dict[int, asyncio.Task] = {}
        self.execution_stats: Dict[str, int] = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'retried_executions': 0,
            'circuit_breaker_trips': 0
        }
        self._shutdown_event = asyncio.Event()
        
        # 初始化默认交易所适配器
        self._initialize_default_exchanges()
    
    def _initialize_default_exchanges(self):
        """初始化默认交易所适配器"""
        primary_exchanges = ['binance', 'okx']
        for exchange_name in primary_exchanges:
            self.exchanges[exchange_name] = ExchangeAdapter(exchange_name)
    
    async def start(self):
        """启动执行引擎"""
        # 初始化所有交易所连接
        for exchange in self.exchanges.values():
            await exchange.initialize()
        
        # 启动执行循环
        execution_task = asyncio.create_task(self._execution_loop())
        
        # 启动监控任务
        monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("执行引擎已启动")
        
        # 等待关闭事件
        await self._shutdown_event.wait()
        
        # 取消任务
        execution_task.cancel()
        monitor_task.cancel()
        
        # 关闭交易所连接
        for exchange in self.exchanges.values():
            await exchange.close()
        
        logger.info("执行引擎已关闭")
    
    async def stop(self):
        """停止执行引擎"""
        self._shutdown_event.set()
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """执行订单"""
        if request.order_id in self.active_executions:
            raise ValueError(f"Order {request.order_id} is already executing")
        
        # 创建执行任务
        execution_task = asyncio.create_task(self._execute_order_internal(request))
        self.active_executions[request.order_id] = execution_task
        
        try:
            result = await execution_task
            return result
        finally:
            # 清理活跃执行记录
            self.active_executions.pop(request.order_id, None)
    
    async def _execute_order_internal(self, request: ExecutionRequest) -> ExecutionResult:
        """内部订单执行逻辑"""
        start_time = time.time()
        retry_count = 0
        last_error = None
        exchanges_attempted = []
        
        # 选择首选交易所
        primary_exchange = self._select_primary_exchange(request)
        failover_exchanges = self.config.failover_exchanges.copy()
        if primary_exchange in failover_exchanges:
            failover_exchanges.remove(primary_exchange)
        
        # 准备交易所列表（主备顺序）
        exchanges_to_try = [primary_exchange] + failover_exchanges
        
        while retry_count <= self.config.max_retries:
            for exchange_name in exchanges_to_try:
                if exchange_name in exchanges_attempted:
                    continue
                
                exchanges_attempted.append(exchange_name)
                
                try:
                    # 检查熔断器状态
                    exchange = self.exchanges.get(exchange_name)
                    if not exchange or not exchange.circuit_breaker.can_execute():
                        logger.warning(f"交易所 {exchange_name} 不可用，跳过")
                        continue
                    
                    # 执行订单
                    exchange_result = await exchange.place_order(request)
                    
                    # 记录成功统计
                    self.execution_stats['total_executions'] += 1
                    self.execution_stats['successful_executions'] += 1
                    
                    # 返回成功结果
                    return ExecutionResult(
                        success=True,
                        order_id=request.order_id,
                        exchange_order_id=exchange_result['order_id'],
                        filled_quantity=Decimal(str(exchange_result['filled_quantity'])),
                        average_price=Decimal(str(exchange_result['average_price'])),
                        commission=Decimal(str(exchange_result['commission'])),
                        latency_ms=exchange_result['latency_ms'],
                        retry_count=retry_count,
                        execution_time=datetime.now(),
                        exchange_used=exchange_name,
                        execution_details=exchange_result
                    )
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"交易所 {exchange_name} 执行失败: {e}")
                    continue
            
            # 所有交易所都失败了，决定是否重试
            retry_count += 1
            self.execution_stats['retried_executions'] += 1
            
            if retry_count <= self.config.max_retries:
                # 计算重试延迟
                retry_delay = self._calculate_retry_delay(retry_count)
                logger.info(f"准备重试订单 {request.order_id}，第 {retry_count} 次重试，延迟 {retry_delay:.2f}s")
                
                # 等待重试延迟（可能被取消）
                try:
                    await asyncio.wait_for(
                        asyncio.sleep(retry_delay),
                        timeout=self.config.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    break
        
        # 执行失败
        self.execution_stats['total_executions'] += 1
        self.execution_stats['failed_executions'] += 1
        
        return ExecutionResult(
            success=False,
            order_id=request.order_id,
            retry_count=retry_count,
            execution_time=datetime.now(),
            error_code="EXECUTION_FAILED",
            error_message=str(last_error) if last_error else "Unknown error",
            exchange_used=exchanges_attempted[-1] if exchanges_attempted else None,
            execution_details={
                'exchanges_attempted': exchanges_attempted,
                'total_attempts': len(exchanges_attempted)
            }
        )
    
    def _select_primary_exchange(self, request: ExecutionRequest) -> str:
        """选择首选交易所"""
        # 简单的选择逻辑：基于市场类型和符号
        if request.market_type == MarketType.FUTURES:
            # 期货主要使用binance
            return 'binance'
        else:
            # 现货随机选择（可以实现更复杂的逻辑）
            return random.choice(['binance', 'okx'])
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟"""
        if self.config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_retry_delay * (2 ** (retry_count - 1))
            return min(delay, self.config.max_retry_delay)
        elif self.config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(retry_count * self.config.base_retry_delay, self.config.max_retry_delay)
        elif self.config.retry_strategy == RetryStrategy.FIXED_INTERVAL:
            return self.config.base_retry_delay
        elif self.config.retry_strategy == RetryStrategy.IMMEDIATE_RETRY:
            return 0.1
        else:
            return self.config.base_retry_delay
    
    async def _execution_loop(self):
        """执行循环（可以处理队列中的请求）"""
        while not self._shutdown_event.is_set():
            try:
                # 非阻塞式获取执行请求
                try:
                    request = await asyncio.wait_for(
                        self.execution_queue.get(),
                        timeout=1.0
                    )
                    
                    # 异步执行订单
                    asyncio.create_task(self.execute_order(request))
                    
                except asyncio.TimeoutError:
                    # 没有新的请求，继续循环
                    continue
                    
            except Exception as e:
                logger.error(f"执行循环错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _monitor_loop(self):
        """监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # 记录执行统计
                if self.execution_stats['total_executions'] > 0:
                    success_rate = (
                        self.execution_stats['successful_executions'] / 
                        self.execution_stats['total_executions'] * 100
                    )
                    
                    logger.info(f"执行统计: 总计={self.execution_stats['total_executions']}, "
                              f"成功={self.execution_stats['successful_executions']}, "
                              f"失败={self.execution_stats['failed_executions']}, "
                              f"重试={self.execution_stats['retried_executions']}, "
                              f"成功率={success_rate:.1f}%")
                
                # 检查交易所熔断器状态
                for exchange_name, exchange in self.exchanges.items():
                    if exchange.circuit_breaker.state != "CLOSED":
                        logger.warning(f"交易所 {exchange_name} 熔断器状态: {exchange.circuit_breaker.state}")
                
                await asyncio.sleep(30)  # 30秒监控间隔
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(5)
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = self.execution_stats['total_executions']
        
        return {
            'execution_stats': self.execution_stats.copy(),
            'success_rate': (
                self.execution_stats['successful_executions'] / total * 100 
                if total > 0 else 0
            ),
            'active_executions': len(self.active_executions),
            'queue_size': self.execution_queue.qsize(),
            'exchange_status': {
                name: {
                    'circuit_breaker_state': exchange.circuit_breaker.state,
                    'failure_count': exchange.circuit_breaker.failure_count
                }
                for name, exchange in self.exchanges.items()
            }
        }
    
    async def add_exchange(self, exchange: ExchangeAdapter):
        """添加交易所适配器"""
        self.exchanges[exchange.exchange_name] = exchange
        await exchange.initialize()
        logger.info(f"添加交易所: {exchange.exchange_name}")
    
    async def remove_exchange(self, exchange_name: str):
        """移除交易所适配器"""
        if exchange_name in self.exchanges:
            await self.exchanges[exchange_name].close()
            del self.exchanges[exchange_name]
            logger.info(f"移除交易所: {exchange_name}")
    
    async def cancel_order(self, order_id: int) -> bool:
        """取消订单"""
        if order_id in self.active_executions:
            execution_task = self.active_executions[order_id]
            execution_task.cancel()
            
            # 等待任务完成
            try:
                await execution_task
            except asyncio.CancelledError:
                pass
            
            # 从活跃执行中移除
            self.active_executions.pop(order_id, None)
            
            logger.info(f"订单 {order_id} 已取消")
            return True
        
        return False


class HighPerformanceExecutionEngine(ExecutionEngine):
    """高性能执行引擎"""
    
    def __init__(self, config: ExecutionConfig = None):
        super().__init__(config)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.concurrent_limit)
        self.pending_requests: List[ExecutionRequest] = []
        self.request_semaphore = asyncio.Semaphore(self.config.concurrent_limit)
    
    async def batch_execute_orders(self, requests: List[ExecutionRequest]) -> List[ExecutionResult]:
        """批量执行订单"""
        if not requests:
            return []
        
        # 按优先级排序
        sorted_requests = sorted(requests, key=lambda x: x.priority, reverse=True)
        
        # 并发执行
        semaphore_tasks = []
        for request in sorted_requests:
            task = self._execute_with_semaphore(request)
            semaphore_tasks.append(task)
        
        results = await asyncio.gather(*semaphore_tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExecutionResult(
                    success=False,
                    order_id=sorted_requests[i].order_id,
                    error_code="BATCH_EXECUTION_ERROR",
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_with_semaphore(self, request: ExecutionRequest) -> ExecutionResult:
        """使用信号量执行订单"""
        async with self.request_semaphore:
            return await self.execute_order(request)
    
    async def _execute_order_internal(self, request: ExecutionRequest) -> ExecutionResult:
        """在线程池中执行订单（CPU密集型任务）"""
        loop = asyncio.get_event_loop()
        
        # 将CPU密集型任务在线程池中执行
        return await loop.run_in_executor(
            self.thread_pool,
            self._sync_execute_order,
            request
        )
    
    def _sync_execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """同步执行订单（在线程池中运行）"""
        # 这里可以进行CPU密集型的计算
        # 比如复杂的订单验证、计算等
        
        time.sleep(0.01)  # 模拟CPU密集型工作
        
        # 然后调用异步版本执行实际的网络请求
        # 这里简化处理，直接返回成功结果
        return ExecutionResult(
            success=True,
            order_id=request.order_id,
            filled_quantity=request.quantity,
            average_price=request.price or Decimal('50000'),
            commission=Decimal('0'),
            latency_ms=10.0,
            retry_count=0,
            execution_time=datetime.now()
        )