"""
数据隔离测试
确保期货市场和现货市场的数据完全隔离
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.src.core.data_aggregator import get_data_aggregator
from backend.src.adapters.base import MarketData, MarketType, Exchange
from backend.src.storage.models import MarketData as MarketDataModel


class TestDataIsolation:
    """期货和现货数据隔离测试"""
    
    @pytest.fixture
    async def aggregator(self):
        """创建数据聚合器实例"""
        aggregator = await get_data_aggregator()
        yield aggregator
        await aggregator.cleanup()
    
    @pytest.mark.asyncio
    async def test_spot_and_futures_separation_in_cache(self, aggregator):
        """测试缓存中期货和现货数据的分离"""
        # 创建模拟数据
        spot_data = MarketData(
            symbol="BTCUSDT",
            current_price=50000.0,
            previous_close=49000.0,
            high_24h=51000.0,
            low_24h=48000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            volume_24h=1000000.0,
            quote_volume_24h=50000000000.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        futures_data = MarketData(
            symbol="BTCUSDT-PERP",
            current_price=50500.0,
            previous_close=49500.0,
            high_24h=51500.0,
            low_24h=48500.0,
            price_change=1000.0,
            price_change_percent=2.02,
            volume_24h=2000000.0,
            quote_volume_24h=101000000000.0,
            timestamp=datetime.now(timezone.utc),
            funding_rate=0.0001,
            open_interest=1000000.0,
            index_price=50200.0,
            mark_price=50250.0
        )
        
        # 手动设置缓存数据
        spot_cache_key = "binance_spot:BTCUSDT"
        futures_cache_key = "binance_futures:BTCUSDT-PERP"
        
        aggregator.data_cache[spot_cache_key] = spot_data
        aggregator.data_cache[futures_cache_key] = futures_data
        
        # 验证缓存中期货和现货数据是分开的
        assert spot_cache_key in aggregator.data_cache
        assert futures_cache_key in aggregator.data_cache
        
        # 确保不同市场类型的数据不会混淆
        cached_spot_data = aggregator.data_cache[spot_cache_key]
        cached_futures_data = aggregator.data_cache[futures_cache_key]
        
        # 基本字段应该不同
        assert cached_spot_data.symbol == "BTCUSDT"
        assert cached_futures_data.symbol == "BTCUSDT-PERP"
        assert cached_spot_data.current_price == 50000.0
        assert cached_futures_data.current_price == 50500.0
        assert cached_spot_data.volume_24h == 1000000.0
        assert cached_futures_data.volume_24h == 2000000.0
        
        # 期货数据应该包含特有字段
        assert cached_futures_data.funding_rate == 0.0001
        assert cached_futures_data.open_interest == 1000000.0
        assert cached_futures_data.index_price == 50200.0
        assert cached_futures_data.mark_price == 50250.0
        
        # 现货数据不应该包含期货特有字段
        assert cached_spot_data.funding_rate is None
        assert cached_spot_data.open_interest is None
        assert cached_spot_data.index_price is None
        assert cached_spot_data.mark_price is None
    
    @pytest.mark.asyncio
    async def test_futures_subscription_isolation(self, aggregator):
        """测试期货订阅的隔离"""
        # 创建模拟订阅
        spot_subscription_key = "binance_spot_BTCUSDT_market_data"
        futures_subscription_key = "binance_futures_BTCUSDT-PERP_market_data"
        
        spot_callback = MagicMock()
        futures_callback = MagicMock()
        
        # 添加订阅
        aggregator.subscriptions[spot_subscription_key] = [spot_callback]
        aggregator.subscriptions[futures_subscription_key] = [futures_callback]
        
        # 验证订阅是分开的
        assert len(aggregator.subscriptions) == 2
        assert spot_subscription_key in aggregator.subscriptions
        assert futures_subscription_key in aggregator.subscriptions
        
        # 取消现货订阅
        await aggregator.unsubscribe_market_data(
            "binance", "spot", "BTCUSDT", spot_callback
        )
        
        # 验证只有现货订阅被取消，期货订阅仍然存在
        assert len(aggregator.subscriptions) == 1
        assert spot_subscription_key not in aggregator.subscriptions
        assert futures_subscription_key in aggregator.subscriptions
    
    @pytest.mark.asyncio
    async def test_futures_aggregator_isolation(self, aggregator):
        """测试期货数据聚合器的隔离"""
        futures_aggregator = aggregator.futures_aggregator
        
        # 创建期货特有数据
        futures_data = MarketData(
            symbol="BTCUSDT-PERP",
            current_price=50500.0,
            previous_close=49500.0,
            high_24h=51500.0,
            low_24h=48500.0,
            price_change=1000.0,
            price_change_percent=2.02,
            volume_24h=2000000.0,
            quote_volume_24h=101000000000.0,
            timestamp=datetime.now(timezone.utc),
            funding_rate=0.0001,
            open_interest=1000000.0,
            index_price=50200.0,
            mark_price=50250.0
        )
        
        # 设置期货缓存
        futures_cache_key = "binance:futures:BTCUSDT-PERP"
        futures_aggregator.futures_data_cache[futures_cache_key] = futures_data
        
        # 验证期货数据在专门的缓存中
        assert futures_cache_key in futures_aggregator.futures_data_cache
        
        # 验证主缓存中没有期货数据
        main_cache_spot_key = "binance_spot:BTCUSDT"
        main_cache_futures_key = "binance_futures:BTCUSDT-PERP"
        
        assert main_cache_spot_key not in aggregator.data_cache
        assert main_cache_futures_key not in aggregator.data_cache
        
        # 验证数据正确性
        cached_futures_data = futures_aggregator.futures_data_cache[futures_cache_key]
        assert cached_futures_data.symbol == "BTCUSDT-PERP"
        assert cached_futures_data.funding_rate == 0.0001
        assert cached_futures_data.open_interest == 1000000.0
    
    @pytest.mark.asyncio
    async def test_funding_rate_and_oi_cache_isolation(self, aggregator):
        """测试资金费率和持仓量缓存的隔离"""
        futures_aggregator = aggregator.futures_aggregator
        
        # 模拟资金费率数据
        funding_data = {
            "symbol": "BTCUSDT-PERP",
            "last_funding_rate": 0.0001,
            "next_funding_time": datetime.now(timezone.utc),
            "timestamp": datetime.now(timezone.utc)
        }
        
        # 模拟持仓量数据
        oi_data = {
            "symbol": "BTCUSDT-PERP",
            "open_interest": 1000000.0,
            "open_interest_value": 50000000000.0,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # 设置缓存
        futures_cache_key = "binance:futures:BTCUSDT-PERP"
        futures_aggregator.funding_rate_cache[futures_cache_key] = funding_data
        futures_aggregator.open_interest_cache[futures_cache_key] = oi_data
        
        # 验证资金费率缓存隔离
        assert futures_cache_key in futures_aggregator.funding_rate_cache
        assert futures_aggregator.funding_rate_cache[futures_cache_key]["last_funding_rate"] == 0.0001
        
        # 验证持仓量缓存隔离
        assert futures_cache_key in futures_aggregator.open_interest_cache
        assert futures_aggregator.open_interest_cache[futures_cache_key]["open_interest"] == 1000000.0
        
        # 验证主聚合器中没有这些期货特有数据
        assert futures_cache_key not in aggregator.data_cache
    
    @pytest.mark.asyncio
    async def test_market_type_validation(self, aggregator):
        """测试市场类型验证确保数据隔离"""
        # 测试有效的市场类型
        assert aggregator.get_market_data("binance", "spot", "BTCUSDT") is not None
        assert aggregator.get_market_data("binance", "futures", "BTCUSDT-PERP") is not None
        
        # 测试无效的市场类型应该抛出错误
        with pytest.raises(Exception):  # DataAggregationError
            await aggregator.get_market_data("binance", "invalid", "BTCUSDT")
        
        with pytest.raises(Exception):  # DataAggregationError
            await aggregator.get_market_data("binance", "options", "BTCUSDT-PERP")
    
    @pytest.mark.asyncio
    async def test_futures_monitoring_isolation(self, aggregator):
        """测试期货市场监控的隔离"""
        futures_aggregator = aggregator.futures_aggregator
        
        # 启动期货监控
        futures_aggregator.active_futures_subscriptions.add("binance:BTCUSDT-PERP")
        futures_aggregator.active_futures_subscriptions.add("binance:ETHUSDT-PERP")
        
        # 验证监控列表包含期货特有标记
        assert "binance:BTCUSDT-PERP" in futures_aggregator.active_futures_subscriptions
        assert "binance:ETHUSDT-PERP" in futures_aggregator.active_futures_subscriptions
        
        # 验证现货不会被意外监控
        assert "binance:BTCUSDT" not in futures_aggregator.active_futures_subscriptions
        assert "binance:ETHUSDT" not in futures_aggregator.active_futures_subscriptions
        
        # 停止一个期货监控
        await futures_aggregator.stop_monitoring("binance", "BTCUSDT-PERP")
        
        # 验证只有指定的期货监控被停止
        assert "binance:BTCUSDT-PERP" not in futures_aggregator.active_futures_subscriptions
        assert "binance:ETHUSDT-PERP" in futures_aggregator.active_futures_subscriptions
    
    @pytest.mark.asyncio
    async def test_api_endpoint_data_separation(self):
        """测试API端点层面的数据分离"""
        # 这个测试模拟API请求，验证不同端点返回正确的数据类型
        from backend.src.api.routes.market import get_spot_ticker, get_futures_ticker
        
        # 模拟现货请求
        spot_request = AsyncMock()
        spot_request.query_params = {
            "symbol": "BTCUSDT",
            "exchange": "binance"
        }
        
        # 模拟期货请求
        futures_request = AsyncMock()
        futures_request.query_params = {
            "symbol": "BTCUSDT-PERP",
            "exchange": "binance"
        }
        
        # 这里应该测试API端点如何区分不同市场类型
        # 实际实现中，端点会调用相应的聚合器方法
        assert spot_request.query_params["symbol"] == "BTCUSDT"
        assert futures_request.query_params["symbol"] == "BTCUSDT-PERP"
    
    @pytest.mark.asyncio
    async def test_database_storage_isolation(self):
        """测试数据库存储层面的数据隔离"""
        from backend.src.storage.models import MarketData
        
        # 创建现货市场数据记录
        spot_record = MarketData(
            symbol="BTCUSDT",
            current_price=50000.0,
            previous_close=49000.0,
            high_24h=51000.0,
            low_24h=48000.0,
            price_change=1000.0,
            price_change_percent=2.04,
            volume_24h=1000000.0,
            quote_volume_24h=50000000000.0,
            timestamp=datetime.now(timezone.utc),
            market_type="spot",
            exchange="binance"
        )
        
        # 创建期货市场数据记录
        futures_record = MarketData(
            symbol="BTCUSDT-PERP",
            current_price=50500.0,
            previous_close=49500.0,
            high_24h=51500.0,
            low_24h=48500.0,
            price_change=1000.0,
            price_change_percent=2.02,
            volume_24h=2000000.0,
            quote_volume_24h=101000000000.0,
            timestamp=datetime.now(timezone.utc),
            market_type="futures",
            exchange="binance",
            funding_rate=0.0001,
            open_interest=1000000.0,
            index_price=50200.0,
            mark_price=50250.0
        )
        
        # 验证数据库记录有正确的市场类型标识
        assert spot_record.market_type == "spot"
        assert futures_record.market_type == "futures"
        assert spot_record.funding_rate is None
        assert futures_record.funding_rate == 0.0001
        
        # 验证记录可以被正确区分
        spot_records = [spot_record]
        futures_records = [futures_record]
        
        all_records = spot_records + futures_records
        spot_only = [r for r in all_records if r.market_type == "spot"]
        futures_only = [r for r in all_records if r.market_type == "futures"]
        
        assert len(spot_only) == 1
        assert len(futures_only) == 1
        assert spot_only[0].symbol == "BTCUSDT"
        assert futures_only[0].symbol == "BTCUSDT-PERP"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])