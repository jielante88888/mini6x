"""
交易所切换延迟性能测试
验证交易所故障转移的延迟满足≤3秒的要求
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal
import psutil
import gc

from src.core.data_aggregator import DataAggregator
from src.core.exchange_failover import ExchangeFailoverManager


class TestExchangeSwitchingLatency:
    """交易所切换延迟性能测试"""

    @pytest.fixture
    async def data_aggregator(self):
        """创建数据聚合器实例"""
        aggregator = DataAggregator()
        await aggregator.initialize()
        yield aggregator
        await aggregator.cleanup()

    @pytest.fixture
    def performance_monitor(self):
        """性能监控器"""
        return ExchangeSwitchingMonitor()

    @pytest.fixture
    def mock_adapters(self):
        """模拟所有交易所适配器"""
        adapters = {}
        
        # 现货适配器
        spot_binance = Mock()
        spot_binance.exchange_type = 'binance_spot'
        spot_binance.is_healthy.return_value = True
        spot_binance.connect.return_value = True
        spot_binance.disconnect.return_value = True
        adapters['binance_spot'] = spot_binance

        spot_okx = Mock()
        spot_okx.exchange_type = 'okx_spot'
        spot_okx.is_healthy.return_value = True
        spot_okx.connect.return_value = True
        spot_okx.disconnect.return_value = True
        adapters['okx_spot'] = spot_okx

        # 期货适配器
        futures_binance = Mock()
        futures_binance.exchange_type = 'binance_futures'
        futures_binance.is_healthy.return_value = True
        futures_binance.connect.return_value = True
        futures_binance.disconnect.return_value = True
        adapters['binance_futures'] = futures_binance

        futures_okx = Mock()
        futures_okx.exchange_type = 'okx_futures'
        futures_okx.is_healthy.return_value = True
        futures_okx.connect.return_value = True
        futures_okx.disconnect.return_value = True
        adapters['okx_futures'] = futures_okx

        return adapters

    def test_basic_switching_latency(self, data_aggregator, performance_monitor, mock_adapters):
        """测试基本切换延迟"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        # 创建故障转移管理器
        failover_manager = ExchangeFailoverManager(data_aggregator)

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 测量切换延迟
        switching_times = []
        num_tests = 10

        for i in range(num_tests):
            # 开始监控
            performance_monitor.start_monitoring()
            
            # 执行切换
            start_time = time.time()
            
            # 模拟币安故障
            mock_adapters['binance_spot'].is_healthy.return_value = False
            
            # 启动监控
            asyncio.run(failover_manager.start_monitoring())
            
            # 等待切换完成
            async def wait_for_switch():
                active_exchange = await failover_manager.get_active_exchange('spot')
                return active_exchange
            
            # 异步等待切换
            timeout = 5.0  # 5秒超时
            start_wait = time.time()
            
            while time.time() - start_wait < timeout:
                if asyncio.run(wait_for_switch()) == 'okx':
                    break
                time.sleep(0.01)
            
            end_time = time.time()
            switching_duration = end_time - start_time
            
            switching_times.append(switching_duration)
            
            # 清理
            asyncio.run(failover_manager.stop_monitoring())
            
            # 重置模拟
            mock_adapters['binance_spot'].is_healthy.return_value = True
            mock_adapters['okx_spot'].is_healthy.return_value = True
            
            # 清理内存
            gc.collect()

        # 分析结果
        avg_switching_time = statistics.mean(switching_times)
        max_switching_time = max(switching_times)
        min_switching_time = min(switching_times)
        p95_switching_time = statistics.quantiles(switching_times, n=20)[18]  # 95th percentile

        # 性能要求验证
        assert avg_switching_time <= 3.0, f"平均切换时间 {avg_switching_time:.3f}s 超过3秒要求"
        assert max_switching_time <= 5.0, f"最大切换时间 {max_switching_time:.3f}s 超过5秒限制"
        assert p95_switching_time <= 3.0, f"95%切换时间 {p95_switching_time:.3f}s 超过3秒要求"

        print(f"切换延迟统计:")
        print(f"  平均: {avg_switching_time:.3f}s")
        print(f"  最小: {min_switching_time:.3f}s")
        print(f"  最大: {max_switching_time:.3f}s")
        print(f"  95%: {p95_switching_time:.3f}s")

    def test_concurrent_switching_load(self, data_aggregator, performance_monitor, mock_adapters):
        """测试并发负载下的切换延迟"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        # 创建多个故障转移管理器（模拟不同市场类型）
        spot_failover = ExchangeFailoverManager(data_aggregator)
        futures_failover = ExchangeFailoverManager(data_aggregator)

        # 配置优先级
        spot_failover.set_exchange_priority('binance', 'spot', priority=1)
        spot_failover.set_exchange_priority('okx', 'spot', priority=2)
        
        futures_failover.set_exchange_priority('binance', 'futures', priority=1)
        futures_failover.set_exchange_priority('okx', 'futures', priority=2)

        # 并发切换测试
        switching_times = {'spot': [], 'futures': []}

        async def concurrent_switching_test():
            """并发切换测试"""
            tasks = []
            
            # 启动监控
            await asyncio.gather(
                spot_failover.start_monitoring(),
                futures_failover.start_monitoring()
            )
            
            # 并发执行切换
            async def switch_spot():
                start_time = time.time()
                mock_adapters['binance_spot'].is_healthy.return_value = False
                
                # 等待切换
                timeout = 5.0
                start_wait = time.time()
                while time.time() - start_wait < timeout:
                    active = await spot_failover.get_active_exchange('spot')
                    if active == 'okx':
                        break
                    await asyncio.sleep(0.01)
                
                end_time = time.time()
                switching_times['spot'].append(end_time - start_time)
            
            async def switch_futures():
                start_time = time.time()
                mock_adapters['binance_futures'].is_healthy.return_value = False
                
                # 等待切换
                timeout = 5.0
                start_wait = time.time()
                while time.time() - start_wait < timeout:
                    active = await futures_failover.get_active_exchange('futures')
                    if active == 'okx':
                        break
                    await asyncio.sleep(0.01)
                
                end_time = time.time()
                switching_times['futures'].append(end_time - start_time)
            
            # 并发执行
            await asyncio.gather(
                switch_spot(),
                switch_futures()
            )
            
            # 清理
            await asyncio.gather(
                spot_failover.stop_monitoring(),
                futures_failover.stop_monitoring()
            )

        # 执行10轮测试
        for _ in range(10):
            asyncio.run(concurrent_switching_test())
            
            # 重置模拟
            mock_adapters['binance_spot'].is_healthy.return_value = True
            mock_adapters['binance_futures'].is_healthy.return_value = True
            mock_adapters['okx_spot'].is_healthy.return_value = True
            mock_adapters['okx_futures'].is_healthy.return_value = True

        # 分析并发性能
        for market_type, times in switching_times.items():
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            assert avg_time <= 3.0, f"{market_type} 并发平均切换时间 {avg_time:.3f}s 超过3秒"
            assert max_time <= 5.0, f"{market_type} 并发最大切换时间 {max_time:.3f}s 超过5秒"

        print(f"并发切换性能:")
        print(f"  现货 - 平均: {statistics.mean(switching_times['spot']):.3f}s, 最大: {max(switching_times['spot']):.3f}s")
        print(f"  期货 - 平均: {statistics.mean(switching_times['futures']):.3f}s, 最大: {max(switching_times['futures']):.3f}s")

    def test_high_frequency_switching_stability(self, data_aggregator, performance_monitor, mock_adapters):
        """测试高频切换稳定性"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        failover_manager = ExchangeFailoverManager(data_aggregator)
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 高频切换测试
        switching_times = []
        num_switches = 50

        async def rapid_switching_test():
            await failover_manager.start_monitoring()
            
            for i in range(num_switches):
                start_time = time.time()
                
                # 切换到OKX
                mock_adapters['binance_spot'].is_healthy.return_value = False
                
                # 等待切换完成
                timeout = 5.0
                start_wait = time.time()
                while time.time() - start_wait < timeout:
                    active = await failover_manager.get_active_exchange('spot')
                    if active == 'okx':
                        break
                    await asyncio.sleep(0.01)
                
                switch_time_1 = time.time() - start_time
                
                # 等待一点时间
                await asyncio.sleep(0.1)
                
                # 切换回币安
                start_time = time.time()
                mock_adapters['binance_spot'].is_healthy.return_value = True
                
                # 等待切换完成
                start_wait = time.time()
                while time.time() - start_wait < timeout:
                    active = await failover_manager.get_active_exchange('spot')
                    if active == 'binance':
                        break
                    await asyncio.sleep(0.01)
                
                switch_time_2 = time.time() - start_time
                
                switching_times.extend([switch_time_1, switch_time_2])
                
                # 清理
                mock_adapters['binance_spot'].is_healthy.return_value = True
                mock_adapters['okx_spot'].is_healthy.return_value = True
                
                await asyncio.sleep(0.05)  # 短暂暂停
            
            await failover_manager.stop_monitoring()

        asyncio.run(rapid_switching_test())

        # 稳定性验证
        avg_switching_time = statistics.mean(switching_times)
        max_switching_time = max(switching_times)
        
        assert avg_switching_time <= 3.0, f"高频切换平均时间 {avg_switching_time:.3f}s 超过3秒"
        assert max_switching_time <= 5.0, f"高频切换最大时间 {max_switching_time:.3f}s 超过5秒"

        # 检查性能退化
        first_quarter = switching_times[:len(switching_times)//4]
        last_quarter = switching_times[-len(switching_times)//4:]
        
        first_avg = statistics.mean(first_quarter)
        last_avg = statistics.mean(last_quarter)
        
        performance_degradation = (last_avg - first_avg) / first_avg * 100
        
        assert performance_degradation <= 20.0, f"高频切换性能退化 {performance_degradation:.1f}% 超过20%"

        print(f"高频切换稳定性:")
        print(f"  平均切换时间: {avg_switching_time:.3f}s")
        print(f"  最大切换时间: {max_switching_time:.3f}s")
        print(f"  性能退化: {performance_degradation:.1f}%")

    def test_resource_usage_during_switching(self, data_aggregator, mock_adapters):
        """测试切换过程中的资源使用"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        failover_manager = ExchangeFailoverManager(data_aggregator)
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 监控资源使用
        resource_metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'thread_count': []
        }

        def monitor_resources():
            process = psutil.Process()
            resource_metrics['cpu_usage'].append(process.cpu_percent())
            resource_metrics['memory_usage'].append(process.memory_info().rss / 1024 / 1024)  # MB
            resource_metrics['thread_count'].append(process.num_threads())

        async def switching_with_monitoring():
            # 启动监控
            await failover_manager.start_monitoring()
            
            # 基线测量
            baseline_cpu = psutil.Process().cpu_percent()
            baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # 执行多次切换
            for _ in range(20):
                monitor_resources()
                
                # 切换
                mock_adapters['binance_spot'].is_healthy.return_value = False
                await asyncio.sleep(0.1)
                
                # 恢复
                mock_adapters['binance_spot'].is_healthy.return_value = True
                await asyncio.sleep(0.1)
            
            monitor_resources()
            await failover_manager.stop_monitoring()

        asyncio.run(switching_with_monitoring())

        # 资源使用验证
        avg_memory = statistics.mean(resource_metrics['memory_usage'])
        max_memory = max(resource_metrics['memory_usage'])
        
        # 内存使用应该控制在合理范围内
        assert max_memory <= 200, f"最大内存使用 {max_memory:.1f}MB 超过200MB限制"

        # CPU使用应该在合理范围内
        avg_cpu = statistics.mean(resource_metrics['cpu_usage'])
        max_cpu = max(resource_metrics['cpu_usage'])
        
        assert avg_cpu <= 50.0, f"平均CPU使用 {avg_cpu:.1f}% 超过50%"
        assert max_cpu <= 80.0, f"最大CPU使用 {max_cpu:.1f}% 超过80%"

        print(f"资源使用情况:")
        print(f"  内存 - 平均: {avg_memory:.1f}MB, 最大: {max_memory:.1f}MB")
        print(f"  CPU - 平均: {avg_cpu:.1f}%, 最大: {max_cpu:.1f}%")
        print(f"  线程数 - 平均: {statistics.mean(resource_metrics['thread_count']):.1f}")

    def test_switching_latency_under_stress(self, data_aggregator, mock_adapters):
        """测试压力下的切换延迟"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        failover_manager = ExchangeFailoverManager(data_aggregator)
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 模拟系统压力
        async def simulate_load():
            """模拟系统负载"""
            tasks = []
            
            # 模拟数据处理负载
            for i in range(10):
                async def process_data():
                    for _ in range(100):
                        await asyncio.sleep(0.001)  # 模拟数据处理
                        time.sleep(0.001)
                
                tasks.append(asyncio.create_task(process_data()))
            
            return tasks

        switching_times = []

        async def stress_switching_test():
            # 启动负载
            load_tasks = await simulate_load()
            
            await failover_manager.start_monitoring()
            
            # 在负载下执行切换
            start_time = time.time()
            
            # 切换
            mock_adapters['binance_spot'].is_healthy.return_value = False
            
            # 等待切换
            timeout = 10.0  # 压力下允许更长超时
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                active = await failover_manager.get_active_exchange('spot')
                if active == 'okx':
                    break
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            switching_times.append(end_time - start_time)
            
            # 清理
            await failover_manager.stop_monitoring()
            
            # 取消负载任务
            for task in load_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(stress_switching_test())

        # 压力下的性能要求稍宽松
        switching_time = switching_times[0] if switching_times else float('inf')
        
        assert switching_time <= 10.0, f"压力下切换时间 {switching_time:.3f}s 超过10秒"

        print(f"压力测试切换时间: {switching_time:.3f}s")

    def test_switching_reliability(self, data_aggregator, mock_adapters):
        """测试切换可靠性"""
        # 设置适配器
        data_aggregator.adapters.update(mock_adapters)

        failover_manager = ExchangeFailoverManager(data_aggregator)
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        switching_results = {'success': 0, 'failure': 0, 'timeout': 0}
        num_tests = 100

        async def reliability_test():
            await failover_manager.start_monitoring()
            
            for i in range(num_tests):
                try:
                    # 切换
                    mock_adapters['binance_spot'].is_healthy.return_value = False
                    
                    # 等待切换结果
                    switch_success = False
                    timeout = 5.0
                    start_wait = time.time()
                    
                    while time.time() - start_wait < timeout:
                        active = await failover_manager.get_active_exchange('spot')
                        if active == 'okx':
                            switch_success = True
                            break
                        await asyncio.sleep(0.01)
                    
                    if switch_success:
                        switching_results['success'] += 1
                    else:
                        switching_results['timeout'] += 1
                    
                except Exception as e:
                    switching_results['failure'] += 1
                
                finally:
                    # 恢复
                    mock_adapters['binance_spot'].is_healthy.return_value = True
                    await asyncio.sleep(0.05)
            
            await failover_manager.stop_monitoring()

        asyncio.run(reliability_test())

        # 可靠性要求
        success_rate = switching_results['success'] / num_tests * 100
        timeout_rate = switching_results['timeout'] / num_tests * 100
        
        assert success_rate >= 95.0, f"切换成功率 {success_rate:.1f}% 低于95%"
        assert timeout_rate <= 5.0, f"超时率 {timeout_rate:.1f}% 超过5%"

        print(f"切换可靠性:")
        print(f"  成功: {switching_results['success']}/{num_tests} ({success_rate:.1f}%)")
        print(f"  超时: {switching_results['timeout']}/{num_tests} ({timeout_rate:.1f}%)")
        print(f"  失败: {switching_results['failure']}/{num_tests}")


class ExchangeSwitchingMonitor:
    """交易所切换性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
    
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        
        # 基线内存使用
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # 开始CPU监控
        process.cpu_percent()
    
    def end_monitoring(self):
        """结束监控"""
        self.end_time = time.time()
        
        # 记录最终内存使用
        process = psutil.Process()
        final_memory = process.memory_info().rss / 1024 / 1024
        self.memory_usage.append(final_memory)
        
        # 记录CPU使用
        final_cpu = process.cpu_percent()
        self.cpu_usage.append(final_cpu)
    
    def get_switching_time(self) -> float:
        """获取切换时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_memory_overhead(self) -> float:
        """获取内存开销"""
        if self.memory_usage:
            return max(self.memory_usage)
        return 0.0
    
    def get_cpu_overhead(self) -> float:
        """获取CPU开销"""
        if self.cpu_usage:
            return max(self.cpu_usage)
        return 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])