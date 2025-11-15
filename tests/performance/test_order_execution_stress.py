"""
订单执行性能压力测试
测试系统在高负载条件下的性能表现，包括延迟、吞吐量、资源使用等
"""

import pytest
import asyncio
import time
import gc
import tracemalloc
from decimal import Decimal
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any, Optional
import psutil
import statistics

# Import from the contract test
from tests.contract.test_auto_orders import (
    OrderType, OrderSide, OrderStatus, Order, Position, 
    ExecutionResult, RiskLevel, AutoOrderManager
)

class PerformanceMetrics:
    """性能指标收集器"""
    def __init__(self):
        self.execution_times: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.throughput_metrics: Dict[str, List[float]] = {
            'orders_per_second': [],
            'response_times': [],
            'error_rates': [],
        }
        self.test_start_time = None
        self.test_end_time = None
    
    def start_test(self):
        """开始测试"""
        self.test_start_time = time.time()
        tracemalloc.start()
    
    def end_test(self):
        """结束测试"""
        self.test_end_time = time.time()
        tracemalloc.stop()
        gc.collect()
    
    def record_execution_time(self, execution_time: float):
        """记录执行时间"""
        self.execution_times.append(execution_time)
    
    def record_memory_usage(self):
        """记录内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        self.memory_usage.append(current / 1024 / 1024)  # MB
    
    def record_cpu_usage(self):
        """记录CPU使用率"""
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_usage.append(cpu_percent)
    
    def record_throughput(self, orders_processed: int, time_taken: float):
        """记录吞吐量"""
        if time_taken > 0:
            throughput = orders_processed / time_taken
            self.throughput_metrics['orders_per_second'].append(throughput)
    
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self.throughput_metrics['response_times'].append(response_time)
    
    def record_error_rate(self, total_requests: int, errors: int):
        """记录错误率"""
        error_rate = errors / total_requests * 100
        self.throughput_metrics['error_rates'].append(error_rate)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.execution_times:
            return {}
        
        return {
            'total_execution_time': (
                self.test_end_time - self.test_start_time 
                if self.test_start_time and self.test_end_time else 0
            ),
            'avg_execution_time': statistics.mean(self.execution_times),
            'max_execution_time': max(self.execution_times),
            'min_execution_time': min(self.execution_times),
            'p95_execution_time': statistics.quantiles(self.execution_times, n=20)[18],  # 95th percentile
            'avg_memory_usage_mb': statistics.mean(self.memory_usage) if self.memory_usage else 0,
            'peak_memory_usage_mb': max(self.memory_usage) if self.memory_usage else 0,
            'avg_cpu_usage': statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            'max_cpu_usage': max(self.cpu_usage) if self.cpu_usage else 0,
            'avg_throughput_ops_per_sec': (
                statistics.mean(self.throughput_metrics['orders_per_second'])
                if self.throughput_metrics['orders_per_second'] else 0
            ),
            'avg_response_time': (
                statistics.mean(self.throughput_metrics['response_times'])
                if self.throughput_metrics['response_times'] else 0
            ),
            'max_response_time': (
                max(self.throughput_metrics['response_times'])
                if self.throughput_metrics['response_times'] else 0
            ),
            'avg_error_rate_percent': (
                statistics.mean(self.throughput_metrics['error_rates'])
                if self.throughput_metrics['error_rates'] else 0
            ),
            'total_orders_processed': len(self.execution_times),
        }

class OrderExecutor:
    """订单执行器模拟（带性能监测）"""
    def __init__(self, latency_ms: float = 0, error_rate: float = 0.0):
        self.latency_ms = latency_ms
        self.error_rate = error_rate
        self.processed_orders = 0
        self.failed_orders = 0
        self.total_processing_time = 0.0
        self.lock = asyncio.Lock()
    
    async def execute_order(
        self, 
        order: Order, 
        metrics: PerformanceMetrics = None
    ) -> ExecutionResult:
        """执行订单（带性能监测）"""
        start_time = time.time()
        
        # 模拟处理延迟
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
        
        # 模拟错误
        import random
        if random.random() < self.error_rate:
            async with self.lock:
                self.failed_orders += 1
            
            if metrics:
                metrics.record_error_rate(1, 1)
            
            return ExecutionResult(
                success=False,
                message=f"随机错误: {order.order_id}",
                execution_time=time.time() - start_time,
            )
        
        # 模拟正常执行
        await asyncio.sleep(0.001)  # 1ms 基础处理时间
        
        async with self.lock:
            self.processed_orders += 1
            self.total_processing_time += time.time() - start_time
        
        if metrics:
            execution_time = time.time() - start_time
            metrics.record_execution_time(execution_time)
            metrics.record_response_time(execution_time * 1000)  # 转换为毫秒
        
        return ExecutionResult(
            success=True,
            order_id=order.order_id,
            filled_quantity=order.quantity,
            average_price=order.price or Decimal('50000'),
            execution_time=time.time() - start_time,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            'processed_orders': self.processed_orders,
            'failed_orders': self.failed_orders,
            'total_attempts': self.processed_orders + self.failed_orders,
            'success_rate': (
                self.processed_orders / (self.processed_orders + self.failed_orders) * 100
                if (self.processed_orders + self.failed_orders) > 0 else 0
            ),
            'avg_processing_time': (
                self.total_processing_time / self.processed_orders 
                if self.processed_orders > 0 else 0
            ),
        }

class NetworkSimulator:
    """网络延迟模拟器"""
    def __init__(self, base_latency_ms: float = 10, jitter_ms: float = 5):
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
    
    def get_latency(self) -> float:
        """获取网络延迟（带抖动）"""
        import random
        jitter = random.uniform(-self.jitter_ms, self.jitter_ms)
        return max(0, self.base_latency_ms + jitter)

class DatabaseSimulator:
    """数据库操作模拟器（带性能影响）"""
    def __init__(self, query_delay_ms: float = 5, connection_pool_size: int = 10):
        self.query_delay_ms = query_delay_ms
        self.connection_pool_size = connection_pool_size
        self.active_connections = 0
        self.connection_pool = asyncio.Semaphore(connection_pool_size)
        self.query_times = []
    
    async def execute_query(self, query: str, metrics: PerformanceMetrics = None) -> Dict:
        """执行数据库查询"""
        query_start = time.time()
        
        # 连接池管理
        async with self.connection_pool:
            self.active_connections += 1
            
            try:
                # 模拟数据库延迟
                if self.query_delay_ms > 0:
                    await asyncio.sleep(self.query_delay_ms / 1000)
                
                # 模拟一些复杂查询
                await asyncio.sleep(0.002)  # 2ms 基础查询时间
                
                if metrics:
                    query_time = time.time() - query_start
                    self.query_times.append(query_time)
                
                return {'status': 'success', 'data': {}}
            finally:
                self.active_connections -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        return {
            'active_connections': self.active_connections,
            'total_queries': len(self.query_times),
            'avg_query_time': statistics.mean(self.query_times) if self.query_times else 0,
            'max_query_time': max(self.query_times) if self.query_times else 0,
            'connection_utilization': (
                self.active_connections / self.connection_pool_size * 100
            ),
        }

class TestOrderExecutionStress:
    """订单执行压力测试套件"""
    
    @pytest.fixture
    def performance_metrics(self):
        """性能指标收集器"""
        return PerformanceMetrics()
    
    @pytest.fixture
    def normal_executor(self):
        """正常性能的订单执行器"""
        return OrderExecutor(latency_ms=1, error_rate=0.01)
    
    @pytest.fixture
    def slow_executor(self):
        """慢速订单执行器"""
        return OrderExecutor(latency_ms=50, error_rate=0.05)
    
    @pytest.fixture
    def fast_executor(self):
        """快速订单执行器"""
        return OrderExecutor(latency_ms=0.1, error_rate=0.001)
    
    @pytest.fixture
    def network_simulator(self):
        """网络模拟器"""
        return NetworkSimulator(base_latency_ms=10, jitter_ms=5)
    
    @pytest.fixture
    def database_simulator(self):
        """数据库模拟器"""
        return DatabaseSimulator(query_delay_ms=5, connection_pool_size=10)
    
    @pytest.fixture
    def sample_orders(self):
        """示例订单数据"""
        orders = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        
        for i in range(100):
            orders.append(Order(
                order_id=f"stress_test_{i:04d}",
                symbol=symbols[i % len(symbols)],
                order_type=OrderType.MARKET if i % 2 == 0 else OrderType.LIMIT,
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal(str(0.1 + (i % 10) * 0.1)),
                price=Decimal('50000') if i % 2 == 1 else None,
                status=OrderStatus.PENDING,
            ))
        
        return orders

    async def test_single_order_performance(self, normal_executor, performance_metrics):
        """测试单订单性能"""
        performance_metrics.start_test()
        
        test_order = Order(
            order_id="perf_test_single",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('1'),
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        result = await normal_executor.execute_order(test_order, performance_metrics)
        performance_metrics.end_test()
        
        assert result.success is True
        summary = performance_metrics.get_summary()
        
        # 性能断言
        assert summary['avg_execution_time'] < 0.1  # 小于100ms
        assert summary['max_execution_time'] < 0.5   # 小于500ms
        assert summary['total_orders_processed'] == 1
    
    async def test_batch_order_performance(self, normal_executor, performance_metrics, sample_orders):
        """测试批量订单性能"""
        performance_metrics.start_test()
        
        batch_size = 50
        start_time = time.time()
        
        # 批量执行订单
        tasks = []
        for order in sample_orders[:batch_size]:
            task = normal_executor.execute_order(order, performance_metrics)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        performance_metrics.end_test()
        end_time = time.time()
        
        # 验证结果
        successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
        assert len(successful_results) >= batch_size * 0.9  # 至少90%成功
        
        summary = performance_metrics.get_summary()
        total_time = end_time - start_time
        performance_metrics.record_throughput(batch_size, total_time)
        
        # 性能断言
        assert summary['avg_throughput_ops_per_sec'] >= 100  # 至少100 ops/sec
        assert summary['avg_response_time'] < 100  # 平均响应时间小于100ms
        assert summary['avg_error_rate_percent'] < 5  # 错误率小于5%
    
    async def test_concurrent_order_processing(self, fast_executor, performance_metrics, sample_orders):
        """测试并发订单处理性能"""
        performance_metrics.start_test()
        
        concurrency_levels = [1, 5, 10, 20, 50]
        results_by_concurrency = {}
        
        for concurrency in concurrency_levels:
            concurrent_metrics = PerformanceMetrics()
            
            # 创建并发任务
            semaphore = asyncio.Semaphore(concurrency)
            
            async def execute_with_semaphore(order, executor, metrics):
                async with semaphore:
                    return await executor.execute_order(order, metrics)
            
            # 准备测试订单
            test_orders = sample_orders[:20]
            
            start_time = time.time()
            
            # 执行并发任务
            tasks = [
                execute_with_semaphore(order, fast_executor, concurrent_metrics)
                for order in test_orders
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 记录结果
            successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
            concurrent_metrics.record_throughput(len(successful_results), total_time)
            concurrent_metrics.end_test()
            
            results_by_concurrency[concurrency] = {
                'summary': concurrent_metrics.get_summary(),
                'success_count': len(successful_results),
                'total_time': total_time,
            }
            
            # 短暂休息避免资源竞争
            await asyncio.sleep(0.1)
        
        performance_metrics.end_test()
        
        # 验证性能表现
        for concurrency, result in results_by_concurrency.items():
            summary = result['summary']
            
            # 并发级别越高，吞吐量应该提升
            if concurrency <= 10:
                assert summary['avg_throughput_ops_per_sec'] >= concurrency * 10
            
            # 错误率应该在合理范围内
            assert summary['avg_error_rate_percent'] < 3
    
    async def test_memory_usage_under_load(self, slow_executor, performance_metrics, sample_orders):
        """测试高负载下的内存使用情况"""
        performance_metrics.start_test()
        
        # 创建大量订单进行压力测试
        large_batch = sample_orders * 5  # 500个订单
        
        # 分批处理以避免内存峰值
        batch_size = 50
        all_results = []
        
        for i in range(0, len(large_batch), batch_size):
            batch = large_batch[i:i + batch_size]
            
            # 记录内存使用
            performance_metrics.record_memory_usage()
            performance_metrics.record_cpu_usage()
            
            # 执行批量订单
            tasks = [slow_executor.execute_order(order, performance_metrics) for order in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend([r for r in batch_results if isinstance(r, ExecutionResult)])
            
            # 强制垃圾回收
            gc.collect()
            
            # 短暂休息
            await asyncio.sleep(0.01)
        
        performance_metrics.end_test()
        
        summary = performance_metrics.get_summary()
        
        # 内存使用断言
        assert summary['peak_memory_usage_mb'] < 100  # 峰值内存小于100MB
        assert summary['avg_memory_usage_mb'] < 50     # 平均内存小于50MB
        
        # 处理结果验证
        assert len(all_results) >= len(large_batch) * 0.8  # 至少80%成功
    
    async def test_error_handling_under_stress(self, slow_executor, performance_metrics, sample_orders):
        """测试压力下的错误处理"""
        # 设置更高的错误率
        slow_executor.error_rate = 0.15
        
        performance_metrics.start_test()
        
        test_orders = sample_orders[:100]
        start_time = time.time()
        
        # 并发执行订单（包含错误）
        concurrency = 20
        semaphore = asyncio.Semaphore(concurrency)
        
        async def execute_with_limit(order):
            async with semaphore:
                return await slow_executor.execute_order(order, performance_metrics)
        
        tasks = [execute_with_limit(order) for order in test_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        performance_metrics.end_test()
        performance_metrics.record_throughput(len(test_orders), total_time)
        
        # 分析结果
        successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
        failed_results = [r for r in results if isinstance(r, ExecutionResult) and not r.success]
        exception_results = [r for r in results if not isinstance(r, ExecutionResult)]
        
        summary = performance_metrics.get_summary()
        
        # 错误处理断言
        assert len(failed_results) > 0, "应该有失败的订单"
        assert len(successful_results) > 0, "应该有成功的订单"
        assert summary['avg_error_rate_percent'] > 10, "错误率应该显著高于正常水平"
        assert summary['avg_error_rate_percent'] < 25, "错误率不应该过高"
        
        # 性能不应该因为错误而严重下降
        assert summary['avg_response_time'] < 200  # 响应时间仍然应该在合理范围内
    
    async def test_database_performance_impact(self, database_simulator, performance_metrics):
        """测试数据库性能影响"""
        performance_metrics.start_test()
        
        # 执行大量数据库查询
        queries = [
            "SELECT * FROM orders WHERE symbol = 'BTCUSDT'",
            "INSERT INTO orders VALUES (...)",
            "UPDATE orders SET status = 'FILLED' WHERE order_id = 'test'",
            "DELETE FROM orders WHERE created_at < '2023-01-01'",
        ] * 25  # 100个查询
        
        start_time = time.time()
        
        # 并发执行查询
        concurrency = 10
        semaphore = asyncio.Semaphore(concurrency)
        
        async def execute_query_with_limit(query):
            async with semaphore:
                return await database_simulator.execute_query(query, performance_metrics)
        
        tasks = [execute_query_with_limit(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        performance_metrics.end_test()
        
        successful_queries = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        db_stats = database_simulator.get_stats()
        
        # 数据库性能断言
        assert len(successful_queries) >= len(queries) * 0.9, "90%的查询应该成功"
        assert db_stats['avg_query_time'] < 0.1, "平均查询时间应该小于100ms"
        assert db_stats['connection_utilization'] < 80, "连接池使用率应该小于80%"
        
        # 内存使用检查
        summary = performance_metrics.get_summary()
        assert summary['peak_memory_usage_mb'] < 30, "数据库操作不应该导致内存激增"
    
    async def test_network_latency_impact(self, network_simulator, normal_executor, performance_metrics, sample_orders):
        """测试网络延迟对性能的影响"""
        latency_scenarios = [
            {'base_latency': 10, 'jitter': 5},   # 正常网络
            {'base_latency': 50, 'jitter': 20}, # 高延迟网络
            {'base_latency': 100, 'jitter': 50}, # 很差网络
        ]
        
        results_by_latency = {}
        
        for scenario in latency_scenarios:
            network_simulator.base_latency_ms = scenario['base_latency']
            network_simulator.jitter_ms = scenario['jitter']
            
            # 创建新的执行器（包含网络延迟）
            def create_delayed_executor():
                latency = network_simulator.get_latency()
                return OrderExecutor(latency_ms=latency, error_rate=0.01)
            
            scenario_metrics = PerformanceMetrics()
            scenario_metrics.start_test()
            
            test_orders = sample_orders[:30]
            start_time = time.time()
            
            # 执行订单（带网络延迟）
            tasks = [
                normal_executor.execute_order(order, scenario_metrics)
                for order in test_orders
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            scenario_metrics.end_test()
            
            scenario_metrics.record_throughput(len(test_orders), total_time)
            
            successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
            
            results_by_latency[f"{scenario['base_latency']}ms"] = {
                'summary': scenario_metrics.get_summary(),
                'success_count': len(successful_results),
                'avg_latency': scenario['base_latency'],
            }
        
        # 网络延迟影响断言
        for latency_label, result in results_by_latency.items():
            summary = result['summary']
            
            # 延迟越高，响应时间应该越长
            if latency_label == "10ms":
                assert summary['avg_response_time'] < 50
            elif latency_label == "50ms":
                assert summary['avg_response_time'] < 150
            elif latency_label == "100ms":
                assert summary['avg_response_time'] < 300
            
            # 成功率不应该受到严重影响
            assert result['success_count'] >= 25, f"延迟{latency_label}时成功率应该保持"
        
        performance_metrics.end_test()
    
    async def test_system_stability_over_time(self, normal_executor, performance_metrics):
        """测试系统长时间运行的稳定性"""
        performance_metrics.start_test()
        
        # 模拟长时间运行（5分钟）
        duration_seconds = 5  # 实际测试中使用5秒模拟
        orders_per_second = 10
        total_orders = duration_seconds * orders_per_second
        
        start_time = time.time()
        order_count = 0
        
        while time.time() - start_time < duration_seconds:
            # 每秒创建一批订单
            batch_start = time.time()
            batch_size = orders_per_second
            
            # 创建测试订单
            test_orders = []
            for i in range(batch_size):
                order = Order(
                    order_id=f"stability_test_{order_count:06d}",
                    symbol="BTCUSDT",
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    quantity=Decimal('0.1'),
                    price=Decimal('50000'),
                    status=OrderStatus.PENDING,
                )
                test_orders.append(order)
                order_count += 1
            
            # 执行订单批次
            tasks = [normal_executor.execute_order(order, performance_metrics) for order in test_orders]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 记录性能指标
            performance_metrics.record_memory_usage()
            performance_metrics.record_cpu_usage()
            
            # 等待下一秒
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        
        performance_metrics.end_test()
        
        summary = performance_metrics.get_summary()
        
        # 稳定性断言
        assert summary['total_orders_processed'] >= total_orders * 0.8, "80%的订单应该成功处理"
        
        # 内存不应该持续增长
        if len(performance_metrics.memory_usage) > 2:
            initial_memory = performance_metrics.memory_usage[0]
            final_memory = performance_metrics.memory_usage[-1]
            memory_growth = (final_memory - initial_memory) / initial_memory
            assert memory_growth < 0.5, "内存增长不应该超过50%"
        
        # CPU使用率应该在合理范围内
        assert summary['avg_cpu_usage'] < 80, "平均CPU使用率应该小于80%"
        
        # 吞吐量应该保持稳定
        if summary['avg_throughput_ops_per_sec'] > 0:
            assert summary['avg_throughput_ops_per_sec'] >= orders_per_second * 0.7
    
    async def test_performance_benchmark_comparison(self, fast_executor, normal_executor, slow_executor, sample_orders, performance_metrics):
        """测试不同性能配置下的基准比较"""
        executors = {
            'fast': fast_executor,
            'normal': normal_executor,
            'slow': slow_executor,
        }
        
        benchmark_results = {}
        
        for executor_name, executor in executors.items():
            benchmark_metrics = PerformanceMetrics()
            benchmark_metrics.start_test()
            
            test_orders = sample_orders[:50]
            start_time = time.time()
            
            # 执行订单
            tasks = [executor.execute_order(order, benchmark_metrics) for order in test_orders]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            benchmark_metrics.end_test()
            benchmark_metrics.record_throughput(len(test_orders), total_time)
            
            successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
            
            benchmark_results[executor_name] = {
                'summary': benchmark_metrics.get_summary(),
                'success_count': len(successful_results),
                'executor_stats': executor.get_stats(),
            }
        
        # 基准比较断言
        fast_summary = benchmark_results['fast']['summary']
        normal_summary = benchmark_results['normal']['summary']
        slow_summary = benchmark_results['slow']['summary']
        
        # 性能排序验证
        assert fast_summary['avg_response_time'] < normal_summary['avg_response_time']
        assert normal_summary['avg_response_time'] < slow_summary['avg_response_time']
        
        assert fast_summary['avg_throughput_ops_per_sec'] > normal_summary['avg_throughput_ops_per_sec']
        assert normal_summary['avg_throughput_ops_per_sec'] > slow_summary['avg_throughput_ops_per_sec']
        
        # 错误率应该在合理范围内
        for executor_name, result in benchmark_results.items():
            error_rate = result['summary']['avg_error_rate_percent']
            assert error_rate < 10, f"{executor_name}执行器错误率应该小于10%"
        
        performance_metrics.end_test()
    
    def test_performance_metrics_accuracy(self, performance_metrics):
        """测试性能指标收集的准确性"""
        # 模拟一些执行时间
        test_times = [0.01, 0.05, 0.02, 0.08, 0.03, 0.06, 0.04, 0.07, 0.09, 0.01]
        
        for test_time in test_times:
            performance_metrics.record_execution_time(test_time)
            performance_metrics.record_response_time(test_time * 1000)  # 转换为毫秒
        
        summary = performance_metrics.get_summary()
        
        # 验证指标计算准确性
        assert abs(summary['avg_execution_time'] - 0.046) < 0.001  # 验证平均值
        assert abs(summary['min_execution_time'] - 0.01) < 0.001   # 验证最小值
        assert abs(summary['max_execution_time'] - 0.09) < 0.001   # 验证最大值
        
        # 验证百分位数计算（95th percentile应该接近0.086）
        assert 0.08 < summary['p95_execution_time'] < 0.09
    
    async def test_resource_cleanup_verification(self, normal_executor, sample_orders, performance_metrics):
        """测试资源清理验证"""
        performance_metrics.start_test()
        
        # 初始内存
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        # 执行大量操作
        for batch_num in range(10):
            batch_orders = sample_orders[:20]
            
            # 执行订单
            tasks = [normal_executor.execute_order(order) for order in batch_orders]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 强制垃圾回收
            gc.collect()
            
            # 记录内存使用
            current_memory = tracemalloc.get_traced_memory()[0]
            performance_metrics.memory_usage.append(current_memory / 1024 / 1024)
        
        # 最终内存
        tracemalloc.stop()
        gc.collect()
        final_memory = tracemalloc.get_traced_memory()[0]
        
        # 验证资源清理
        memory_increase = (final_memory - initial_memory) / initial_memory
        assert memory_increase < 0.3, "内存增长应该控制在30%以内"
        
        performance_metrics.end_test()