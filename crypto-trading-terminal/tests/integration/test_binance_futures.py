"""
币安期货API集成测试
测试期货市场的实时数据获取和功能验证
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from backend.src.adapters.binance.futures import BinanceFuturesAdapter
from backend.src.storage.models import MarketType, Exchange


class TestBinanceFuturesAdapter:
    """币安期货适配器测试类"""
    
    @pytest.fixture
    def adapter(self):
        """创建测试适配器实例"""
        return BinanceFuturesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            is_testnet=True
        )
    
    @pytest.fixture
    def sample_futures_symbols(self):
        """测试期货交易对"""
        return [
            "BTCUSDT-PERP",
            "ETHUSDT-PERP", 
            "BNBUSDT-PERP",
            "ADAUSDT-PERP",
            "SOLUSDT-PERP"
        ]
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.exchange == "binance"
        assert adapter.market_type == MarketType.FUTURES
        assert adapter.api_key == "test_key"
        assert adapter.is_testnet is True
    
    @pytest.mark.asyncio
    async def test_get_futures_ticker(self, adapter, sample_futures_symbols):
        """测试获取期货价格信息"""
        # Mock响应数据
        mock_response = {
            "symbol": "BTCUSDT-PERP",
            "priceChange": "125.34",
            "priceChangePercent": "0.25",
            "lastPrice": "50123.45",
            "lastQty": "0.00123",
            "bidPrice": "50120.00",
            "bidQty": "0.00234",
            "askPrice": "50126.90",
            "askQty": "0.00123",
            "openPrice": "49998.11",
            "highPrice": "50500.00",
            "lowPrice": "49800.00",
            "volume": "12345.678",
            "quoteVolume": "618901234.56",
            "openTime": 1640995200000,
            "closeTime": 1641081600000,
            "count": 12345,
            # 期货特有字段
            "openInterest": "12345.67",
            "markPrice": "50123.45",
            "indexPrice": "50118.90",
            "fundingRate": "0.0001",
            "nextFundingTime": 1641081600000
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_ticker("BTCUSDT-PERP")
            
            # 验证返回数据
            assert result.symbol == "BTCUSDT-PERP"
            assert result.current_price == 50123.45
            assert result.price_change == 125.34
            assert result.price_change_percent == 0.25
            assert result.volume_24h == 12345.678
            assert result.funding_rate == 0.0001
            assert result.open_interest == 12345.67
            assert result.mark_price == 50123.45
            assert result.index_price == 50118.90
            
            # 验证请求参数
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/fapi/v1/ticker/24hr",
                params={"symbol": "BTCUSDT-PERP"}
            )
    
    @pytest.mark.asyncio
    async def test_get_futures_orderbook(self, adapter):
        """测试获取期货订单簿"""
        mock_response = {
            "lastUpdateId": 123456789,
            "bids": [
                ["50120.00", "0.00234"],
                ["50119.00", "0.00567"],
                ["50118.00", "0.00890"]
            ],
            "asks": [
                ["50126.90", "0.00123"],
                ["50127.90", "0.00345"],
                ["50128.90", "0.00678"]
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_order_book("BTCUSDT-PERP", 3)
            
            # 验证订单簿数据
            assert result.symbol == "BTCUSDT-PERP"
            assert len(result.bids) == 3
            assert len(result.asks) == 3
            assert result.bids[0][0] == 50120.00  # 价格
            assert result.bids[0][1] == 0.00234   # 数量
            assert result.asks[0][0] == 50126.90  # 价格
            assert result.asks[0][1] == 0.00123   # 数量
            
            # 验证请求参数
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/fapi/v1/depth",
                params={
                    "symbol": "BTCUSDT-PERP",
                    "limit": 3
                }
            )
    
    @pytest.mark.asyncio
    async def test_get_futures_trades(self, adapter):
        """测试获取期货交易记录"""
        mock_response = [
            {
                "id": 12345678,
                "price": "50123.45",
                "qty": "0.00123",
                "quoteQty": "61.89",
                "time": 1640995200000,
                "isBuyerMaker": True
            },
            {
                "id": 12345679,
                "price": "50124.56",
                "qty": "0.00234",
                "quoteQty": "117.42",
                "time": 1640995201000,
                "isBuyerMaker": False
            }
        ]
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_trades("BTCUSDT-PERP", 2)
            
            # 验证交易记录
            assert len(result) == 2
            assert result[0].id == "12345678"
            assert result[0].price == 50123.45
            assert result[0].quantity == 0.00123
            assert result[0].side == "sell"  # isBuyerMaker=True 表示卖单
            
            assert result[1].id == "12345679"
            assert result[1].price == 50124.56
            assert result[1].quantity == 0.00234
            assert result[1].side == "buy"   # isBuyerMaker=False 表示买单
    
    @pytest.mark.asyncio
    async def test_get_futures_klines(self, adapter):
        """测试获取期货K线数据"""
        mock_response = [
            [
                1640995200000,  # Open time
                "50100.00",     # Open price
                "50500.00",     # High price
                "49998.11",     # Low price
                "50123.45",     # Close price
                "12345.678",    # Volume
                1640998799000,  # Close time
                "618901234.56", # Quote asset volume
                12345,          # Number of trades
                "1234.567",     # Taker buy base asset volume
                "61890.123"     # Taker buy quote asset volume
            ]
        ]
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_klines("BTCUSDT-PERP", "1h", 1)
            
            # 验证K线数据
            assert len(result) == 1
            assert result[0].symbol == "BTCUSDT-PERP"
            assert result[0].interval == "1h"
            assert result[0].open_price == 50100.00
            assert result[0].high_price == 50500.00
            assert result[0].low_price == 49998.11
            assert result[0].close_price == 50123.45
            assert result[0].volume == 12345.678
            assert result[0].trades_count == 12345
    
    @pytest.mark.asyncio
    async def test_get_funding_rate(self, adapter):
        """测试获取资金费率"""
        mock_response = {
            "symbol": "BTCUSDT-PERP",
            "markPrice": "50123.45",
            "indexPrice": "50118.90",
            "lastFundingRate": "0.0001",
            "lastFundingTime": 1640995200000,
            "nextFundingRate": "0.0002",
            "nextFundingTime": 1641081600000
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_funding_rate("BTCUSDT-PERP")
            
            # 验证资金费率数据
            assert result["symbol"] == "BTCUSDT-PERP"
            assert result["last_funding_rate"] == 0.0001
            assert result["next_funding_rate"] == 0.0002
            assert result["funding_time"] == 1641081600000
    
    @pytest.mark.asyncio
    async def test_get_open_interest(self, adapter):
        """测试获取持仓量"""
        mock_response = {
            "symbol": "BTCUSDT-PERP",
            "openInterest": "12345.67",
            "pair": "BTCUSDT",
            "timestamp": 1640995200000
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_open_interest("BTCUSDT-PERP")
            
            # 验证持仓量数据
            assert result["symbol"] == "BTCUSDT-PERP"
            assert result["open_interest"] == 12345.67
    
    @pytest.mark.asyncio
    async def test_error_handling(self, adapter):
        """测试错误处理"""
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            # 模拟API错误
            mock_request.side_effect = Exception("API连接失败")
            
            with pytest.raises(Exception, match="API连接失败"):
                await adapter.get_futures_ticker("INVALID-SYMBOL")
    
    @pytest.mark.asyncio
    async def test_data_validation(self, adapter):
        """测试数据验证"""
        # 测试无效交易对
        mock_response = {
            "code": -1121,
            "msg": "Invalid symbol"
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # 应该抛出验证错误
            with pytest.raises(ValueError, match="Invalid symbol"):
                await adapter.get_futures_ticker("INVALID-SYMBOL")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, adapter):
        """测试速率限制"""
        # 模拟快速连续请求
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                adapter.get_futures_ticker("BTCUSDT-PERP")
            )
            tasks.append(task)
        
        # 所有请求应该都能成功（使用mock）
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "symbol": "BTCUSDT-PERP",
                "priceChange": "0.00",
                "priceChangePercent": "0.00",
                "lastPrice": "50000.00",
                "volume": "1000.00"
            }
            
            results = await asyncio.gather(*tasks)
            
            # 验证所有请求都成功返回
            assert len(results) == 10
            for result in results:
                assert result.symbol == "BTCUSDT-PERP"
                assert result.current_price == 50000.00
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_batch(self, adapter, sample_futures_symbols):
        """测试批量获取多个交易对数据"""
        mock_responses = {
            "BTCUSDT-PERP": {
                "symbol": "BTCUSDT-PERP",
                "priceChange": "125.34",
                "priceChangePercent": "0.25",
                "lastPrice": "50123.45",
                "volume": "12345.678"
            },
            "ETHUSDT-PERP": {
                "symbol": "ETHUSDT-PERP",
                "priceChange": "-12.45",
                "priceChangePercent": "-0.18",
                "lastPrice": "6890.12",
                "volume": "23456.789"
            }
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            # 模拟批量请求
            async def mock_batch_request(symbol):
                return mock_responses.get(symbol, {})
            
            mock_request.side_effect = mock_batch_request
            
            results = []
            for symbol in sample_futures_symbols[:2]:  # 只测试前两个
                result = await adapter.get_futures_ticker(symbol)
                results.append(result)
            
            # 验证批量结果
            assert len(results) == 2
            assert results[0].symbol == "BTCUSDT-PERP"
            assert results[1].symbol == "ETHUSDT-PERP"
    
    @pytest.mark.asyncio
    async def test_futures_specific_fields(self, adapter):
        """测试期货特有字段验证"""
        mock_response = {
            "symbol": "BTCUSDT-PERP",
            "priceChange": "0.00",
            "priceChangePercent": "0.00",
            "lastPrice": "50000.00",
            "volume": "1000.00",
            # 期货特有字段
            "openInterest": "9876.54",
            "markPrice": "50005.00",
            "indexPrice": "50000.00",
            "fundingRate": "0.0001",
            "nextFundingTime": 1641081600000
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_ticker("BTCUSDT-PERP")
            
            # 验证期货特有字段
            assert hasattr(result, 'funding_rate')
            assert hasattr(result, 'open_interest')
            assert hasattr(result, 'mark_price')
            assert hasattr(result, 'index_price')
            
            assert result.funding_rate == 0.0001
            assert result.open_interest == 9876.54
            assert result.mark_price == 50005.00
            assert result.index_price == 50000.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])