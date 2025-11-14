"""
条件评估性能测试
验证条件引擎在高负载下的性能表现
"""

import asyncio
import pytest
import time
import gc
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crypto_trading_terminal.backend.src.conditions.base_conditions import (
    MarketData,
    ConditionOperator,
    ConditionType
)
from crypto_trading_terminal.backend.src.conditions.price_conditions import PriceCondition
from crypto_trading_terminal.backend.src.conditions.volume_conditions import VolumeCondition
from crypto_trading_terminal.backend.src.conditions.time_conditions import TimeCondition, TimeType
from crypto_trading_terminal.backend.src.conditions.indicator_conditions import TechnicalIndicatorCondition
from crypto_trading_terminal.backend.src.conditions.market_alert_conditions import MarketAlertCondition
from crypto_trading_terminal.backend.src.conditions.condition_engine import (
    ConditionEngine,
    EvaluationContext,
    EvaluationStrategy,
    TriggerEvent
)
from crypto_trading_terminal.backend.src.notification.notify_manager import (
    NotificationManager,
    NotificationChannel,
    NotificationPriority
)

# 可选的系统监控
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, some performance metrics will be limited")


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.response_times = []
        self.throughput = []
        self.errors = []
        self.success_count = 0
        self.failure_count = 0
        
    def start_measurement(self):
        """开始测量"""
        self.start_time = time.time()
        self._collect_system_metrics()
    
    def end_measurement(self):
        """结束测量"""
        self.end_time = time.time()
        self._collect_system_metrics()
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.response_times.append(response_time)
    
    def record_result(self, success: bool):
        """记录结果"""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def record_error(self, error: str):
        """记录错误"""
        self.errors.append(error)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                self.memory_usage.append(memory_info.rss / 1024 / 1024)  # MB
                self.cpu_usage.append(cpu_percent)
            except:
                pass
    
    def get_summary(self) -> dict:
        """获取性能摘要"""
        if not self.start_time or not self.end_time:
            return {"error": "Measurement not completed"}
        
        total_time = self.end_time - self.start_time
        
        return {
            "total_time": total_time,
            "total_evaluations": len(self.response_times),
            "success_rate": self.success_count / (self.success_count + self.failure_count) if (self.success_count + self.failure_count) > 0 else 0,
            "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "p95_response_time": statistics.quantile(self.response_times, 0.95) if len(self.response_times) > 1 else 0,
            "p99_response_time": statistics.quantile(self.response_times, 0.99) if len(self.response_times) > 1 else 0,
            "throughput_per_second": len(self.response_times) / total_time if total_time > 0 else 0,
            "avg_memory_usage_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0,
            "peak_memory_usage_mb": max(self.memory_usage) if self.memory_usage else 0,
            "avg_cpu_percent": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            "error_count": len(self.errors)
        }


class TestConditionEvaluationPerformance:
    """条件评估性能测试类"""
    
    @pytest.fixture
    async def performance_engine(self):
        """创建性能测试引擎"""
        config = {
            "max_parallel_evaluations": 20,
            "evaluation_timeout": 10.0,
            "cache_ttl": 300,
            "performance_monitoring": True
        }
        
        engine = ConditionEngine(config)
        await engine.start()
        yield engine
        await engine.stop()
    
    @pytest.fixture
    def sample_market_data(self):
        """创建测试市场数据"""
        return MarketData(
            symbol="BTCUSDT",
            price=50000.0,
            volume_24h=1000000.0,
            price_change_24h=2500.0,
            price_change_percent_24h=5.0,
            high_24h=52000.0,
            low_24h=48000.0,
            timestamp=datetime.now(),
            rsi=65.0,
            macd=120.5,
            macd_signal=115.2,
            bollinger_upper=51000.0,
            bollinger_lower=49000.0,
            moving_average_20=49500.0,
            moving_average_50=49200.0,
            open_interest=500000.0,
            funding_rate=0.001
        )
    
    @pytest.mark.asyncio
    async def test_single_condition_performance(self, performance_engine, sample_market_data):
        """测试单个条件性能"""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # 创建测试条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Performance Test Condition"
        )
        
        condition_id = performance_engine.register_condition(condition)
        
        # 执行多次评估
        iterations = 1000
        for i in range(iterations):
            start_time = time.time()
            
            # 使用正确的评估方法
            trigger_events = await performance_engine.evaluate_all(sample_market_data)
            trigger_event = trigger_events[0] if trigger_events else None
            
            end_time = time.time()
            response_time = end_time - start_time
            
            metrics.record_response_time(response_time)
            metrics.record_result(len(trigger_events) >= 0)
            
            if i % 100 == 0:
                metrics._collect_system_metrics()
        
        metrics.end_measurement()
        summary = metrics.get_summary()
        
        # 性能断言
        assert summary["total_evaluations"] == iterations
        assert summary["avg_response_time"] < 0.1  # 平均响应时间小于100ms
        assert summary["success_rate"] >= 0.99  # 成功率大于99%
        assert summary["throughput_per_second"] > 10  # 每秒处理超过10个请求
        
        print(f"Single Condition Performance: {summary}")
    
    @pytest.mark.asyncio
    async def test_multiple_conditions_performance(self, performance_engine, sample_market_data):
        """测试多条件性能"""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # 创建多种类型的条件
        conditions = []
        condition_types = [
            ("price", lambda: PriceCondition("BTCUSDT", ConditionOperator.GREATER_THAN, 49000.0)),
            ("volume", lambda: VolumeCondition("BTCUSDT", ConditionOperator.GREATER_THAN, 500000.0)),
            ("time", lambda: TimeCondition(TimeType.CURRENT_TIME, ConditionOperator.EQUAL, "12:00")),
            ("indicator", lambda: TechnicalIndicatorCondition("BTCUSDT", "RSI", ConditionOperator.GREATER_THAN, 50.0)),
            ("alert", lambda: MarketAlertCondition("price_change", "BTCUSDT", 5.0))
        ]
        
        # 创建100个条件（每种类型20个）
        condition_ids = []
        for condition_type, factory in condition_types:
            for i in range(20):
                condition = factory()
                condition.name = f"{condition_type.title()} Condition {i}"
                condition_id = performance_engine.register_condition(condition)
                condition_ids.append(condition_id)
        
        # 评估所有条件
        iterations = 100
        for i in range(iterations):
            start_time = time.time()
            
            trigger_events = await performance_engine.evaluate_all(sample_market_data)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            metrics.record_response_time(response_time)
            metrics.record_result(len(trigger_events) >= 0)
            
            if i % 20 == 0:
                metrics._collect_system_metrics()
        
        metrics.end_measurement()
        summary = metrics.get_summary()
        
        # 性能断言
        assert summary["total_evaluations"] == iterations
        assert summary["avg_response_time"] < 0.5  # 平均响应时间小于500ms
        assert summary["p95_response_time"] < 1.0  # 95%请求小于1秒
        assert summary["throughput_per_second"] > 2  # 每秒处理超过2次完整评估
        assert summary["peak_memory_usage_mb"] < 1000  # 内存使用小于1GB
        
        print(f"Multiple Conditions Performance: {summary}")
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluation_performance(self, performance_engine, sample_market_data):
        """测试并发评估性能"""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # 创建多个条件
        condition_ids = []
        for i in range(50):
            condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0 - i * 100,  # 不同的阈值
                name=f"Concurrent Condition {i}"
            )
            condition_id = performance_engine.register_condition(condition)
            condition_ids.append(condition_id)
        
        # 并发评估
        concurrent_tasks = []
        iterations_per_task = 20
        
        async def evaluate_conditions():
            for _ in range(iterations_per_task):
                # 随机选择条件进行评估
                import random
                condition_id = random.choice(condition_ids)
                
                start_time = time.time()
                trigger_events = await performance_engine.evaluate_all(sample_market_data)
                trigger_event = trigger_events[0] if trigger_events else None
                end_time = time.time()
                
                response_time = end_time - start_time
                metrics.record_response_time(response_time)
                metrics.record_result(len(trigger_events) >= 0)
        
        # 创建并发任务
        num_concurrent_tasks = 10
        for _ in range(num_concurrent_tasks):
            task = asyncio.create_task(evaluate_conditions())
            concurrent_tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*concurrent_tasks)
        
        metrics.end_measurement()
        summary = metrics.get_summary()
        
        # 并发性能断言
        assert summary["total_evaluations"] == num_concurrent_tasks * iterations_per_task
        assert summary["avg_response_time"] < 0.2  # 平均响应时间小于200ms
        assert summary["p95_response_time"] < 0.5  # 95%请求小于500ms
        assert summary["throughput_per_second"] > 20  # 每秒处理超过20个请求
        
        print(f"Concurrent Evaluation Performance: {summary}")
    
    @pytest.mark.asyncio
    async def test_evaluation_strategies_performance_comparison(self, performance_engine, sample_market_data):
        """测试不同评估策略的性能对比"""
        # 创建多个条件
        condition_ids = []
        for i in range(30):
            condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0 - i * 100,
                name=f"Strategy Test Condition {i}"
            )
            condition_id = performance_engine.register_condition(condition)
            condition_ids.append(condition_id)
        
        strategies = [
            EvaluationStrategy.SEQUENTIAL,
            EvaluationStrategy.PARALLEL,
            EvaluationStrategy.PRIORITY,
            EvaluationStrategy.ADAPTIVE
        ]
        
        strategy_results = {}
        
        for strategy in strategies:
            performance_engine.set_evaluation_strategy(strategy)
            
            metrics = PerformanceMetrics()
            metrics.start_measurement()
            
            iterations = 50
            for _ in range(iterations):
                start_time = time.time()
                
                trigger_events = await performance_engine.evaluate_all(sample_market_data)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                metrics.record_response_time(response_time)
                metrics.record_result(len(trigger_events) >= 0)
            
            metrics.end_measurement()
            strategy_results[strategy.value] = metrics.get_summary()
        
        # 性能对比断言
        for strategy_name, summary in strategy_results.items():
            assert summary["avg_response_time"] < 1.0
            assert summary["success_rate"] >= 0.95
            assert summary["throughput_per_second"] > 1
        
        # 比较策略性能
        sequential_time = strategy_results["sequential"]["avg_response_time"]
        parallel_time = strategy_results["parallel"]["avg_response_time"]
        
        # 并行策略应该比顺序策略快
        # (在大约30个条件的场景下)
        print(f"Strategy Performance Comparison: {strategy_results}")
        
        # 验证所有策略都产生了有效结果
        assert all(summary["total_evaluations"] == 50 for summary in strategy_results.values())
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, performance_engine, sample_market_data):
        """测试缓存对性能的影响"""
        # 创建测试条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Cache Test Condition"
        )
        
        condition_id = performance_engine.register_condition(condition)
        
        # 测试无缓存性能
        context_no_cache = EvaluationContext(
            evaluation_id="no_cache",
            timestamp=datetime.now(),
            strategy=EvaluationStrategy.SEQUENTIAL,
            max_execution_time=30.0,
            timeout_handling="skip",
            enable_cache=False
        )
        
        metrics_no_cache = PerformanceMetrics()
        metrics_no_cache.start_measurement()
        
        # 执行多次评估（无缓存）
        for _ in range(100):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data, context_no_cache)
            end_time = time.time()
            
            metrics_no_cache.record_response_time(end_time - start_time)
            metrics_no_cache.record_result(trigger_event is not None)
        
        metrics_no_cache.end_measurement()
        no_cache_summary = metrics_no_cache.get_summary()
        
        # 测试有缓存性能
        context_with_cache = EvaluationContext(
            evaluation_id="with_cache",
            timestamp=datetime.now(),
            strategy=EvaluationStrategy.SEQUENTIAL,
            max_execution_time=30.0,
            timeout_handling="skip",
            enable_cache=True
        )
        
        metrics_with_cache = PerformanceMetrics()
        metrics_with_cache.start_measurement()
        
        # 执行多次评估（有缓存）
        for _ in range(100):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data, context_with_cache)
            end_time = time.time()
            
            metrics_with_cache.record_response_time(end_time - start_time)
            metrics_with_cache.record_result(trigger_event is not None)
        
        metrics_with_cache.end_measurement()
        with_cache_summary = metrics_with_cache.get_summary()
        
        # 缓存性能断言
        print(f"No Cache Performance: {no_cache_summary}")
        print(f"With Cache Performance: {with_cache_summary}")
        
        # 缓存应该显著提高性能
        assert with_cache_summary["avg_response_time"] < no_cache_summary["avg_response_time"]
        assert with_cache_summary["throughput_per_second"] > no_cache_summary["throughput_per_second"]
        assert len(performance_engine.result_cache) > 0  # 确认缓存工作
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_engine, sample_market_data):
        """测试高负载下的内存使用"""
        # 记录初始内存
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # 创建大量条件
        condition_ids = []
        for i in range(200):  # 创建200个条件
            condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0 - i,
                name=f"Memory Test Condition {i}"
            )
            condition_id = performance_engine.register_condition(condition)
            condition_ids.append(condition_id)
            
            # 每创建50个条件检查一次内存
            if (i + 1) % 50 == 0:
                gc.collect()  # 强制垃圾回收
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                print(f"After {i+1} conditions: Memory increase = {memory_increase:.2f} MB")
        
        # 执行大量评估
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        for iteration in range(100):
            trigger_events = await performance_engine.evaluate_all(sample_market_data)
            
            metrics.record_result(len(trigger_events) >= 0)
            
            # 每10次迭代检查内存
            if iteration % 10 == 0:
                gc.collect()
                metrics._collect_system_metrics()
        
        metrics.end_measurement()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        summary = metrics.get_summary()
        
        # 内存使用断言
        assert summary["success_rate"] >= 0.95
        assert total_memory_increase < 2000  # 内存增长小于2GB
        assert summary["avg_response_time"] < 1.0
        
        print(f"Memory Usage Test: Total increase = {total_memory_increase:.2f} MB")
        print(f"Memory Performance Summary: {summary}")
    
    @pytest.mark.asyncio
    async def test_stress_conditions_performance(self, performance_engine, sample_market_data):
        """测试极端条件下的性能"""
        # 创建大量复杂条件
        complex_conditions = []
        for i in range(100):
            # 混合不同类型的条件
            if i % 4 == 0:
                condition = PriceCondition("BTCUSDT", ConditionOperator.GREATER_THAN, 49000.0)
            elif i % 4 == 1:
                condition = VolumeCondition("BTCUSDT", ConditionOperator.GREATER_THAN, 500000.0)
            elif i % 4 == 2:
                condition = TechnicalIndicatorCondition("BTCUSDT", "RSI", ConditionOperator.GREATER_THAN, 50.0)
            else:
                condition = MarketAlertCondition("price_change", "BTCUSDT", ConditionOperator.GREATER_THAN, 5.0)
            
            condition.name = f"Stress Test Condition {i}"
            condition_id = performance_engine.register_condition(condition)
            complex_conditions.append(condition_id)
        
        # 压力测试：快速连续评估
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        stress_iterations = 500
        for i in range(stress_iterations):
            start_time = time.time()
            
            try:
                trigger_events = await performance_engine.evaluate_all(sample_market_data)
                end_time = time.time()
                
                response_time = end_time - start_time
                metrics.record_response_time(response_time)
                metrics.record_result(True)
                
                # 模拟系统负载：偶尔触发垃圾回收
                if i % 100 == 0:
                    gc.collect()
                    
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                metrics.record_response_time(response_time)
                metrics.record_result(False)
                metrics.record_error(str(e))
        
        metrics.end_measurement()
        summary = metrics.get_summary()
        
        # 压力测试断言
        assert summary["total_evaluations"] == stress_iterations
        assert summary["success_rate"] >= 0.90  # 压力下成功率允许略有下降
        assert summary["avg_response_time"] < 2.0  # 平均响应时间小于2秒
        assert summary["p95_response_time"] < 5.0  # 95%请求小于5秒
        assert summary["error_count"] < stress_iterations * 0.1  # 错误率小于10%
        
        print(f"Stress Test Performance: {summary}")
    
    @pytest.mark.asyncio
    async def test_recovery_after_failure_performance(self, performance_engine, sample_market_data):
        """测试故障恢复后的性能"""
        # 创建测试条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Recovery Test Condition"
        )
        
        condition_id = performance_engine.register_condition(condition)
        
        # 正常性能测试
        normal_metrics = PerformanceMetrics()
        normal_metrics.start_measurement()
        
        for _ in range(50):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data)
            end_time = time.time()
            
            normal_metrics.record_response_time(end_time - start_time)
            normal_metrics.record_result(trigger_event is not None)
        
        normal_metrics.end_measurement()
        normal_summary = normal_metrics.get_summary()
        
        # 模拟故障：暂停引擎
        await performance_engine.pause()
        
        # 模拟恢复过程中的性能
        recovery_metrics = PerformanceMetrics()
        recovery_metrics.start_measurement()
        
        # 恢复引擎
        await performance_engine.resume()
        
        # 故障恢复后性能测试
        for _ in range(50):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data)
            end_time = time.time()
            
            recovery_metrics.record_response_time(end_time - start_time)
            recovery_metrics.record_result(trigger_event is not None)
        
        recovery_metrics.end_measurement()
        recovery_summary = recovery_metrics.get_summary()
        
        # 恢复性能断言
        print(f"Normal Performance: {normal_summary}")
        print(f"Recovery Performance: {recovery_summary}")
        
        # 恢复后的性能应该接近正常性能
        performance_ratio = recovery_summary["avg_response_time"] / normal_summary["avg_response_time"]
        assert performance_ratio < 2.0  # 恢复后性能不应下降超过100%
        assert recovery_summary["success_rate"] >= 0.95
    
    @pytest.mark.asyncio
    async def test_long_running_stability_performance(self, performance_engine, sample_market_data):
        """测试长时间运行稳定性"""
        # 创建多个条件
        condition_ids = []
        for i in range(20):
            condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0 - i * 100,
                name=f"Stability Test Condition {i}"
            )
            condition_id = performance_engine.register_condition(condition)
            condition_ids.append(condition_id)
        
        # 长时间运行测试
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        total_iterations = 1000
        batch_size = 50
        stability_checkpoints = []
        
        for batch in range(total_iterations // batch_size):
            batch_start_time = time.time()
            
            batch_results = []
            for _ in range(batch_size):
                start_time = time.time()
                trigger_events = await performance_engine.evaluate_all(sample_market_data)
                end_time = time.time()
                
                response_time = end_time - start_time
                batch_results.append(response_time)
            
            batch_end_time = time.time()
            batch_avg_time = statistics.mean(batch_results)
            
            # 记录性能检查点
            checkpoint = {
                "batch": batch + 1,
                "avg_response_time": batch_avg_time,
                "timestamp": time.time()
            }
            stability_checkpoints.append(checkpoint)
            
            # 每10个批次执行垃圾回收
            if (batch + 1) % 10 == 0:
                gc.collect()
                metrics._collect_system_metrics()
            
            # 检查性能稳定性
            if batch > 0:
                previous_avg = stability_checkpoints[batch - 1]["avg_response_time"]
                performance_degradation = (batch_avg_time - previous_avg) / previous_avg
                
                # 性能下降不应超过20%
                assert performance_degradation < 0.2, f"Performance degradation: {performance_degradation}"
        
        metrics.end_measurement()
        summary = metrics.get_summary()
        
        # 稳定性测试断言
        assert summary["success_rate"] >= 0.95
        assert summary["avg_response_time"] < 1.0
        assert summary["throughput_per_second"] > 1
        
        # 计算性能趋势
        first_half_avg = statistics.mean([cp["avg_response_time"] for cp in stability_checkpoints[:len(stability_checkpoints)//2]])
        second_half_avg = statistics.mean([cp["avg_response_time"] for cp in stability_checkpoints[len(stability_checkpoints)//2:]])
        
        performance_trend = (second_half_avg - first_half_avg) / first_half_avg
        
        # 长期性能不应显著恶化
        assert performance_trend < 0.5, f"Performance degradation over time: {performance_trend}"
        
        print(f"Long Running Stability: {summary}")
        print(f"Performance Trend: {performance_trend:.2%}")
    
    @pytest.mark.asyncio
    async def test_notification_performance_impact(self, performance_engine, sample_market_data):
        """测试通知对性能的影响"""
        # 创建通知管理器
        notification_manager = NotificationManager()
        
        # 启用多个通知渠道
        channels = [
            NotificationChannel.POPUP,
            NotificationChannel.DESKTOP,
            NotificationChannel.FILE_LOG
        ]
        
        for channel in channels:
            notification_manager.enable_channel(channel, True)
        
        # 创建价格预警条件
        alert_condition = MarketAlertCondition(
            alert_type="price_change",
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold_value=5.0,
            name="Notification Performance Test"
        )
        
        condition_id = performance_engine.register_condition(alert_condition)
        
        # 注册通知处理器
        async def notification_handler(trigger_event):
            notification_manager.send_notification(trigger_event)
        
        performance_engine.register_trigger_handler("market_alert", notification_handler)
        
        # 测试无通知性能
        no_notification_metrics = PerformanceMetrics()
        no_notification_metrics.start_measurement()
        
        for _ in range(100):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data)
            end_time = time.time()
            
            no_notification_metrics.record_response_time(end_time - start_time)
            no_notification_metrics.record_result(trigger_event is not None)
        
        no_notification_metrics.end_measurement()
        no_notif_summary = no_notification_metrics.get_summary()
        
        # 测试有通知性能（如果条件触发）
        with_notification_metrics = PerformanceMetrics()
        with_notification_metrics.start_measurement()
        
        for _ in range(100):
            start_time = time.time()
            trigger_event = await performance_engine.evaluate_condition(condition_id, sample_market_data)
            
            # 如果触发条件，发送通知
            if trigger_event and trigger_event.result.satisfied:
                await notification_handler(trigger_event)
            
            end_time = time.time()
            
            with_notification_metrics.record_response_time(end_time - start_time)
            with_notification_metrics.record_result(True)
        
        with_notification_metrics.end_measurement()
        with_notif_summary = with_notification_metrics.get_summary()
        
        # 通知性能影响断言
        print(f"No Notification Performance: {no_notif_summary}")
        print(f"With Notification Performance: {with_notif_summary}")
        
        # 通知不应该严重影响性能
        performance_impact = (with_notif_summary["avg_response_time"] - no_notif_summary["avg_response_time"]) / no_notif_summary["avg_response_time"]
        assert performance_impact < 1.0  # 性能影响小于100%
        assert with_notif_summary["success_rate"] >= 0.95


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])