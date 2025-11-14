"""
交易所故障转移机制集成测试
测试当主交易所故障时自动切换到备用交易所的功能
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from decimal import Decimal

from src.core.data_aggregator import DataAggregator
from src.core.exchange_failover import ExchangeFailoverManager
from src.adapters.base import MarketData, ExchangeAdapterFactory, Exchange


class TestExchangeFailover:
    """交易所故障转移测试"""

    @pytest.fixture
    async def data_aggregator(self):
        """创建数据聚合器实例"""
        aggregator = DataAggregator()
        await aggregator.initialize()
        yield aggregator
        await aggregator.cleanup()

    @pytest.fixture
    def mock_adapter_binance_spot(self):
        """模拟币安现货适配器"""
        adapter = Mock(spec=['connect', 'disconnect', 'is_healthy', 'get_spot_ticker'])
        adapter.exchange_type = 'binance_spot'
        adapter.is_healthy.return_value = True
        return adapter

    @pytest.fixture
    def mock_adapter_okx_spot(self):
        """模拟OKX现货适配器"""
        adapter = Mock(spec=['connect', 'disconnect', 'is_healthy', 'get_spot_ticker'])
        adapter.exchange_type = 'okx_spot'
        adapter.is_healthy.return_value = True
        return adapter

    @pytest.fixture
    def mock_adapter_binance_futures(self):
        """模拟币安期货适配器"""
        adapter = Mock(spec=['connect', 'disconnect', 'is_healthy', 'get_futures_ticker'])
        adapter.exchange_type = 'binance_futures'
        adapter.is_healthy.return_value = True
        return adapter

    @pytest.fixture
    def mock_adapter_okx_futures(self):
        """模拟OKX期货适配器"""
        adapter = Mock(spec=['connect', 'disconnect', 'is_healthy', 'get_futures_ticker'])
        adapter.exchange_type = 'okx_futures'
        adapter.is_healthy.return_value = True
        return adapter

    @pytest.fixture
    def failover_manager(self, data_aggregator):
        """创建故障转移管理器"""
        return ExchangeFailoverManager(data_aggregator)

    async def test_primary_exchange_healthy(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试主交易所健康时不需要切换"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级：币安为主，OKX为备
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 检查健康状态
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'binance'

    async def test_failover_when_primary_down(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试主交易所故障时自动切换到备用交易所"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 模拟币安故障
        mock_adapter_binance_spot.is_healthy.return_value = False

        # 等待健康检查
        await failover_manager.start_monitoring()
        await asyncio.sleep(0.1)

        # 验证切换到OKX
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'okx'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_failover_latency_within_requirement(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试故障转移延迟满足要求（≤3秒）"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 启动监控
        await failover_manager.start_monitoring()

        # 记录初始主交易所
        initial_exchange = await failover_manager.get_active_exchange('spot')
        assert initial_exchange == 'binance'

        # 模拟币安故障并测量切换时间
        start_time = time.time()
        mock_adapter_binance_spot.is_healthy.return_value = False

        # 等待切换完成
        await failover_manager.wait_for_failover('spot', timeout=5.0)

        end_time = time.time()
        failover_time = end_time - start_time

        # 验证切换延迟
        assert failover_time <= 3.0, f"故障转移耗时 {failover_time:.2f}s，超过要求3秒"

        # 验证切换到了OKX
        new_exchange = await failover_manager.get_active_exchange('spot')
        assert new_exchange == 'okx'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_data_isolation_during_failover(self, failover_manager, mock_adapter_binance_spot, mock_adapter_binance_futures, 
                                                mock_adapter_okx_spot, mock_adapter_okx_futures):
        """测试故障转移时现货和合约数据完全隔离"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['binance_futures'] = mock_adapter_binance_futures
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot
        failover_manager.data_aggregator.adapters['okx_futures'] = mock_adapter_okx_futures

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('binance', 'futures', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)
        failover_manager.set_exchange_priority('okx', 'futures', priority=2)

        # 模拟现货数据
        spot_data = MarketData(
            symbol="BTCUSDT",
            current_price=Decimal("50000.00"),
            previous_close=Decimal("49000.00"),
            high_24h=Decimal("51000.00"),
            low_24h=Decimal("48000.00"),
            price_change=Decimal("1000.00"),
            price_change_percent=Decimal("2.04"),
            volume_24h=Decimal("1500.50"),
            quote_volume_24h=Decimal("75000000.00"),
            timestamp=datetime.now(timezone.utc),
            exchange="binance",
            market_type="spot"
        )

        # 模拟合约数据
        futures_data = MarketData(
            symbol="BTCUSDT-PERP",
            current_price=Decimal("50025.00"),
            previous_close=Decimal("49025.00"),
            high_24h=Decimal("51025.00"),
            low_24h=Decimal("48025.00"),
            price_change=Decimal("1000.00"),
            price_change_percent=Decimal("2.04"),
            volume_24h=Decimal("2000.75"),
            quote_volume_24h=Decimal("100000000.00"),
            timestamp=datetime.now(timezone.utc),
            exchange="binance",
            market_type="futures"
        )

        # 设置返回数据
        mock_adapter_binance_spot.get_spot_ticker.return_value = spot_data
        mock_adapter_binance_futures.get_futures_ticker.return_value = futures_data

        # 启动监控
        await failover_manager.start_monitoring()

        # 验证初始状态（现货和合约都使用币安）
        spot_exchange = await failover_manager.get_active_exchange('spot')
        futures_exchange = await failover_manager.get_active_exchange('futures')
        assert spot_exchange == 'binance'
        assert futures_exchange == 'binance'

        # 模拟现货故障但期货正常
        mock_adapter_binance_spot.is_healthy.return_value = False
        mock_adapter_binance_futures.is_healthy.return_value = True

        # 等待故障检测
        await asyncio.sleep(0.1)

        # 验证只有现货切换到OKX，期货仍使用币安
        new_spot_exchange = await failover_manager.get_active_exchange('spot')
        new_futures_exchange = await failover_manager.get_active_exchange('futures')
        assert new_spot_exchange == 'okx'
        assert new_futures_exchange == 'binance'

        # 验证数据隔离：获取数据时应使用对应的交易所
        spot_result = await failover_manager.get_market_data_with_failover('spot', 'BTCUSDT')
        assert spot_result.exchange == 'okx'

        futures_result = await failover_manager.get_market_data_with_failover('futures', 'BTCUSDT-PERP')
        assert futures_result.exchange == 'binance'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_failover_recovery(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试主交易所恢复后自动切换回主交易所"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 启动监控
        await failover_manager.start_monitoring()

        # 初始状态
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'binance'

        # 模拟币安故障
        mock_adapter_binance_spot.is_healthy.return_value = False
        await failover_manager.wait_for_failover('spot', timeout=5.0)

        # 验证切换到OKX
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'okx'

        # 模拟OKX也故障
        mock_adapter_okx_spot.is_healthy.return_value = False

        # 等待检测
        await asyncio.sleep(0.1)

        # 验证两个交易所都故障时的处理
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange is None  # 没有可用交易所

        # 恢复币安
        mock_adapter_binance_spot.is_healthy.return_value = True
        mock_adapter_okx_spot.is_healthy.return_value = True

        # 等待恢复
        await failover_manager.wait_for_recovery('spot', timeout=5.0)

        # 验证切换回币安
        final_exchange = await failover_manager.get_active_exchange('spot')
        assert final_exchange == 'binance'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_circuit_breaker_pattern(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试断路器模式防止频繁切换"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级和断路器
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 设置断路器参数
        failover_manager.set_circuit_breaker_threshold('spot', failure_count=3, timeout_seconds=30)

        # 启动监控
        await failover_manager.start_monitoring()

        # 初始状态
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'binance'

        # 模拟多次币安故障但快速恢复
        for i in range(3):
            mock_adapter_binance_spot.is_healthy.return_value = False
            await asyncio.sleep(0.1)
            mock_adapter_binance_spot.is_healthy.return_value = True
            await asyncio.sleep(0.1)

        # 验证断路器激活，币安被禁用一段时间
        await asyncio.sleep(0.1)
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'okx'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_futures_failover_monitoring(self, failover_manager, mock_adapter_binance_futures, mock_adapter_okx_futures):
        """测试期货市场故障转移监控"""
        # 设置期货适配器
        failover_manager.data_aggregator.adapters['binance_futures'] = mock_adapter_binance_futures
        failover_manager.data_aggregator.adapters['okx_futures'] = mock_adapter_okx_futures

        # 配置期货优先级
        failover_manager.set_exchange_priority('binance', 'futures', priority=1)
        failover_manager.set_exchange_priority('okx', 'futures', priority=2)

        # 启动监控
        await failover_manager.start_monitoring()

        # 初始状态
        active_exchange = await failover_manager.get_active_exchange('futures')
        assert active_exchange == 'binance'

        # 模拟币安期货故障
        mock_adapter_binance_futures.is_healthy.return_value = False
        await failover_manager.wait_for_failover('futures', timeout=5.0)

        # 验证切换到OKX期货
        active_exchange = await failover_manager.get_active_exchange('futures')
        assert active_exchange == 'okx'

        # 清理
        await failover_manager.stop_monitoring()

    async def test_failover_statistics(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试故障转移统计信息收集"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置优先级
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=2)

        # 启动监控
        await failover_manager.start_monitoring()

        # 初始统计
        stats = failover_manager.get_failover_statistics()
        assert stats['total_failover_events'] == 0

        # 执行一次故障转移
        mock_adapter_binance_spot.is_healthy.return_value = False
        await failover_manager.wait_for_failover('spot', timeout=5.0)

        # 检查统计信息
        stats = failover_manager.get_failover_statistics()
        assert stats['total_failover_events'] == 1
        assert stats['last_failover_time'] is not None
        assert 'spot' in stats['market_failover_counts']

        # 清理
        await failover_manager.stop_monitoring()

    async def test_load_balancing_failover(self, failover_manager, mock_adapter_binance_spot, mock_adapter_okx_spot):
        """测试负载均衡模式下的故障转移"""
        # 设置适配器
        failover_manager.data_aggregator.adapters['binance_spot'] = mock_adapter_binance_spot
        failover_manager.data_aggregator.adapters['okx_spot'] = mock_adapter_okx_spot

        # 配置负载均衡模式
        failover_manager.set_failover_mode('load_balancing')
        failover_manager.set_exchange_priority('binance', 'spot', priority=1)
        failover_manager.set_exchange_priority('okx', 'spot', priority=1)

        # 启动监控
        await failover_manager.start_monitoring()

        # 验证负载均衡选择
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange in ['binance', 'okx']  # 任意一个都可以

        # 模拟一个交易所故障
        mock_adapter_binance_spot.is_healthy.return_value = False

        # 等待检测并切换
        await asyncio.sleep(0.1)

        # 验证切换到可用的交易所
        active_exchange = await failover_manager.get_active_exchange('spot')
        assert active_exchange == 'okx'

        # 清理
        await failover_manager.stop_monitoring()


class TestFailoverPerformance:
    """故障转移性能测试"""

    async def test_failover_performance_requirement(self):
        """测试故障转移性能要求"""
        # 模拟高负载环境下的故障转移性能
        pass

    async def test_concurrent_failover_handling(self):
        """测试并发故障转移处理"""
        # 测试多个市场同时发生故障时的处理能力
        pass

    async def test_memory_usage_during_failover(self):
        """测试故障转移过程中的内存使用"""
        # 监控故障转移过程中的内存使用情况
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])