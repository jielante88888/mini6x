"""
条件引擎
提供条件组合、评估、优化的核心引擎
支持AND/OR/NOT逻辑操作和复杂条件组合
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    ConditionType,
    AndCondition,
    OrCondition,
    NotCondition,
    CompositeCondition
)
from .price_conditions import PriceCondition
from .volume_conditions import VolumeCondition
from .time_conditions import TimeCondition
from .indicator_conditions import TechnicalIndicatorCondition
from .market_alert_conditions import MarketAlertCondition


class EngineStatus(Enum):
    """引擎状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class EvaluationStrategy(Enum):
    """评估策略枚举"""
    SEQUENTIAL = "sequential"  # 顺序评估
    PARALLEL = "parallel"      # 并行评估
    PRIORITY = "priority"      # 按优先级评估
    ADAPTIVE = "adaptive"      # 自适应评估


class TriggerMode(Enum):
    """触发模式枚举"""
    IMMEDIATE = "immediate"    # 立即触发
    DELAYED = "delayed"        # 延迟触发
    BATCH = "batch"           # 批量触发


@dataclass
class EvaluationContext:
    """评估上下文"""
    evaluation_id: str
    timestamp: datetime
    strategy: EvaluationStrategy
    max_execution_time: float
    timeout_handling: str  # "skip", "timeout", "error"
    parallel_workers: int = 4
    enable_cache: bool = True


@dataclass
class EngineMetrics:
    """引擎性能指标"""
    total_evaluations: int
    successful_evaluations: int
    failed_evaluations: int
    average_execution_time: float
    total_conditions: int
    active_conditions: int
    conditions_by_type: Dict[str, int]
    last_evaluation_time: Optional[datetime]
    peak_memory_usage: float
    cache_hit_rate: float


@dataclass
class TriggerEvent:
    """触发事件"""
    event_id: str
    condition_id: str
    condition_name: str
    result: ConditionResult
    timestamp: datetime
    context: EvaluationContext
    priority: int
    metadata: Dict[str, Any]


class ConditionEngine:
    """条件引擎核心类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 引擎状态
        self.status = EngineStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.metrics = EngineMetrics(
            total_evaluations=0,
            successful_evaluations=0,
            failed_evaluations=0,
            average_execution_time=0.0,
            total_conditions=0,
            active_conditions=0,
            conditions_by_type={},
            last_evaluation_time=None,
            peak_memory_usage=0.0,
            cache_hit_rate=0.0
        )
        
        # 条件管理
        self.conditions: Dict[str, Condition] = {}
        self.condition_dependencies: Dict[str, Set[str]] = {}  # 条件依赖关系
        self.condition_priority: Dict[str, int] = {}  # 条件优先级
        self.condition_history: Dict[str, List[ConditionResult]] = {}  # 条件历史
        
        # 触发管理
        self.trigger_handlers: Dict[str, Callable] = {}
        self.pending_triggers: List[TriggerEvent] = []
        self.trigger_queue: asyncio.Queue = asyncio.Queue()
        self.trigger_mode = TriggerMode.IMMEDIATE
        
        # 缓存和性能优化
        self.result_cache: Dict[str, Tuple[ConditionResult, datetime]] = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5分钟缓存
        
        # 并发控制
        self.evaluation_strategy = EvaluationStrategy.ADAPTIVE
        self.max_parallel_evaluations = self.config.get('max_parallel_evaluations', 10)
        self.evaluation_timeout = self.config.get('evaluation_timeout', 30.0)
        
        # 统计和监控
        self.evaluation_stats: Dict[str, Any] = {}
        self.performance_monitoring = self.config.get('performance_monitoring', True)
        
        # 事件循环和线程
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor = ThreadPoolExecutor(max_workers=self.max_parallel_evaluations)
        self.background_tasks: Set[asyncio.Task] = set()
        
        # 锁定
        self.lock = threading.RLock()
        
        # 条件工厂
        self.condition_factory = ConditionFactory()
    
    async def start(self):
        """启动条件引擎"""
        with self.lock:
            if self.status == EngineStatus.RUNNING:
                return
            
            self.status = EngineStatus.RUNNING
            self.start_time = datetime.now()
            
            # 创建事件循环
            self.loop = asyncio.get_event_loop()
            
            # 启动后台任务
            self.background_tasks.add(asyncio.create_task(self._evaluation_loop()))
            self.background_tasks.add(asyncio.create_task(self._trigger_processor()))
            self.background_tasks.add(asyncio.create_task(self._cache_cleanup_loop()))
            
            print(f"条件引擎已启动 - 策略: {self.evaluation_strategy.value}")
    
    async def stop(self):
        """停止条件引擎"""
        with self.lock:
            if self.status == EngineStatus.STOPPED:
                return
            
            self.status = EngineStatus.STOPPED
            
            # 取消后台任务
            for task in self.background_tasks:
                task.cancel()
            
            self.background_tasks.clear()
            
            # 关闭执行器
            self.executor.shutdown(wait=True)
            
            print("条件引擎已停止")
    
    async def pause(self):
        """暂停引擎"""
        with self.lock:
            self.status = EngineStatus.PAUSED
    
    async def resume(self):
        """恢复引擎"""
        with self.lock:
            self.status = EngineStatus.RUNNING
    
    def register_condition(self, condition: Condition) -> str:
        """注册条件"""
        with self.lock:
            condition_id = condition.condition_id
            self.conditions[condition_id] = condition
            self.condition_priority[condition_id] = condition.priority
            
            # 更新指标
            self.metrics.total_conditions = len(self.conditions)
            self.metrics.active_conditions = sum(1 for c in self.conditions.values() if c.enabled)
            
            # 按类型统计
            condition_type = condition.condition_type.value
            self.metrics.conditions_by_type[condition_type] = self.metrics.conditions_by_type.get(condition_type, 0) + 1
            
            print(f"条件已注册: {condition.name or condition_id} ({condition_type})")
            return condition_id
    
    def unregister_condition(self, condition_id: str) -> bool:
        """注销条件"""
        with self.lock:
            if condition_id not in self.conditions:
                return False
            
            condition = self.conditions.pop(condition_id)
            
            # 更新指标
            self.metrics.total_conditions = len(self.conditions)
            self.metrics.active_conditions = sum(1 for c in self.conditions.values() if c.enabled)
            
            # 更新类型统计
            condition_type = condition.condition_type.value
            if condition_type in self.metrics.conditions_by_type:
                self.metrics.conditions_by_type[condition_type] -= 1
                if self.metrics.conditions_by_type[condition_type] == 0:
                    del self.metrics.conditions_by_type[condition_type]
            
            # 清理相关数据
            self.condition_priority.pop(condition_id, None)
            self.condition_history.pop(condition_id, None)
            self.condition_dependencies.pop(condition_id, None)
            
            print(f"条件已注销: {condition.name or condition_id}")
            return True
    
    def enable_condition(self, condition_id: str) -> bool:
        """启用条件"""
        with self.lock:
            if condition_id in self.conditions:
                self.conditions[condition_id].enabled = True
                self.metrics.active_conditions = sum(1 for c in self.conditions.values() if c.enabled)
                return True
            return False
    
    def disable_condition(self, condition_id: str) -> bool:
        """禁用条件"""
        with self.lock:
            if condition_id in self.conditions:
                self.conditions[condition_id].enabled = False
                self.metrics.active_conditions = sum(1 for c in self.conditions.values() if c.enabled)
                return True
            return False
    
    async def evaluate_all(self, market_data: MarketData, context: Optional[EvaluationContext] = None) -> List[TriggerEvent]:
        """评估所有条件"""
        if self.status != EngineStatus.RUNNING:
            raise RuntimeError("引擎未运行")
        
        start_time = time.time()
        context = context or self._create_default_context()
        
        with self.lock:
            enabled_conditions = [c for c in self.conditions.values() if c.enabled]
        
        try:
            # 根据策略选择评估方法
            if self.evaluation_strategy == EvaluationStrategy.PARALLEL:
                results = await self._evaluate_parallel(enabled_conditions, market_data, context)
            elif self.evaluation_strategy == EvaluationStrategy.PRIORITY:
                results = await self._evaluate_by_priority(enabled_conditions, market_data, context)
            elif self.evaluation_strategy == EvaluationStrategy.ADAPTIVE:
                results = await self._evaluate_adaptive(enabled_conditions, market_data, context)
            else:
                results = await self._evaluate_sequential(enabled_conditions, market_data, context)
            
            # 处理触发事件
            trigger_events = self._process_evaluation_results(results, market_data, context)
            
            # 更新指标
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, len(results), True)
            
            return trigger_events
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, 0, False)
            print(f"评估过程出错: {str(e)}")
            raise
    
    async def evaluate_condition(self, condition_id: str, market_data: MarketData, context: Optional[EvaluationContext] = None) -> Optional[TriggerEvent]:
        """评估单个条件"""
        if self.status != EngineStatus.RUNNING:
            raise RuntimeError("引擎未运行")
        
        with self.lock:
            condition = self.conditions.get(condition_id)
            if not condition or not condition.enabled:
                return None
        
        context = context or self._create_default_context()
        
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(condition.evaluate, market_data),
                timeout=context.max_execution_time
            )
            
            # 记录结果历史
            self._record_condition_history(condition_id, result)
            
            if result.satisfied:
                trigger_event = TriggerEvent(
                    event_id=str(uuid.uuid4()),
                    condition_id=condition_id,
                    condition_name=condition.name or condition_id,
                    result=result,
                    timestamp=datetime.now(),
                    context=context,
                    priority=condition.priority,
                    metadata={"single_evaluation": True}
                )
                
                # 处理触发事件
                await self._process_trigger_event(trigger_event)
                
                return trigger_event
            
            return None
            
        except asyncio.TimeoutError:
            error_result = ConditionResult(False, None, f"评估超时: {context.max_execution_time}秒")
            return TriggerEvent(
                event_id=str(uuid.uuid4()),
                condition_id=condition_id,
                condition_name=condition.name or condition_id,
                result=error_result,
                timestamp=datetime.now(),
                context=context,
                priority=condition.priority,
                metadata={"timeout": True}
            )
    
    async def create_and_condition(self, condition_ids: List[str], name: str = "", description: str = "") -> str:
        """创建AND条件"""
        conditions = []
        for condition_id in condition_ids:
            condition = self.conditions.get(condition_id)
            if not condition:
                raise ValueError(f"条件不存在: {condition_id}")
            conditions.append(condition)
        
        and_condition = AndCondition(conditions, name, description)
        return self.register_condition(and_condition)
    
    async def create_or_condition(self, condition_ids: List[str], name: str = "", description: str = "") -> str:
        """创建OR条件"""
        conditions = []
        for condition_id in condition_ids:
            condition = self.conditions.get(condition_id)
            if not condition:
                raise ValueError(f"条件不存在: {condition_id}")
            conditions.append(condition)
        
        or_condition = OrCondition(conditions, name, description)
        return self.register_condition(or_condition)
    
    async def create_not_condition(self, condition_id: str, name: str = "", description: str = "") -> str:
        """创建NOT条件"""
        condition = self.conditions.get(condition_id)
        if not condition:
            raise ValueError(f"条件不存在: {condition_id}")
        
        not_condition = NotCondition(condition, name, description)
        return self.register_condition(not_condition)
    
    def register_trigger_handler(self, condition_type: str, handler: Callable[[TriggerEvent], Any]):
        """注册触发处理器"""
        self.trigger_handlers[condition_type] = handler
        print(f"触发处理器已注册: {condition_type}")
    
    def set_evaluation_strategy(self, strategy: EvaluationStrategy):
        """设置评估策略"""
        self.evaluation_strategy = strategy
        print(f"评估策略已设置为: {strategy.value}")
    
    def set_trigger_mode(self, mode: TriggerMode):
        """设置触发模式"""
        self.trigger_mode = mode
        print(f"触发模式已设置为: {mode.value}")
    
    def get_condition_status(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """获取条件状态"""
        with self.lock:
            condition = self.conditions.get(condition_id)
            if not condition:
                return None
            
            history = self.condition_history.get(condition_id, [])
            recent_results = [asdict(result) for result in history[-10:]]  # 最近10次结果
            
            return {
                "condition_id": condition_id,
                "name": condition.name,
                "type": condition.condition_type.value,
                "enabled": condition.enabled,
                "priority": condition.priority,
                "recent_results": recent_results,
                "evaluation_count": len(history),
                "success_rate": sum(1 for r in history if r.satisfied) / len(history) if history else 0,
                "last_evaluation": history[-1].timestamp.isoformat() if history else None
            }
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        with self.lock:
            return {
                "status": self.status.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "total_conditions": len(self.conditions),
                "active_conditions": sum(1 for c in self.conditions.values() if c.enabled),
                "evaluation_strategy": self.evaluation_strategy.value,
                "trigger_mode": self.trigger_mode.value,
                "metrics": asdict(self.metrics),
                "conditions_by_type": dict(self.metrics.conditions_by_type)
            }
    
    def clear_cache(self):
        """清除缓存"""
        self.result_cache.clear()
        print("缓存已清除")
    
    def export_conditions(self) -> Dict[str, Any]:
        """导出条件配置"""
        with self.lock:
            exported_conditions = {}
            for condition_id, condition in self.conditions.items():
                try:
                    exported_conditions[condition_id] = condition.to_dict()
                except Exception as e:
                    print(f"导出条件失败 {condition_id}: {str(e)}")
                    continue
            
            return {
                "export_time": datetime.now().isoformat(),
                "engine_config": self.config,
                "conditions": exported_conditions,
                "dependencies": {k: list(v) for k, v in self.condition_dependencies.items()},
                "priorities": dict(self.condition_priority)
            }
    
    def import_conditions(self, data: Dict[str, Any]) -> List[str]:
        """导入条件配置"""
        imported_ids = []
        
        try:
            conditions_data = data.get("conditions", {})
            
            for condition_id, condition_dict in conditions_data.items():
                try:
                    # 使用工厂创建条件
                    condition = self.condition_factory.create_from_dict(condition_dict)
                    
                    # 注册条件
                    registered_id = self.register_condition(condition)
                    imported_ids.append(registered_id)
                    
                except Exception as e:
                    print(f"导入条件失败 {condition_id}: {str(e)}")
                    continue
            
            print(f"成功导入 {len(imported_ids)} 个条件")
            return imported_ids
            
        except Exception as e:
            print(f"导入配置失败: {str(e)}")
            return []
    
    def _create_default_context(self) -> EvaluationContext:
        """创建默认评估上下文"""
        return EvaluationContext(
            evaluation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            strategy=self.evaluation_strategy,
            max_execution_time=self.evaluation_timeout,
            timeout_handling="skip",
            parallel_workers=self.max_parallel_evaluations,
            enable_cache=True
        )
    
    async def _evaluation_loop(self):
        """评估循环"""
        while True:
            try:
                if self.status == EngineStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                if self.status != EngineStatus.RUNNING:
                    break
                
                # 定期触发评估（如果有需要）
                await asyncio.sleep(0.1)  # 100ms检查间隔
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"评估循环错误: {str(e)}")
                await asyncio.sleep(1)
    
    async def _trigger_processor(self):
        """触发处理器"""
        while True:
            try:
                if self.status == EngineStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                if self.status != EngineStatus.RUNNING:
                    break
                
                # 处理触发队列
                try:
                    trigger_event = await asyncio.wait_for(self.trigger_queue.get(), timeout=1.0)
                    await self._process_trigger_event(trigger_event)
                except asyncio.TimeoutError:
                    continue
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"触发处理器错误: {str(e)}")
                await asyncio.sleep(1)
    
    async def _cache_cleanup_loop(self):
        """缓存清理循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                
                current_time = datetime.now()
                expired_keys = [
                    key for key, (_, timestamp) in self.result_cache.items()
                    if (current_time - timestamp).total_seconds() > self.cache_ttl
                ]
                
                for key in expired_keys:
                    del self.result_cache[key]
                
                if expired_keys:
                    print(f"清理了 {len(expired_keys)} 个过期缓存项")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"缓存清理错误: {str(e)}")
                await asyncio.sleep(60)
    
    async def _evaluate_sequential(self, conditions: List[Condition], market_data: MarketData, context: EvaluationContext) -> List[Tuple[Condition, ConditionResult]]:
        """顺序评估"""
        results = []
        
        for condition in conditions:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(condition.evaluate, market_data),
                    timeout=context.max_execution_time
                )
                results.append((condition, result))
                self._record_condition_history(condition.condition_id, result)
                
            except asyncio.TimeoutError:
                error_result = ConditionResult(False, None, f"评估超时: {context.max_execution_time}秒")
                results.append((condition, error_result))
        
        return results
    
    async def _evaluate_parallel(self, conditions: List[Condition], market_data: MarketData, context: EvaluationContext) -> List[Tuple[Condition, ConditionResult]]:
        """并行评估"""
        tasks = []
        
        for condition in conditions:
            task = asyncio.create_task(self._evaluate_single_condition(condition, market_data, context))
            tasks.append((condition, task))
        
        results = []
        for condition, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=context.max_execution_time)
                results.append((condition, result))
                self._record_condition_history(condition.condition_id, result)
            except asyncio.TimeoutError:
                error_result = ConditionResult(False, None, f"评估超时: {context.max_execution_time}秒")
                results.append((condition, error_result))
        
        return results
    
    async def _evaluate_by_priority(self, conditions: List[Condition], market_data: MarketData, context: EvaluationContext) -> List[Tuple[Condition, ConditionResult]]:
        """按优先级评估"""
        # 按优先级排序
        sorted_conditions = sorted(conditions, key=lambda c: c.priority, reverse=True)
        return await self._evaluate_sequential(sorted_conditions, market_data, context)
    
    async def _evaluate_adaptive(self, conditions: List[Condition], market_data: MarketData, context: EvaluationContext) -> List[Tuple[Condition, ConditionResult]]:
        """自适应评估"""
        # 根据条件数量和类型选择策略
        if len(conditions) <= 3:
            return await self._evaluate_sequential(conditions, market_data, context)
        elif len(conditions) <= 10:
            return await self._evaluate_parallel(conditions, market_data, context)
        else:
            return await self._evaluate_by_priority(conditions, market_data, context)
    
    async def _evaluate_single_condition(self, condition: Condition, market_data: MarketData, context: EvaluationContext) -> ConditionResult:
        """评估单个条件"""
        # 检查缓存
        cache_key = self._get_cache_key(condition, market_data)
        if context.enable_cache and cache_key in self.result_cache:
            result, timestamp = self.result_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return result
        
        # 执行评估
        result = await asyncio.to_thread(condition.evaluate, market_data)
        
        # 更新缓存
        if context.enable_cache:
            self.result_cache[cache_key] = (result, datetime.now())
        
        return result
    
    def _process_evaluation_results(self, results: List[Tuple[Condition, ConditionResult]], market_data: MarketData, context: EvaluationContext) -> List[TriggerEvent]:
        """处理评估结果"""
        trigger_events = []
        
        for condition, result in results:
            if result.satisfied:
                trigger_event = TriggerEvent(
                    event_id=str(uuid.uuid4()),
                    condition_id=condition.condition_id,
                    condition_name=condition.name or condition.condition_id,
                    result=result,
                    timestamp=datetime.now(),
                    context=context,
                    priority=condition.priority,
                    metadata={"batch_evaluation": True}
                )
                
                trigger_events.append(trigger_event)
                
                # 添加到队列
                if self.trigger_mode == TriggerMode.BATCH:
                    self.pending_triggers.append(trigger_event)
                else:
                    asyncio.create_task(self.trigger_queue.put(trigger_event))
        
        # 如果是批量模式，处理所有触发
        if self.trigger_mode == TriggerMode.BATCH and self.pending_triggers:
            for trigger_event in self.pending_triggers:
                asyncio.create_task(self.trigger_queue.put(trigger_event))
            self.pending_triggers.clear()
        
        return trigger_events
    
    async def _process_trigger_event(self, trigger_event: TriggerEvent):
        """处理触发事件"""
        try:
            # 调用注册的处理器
            condition_type = self.conditions[trigger_event.condition_id].condition_type.value
            
            if condition_type in self.trigger_handlers:
                handler = self.trigger_handlers[condition_type]
                await handler(trigger_event)
            else:
                # 默认处理
                print(f"触发事件: {trigger_event.condition_name} - {trigger_event.result.details}")
            
        except Exception as e:
            print(f"触发事件处理失败: {str(e)}")
    
    def _record_condition_history(self, condition_id: str, result: ConditionResult):
        """记录条件历史"""
        if condition_id not in self.condition_history:
            self.condition_history[condition_id] = []
        
        self.condition_history[condition_id].append(result)
        
        # 保持历史记录数量
        if len(self.condition_history[condition_id]) > 1000:
            self.condition_history[condition_id] = self.condition_history[condition_id][-500:]
    
    def _update_metrics(self, execution_time: float, result_count: int, success: bool):
        """更新性能指标"""
        self.metrics.total_evaluations += 1
        
        if success:
            self.metrics.successful_evaluations += 1
        else:
            self.metrics.failed_evaluations += 1
        
        # 更新平均执行时间
        total_time = self.metrics.average_execution_time * (self.metrics.total_evaluations - 1)
        self.metrics.average_execution_time = (total_time + execution_time) / self.metrics.total_evaluations
        
        self.metrics.last_evaluation_time = datetime.now()
    
    def _get_cache_key(self, condition: Condition, market_data: MarketData) -> str:
        """生成缓存键"""
        return f"{condition.condition_id}:{market_data.symbol}:{market_data.timestamp.isoformat()}"


class ConditionFactory:
    """条件工厂类"""
    
    def __init__(self):
        self.condition_classes = {
            ConditionType.PRICE: PriceCondition,
            ConditionType.VOLUME: VolumeCondition,
            ConditionType.TIME: TimeCondition,
            ConditionType.TECHNICAL_INDICATOR: TechnicalIndicatorCondition,
            ConditionType.MARKET_ALERT: MarketAlertCondition,
        }
    
    def create_condition(self, condition_type: ConditionType, **kwargs) -> Condition:
        """创建条件实例"""
        condition_class = self.condition_classes.get(condition_type)
        if not condition_class:
            raise ValueError(f"不支持的条件类型: {condition_type}")
        
        return condition_class(**kwargs)
    
    def create_from_dict(self, data: Dict[str, Any]) -> Condition:
        """从字典创建条件"""
        condition_type = ConditionType(data.get("condition_type"))
        
        if condition_type == ConditionType.PRICE:
            return PriceCondition(**data)
        elif condition_type == ConditionType.VOLUME:
            return VolumeCondition(**data)
        elif condition_type == ConditionType.TIME:
            return TimeCondition(**data)
        elif condition_type == ConditionType.TECHNICAL_INDICATOR:
            return TechnicalIndicatorCondition(**data)
        elif condition_type == ConditionType.MARKET_ALERT:
            return MarketAlertCondition(**data)
        elif condition_type == ConditionType.COMPOSITE:
            # 创建复合条件
            sub_conditions_data = data.get("conditions", [])
            sub_conditions = [self.create_from_dict(sub_data) for sub_data in sub_conditions_data]
            
            if data.get("operator") == "and":
                return AndCondition(sub_conditions, data.get("name", ""), data.get("description", ""))
            elif data.get("operator") == "or":
                return OrCondition(sub_conditions, data.get("name", ""), data.get("description", ""))
            else:
                raise ValueError(f"不支持的复合条件操作符: {data.get('operator')}")
        else:
            raise ValueError(f"不支持的条件类型: {condition_type}")


# 全局条件引擎实例
_global_engine: Optional[ConditionEngine] = None


def get_condition_engine() -> ConditionEngine:
    """获取全局条件引擎实例"""
    global _global_engine
    if _global_engine is None:
        _global_engine = ConditionEngine()
    return _global_engine


async def init_condition_engine(config: Optional[Dict[str, Any]] = None) -> ConditionEngine:
    """初始化全局条件引擎"""
    global _global_engine
    if _global_engine is None:
        _global_engine = ConditionEngine(config)
    await _global_engine.start()
    return _global_engine


async def shutdown_condition_engine():
    """关闭全局条件引擎"""
    global _global_engine
    if _global_engine is not None:
        await _global_engine.stop()
        _global_engine = None