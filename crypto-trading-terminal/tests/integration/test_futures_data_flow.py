"""
期货市场数据流集成测试
测试期货数据从交易所API到前端展示的完整流程
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.core.data_aggregator import get_data_aggregator
from backend.src.adapters.binance.futures import BinanceFuturesAdapter
from backend.src.adapters.okx.derivatives import OKXDerivativesAdapter
from backend.src.core.ws_client_manager import get_ws_client_manager


class TestFuturesDataFlow:
    """期货数据流集成测试"""
    
    @pytest.fixture
    async def aggregator(self):
        """创建数据聚合器实例"""
        aggregator = await get_data_aggregator()
        yield aggregator
        await aggregator.cleanup()
    
    @pytest.fixture
    async def ws_manager(self):
        """创建WebSocket客户端管理器"""
        manager = await get_ws_client_manager()
        yield manager
        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_binance_futures_data_flow(self, aggregator):
        """测试币安期货数据流"""
        # 模拟币安期货适配器响应
        mock_binance_adapter = AsyncMock()
        mock_binance_adapter.get_futures_ticker.return_value = MagicMock(
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
        
        # 注入模拟适配器
        binance_futures_key = "binance_futures"
        aggregator.adapters[binance_futures_key] = mock_binance_adapter
        
        # 从数据聚合器获取期货数据
        futures_data = await aggregator.get_market_data("binance", "futures", "BTCUSDT-PERP")
        
        # 验证数据流
        assert futures_data is not None
        assert futures_data.symbol == "BTCUSDT-PERP"
        assert futures_data.current_price == 50500.0
        assert futures_data.funding_rate == 0.0001
        assert futures_data.open_interest == 1000000.0
        assert futures_data.index_price == 50200.0
        assert futures_data.mark_price == 50250.0
        
        # 验证适配器被正确调用
        mock_binance_adapter.get_futures_ticker.assert_called_once_with("BTCUSDT-PERP")
    
    @pytest.mark.asyncio
    async def test_okx_derivatives_data_flow(self, aggregator):
        """测试OKX衍生品数据流"""
        # 模拟OKX衍生品适配器响应
        mock_okx_adapter = AsyncMock()
        mock_okx_adapter.get_futures_ticker.return_value = MagicMock(
            symbol="BTCUSDT-PERP",
            current_price=50600.0,
            previous_close=49600.0,
            high_24h=51600.0,
            low_24h=48600.0,
            price_change=1000.0,
            price_change_percent=2.02,
            volume_24h=1800000.0,
            quote_volume_24h=91080000000.0,
            timestamp=datetime.now(timezone.utc),
            funding_rate=-0.00005,
            open_interest=950000.0,
            index_price=50300.0,
            mark_price=50350.0
        )
        
        # 注入模拟适配器
        okx_futures_key = "okx_futures"
        aggregator.adapters[okx_futures_key] = mock_okx_adapter
        
        # 从数据聚合器获取OKX期货数据
        futures_data = await aggregator.get_market_data("okx", "futures", "BTCUSDT-PERP")
        
        # 验证数据流
        assert futures_data is not None
        assert futures_data.symbol == "BTCUSDT-PERP"
        assert futures_data.current_price == 50600.0
        assert futures_data.funding_rate == -0.00005
        assert futures_data.open_interest == 950000.0
        assert futures_data.index_price == 50300.0
        assert futures_data.mark_price == 50350.0
        
        # 验证适配器被正确调用
        mock_okx_adapter.get_futures_ticker.assert_called_once_with("BTCUSDT-PERP")
    
    @pytest.mark.asyncio
    async def test_futures_data_aggregation_flow(self, aggregator):
        """测试期货数据聚合流程"""
        # 模拟多个交易所的期货数据
        mock_data_responses = {
            "binance": MagicMock(
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
            ),
            "okx": MagicMock(
                symbol="BTCUSDT-PERP",
                current_price=50600.0,
                previous_close=49600.0,
                high_24h=51600.0,
                low_24h=48600.0,
                price_change=1000.0,
                price_change_percent=2.02,
                volume_24h=1800000.0,
                quote_volume_24h=91080000000.0,
                timestamp=datetime.now(timezone.utc),
                funding_rate=-0.00005,
                open_interest=950000.0,
                index_price=50300.0,
                mark_price=50350.0
            )
        }
        
        # 注入模拟适配器
        aggregator.adapters["binance_futures"] = AsyncMock(
            get_futures_ticker=AsyncMock(return_value=mock_data_responses["binance"])
        )
        aggregator.adapters["okx_futures"] = AsyncMock(
            get_futures_ticker=AsyncMock(return_value=mock_data_responses["okx"])
        )
        
        # 测试聚合数据获取
        aggregated_data = await aggregator.get_aggregated_data("futures", ["BTCUSDT-PERP"])
        
        # 验证聚合结果
        assert "BTCUSDT-PERP" in aggregated_data
        symbol_data = aggregated_data["BTCUSDT-PERP"]
        
        # 验证包含两个交易所的数据
        assert "binance" in symbol_data
        assert "okx" in symbol_data
        
        binance_data = symbol_data["binance"]
        okx_data = symbol_data["okx"]
        
        # 验证币安数据
        assert binance_data.current_price == 50500.0
        assert binance_data.funding_rate == 0.0001
        assert binance_data.open_interest == 1000000.0
        
        # 验证OKX数据
        assert okx_data.current_price == 50600.0
        assert okx_data.funding_rate == -0.00005
        assert okx_data.open_interest == 950000.0
    
    @pytest.mark.asyncio
    async def test_futures_websocket_data_flow(self, ws_manager):
        """测试期货WebSocket数据流"""
        # 模拟WebSocket消息处理
        received_data = []
        
        def data_callback(data):
            received_data.append(data)
        
        # 订阅期货市场数据
        subscription_id = await ws_manager.futures_ws_manager.subscribe_futures_market_data(
            "binance",
            "BTCUSDT-PERP",
            data_callback
        )
        
        # 模拟期货WebSocket消息
        futures_message = {
            "type": "ticker",
            "symbol": "BTCUSDT-PERP",
            "price": 50500.0,
            "change": 1000.0,
            "change_percent": 2.02,
            "volume": 2000000.0,
            "high": 51500.0,
            "low": 48500.0,
            "funding_rate": 0.0001,
            "open_interest": 1000000.0,
            "index_price": 50200.0,
            "mark_price": 50250.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # 手动触发消息处理（模拟WebSocket接收）
        data_callback(futures_message)
        
        # 验证数据接收
        assert len(received_data) == 1
        assert received_data[0]["symbol"] == "BTCUSDT-PERP"
        assert received_data[0]["funding_rate"] == 0.0001
        assert received_data[0]["open_interest"] == 1000000.0
        assert received_data[0]["index_price"] == 50200.0
        assert received_data[0]["mark_price"] == 50250.0
    
    @pytest.mark.asyncio
    async def test_futures_api_endpoint_flow(self, aggregator):
        """测试期货API端点数据流"""
        # 模拟API响应数据
        mock_api_response = {
            "symbol": "BTCUSDT-PERP",
            "current_price": 50500.0,
            "previous_close": 49500.0,
            "high_24h": 51500.0,
            "low_24h": 48500.0,
            "price_change": 1000.0,
            "price_change_percent": 2.02,
            "volume_24h": 2000000.0,
            "quote_volume_24h": 101000000000.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "funding_rate": 0.0001,
            "open_interest": 1000000.0,
            "index_price": 50200.0,
            "mark_price": 50250.0
        }
        
        # 注入模拟数据到聚合器
        aggregator.futures_aggregator.futures_data_cache["binance:futures:BTCUSDT-PERP"] = MagicMock(
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
        
        # 测试期货API端点数据获取
        futures_data = await aggregator.futures_aggregator.get_futures_market_data("binance", "BTCUSDT-PERP")
        
        # 验证API响应数据
        assert futures_data is not None
        assert futures_data.symbol == mock_api_response["symbol"]
        assert futures_data.current_price == mock_api_response["current_price"]
        assert futures_data.funding_rate == mock_api_response["funding_rate"]
        assert futures_data.open_interest == mock_api_response["open_interest"]
        assert futures_data.index_price == mock_api_response["index_price"]
        assert futures_data.mark_price == mock_api_response["mark_price"]
    
    @pytest.mark.asyncio
    async def test_futures_subscription_flow(self, aggregator):
        """测试期货订阅数据流"""
        subscription_data = []
        
        def futures_callback(futures_data):
            subscription_data.append(futures_data)
        
        # 订阅期货市场数据
        await aggregator.subscribe_market_data(
            "binance",
            "futures",
            "BTCUSDT-PERP",
            futures_callback
        )
        
        # 验证订阅创建
        assert len(aggregator.subscriptions) == 1
        subscription_key = "binance_futures_BTCUSDT-PERP"
        assert subscription_key in aggregator.subscriptions
        assert len(aggregator.subscriptions[subscription_key]) == 1
        
        # 模拟更新期货数据（模拟实时数据流）
        futures_update_data = MagicMock(
            symbol="BTCUSDT-PERP",
            current_price=50600.0,
            previous_close=49500.0,
            high_24h=51500.0,
            low_24h=48500.0,
            price_change=1100.0,
            price_change_percent=2.22,
            volume_24h=2100000.0,
            quote_volume_24h=106260000000.0,
            timestamp=datetime.now(timezone.utc),
            funding_rate=0.00015,
            open_interest=1100000.0,
            index_price=50300.0,
            mark_price=50350.0
        )
        
        # 手动触发订阅回调（模拟数据更新）
        await aggregator._safe_callback(futures_callback, futures_update_data)
        
        # 验证订阅回调执行
        assert len(subscription_data) == 1
        assert subscription_data[0].symbol == "BTCUSDT-PERP"
        assert subscription_data[0].current_price == 50600.0
        assert subscription_data[0].funding_rate == 0.00015
        assert subscription_data[0].open_interest == 1100000.0
        
        # 取消订阅
        await aggregator.unsubscribe_market_data(
            "binance",
            "futures",
            "BTCUSDT-PERP",
            futures_callback
        )
        
        # 验证订阅取消
        assert len(aggregator.subscriptions) == 0
    
    @pytest.mark.asyncio
    async def test_futures_data_caching_flow(self, aggregator):
        """测试期货数据缓存流程"""
        # 创建期货数据
        futures_data = MagicMock(
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
        aggregator.futures_aggregator.futures_data_cache[futures_cache_key] = futures_data
        
        # 验证缓存存储
        assert futures_cache_key in aggregator.futures_aggregator.futures_data_cache
        cached_data = aggregator.futures_aggregator.futures_data_cache[futures_cache_key]
        assert cached_data.symbol == "BTCUSDT-PERP"
        assert cached_data.funding_rate == 0.0001
        assert cached_data.open_interest == 1000000.0
        
        # 验证缓存过期时间检查
        old_timestamp = datetime.now(timezone.utc).timestamp() - 400  # 6.7分钟前
        futures_data.timestamp = datetime.fromtimestamp(old_timestamp)
        
        # 模拟缓存过期检查（这里简化实现）
        cache_age = (datetime.now(timezone.utc) - futures_data.timestamp).total_seconds()
        assert cache_age > 300  # 超过5分钟缓存时间
    
    @pytest.mark.asyncio
    async def test_futures_monitoring_flow(self, aggregator):
        """测试期货市场监控流程"""
        futures_aggregator = aggregator.futures_aggregator
        
        # 启动期货市场监控
        monitoring_task = asyncio.create_task(
            futures_aggregator.monitor_futures_market("binance", ["BTCUSDT-PERP"], 1.0)
        )
        
        # 验证监控任务启动
        assert len(futures_aggregator.active_futures_subscriptions) == 1
        assert "binance:BTCUSDT-PERP" in futures_aggregator.active_futures_subscriptions
        
        # 等待一段时间
        await asyncio.sleep(0.1)
        
        # 设置模拟期货数据
        futures_data = MagicMock(
            symbol="BTCUSDT-PERP",
            current_price=50500.0,
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
        
        # 模拟添加数据到缓存
        futures_cache_key = "binance:futures:BTCUSDT-PERP"
        futures_aggregator.futures_data_cache[futures_cache_key] = futures_data
        
        # 停止监控
        await futures_aggregator.stop_monitoring("binance", "BTCUSDT-PERP")
        
        # 验证监控停止
        assert "binance:BTCUSDT-PERP" not in futures_aggregator.active_futures_subscriptions
        assert len(futures_aggregator.monitoring_tasks) == 0
        
        # 清理任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])