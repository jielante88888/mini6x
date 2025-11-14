"""
OKX衍生品API集成测试
测试OKX期货/期权市场的实时数据获取和功能验证
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from backend.src.adapters.okx.derivatives import OKXDerivativesAdapter
from backend.src.storage.models import MarketType, Exchange


class TestOKXDerivativesAdapter:
    """OKX衍生品适配器测试类"""
    
    @pytest.fixture
    def adapter(self):
        """创建测试适配器实例"""
        return OKXDerivativesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
            is_paper=True  # 使用模拟账户
        )
    
    @pytest.fixture
    def sample_futures_symbols(self):
        """测试期货交易对"""
        return [
            "BTC-USDT-SWAP",
            "ETH-USDT-SWAP",
            "BNB-USDT-SWAP",
            "ADA-USDT-SWAP",
            "SOL-USDT-SWAP"
        ]
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.exchange == "okx"
        assert adapter.market_type == MarketType.FUTURES
        assert adapter.api_key == "test_key"
        assert adapter.passphrase == "test_passphrase"
        assert adapter.is_paper is True
    
    @pytest.mark.asyncio
    async def test_get_futures_ticker(self, adapter, sample_futures_symbols):
        """测试获取期货价格信息"""
        # Mock响应数据
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "last": "50123.45",
                    "bidPx": "50120.00",
                    "askPx": "50126.90",
                    "bidSz": "0.00234",
                    "askSz": "0.00123",
                    "open24h": "49998.11",
                    "high24h": "50500.00",
                    "low24h": "49800.00",
                    "vol24h": "12345.678",
                    "volCcy24h": "618901234.56",
                    "ts": "1640995200000",
                    # 期货特有字段
                    "fundingRate": "0.0001",
                    "nextFundingRate": "0.0002",
                    "fundingTime": "1641081600000",
                    "markPrice": "50123.45",
                    "indexPrice": "50118.90"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_ticker("BTC-USDT-SWAP")
            
            # 验证返回数据
            assert result.symbol == "BTC-USDT-SWAP"
            assert result.current_price == 50123.45
            assert result.volume_24h == 12345.678
            assert result.high_24h == 50500.00
            assert result.low_24h == 49800.00
            assert result.funding_rate == 0.0001
            assert result.mark_price == 50123.45
            assert result.index_price == 50118.90
            
            # 验证请求参数
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v5/market/ticker",
                params={"instId": "BTC-USDT-SWAP"}
            )
    
    @pytest.mark.asyncio
    async def test_get_futures_orderbook(self, adapter):
        """测试获取期货订单簿"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "bids": [
                        ["50120.00", "0.00234", "0"],
                        ["50119.00", "0.00567", "0"],
                        ["50118.00", "0.00890", "0"]
                    ],
                    "asks": [
                        ["50126.90", "0.00123", "0"],
                        ["50127.90", "0.00345", "0"],
                        ["50128.90", "0.00678", "0"]
                    ],
                    "ts": "1640995200000"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_order_book("BTC-USDT-SWAP", 3)
            
            # 验证订单簿数据
            assert result.symbol == "BTC-USDT-SWAP"
            assert len(result.bids) == 3
            assert len(result.asks) == 3
            assert result.bids[0][0] == 50120.00  # 价格
            assert result.bids[0][1] == 0.00234   # 数量
            assert result.asks[0][0] == 50126.90  # 价格
            assert result.asks[0][1] == 0.00123   # 数量
            
            # 验证请求参数
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v5/market/books",
                params={
                    "instId": "BTC-USDT-SWAP",
                    "sz": "3"
                }
            )
    
    @pytest.mark.asyncio
    async def test_get_futures_trades(self, adapter):
        """测试获取期货交易记录"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "side": "sell",
                    "sz": "0.00123",
                    "px": "50123.45",
                    "ts": "1640995200000",
                    "tradeId": "12345678"
                },
                {
                    "instId": "BTC-USDT-SWAP",
                    "side": "buy",
                    "sz": "0.00234",
                    "px": "50124.56",
                    "ts": "1640995201000",
                    "tradeId": "12345679"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_trades("BTC-USDT-SWAP", 2)
            
            # 验证交易记录
            assert len(result) == 2
            assert result[0].id == "12345678"
            assert result[0].price == 50123.45
            assert result[0].quantity == 0.00123
            assert result[0].side == "sell"
            
            assert result[1].id == "12345679"
            assert result[1].price == 50124.56
            assert result[1].quantity == 0.00234
            assert result[1].side == "buy"
    
    @pytest.mark.asyncio
    async def test_get_futures_klines(self, adapter):
        """测试获取期货K线数据"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1640995200000",  # Timestamp
                    "50100.00",       # Open price
                    "50500.00",       # High price
                    "49998.11",       # Low price
                    "50123.45",       # Close price
                    "12345.678",      # Volume
                    "618901234.56"    # Quote volume
                ]
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_klines("BTC-USDT-SWAP", "1H", 1)
            
            # 验证K线数据
            assert len(result) == 1
            assert result[0].symbol == "BTC-USDT-SWAP"
            assert result[0].interval == "1H"
            assert result[0].open_price == 50100.00
            assert result[0].high_price == 50500.00
            assert result[0].low_price == 49998.11
            assert result[0].close_price == 50123.45
            assert result[0].volume == 12345.678
    
    @pytest.mark.asyncio
    async def test_get_funding_rate(self, adapter):
        """测试获取资金费率"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "fundingRate": "0.0001",
                    "nextFundingRate": "0.0002",
                    "fundingTime": "1641081600000"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_funding_rate("BTC-USDT-SWAP")
            
            # 验证资金费率数据
            assert result["symbol"] == "BTC-USDT-SWAP"
            assert result["last_funding_rate"] == 0.0001
            assert result["next_funding_rate"] == 0.0002
            assert result["funding_time"] == 1641081600000
    
    @pytest.mark.asyncio
    async def test_get_open_interest(self, adapter):
        """测试获取持仓量"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "oi": "12345.67",
                    "oiCcy": "12345.67",
                    "ts": "1640995200000"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_open_interest("BTC-USDT-SWAP")
            
            # 验证持仓量数据
            assert result["symbol"] == "BTC-USDT-SWAP"
            assert result["open_interest"] == 12345.67
    
    @pytest.mark.asyncio
    async def test_get_swap_instruments(self, adapter):
        """测试获取永续合约列表"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instType": "SWAP",
                    "instId": "BTC-USDT-SWAP",
                    "quoteCcy": "USDT",
                    "baseCcy": "BTC",
                    "category": "1",
                    "ctType": "linear",
                    "state": "live",
                    "st": "2022-05-20T07:00:00.000Z",
                    "ctDist": "0.005,0.001,0.0005,0.0002",
                    "ctMult": "1",
                    "expTime": ""
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_swap_instruments()
            
            # 验证合约列表
            assert len(result) == 1
            assert result[0]["instId"] == "BTC-USDT-SWAP"
            assert result[0]["ctType"] == "linear"
            assert result[0]["state"] == "live"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, adapter):
        """测试错误处理"""
        mock_error_response = {
            "code": "50001",
            "msg": "Instrument not found"
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_error_response
            
            with pytest.raises(ValueError, match="Instrument not found"):
                await adapter.get_futures_ticker("INVALID-SYMBOL")
    
    @pytest.mark.asyncio
    async def test_futures_specific_fields(self, adapter):
        """测试期货特有字段验证"""
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "last": "50000.00",
                    "vol24h": "1000.00",
                    "fundingRate": "0.0001",
                    "nextFundingRate": "0.0002",
                    "fundingTime": "1641081600000",
                    "markPrice": "50005.00",
                    "indexPrice": "50000.00"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_ticker("BTC-USDT-SWAP")
            
            # 验证期货特有字段
            assert hasattr(result, 'funding_rate')
            assert hasattr(result, 'open_interest')
            assert hasattr(result, 'mark_price')
            assert hasattr(result, 'index_price')
            
            assert result.funding_rate == 0.0001
            assert result.mark_price == 50005.00
            assert result.index_price == 50000.00
    
    @pytest.mark.asyncio
    async def test_symbol_formatting(self, adapter):
        """测试交易对格式转换"""
        # 测试OKX格式到内部格式的转换
        okx_symbol = "BTC-USDT-SWAP"
        
        mock_response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "instId": okx_symbol,
                    "last": "50000.00",
                    "vol24h": "1000.00"
                }
            ]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await adapter.get_futures_ticker(okx_symbol)
            
            # 验证交易对格式正确保留
            assert result.symbol == okx_symbol
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_batch(self, adapter, sample_futures_symbols):
        """测试批量获取多个交易对数据"""
        mock_responses = {
            "BTC-USDT-SWAP": {
                "code": "0",
                "msg": "",
                "data": [{
                    "instId": "BTC-USDT-SWAP",
                    "last": "50123.45",
                    "vol24h": "12345.678"
                }]
            },
            "ETH-USDT-SWAP": {
                "code": "0",
                "msg": "",
                "data": [{
                    "instId": "ETH-USDT-SWAP",
                    "last": "6890.12",
                    "vol24h": "23456.789"
                }]
            }
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            # 模拟批量请求
            async def mock_batch_request(endpoint, params):
                symbol = params.get('instId')
                return mock_responses.get(symbol, {"code": "0", "msg": "", "data": []})
            
            mock_request.side_effect = mock_batch_request
            
            results = []
            for symbol in sample_futures_symbols[:2]:  # 只测试前两个
                result = await adapter.get_futures_ticker(symbol)
                results.append(result)
            
            # 验证批量结果
            assert len(results) == 2
            assert results[0].symbol == "BTC-USDT-SWAP"
            assert results[1].symbol == "ETH-USDT-SWAP"
    
    @pytest.mark.asyncio
    async def test_data_validation(self, adapter):
        """测试数据验证"""
        # 测试无效交易对
        mock_response = {
            "code": "50001",
            "msg": "Instrument not found"
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # 应该抛出验证错误
            with pytest.raises(ValueError, match="Instrument not found"):
                await adapter.get_futures_ticker("INVALID-SYMBOL")
    
    @pytest.mark.asyncio
    async def test_linear_vs_inverse_contracts(self, adapter):
        """测试线性合约vs反向合约"""
        linear_response = {
            "code": "0",
            "msg": "",
            "data": [{
                "instId": "BTC-USDT-SWAP",
                "ctType": "linear",
                "last": "50000.00",
                "vol24h": "1000.00"
            }]
        }
        
        with patch.object(adapter, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = linear_response
            
            result = await adapter.get_futures_ticker("BTC-USDT-SWAP")
            
            # 验证线性合约格式
            assert result.symbol == "BTC-USDT-SWAP"
            assert "linear" in result.symbol.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])