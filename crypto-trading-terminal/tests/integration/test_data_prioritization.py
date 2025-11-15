"""
数据源优先级集成测试
测试币安和OKX交易所的数据源优先级选择和切换逻辑
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.core.data_aggregator import DataAggregator
from src.core.exchange_priority import ExchangePriorityManager
from src.adapters.base import MarketData


class TestDataSourcePrioritization:
    """数据源优先级测试"""

    @pytest.fixture
    async def data_aggregator(self):
        """创建数据聚合器实例"""
        aggregator = DataAggregator()
        await aggregator.initialize()
        yield aggregator
        await aggregator.cleanup()

    @pytest.fixture
    def priority_manager(self):
        """创建优先级管理器"""
        return ExchangePriorityManager()

    @pytest.fixture
    def mock_market_data_btc(self):
        """模拟BTC市场数据"""
        return MarketData(
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

    async def test_binance_priority_for_spot_markets(self, priority_manager, mock_market_data_btc):
        """测试现货市场优先选择币安"""
        # 设置现货市场优先级：币安 > OKX
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.7},
            'okx': {'priority': 2, 'weight': 0.3}
        })

        # 测试选择现货数据源
        selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert selected_exchange == 'binance'

    async def test_okx_priority_for_futures_markets(self, priority_manager):
        """测试期货市场优先选择OKX"""
        # 设置期货市场优先级：OKX > 币安
        priority_manager.set_market_priority('futures', {
            'okx': {'priority': 1, 'weight': 0.6},
            'binance': {'priority': 2, 'weight': 0.4}
        })

        # 测试选择期货数据源
        selected_exchange = priority_manager.get_optimal_exchange('futures', 'BTCUSDT-PERP')
        assert selected_exchange == 'okx'

    async def test_dynamic_priority_adjustment(self, priority_manager, mock_market_data_btc):
        """测试动态优先级调整"""
        # 初始优先级：币安 > OKX
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.8},
            'okx': {'priority': 2, 'weight': 0.2}
        })

        # 初始选择币安
        selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert selected_exchange == 'binance'

        # 模拟币安性能下降，调整优先级
        priority_manager.update_exchange_performance('binance', {
            'latency_ms': 500,  # 高延迟
            'success_rate': 0.7,  # 低成功率
            'error_count': 10
        })

        # 重新计算优先级
        priority_manager.recalculate_priorities('spot')

        # 现在应该选择OKX
        new_selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert new_selected_exchange == 'okx'

    async def test_weighted_round_robin(self, priority_manager):
        """测试加权轮询负载均衡"""
        # 设置权重：币安 70%，OKX 30%
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.7},
            'okx': {'priority': 1, 'weight': 0.3}  # 同优先级，不同权重
        })

        # 测试负载均衡模式
        priority_manager.set_load_balancing_mode(True)

        # 执行多次选择，验证权重分布
        exchange_counts = {'binance': 0, 'okx': 0}
        total_requests = 100

        for _ in range(total_requests):
            selected = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
            exchange_counts[selected] += 1

        # 验证分布接近权重比例
        binance_ratio = exchange_counts['binance'] / total_requests
        okx_ratio = exchange_counts['okx'] / total_requests

        assert 0.6 <= binance_ratio <= 0.8, f"币安选择比例 {binance_ratio:.2f} 不符合预期"
        assert 0.2 <= okx_ratio <= 0.4, f"OKX选择比例 {okx_ratio:.2f} 不符合预期"

    async def test_performance_based_priority(self, priority_manager):
        """测试基于性能数据的优先级"""
        # 模拟币安高性能
        binance_metrics = {
            'latency_ms': 50,
            'success_rate': 0.99,
            'error_count': 1,
            'uptime': 0.999,
            'data_freshness': 0.95
        }

        # 模拟OKX低性能
        okx_metrics = {
            'latency_ms': 200,
            'success_rate': 0.85,
            'error_count': 15,
            'uptime': 0.90,
            'data_freshness': 0.70
        }

        # 更新性能数据
        priority_manager.update_exchange_performance('binance', binance_metrics)
        priority_manager.update_exchange_performance('okx', okx_metrics)

        # 计算性能得分
        binance_score = priority_manager.calculate_performance_score('binance')
        okx_score = priority_manager.calculate_performance_score('okx')

        assert binance_score > okx_score, "币安应该得到更高的性能得分"

        # 自动选择得分更高的交易所
        selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert selected_exchange == 'binance'

    async def test_isolated_spot_futures_priorities(self, priority_manager):
        """测试现货和期货数据源完全隔离"""
        # 设置现货优先级：币安 > OKX
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.8},
            'okx': {'priority': 2, 'weight': 0.2}
        })

        # 设置期货优先级：OKX > 币安（与现货相反）
        priority_manager.set_market_priority('futures', {
            'okx': {'priority': 1, 'weight': 0.6},
            'binance': {'priority': 2, 'weight': 0.4}
        })

        # 验证现货数据源选择
        spot_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert spot_exchange == 'binance'

        # 验证期货数据源选择（应该与现货不同）
        futures_exchange = priority_manager.get_optimal_exchange('futures', 'BTCUSDT-PERP')
        assert futures_exchange == 'okx'

        # 验证完全隔离：同一币种的不同市场类型使用不同交易所
        assert spot_exchange != futures_exchange, "现货和期货应该使用不同的优先级逻辑"

    async def test_failover_within_priority_chain(self, priority_manager):
        """测试优先级链内的故障转移"""
        # 设置优先级：币安 > OKX > Bybit（如果可用）
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.5},
            'okx': {'priority': 2, 'weight': 0.3},
            'bybit': {'priority': 3, 'weight': 0.2}
        })

        # 初始选择币安
        selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert selected_exchange == 'binance'

        # 标记币安为不可用
        priority_manager.mark_exchange_unavailable('binance')

        # 应该转移到OKX
        new_selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert new_selected_exchange == 'okx'

        # 标记OKX也不可用
        priority_manager.mark_exchange_unavailable('okx')

        # 应该转移到Bybit
        final_selected_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert final_selected_exchange == 'bybit'

        # 如果没有可用交易所，返回None
        priority_manager.mark_exchange_unavailable('bybit')
        no_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert no_exchange is None

    async def test_priority_persistence(self, priority_manager, tmp_path):
        """测试优先级配置持久化"""
        # 设置优先级配置
        config = {
            'spot': {
                'binance': {'priority': 1, 'weight': 0.7},
                'okx': {'priority': 2, 'weight': 0.3}
            },
            'futures': {
                'okx': {'priority': 1, 'weight': 0.6},
                'binance': {'priority': 2, 'weight': 0.4}
            }
        }

        priority_manager.set_all_priorities(config)

        # 保存配置
        config_file = tmp_path / "priority_config.json"
        priority_manager.save_config(str(config_file))

        # 创建新的管理器实例
        new_manager = ExchangePriorityManager()
        new_manager.load_config(str(config_file))

        # 验证配置加载正确
        assert new_manager.get_optimal_exchange('spot', 'BTCUSDT') == 'binance'
        assert new_manager.get_optimal_exchange('futures', 'BTCUSDT-PERP') == 'okx'

    async def test_real_time_priority_updates(self, priority_manager):
        """测试实时优先级更新"""
        # 设置初始优先级
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.5},
            'okx': {'priority': 2, 'weight': 0.5}
        })

        # 启动实时监控
        await priority_manager.start_real_time_monitoring()

        # 模拟币安性能下降
        await priority_manager.simulate_exchange_degradation('binance')

        # 等待实时调整生效
        await asyncio.sleep(0.5)

        # 验证优先级已调整
        spot_exchange = priority_manager.get_optimal_exchange('spot', 'BTCUSDT')
        assert spot_exchange == 'okx'

        # 停止监控
        await priority_manager.stop_real_time_monitoring()

    async def test_priority_statistics(self, priority_manager):
        """测试优先级统计信息"""
        # 设置优先级
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.8},
            'okx': {'priority': 2, 'weight': 0.2}
        })

        # 模拟多次请求
        for _ in range(100):
            priority_manager.get_optimal_exchange('spot', 'BTCUSDT')

        # 获取统计信息
        stats = priority_manager.get_priority_statistics()

        assert 'spot' in stats
        assert stats['spot']['total_requests'] == 100
        assert 'binance' in stats['spot']['exchange_usage']
        assert 'okx' in stats['spot']['exchange_usage']

        # 验证币安使用率更高
        binance_usage = stats['spot']['exchange_usage']['binance']
        okx_usage = stats['spot']['exchange_usage']['okx']
        assert binance_usage > okx_usage

    async def test_priority_with_data_quality_factors(self, priority_manager):
        """测试包含数据质量因素的优先级选择"""
        # 设置基础优先级相同
        priority_manager.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.5},
            'okx': {'priority': 2, 'weight': 0.5}
        })

        # 设置数据质量评分
        priority_manager.set_data_quality_score('binance', {
            'completeness': 0.95,  # 数据完整性
            'accuracy': 0.99,      # 数据准确性
            'timeliness': 0.90,    # 数据时效性
            'consistency': 0.98    # 数据一致性
        })

        priority_manager.set_data_quality_score('okx', {
            'completeness': 0.85,
            'accuracy': 0.92,
            'timeliness': 0.88,
            'consistency': 0.90
        })

        # 综合考虑优先级和数据质量
        selected_exchange = priority_manager.get_optimal_exchange_with_quality('spot', 'BTCUSDT')
        
        # 币安应该在综合评分中更高
        assert selected_exchange == 'binance'


class TestMarketSpecificPriorities:
    """特定市场优先级测试"""

    async def test_major_pairs_priority(self, priority_manager):
        """测试主流交易对的数据源优先级"""
        # 定义主流交易对
        major_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        minor_pairs = ['MATICUSDT', 'DOTUSDT', 'LINKUSDT', 'UNIUSDT', 'LTCUSDT']

        # 主流交易对：币安优先
        priority_manager.set_pairs_priority('spot', major_pairs, {
            'binance': {'priority': 1, 'weight': 0.8},
            'okx': {'priority': 2, 'weight': 0.2}
        })

        # 小币种：OKX优先
        priority_manager.set_pairs_priority('spot', minor_pairs, {
            'okx': {'priority': 1, 'weight': 0.7},
            'binance': {'priority': 2, 'weight': 0.3}
        })

        # 验证主流交易对选择币安
        for pair in major_pairs[:3]:
            selected = priority_manager.get_optimal_exchange('spot', pair)
            assert selected == 'binance', f"{pair} 应该选择币安"

        # 验证小币种选择OKX
        for pair in minor_pairs[:3]:
            selected = priority_manager.get_optimal_exchange('spot', pair)
            assert selected == 'okx', f"{pair} 应该选择OKX"

    async def test_futures_contract_priority(self, priority_manager):
        """测试不同合约类型的优先级"""
        # 永续合约
        perpetual_pairs = ['BTCUSDT-PERP', 'ETHUSDT-PERP']
        # 交割合约
        delivery_pairs = ['BTC230929', 'ETH230929']

        # 永续合约：OKX优先
        priority_manager.set_contracts_priority('futures', perpetual_pairs, {
            'okx': {'priority': 1, 'weight': 0.7},
            'binance': {'priority': 2, 'weight': 0.3}
        })

        # 交割合约：币安优先
        priority_manager.set_contracts_priority('futures', delivery_pairs, {
            'binance': {'priority': 1, 'weight': 0.6},
            'okx': {'priority': 2, 'weight': 0.4}
        })

        # 验证永续合约选择OKX
        for pair in perpetual_pairs:
            selected = priority_manager.get_optimal_exchange('futures', pair)
            assert selected == 'okx', f"{pair} 应该选择OKX"

        # 验证交割合约选择币安
        for pair in delivery_pairs:
            selected = priority_manager.get_optimal_exchange('futures', pair)
            assert selected == 'binance', f"{pair} 应该选择币安"

    async def test_time_based_priority_shifts(self, priority_manager):
        """测试基于时间的优先级调整"""
        # 设置不同时段的优先级
        priority_manager.set_time_based_priorities('spot', {
            'peak_hours': {
                'timezone': 'UTC',
                'hours': [8, 9, 13, 14, 20, 21],  # 高峰时段
                'binance': {'priority': 1, 'weight': 0.9},
                'okx': {'priority': 2, 'weight': 0.1}
            },
            'off_peak_hours': {
                'timezone': 'UTC',
                'hours': [1, 2, 3, 4, 5, 6],  # 低峰时段
                'okx': {'priority': 1, 'weight': 0.7},
                'binance': {'priority': 2, 'weight': 0.3}
            }
        })

        # 测试高峰时段
        peak_time = datetime(2023, 9, 1, 13, 0, 0, tzinfo=timezone.utc)  # UTC 13:00
        selected_peak = priority_manager.get_optimal_exchange_for_time('spot', 'BTCUSDT', peak_time)
        assert selected_peak == 'binance', "高峰时段应该选择币安"

        # 测试低峰时段
        off_peak_time = datetime(2023, 9, 1, 3, 0, 0, tzinfo=timezone.utc)  # UTC 03:00
        selected_off_peak = priority_manager.get_optimal_exchange_for_time('spot', 'BTCUSDT', off_peak_time)
        assert selected_off_peak == 'okx', "低峰时段应该选择OKX"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])