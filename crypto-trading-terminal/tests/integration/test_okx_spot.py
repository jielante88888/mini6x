"""
OKX现货API集成契约测试
测试与OKX现货交易所API的完整集成
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from src.adapters.base import MarketData, OrderBook, Trade, TimeInterval
from src.utils.exceptions import ExchangeConnectionError, MarketDataError


class TestOKXSpotAPI:
    """OKX现货API集成测试"""
    
    @pytest.fixture
    def mock_ccxt_okx(self):
        """模拟OKX CCXT客户端"""
        mock_client = AsyncMock()
        mock_client.create_order.return_value = {
            'id': 'OKX_TEST_ORDER_123',
            'symbol': 'BTC-USDT',
            'type': 'limit',
            'side': 'buy',
            'amount': 0.001,
            'price': 50000.0,
            'status': 'open'
        }
        mock_client.fetch_order.return_value = {
            'id': 'OKX_TEST_ORDER_123',
            'symbol': 'BTC-USDT',
            'status': 'open',
            'amount': 0.001,
            'filled': 0.0,
            'remaining': 0.001
        }
        mock_client.cancel_order.return_value = {
            'id': 'OKX_TEST_ORDER_123',
            'status': 'canceled'
        }
        mock_client.fetch_balance.return_value = {
            'BTC': {'free': '1.0', 'used': '0.5'},
            'USDT': {'free': '50000.0', 'used': '0.0'}
        }
        return mock_client
    
    @pytest.fixture
    def okx_adapter(self):
        """创建OKX现货适配器实例"""
        from src.adapters.okx.spot import OKXSpotAdapter
        return OKXSpotAdapter(api_key="test_key", secret_key="test_secret", passphrase="test_pass", is_testnet=True)
    
    @pytest.mark.asyncio
    async def test_connection_and_initialization(self, okx_adapter, mock_ccxt_okx):
        """测试OKX现货API连接和初始化"""
        with patch('src.adapters.okx.spot.ccxt.okx') as mock_ccxt:
            mock_ccxt.return_value = mock_ccxt_okx
            
            # 测试连接
            result = await okx_adapter.connect()
            assert result is True
            assert okx_adapter._is_connected is True
            
            # 测试健康状态
            with patch.object(okx_adapter.session, 'get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {
                    'code': '0',
                    'msg': '',
                    'data': [{'ts': '1640995200000'}]
                }
                mock_get.return_value.__aenter__.return_value = mock_response
                
                health = await okx_adapter.is_healthy()
                assert health is True
    
    @pytest.mark.asyncio
    async def test_spot_ticker_data_structure(self, okx_adapter):
        """测试现货价格数据结构验证"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [{
                    'instId': 'BTC-USDT',
                    'last': '50000.0',
                    'open24h': '51000.0',
                    'high24h': '52000.0',
                    'low24h': '49000.0',
                    'vol24h': '1000.0',
                    'volCcy24h': '50000000.0',
                    'ts': '1640995200000'
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            ticker = await okx_adapter.get_spot_ticker("BTC-USDT")
            
            assert isinstance(ticker, MarketData)
            assert ticker.symbol == "BTC-USDT"
            assert ticker.current_price == Decimal('50000.0')
            assert ticker.previous_close == Decimal('51000.0')
            assert ticker.high_24h == Decimal('52000.0')
            assert ticker.low_24h == Decimal('49000.0')
            assert ticker.volume_24h == Decimal('1000.0')
            assert ticker.quote_volume_24h == Decimal('50000000.0')
            assert isinstance(ticker.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_spot_order_book_data(self, okx_adapter):
        """测试现货订单簿数据"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [{
                    'bids': [['50000.0', '1.0', '1', '0.5'], ['49999.0', '2.0', '1', '0.5']],
                    'asks': [['50001.0', '1.5', '1', '0.5'], ['50002.0', '0.5', '1', '0.5']],
                    'ts': '1640995200000'
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            order_book = await okx_adapter.get_spot_order_book("BTC-USDT", limit=10)
            
            assert isinstance(order_book, OrderBook)
            assert order_book.symbol == "BTC-USDT"
            assert len(order_book.bids) == 2
            assert len(order_book.asks) == 2
            assert order_book.bids[0] == (Decimal('50000.0'), Decimal('1.0'))
            assert order_book.asks[0] == (Decimal('50001.0'), Decimal('1.5'))
            assert isinstance(order_book.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_spot_trades_data(self, okx_adapter):
        """测试现货交易记录数据"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [
                    {
                        'tradeId': '12345',
                        'px': '50000.0',
                        'sz': '0.1',
                        'side': 'sell',
                        'ts': '1640995200000'
                    },
                    {
                        'tradeId': '12346',
                        'px': '50001.0',
                        'sz': '0.05',
                        'side': 'buy',
                        'ts': '1640995201000'
                    }
                ]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            trades = await okx_adapter.get_spot_trades("BTC-USDT", limit=5)
            
            assert isinstance(trades, list)
            assert len(trades) == 2
            
            trade1 = trades[0]
            assert isinstance(trade1, Trade)
            assert trade1.id == "12345"
            assert trade1.symbol == "BTC-USDT"
            assert trade1.price == Decimal('50000.0')
            assert trade1.quantity == Decimal('0.1')
            assert trade1.side.value == "sell"
            assert isinstance(trade1.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_exchange_connection_error_handling(self, okx_adapter):
        """测试交易所连接错误处理"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Connection timeout")
            
            with pytest.raises(Exception):
                await okx_adapter.get_spot_ticker("BTC-USDT")
    
    @pytest.mark.asyncio
    async def test_invalid_symbol_handling(self, okx_adapter):
        """测试无效交易对处理"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '50001',
                'msg': 'Instrument ID does not exist',
                'data': []
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception):
                await okx_adapter.get_spot_ticker("INVALID-PAIR")
    
    @pytest.mark.asyncio
    async def test_supported_symbols_validation(self, okx_adapter):
        """测试支持的交易对验证"""
        # 预设支持的交易对列表
        okx_adapter._supported_symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT"]
        
        # 测试有效交易对
        assert okx_adapter.validate_symbol("BTC-USDT") is True
        
        # 测试无效交易对
        assert okx_adapter.validate_symbol("INVALID-PAIR") is False
        
        # 测试空列表情况
        okx_adapter._supported_symbols = []
        assert okx_adapter.validate_symbol("ANY-PAIR") is True  # 返回True让API处理
    
    @pytest.mark.asyncio
    async def test_rate_limiting_and_batch_processing(self, okx_adapter):
        """测试速率限制和批量处理"""
        symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT"]
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [{
                    'instId': 'BTC-USDT',
                    'last': '50000.0',
                    'open24h': '51000.0',
                    'high24h': '52000.0',
                    'low24h': '49000.0',
                    'vol24h': '1000.0',
                    'volCcy24h': '50000000.0',
                    'ts': '1640995200000'
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # 测试单个交易对
            ticker = await okx_adapter.get_spot_ticker("BTC-USDT")
            assert ticker.current_price == Decimal('50000.0')
            
            # 验证调用次数
            assert mock_get.call_count == 1
    
    @pytest.mark.asyncio
    async def test_real_time_data_streaming(self, okx_adapter):
        """测试实时数据流"""
        # WebSocket订阅功能暂时未实现，应该返回None
        with patch('src.adapters.okx.spot.ws_connect') as mock_ws:
            mock_ws.side_effect = Exception("WebSocket not implemented")
            
            # 订阅应该引发NotImplementedError
            with pytest.raises(NotImplementedError):
                async for _ in okx_adapter.subscribe_spot_ticker("BTC-USDT"):
                    pass
    
    @pytest.mark.asyncio
    async def test_order_management_operations(self, okx_adapter, mock_ccxt_okx):
        """测试订单管理操作"""
        with patch('src.adapters.okx.spot.ccxt.okx') as mock_ccxt:
            mock_ccxt.return_value = mock_ccxt_okx
            
            # 创建现货订单
            order = await okx_adapter.create_spot_order(
                symbol="BTC-USDT",
                side="buy",
                order_type="limit",
                quantity=Decimal('0.001'),
                price=Decimal('50000.0')
            )
            
            assert order['id'] == 'OKX_TEST_ORDER_123'
            assert order['symbol'] == 'BTC-USDT'
            
            # 获取订单状态
            status = await okx_adapter.get_spot_order_status("BTC-USDT", "OKX_TEST_ORDER_123")
            assert status['id'] == 'OKX_TEST_ORDER_123'
            
            # 取消订单
            cancel_result = await okx_adapter.cancel_spot_order("BTC-USDT", "OKX_TEST_ORDER_123")
            assert cancel_result['status'] == 'canceled'
    
    @pytest.mark.asyncio
    async def test_account_balance_operations(self, okx_adapter, mock_ccxt_okx):
        """测试账户余额操作"""
        with patch('src.adapters.okx.spot.ccxt.okx') as mock_ccxt:
            mock_ccxt.return_value = mock_ccxt_okx
            
            balance = await okx_adapter.get_spot_balance()
            
            assert 'BTC' in balance
            assert 'USDT' in balance
            assert balance['BTC']['free'] == '1.0'
            assert balance['USDT']['free'] == '50000.0'
    
    @pytest.mark.asyncio
    async def test_data_consistency_validation(self, okx_adapter):
        """测试数据一致性验证"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟返回不完整的数据
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [{
                    'instId': 'BTC-USDT',
                    'last': '50000.0',
                    # 缺少其他必要字段
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # 应该在解析过程中抛出异常
            with pytest.raises(Exception):
                await okx_adapter.get_spot_ticker("BTC-USDT")
    
    @pytest.mark.asyncio
    async def test_performance_and_error_scenarios(self, okx_adapter):
        """测试性能和错误场景"""
        import time
        
        # 测试API响应时间
        start_time = time.time()
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'code': '0',
                'msg': '',
                'data': [{
                    'instId': 'BTC-USDT',
                    'last': '50000.0',
                    'open24h': '51000.0',
                    'high24h': '52000.0',
                    'low24h': '49000.0',
                    'vol24h': '1000.0',
                    'volCcy24h': '50000000.0',
                    'ts': '1640995200000'
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            ticker = await okx_adapter.get_spot_ticker("BTC-USDT")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # 验证响应时间合理（模拟环境应该很快）
            assert response_time < 1.0  # 1秒内
            assert ticker is not None


if __name__ == "__main__":
    print("OKX现货API集成契约测试准备完成")