"""
策略管理器和执行引擎
负责管理现货交易策略的生命周期、执行调度、状态监控和协调管理
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable, Type
from enum import Enum
from dataclasses import dataclass, field
import uuid

from .base import (
    BaseSpotStrategy, StrategyConfig, StrategyState, StrategyType, 
    StrategyStatus, MarketData, OrderRequest, OrderResult,
    ValidationException, RiskManagementException
)

# 延迟导入避免循环依赖
def _lazy_import():
    from .spot import GridStrategy, MartingaleStrategy, ArbitrageStrategy
    return GridStrategy, MartingaleStrategy, ArbitrageStrategy

# 用于类型提示
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .spot import GridStrategy, MartingaleStrategy, ArbitrageStrategy
    from ..auto_trading.order_manager import OrderManager
    from ..auto_trading.emergency_stop import EmergencyStopService
    from ..storage.models import User, Account
    from ..core.market_analyzer import MarketDataProcessor

# 策略相关异常
class StrategyException(Exception):
    """策略异常基类"""
    pass


logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 并行执行
    PRIORITY = "priority"          # 按优先级执行
    BALANCED = "balanced"          # 负载均衡


@dataclass
class StrategyInstance:
    """策略实例"""
    strategy_id: str
    strategy: BaseSpotStrategy
    config: StrategyConfig
    state: StrategyState
    priority: int = 1
    max_execution_time: int = 3600  # 1小时
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0
    is_active: bool = False  # 默认不激活
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update_stats(self, success: bool):
        """更新执行统计"""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self.last_execution = datetime.now()
        self.updated_at = self.last_execution


@dataclass
class ExecutionTask:
    """执行任务"""
    task_id: str
    strategy_instance: StrategyInstance
    market_data: MarketData
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    orders_generated: int = 0
    
    def is_completed(self) -> bool:
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        return self.status == "failed"


@dataclass
class StrategyPerformance:
    """策略性能统计"""
    total_execution_time: Decimal = Decimal('0')
    average_execution_time: Decimal = Decimal('0')
    total_orders_generated: int = 0
    success_rate: Decimal = Decimal('0')
    profit_loss: Decimal = Decimal('0')
    max_concurrent_strategies: int = 0
    execution_queue_depth: int = 0


class StrategyConflictException(Exception):
    """策略冲突异常"""
    pass


class StrategyNotFoundException(Exception):
    """策略未找到异常"""
    pass


class StrategyExecutionEngine:
    """策略执行引擎"""
    
    def __init__(self, manager: 'StrategyManager'):
        self.manager = manager
        self.execution_semaphore = asyncio.Semaphore(10)  # 最大10个并发执行
        self.active_tasks: Dict[str, ExecutionTask] = {}
        self.completed_tasks: List[ExecutionTask] = []
        self.max_task_history = 1000
    
    async def submit_execution(self, strategy_instance: StrategyInstance, market_data: MarketData) -> str:
        """提交策略执行任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        execution_task = ExecutionTask(
            task_id=task_id,
            strategy_instance=strategy_instance,
            market_data=market_data
        )
        
        self.active_tasks[task_id] = execution_task
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(execution_task))
        
        logger.info(f"提交策略执行任务: {task_id}, 策略: {strategy_instance.strategy_id}")
        return task_id
    
    async def _execute_task(self, execution_task: ExecutionTask):
        """执行任务"""
        task_id = execution_task.task_id
        strategy_instance = execution_task.strategy_instance
        
        try:
            execution_task.status = "running"
            execution_task.started_at = datetime.now()
            
            async with self.execution_semaphore:
                # 执行策略
                orders = await self._execute_strategy(strategy_instance, execution_task.market_data)
                execution_task.orders_generated = len(orders)
                
                execution_task.status = "completed"
                execution_task.completed_at = datetime.now()
                
                # 更新统计
                execution_time = (execution_task.completed_at - execution_task.started_at).total_seconds()
                strategy_instance.update_stats(success=True)
                strategy_instance.strategy.state.update_performance_metrics()
                
                logger.info(f"策略执行完成: {task_id}, 耗时: {execution_time:.2f}s, 生成订单: {len(orders)}")
                
        except Exception as e:
            execution_task.status = "failed"
            execution_task.error_message = str(e)
            execution_task.completed_at = datetime.now()
            
            strategy_instance.update_stats(success=False)
            logger.error(f"策略执行失败: {task_id}, 错误: {e}")
        
        finally:
            # 移动到完成列表
            self.completed_tasks.append(execution_task)
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            # 保持历史记录在合理范围
            if len(self.completed_tasks) > self.max_task_history:
                self.completed_tasks = self.completed_tasks[-self.max_task_history//2:]
    
    async def _execute_strategy(self, strategy_instance: StrategyInstance, market_data: MarketData) -> List[OrderRequest]:
        """执行单个策略"""
        try:
            # 检查策略状态
            if not strategy_instance.is_active:
                raise StrategyException(f"策略 {strategy_instance.strategy_id} 未激活")
            
            if strategy_instance.state.status != StrategyStatus.RUNNING:
                logger.warning(f"策略 {strategy_instance.strategy_id} 当前状态: {strategy_instance.state.status}")
                return []
            
            # 处理市场数据
            await strategy_instance.strategy.process_market_data(market_data)
            
            # 获取订单
            orders = await strategy_instance.strategy.get_next_orders(market_data)
            
            # 执行订单（通过策略管理器）
            if self.manager.order_manager:
                for order in orders:
                    await self.manager._execute_strategy_order(order, strategy_instance)
            
            return orders
            
        except Exception as e:
            logger.error(f"策略 {strategy_instance.strategy_id} 执行异常: {e}")
            raise
    
    def get_execution_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        active_count = len(self.active_tasks)
        completed_count = len(self.completed_tasks)
        
        return {
            'active_tasks': active_count,
            'completed_tasks': completed_count,
            'total_executed': active_count + completed_count,
            'active_task_ids': list(self.active_tasks.keys())
        }


class StrategyManager:
    """策略管理器"""
    
    def __init__(
        self, 
        db_session, 
        order_manager,
        market_data_processor = None,
        emergency_stop_service = None
    ):
        self.db_session = db_session
        self.order_manager = order_manager
        self.market_data_processor = market_data_processor
        # 延迟导入紧急停止服务
        try:
            from ..auto_trading.emergency_stop import get_emergency_stop_service
            self.emergency_stop_service = emergency_stop_service or get_emergency_stop_service(db_session)
        except ImportError:
            self.emergency_stop_service = emergency_stop_service
        
        # 策略实例管理
        self.strategies: Dict[str, StrategyInstance] = {}
        
        # 策略注册表
        self.strategy_registries: Dict[str, type] = {}
        
        # 延迟导入策略类
        self._strategy_classes = None
        
        # 执行引擎
        self.execution_engine = StrategyExecutionEngine(self)
        
        # 执行引擎
        self.execution_engine = StrategyExecutionEngine(self)
        
        # 执行统计
        self.performance_stats = StrategyPerformance()
        self.execution_history: List[Dict[str, Any]] = []
        
        # 控制参数
        self.max_concurrent_strategies = 10
        self.global_execution_timeout = 300  # 5分钟
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 冲突检测
        self.symbol_strategies: Dict[str, Set[str]] = {}  # symbol -> strategy_ids
        
        logger.info("策略管理器初始化完成")
    
    def register_strategy_type(self, strategy_name: str, strategy_class):
        """注册策略类型"""
        if self._strategy_classes is None:
            self._strategy_classes = {}
        self._strategy_classes[strategy_name] = strategy_class
        self.strategy_registries[strategy_name] = strategy_class
        logger.info(f"注册策略类型: {strategy_name} -> {strategy_class.__name__}")
    
    async def create_strategy(
        self, 
        config: StrategyConfig,
        order_manager = None
    ) -> str:
        """创建策略实例"""
        try:
            # 验证配置
            self._validate_config(config)
            
            # 检查冲突
            await self._check_strategy_conflicts(config)
            
            # 创建策略实例
            strategy_class = self._get_strategy_class(config.strategy_type)
            strategy = strategy_class(config, order_manager or self.order_manager)
            
            # 初始化策略
            success = await strategy.initialize()
            if not success:
                raise StrategyException(f"策略初始化失败: {config.strategy_id}")
            
            # 创建实例
            instance = StrategyInstance(
                strategy_id=config.strategy_id,
                strategy=strategy,
                config=config,
                state=strategy.state
            )
            
            # 注册策略
            self.strategies[config.strategy_id] = instance
            self._update_symbol_index(config.symbol, config.strategy_id)
            
            logger.info(f"策略创建成功: {config.strategy_id}, 类型: {config.strategy_type.value}")
            return config.strategy_id
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            raise StrategyException(f"创建策略失败: {e}")
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            if instance.state.status == StrategyStatus.RUNNING:
                logger.warning(f"策略 {strategy_id} 已在运行")
                return True
            
            # 检查全局限制
            running_count = sum(1 for s in self.strategies.values() 
                              if s.state.status == StrategyStatus.RUNNING)
            if running_count >= self.max_concurrent_strategies:
                raise StrategyException(f"达到最大并发策略数限制: {self.max_concurrent_strategies}")
            
            # 启动策略
            success = await instance.strategy.start()
            if not success:
                raise StrategyException(f"策略启动失败: {strategy_id}")
            
            # 更新实例状态
            instance.is_active = True
            instance.updated_at = datetime.now()
            
            logger.info(f"策略启动成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"启动策略失败: {e}")
            return False
    
    async def pause_strategy(self, strategy_id: str) -> bool:
        """暂停策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            if instance.state.status not in [StrategyStatus.RUNNING]:
                logger.warning(f"策略 {strategy_id} 当前状态不支持暂停: {instance.state.status}")
                return False
            
            # 暂停策略
            success = await instance.strategy.pause()
            if not success:
                raise StrategyException(f"策略暂停失败: {strategy_id}")
            
            logger.info(f"策略暂停成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"暂停策略失败: {e}")
            return False
    
    async def resume_strategy(self, strategy_id: str) -> bool:
        """恢复策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            if instance.state.status != StrategyStatus.PAUSED:
                logger.warning(f"策略 {strategy_id} 当前状态不支持恢复: {instance.state.status}")
                return False
            
            # 检查紧急停止
            if await self._is_emergency_stop_active():
                raise StrategyException("紧急停止已激活，无法恢复策略")
            
            # 恢复策略
            success = await instance.strategy.resume()
            if not success:
                raise StrategyException(f"策略恢复失败: {strategy_id}")
            
            logger.info(f"策略恢复成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复策略失败: {e}")
            return False
    
    async def stop_strategy(self, strategy_id: str, force: bool = False) -> bool:
        """停止策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            # 停止策略
            success = await instance.strategy.stop()
            if not success and not force:
                raise StrategyException(f"策略停止失败: {strategy_id}")
            
            # 更新状态
            instance.is_active = False
            instance.state.status = StrategyStatus.STOPPED
            
            logger.info(f"策略停止成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止策略失败: {e}")
            return False
    
    async def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            # 先停止策略
            await self.stop_strategy(strategy_id, force=True)
            
            # 从管理器中移除
            del self.strategies[strategy_id]
            self._remove_symbol_index(instance.config.symbol, strategy_id)
            
            # 清理相关任务
            await self._cleanup_strategy_tasks(strategy_id)
            
            logger.info(f"策略删除成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            return False
    
    async def execute_strategy(self, strategy_id: str, market_data: MarketData) -> str:
        """执行策略"""
        try:
            instance = self._get_strategy_instance(strategy_id)
            
            # 检查策略状态
            if instance.state.status != StrategyStatus.RUNNING:
                raise StrategyException(f"策略 {strategy_id} 当前状态不支持执行: {instance.state.status}")
            
            # 检查紧急停止
            if await self._is_emergency_stop_active():
                raise StrategyException("紧急停止已激活，无法执行策略")
            
            # 提交执行任务
            task_id = await self.execution_engine.submit_execution(instance, market_data)
            
            return task_id
            
        except Exception as e:
            logger.error(f"执行策略失败: {e}")
            raise
    
    async def execute_all_active_strategies(self, market_data: MarketData) -> List[str]:
        """执行所有活跃策略"""
        task_ids = []
        
        # 获取所有运行中的策略
        running_strategies = [
            instance for instance in self.strategies.values()
            if instance.state.status == StrategyStatus.RUNNING and instance.is_active
        ]
        
        # 按优先级排序
        running_strategies.sort(key=lambda s: s.priority, reverse=True)
        
        # 并行执行策略
        tasks = []
        for instance in running_strategies:
            try:
                task_id = await self.execute_strategy(instance.strategy_id, market_data)
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"执行策略 {instance.strategy_id} 失败: {e}")
        
        return task_ids
    
    async def start_monitoring(self):
        """启动监控"""
        if self.is_monitoring:
            logger.warning("监控已在运行")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("策略监控启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("策略监控停止")
    
    def get_strategy_status(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """获取策略状态"""
        if strategy_id:
            instance = self._get_strategy_instance(strategy_id)
            return {
                'strategy_id': instance.strategy_id,
                'status': instance.state.status.value,
                'symbol': instance.config.symbol,
                'strategy_type': instance.config.strategy_type.value,
                'is_active': instance.is_active,
                'priority': instance.priority,
                'execution_count': instance.execution_count,
                'success_count': instance.success_count,
                'error_count': instance.error_count,
                'success_rate': instance.success_count / max(instance.execution_count, 1),
                'last_execution': instance.last_execution.isoformat() if instance.last_execution else None,
                'created_at': instance.created_at.isoformat(),
                'updated_at': instance.updated_at.isoformat(),
                'performance_metrics': instance.strategy.get_performance_metrics()
            }
        else:
            # 返回所有策略概览
            return {
                'total_strategies': len(self.strategies),
                'active_strategies': sum(1 for s in self.strategies.values() if s.is_active),
                'running_strategies': sum(1 for s in self.strategies.values() if s.state.status == StrategyStatus.RUNNING),
                'strategies': [
                    {
                        'strategy_id': s.strategy_id,
                        'status': s.state.status.value,
                        'symbol': s.config.symbol,
                        'type': s.config.strategy_type.value,
                        'is_active': s.is_active,
                        'success_rate': s.success_count / max(s.execution_count, 1)
                    }
                    for s in self.strategies.values()
                ]
            }
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        execution_status = self.execution_engine.get_execution_status()
        
        return {
            'total_strategies': len(self.strategies),
            'active_strategies': sum(1 for s in self.strategies.values() if s.is_active),
            'running_strategies': sum(1 for s in self.strategies.values() if s.state.status == StrategyStatus.RUNNING),
            'paused_strategies': sum(1 for s in self.strategies.values() if s.state.status == StrategyStatus.PAUSED),
            'stopped_strategies': sum(1 for s in self.strategies.values() if s.state.status == StrategyStatus.STOPPED),
            'execution_engine': execution_status,
            'is_monitoring': self.is_monitoring,
            'max_concurrent_strategies': self.max_concurrent_strategies,
            'global_execution_timeout': self.global_execution_timeout,
            'performance_stats': {
                'total_execution_time': str(self.performance_stats.total_execution_time),
                'average_execution_time': str(self.performance_stats.average_execution_time),
                'total_orders_generated': self.performance_stats.total_orders_generated,
                'success_rate': str(self.performance_stats.success_rate),
                'max_concurrent_strategies': self.performance_stats.max_concurrent_strategies,
                'execution_queue_depth': self.performance_stats.execution_queue_depth
            }
        }
    
    # 私有方法
    def _validate_config(self, config: StrategyConfig):
        """验证配置"""
        if not config.strategy_id:
            raise ValidationException("策略ID不能为空")
        
        if config.strategy_id in self.strategies:
            raise ValidationException(f"策略ID已存在: {config.strategy_id}")
        
        if config.user_id <= 0 or config.account_id <= 0:
            raise ValidationException("用户ID和账户ID必须大于0")
        
        # 验证策略特定配置
        strategy_class = self._get_strategy_class(config.strategy_type)
        if hasattr(strategy_class, 'validate_config'):
            if not strategy_class.validate_config(config):
                raise ValidationException(f"策略配置验证失败: {config.strategy_type}")
    
    async def _check_strategy_conflicts(self, config: StrategyConfig):
        """检查策略冲突"""
        # 检查同交易对的策略冲突
        existing_symbol_strategies = self.symbol_strategies.get(config.symbol, set())
        
        # 检查是否存在同方向的活跃策略
        for existing_strategy_id in existing_symbol_strategies:
            existing_instance = self.strategies[existing_strategy_id]
            if (existing_instance.is_active and 
                existing_instance.state.status == StrategyStatus.RUNNING):
                # 这里可以添加更复杂的冲突检测逻辑
                # 例如：相同策略类型、相同风险参数等
                pass
    
    def _get_strategy_class(self, strategy_type: StrategyType):
        """获取策略类"""
        # 如果有手动注册的类，优先使用
        if self._strategy_classes:
            strategy_name = strategy_type.value
            if strategy_name in self._strategy_classes:
                return self._strategy_classes[strategy_name]
        
        # 默认延迟导入
        GridStrategy, MartingaleStrategy, ArbitrageStrategy = _lazy_import()
        
        type_mapping = {
            StrategyType.GRID: GridStrategy,
            StrategyType.MARTINGALE: MartingaleStrategy,
            StrategyType.ARBITRAGE: ArbitrageStrategy
        }
        
        strategy_class = type_mapping.get(strategy_type)
        if not strategy_class:
            raise ValidationException(f"不支持的策略类型: {strategy_type}")
        
        return strategy_class
    
    def _get_strategy_instance(self, strategy_id: str) -> StrategyInstance:
        """获取策略实例"""
        instance = self.strategies.get(strategy_id)
        if not instance:
            raise StrategyNotFoundException(f"策略不存在: {strategy_id}")
        return instance
    
    def _update_symbol_index(self, symbol: str, strategy_id: str):
        """更新交易对索引"""
        if symbol not in self.symbol_strategies:
            self.symbol_strategies[symbol] = set()
        self.symbol_strategies[symbol].add(strategy_id)
    
    def _remove_symbol_index(self, symbol: str, strategy_id: str):
        """移除交易对索引"""
        if symbol in self.symbol_strategies:
            self.symbol_strategies[symbol].discard(strategy_id)
            if not self.symbol_strategies[symbol]:
                del self.symbol_strategies[symbol]
    
    async def _is_emergency_stop_active(self) -> bool:
        """检查紧急停止状态"""
        if self.emergency_stop_service:
            try:
                return await self.emergency_stop_service.is_any_stop_active(
                    user_id=None, account_id=None, symbol=None
                )
            except Exception as e:
                logger.warning(f"检查紧急停止状态失败: {e}")
        return False
    
    async def _execute_strategy_order(self, order: OrderRequest, strategy_instance: StrategyInstance):
        """执行策略订单"""
        try:
            # 这里可以添加策略特定的订单处理逻辑
            # 例如：记录订单来源、设置策略标识等
            
            order.metadata = order.metadata or {}
            order.metadata['strategy_id'] = strategy_instance.strategy_id
            order.metadata['strategy_type'] = strategy_instance.config.strategy_type.value
            order.metadata['execution_timestamp'] = datetime.now().isoformat()
            
            # 调用订单管理器执行订单
            if self.order_manager:
                await self.order_manager.create_order(
                    user_id=strategy_instance.config.user_id,
                    account_id=strategy_instance.config.account_id,
                    symbol=order.symbol,
                    order_side=order.order_side,
                    quantity=order.quantity,
                    order_type=order.order_type,
                    price=order.price,
                    client_order_id=order.client_order_id
                )
            
        except Exception as e:
            logger.error(f"执行策略订单失败: {e}")
            raise
    
    async def _cleanup_strategy_tasks(self, strategy_id: str):
        """清理策略相关任务"""
        # 清理活跃任务
        tasks_to_remove = [
            task_id for task_id, task in self.execution_engine.active_tasks.items()
            if task.strategy_instance.strategy_id == strategy_id
        ]
        
        for task_id in tasks_to_remove:
            if task_id in self.execution_engine.active_tasks:
                del self.execution_engine.active_tasks[task_id]
        
        # 清理历史任务
        self.execution_engine.completed_tasks = [
            task for task in self.execution_engine.completed_tasks
            if task.strategy_instance.strategy_id != strategy_id
        ]
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 更新性能统计
                self._update_performance_stats()
                
                # 检查策略健康状态
                await self._check_strategy_health()
                
                # 清理过期数据
                await self._cleanup_expired_data()
                
                await asyncio.sleep(30)  # 30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(10)
    
    def _update_performance_stats(self):
        """更新性能统计"""
        # 计算总执行时间
        total_time = Decimal('0')
        total_orders = 0
        
        for task in self.execution_engine.completed_tasks:
            if task.completed_at and task.started_at:
                execution_time = (task.completed_at - task.started_at).total_seconds()
                total_time += Decimal(str(execution_time))
                total_orders += task.orders_generated
        
        if len(self.execution_engine.completed_tasks) > 0:
            self.performance_stats.average_execution_time = total_time / Decimal(len(self.execution_engine.completed_tasks))
        
        self.performance_stats.total_execution_time = total_time
        self.performance_stats.total_orders_generated = total_orders
        
        # 计算成功率
        total_tasks = len(self.execution_engine.completed_tasks)
        successful_tasks = sum(1 for task in self.execution_engine.completed_tasks if task.is_completed())
        
        if total_tasks > 0:
            self.performance_stats.success_rate = Decimal(successful_tasks) / Decimal(total_tasks)
        
        # 更新并发数
        running_strategies = sum(1 for s in self.strategies.values() if s.state.status == StrategyStatus.RUNNING)
        self.performance_stats.max_concurrent_strategies = max(
            self.performance_stats.max_concurrent_strategies, running_strategies
        )
        
        # 更新队列深度
        self.performance_stats.execution_queue_depth = len(self.execution_engine.active_tasks)
    
    async def _check_strategy_health(self):
        """检查策略健康状态"""
        for instance in self.strategies.values():
            if instance.state.error_count >= 10:
                logger.warning(f"策略 {instance.strategy_id} 错误次数过多: {instance.state.error_count}")
                # 这里可以实现自动暂停或重启逻辑
            
            if instance.state.consecutive_losses >= 20:
                logger.warning(f"策略 {instance.strategy_id} 连续亏损过多: {instance.state.consecutive_losses}")
    
    async def _cleanup_expired_data(self):
        """清理过期数据"""
        # 清理旧的执行历史
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # 清理过期的任务
        self.execution_engine.completed_tasks = [
            task for task in self.execution_engine.completed_tasks
            if task.created_at > cutoff_time
        ]
        
        # 保持执行历史在合理范围
        if len(self.execution_history) > 10000:
            self.execution_history = self.execution_history[-5000:]


# 工厂函数
def create_strategy_manager(
    db_session,
    order_manager,
    market_data_processor = None,
    emergency_stop_service = None
):
    """创建策略管理器实例"""
    return StrategyManager(
        db_session=db_session,
        order_manager=order_manager,
        market_data_processor=market_data_processor,
        emergency_stop_service=emergency_stop_service
    )