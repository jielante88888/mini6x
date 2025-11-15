"""
OKX现货交易适配器
实现OKX现货市场的所有核心功能
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any, AsyncGenerator, Tuple

import aiohttp
import ccxt.async_support as ccxt
import structlog
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from ..base import (
    BaseExchangeAdapter, MarketData, OrderBook, Trade, Candle, TimeInterval,
    OrderType, OrderSide, MarketType, ExchangeInfo, register_exchange
)

logger = structlog.get_logger(__name__)


@register_exchange("okx")
class OKXSpotAdapter(BaseExchangeAdapter):
    """OKX现货交易适配器"""
    
    # API配置
    BASE_URL = "https://www.okx.com"
    SPOT_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 passphrase: Optional[str] = None, is_testnet: bool = True):
        """
        初始化OKX现货适配器
        
        Args:
            api_key: OKX API密钥
            secret_key: OKX密钥
            passphrase: OKX密码短语
            is_testnet: 是否使用模拟盘
        """
        super().__init__(api_key, secret_key, passphrase, is_testnet)
        
        # 配置CCXT实例
        ccxt_config = {
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'password': self.passphrase,  # OKX需要password而不是passphrase
            'sandbox': self.is_testnet,
            'enableRateLimit': True,
        }
        
        self.ccxt_client = ccxt.okx(ccxt_config)
        self.session = None
        
        # WebSocket连接管理
        self.ws_connections: Dict[str, Any] = {}
        self.ws_subscribers: Dict[str, List] = {}
        
        # 缓存
        self._exchange_info: Optional[Dict[str, Any]] = None
        self._supported_symbols: List[str] = []
        
    @property
    def exchange_name(self) -> str:
        return "okx"
    
    @property
    def exchange_info(self) -> ExchangeInfo:
        """OKX交易所信息"""
        return ExchangeInfo(
            name="OKX",
            is_testnet=self.is_testnet,
            spot_supported=True,
            futures_supported=False,  # 这是现货适配器
            rate_limits={
                'weight': 20,  # OKX rate limits
                'orders': 20,
                'interval': 'second'
            },
            supported_intervals=[
                TimeInterval.MINUTE_1, TimeInterval.MINUTE_3, TimeInterval.MINUTE_5,
                TimeInterval.MINUTE_15, TimeInterval.MINUTE_30, TimeInterval.HOUR_1,
                TimeInterval.HOUR_2, TimeInterval.HOUR_4, TimeInterval.HOUR_6,
                TimeInterval.HOUR_12, TimeInterval.DAY_1, TimeInterval.WEEK_1,
                TimeInterval.MONTH_1
            ]
        )
    
    async def connect(self) -> bool:
        """连接到OKX API"""
        try:
            self.logger.info("正在连接OKX现货API...")
            
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 测试连接 - 获取交易状态
            await self._fetch_exchange_info()
            
            self._is_connected = True
            self._last_heartbeat = datetime.utcnow()
            
            self.logger.info("OKX现货API连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接OKX现货API失败: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            self.logger.info("正在断开OKX现货API连接...")
            
            # 关闭所有WebSocket连接
            for symbol, ws in self.ws_connections.items():
                if not ws.closed:
                    await ws.close()
            
            self.ws_connections.clear()
            self.ws_subscribers.clear()
            
            # 关闭HTTP会话
            if self.session and not self.session.closed:
                await self.session.close()
            
            # 关闭CCXT客户端
            if hasattr(self, 'ccxt_client'):
                await self.ccxt_client.close()
            
            self._is_connected = False
            self.logger.info("OKX现货API连接已断开")
            
        except Exception as e:
            self.logger.error(f"断开OKX现货连接时出错: {e}")
    
    async def is_healthy(self) -> bool:
        """检查连接健康状态"""
        try:
            if not self._is_connected or not self.session:
                return False
            
            # 简单的API调用测试
            async with self.session.get(f"{self.BASE_URL}/api/v5/public/time") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0':
                        self._last_heartbeat = datetime.utcnow()
                        return True
                return False
                
        except Exception as e:
            self.logger.warning(f"OKX健康检查失败: {e}")
            return False
    
    async def get_spot_ticker(self, symbol: str) -> MarketData:
        """获取现货价格信息"""
        try:
            url = f"{self.BASE_URL}/api/v5/market/ticker"
            params = {'instId': symbol.upper()}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        ticker_data = data['data'][0]
                        return self._parse_ticker_data(ticker_data, symbol)
                    else:
                        raise Exception(f"获取{symbol}价格信息失败: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"获取{symbol}价格信息失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货价格失败 {symbol}: {e}")
            raise
    
    async def get_spot_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """获取现货订单簿"""
        try:
            # OKX支持的订单簿深度
            valid_limits = [1, 5, 10, 20, 50, 100]
            if limit not in valid_limits:
                limit = 100
            
            url = f"{self.BASE_URL}/api/v5/market/books"
            params = {
                'instId': symbol.upper(),
                'sz': str(limit)
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        book_data = data['data'][0]
                        return self._parse_order_book_data(book_data, symbol)
                    else:
                        raise Exception(f"获取{symbol}订单簿失败: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"获取{symbol}订单簿失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货订单簿失败 {symbol}: {e}")
            raise
    
    async def get_spot_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """获取现货交易记录"""
        try:
            url = f"{self.BASE_URL}/api/v5/market/trades"
            params = {
                'instId': symbol.upper(),
                'limit': str(min(limit, 100))  # OKX限制
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        trades_data = data['data']
                        return [self._parse_trade_data(trade, symbol) for trade in trades_data]
                    else:
                        raise Exception(f"获取{symbol}交易记录失败: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"获取{symbol}交易记录失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货交易记录失败 {symbol}: {e}")
            raise
    
    async def get_spot_klines(
        self, 
        symbol: str, 
        interval: TimeInterval, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Candle]:
        """获取现货K线数据"""
        try:
            url = f"{self.BASE_URL}/api/v5/market/candles"
            
            params = {
                'instId': symbol.upper(),
                'bar': self._convert_interval(interval),
                'limit': str(min(limit, 100))  # OKX限制
            }
            
            if start_time:
                params['after'] = str(int(start_time.timestamp() * 1000))
            if end_time:
                params['before'] = str(int(end_time.timestamp() * 1000))
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        klines_data = data['data']
                        return [self._parse_kline_data(kline, symbol, interval) for kline in klines_data]
                    else:
                        raise Exception(f"获取{symbol}K线数据失败: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"获取{symbol}K线数据失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货K线数据失败 {symbol}: {e}")
            raise
    
    # 期货方法 - 现货适配器不支持期货交易
    async def get_futures_ticker(self, symbol: str) -> MarketData:
        """现货适配器不支持期货价格"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def get_futures_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """现货适配器不支持期货订单簿"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def get_futures_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """现货适配器不支持期货交易记录"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def get_futures_klines(
        self, 
        symbol: str, 
        interval: TimeInterval, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Candle]:
        """现货适配器不支持期货K线数据"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def subscribe_spot_ticker(self, symbol: str) -> AsyncGenerator[MarketData, None]:
        """订阅现货价格流"""
        # OKX WebSocket实现较为复杂，先返回模拟数据
        self.logger.info(f"WebSocket订阅功能待实现: {symbol}")
        # TODO: 实现OKX WebSocket订阅
        return None
    
    async def subscribe_futures_ticker(self, symbol: str) -> AsyncGenerator[MarketData, None]:
        """现货适配器不支持期货价格流"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def subscribe_spot_order_book(self, symbol: str) -> AsyncGenerator[OrderBook, None]:
        """订阅现货订单簿流"""
        self.logger.info(f"WebSocket订单簿订阅功能待实现: {symbol}")
        # TODO: 实现OKX WebSocket订单簿订阅
        return None
    
    async def subscribe_futures_order_book(self, symbol: str) -> AsyncGenerator[OrderBook, None]:
        """现货适配器不支持期货订单簿流"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def create_spot_order(
        self, 
        symbol: str, 
        side: OrderSide, 
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建现货订单"""
        try:
            if not self.api_key:
                raise Exception("需要API密钥才能下单")
            
            order = await self.ccxt_client.create_order(
                symbol=symbol.upper(),
                type=order_type.value.lower(),
                side=side.value.lower(),
                amount=float(quantity),
                price=float(price) if price else None,
                params={'clientOrderId': client_order_id}
            )
            
            self.logger.info(f"创建现货订单成功: {order.get('id', 'N/A')}")
            return order
            
        except Exception as e:
            self.logger.error(f"创建现货订单失败: {e}")
            raise
    
    async def create_futures_order(
        self, 
        symbol: str, 
        side: OrderSide, 
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
        leverage: Optional[int] = None
    ) -> Dict[str, Any]:
        """现货适配器不支持期货订单"""
        raise NotImplementedError("现货适配器不支持期货订单")
    
    async def get_spot_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """获取现货订单状态"""
        try:
            if not self.api_key:
                raise Exception("需要API密钥才能查询订单状态")
            
            order = await self.ccxt_client.fetch_order(order_id, symbol.upper())
            return order
            
        except Exception as e:
            self.logger.error(f"获取现货订单状态失败: {e}")
            raise
    
    async def get_futures_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """现货适配器不支持期货订单查询"""
        raise NotImplementedError("现货适配器不支持期货订单查询")
    
    async def cancel_spot_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """取消现货订单"""
        try:
            if not self.api_key:
                raise Exception("需要API密钥才能取消订单")
            
            result = await self.ccxt_client.cancel_order(order_id, symbol.upper())
            self.logger.info(f"取消现货订单成功: {order_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"取消现货订单失败: {e}")
            raise
    
    async def cancel_futures_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """现货适配器不支持期货订单取消"""
        raise NotImplementedError("现货适配器不支持期货订单取消")
    
    async def get_spot_balance(self) -> Dict[str, Any]:
        """获取现货账户余额"""
        try:
            if not self.api_key:
                raise Exception("需要API密钥才能获取账户余额")
            
            balance = await self.ccxt_client.fetch_balance()
            return balance
            
        except Exception as e:
            self.logger.error(f"获取现货账户余额失败: {e}")
            raise
    
    async def get_futures_balance(self) -> Dict[str, Any]:
        """现货适配器不支持期货余额查询"""
        raise NotImplementedError("现货适配器不支持期货余额查询")
    
    # ========== 私有方法 ==========
    
    def _convert_interval(self, interval: TimeInterval) -> str:
        """转换时间间隔格式"""
        interval_map = {
            TimeInterval.MINUTE_1: "1m",
            TimeInterval.MINUTE_3: "3m", 
            TimeInterval.MINUTE_5: "5m",
            TimeInterval.MINUTE_15: "15m",
            TimeInterval.MINUTE_30: "30m",
            TimeInterval.HOUR_1: "1H",
            TimeInterval.HOUR_2: "2H",
            TimeInterval.HOUR_4: "4H",
            TimeInterval.HOUR_6: "6H",
            TimeInterval.HOUR_12: "12H",
            TimeInterval.DAY_1: "1D",
            TimeInterval.WEEK_1: "1W",
            TimeInterval.MONTH_1: "1M"
        }
        return interval_map.get(interval, "1m")
    
    async def _fetch_exchange_info(self) -> None:
        """获取交易所信息"""
        try:
            url = f"{self.BASE_URL}/api/v5/public/instruments"
            params = {'instType': 'SPOT'}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        instruments = data['data']
                        self._supported_symbols = [inst['instId'] for inst in instruments]
                        self.logger.info(f"获取到{len(self._supported_symbols)}个现货交易对")
                    else:
                        raise Exception(f"获取交易所信息失败: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"获取交易所信息失败: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"获取交易所信息失败: {e}")
            raise
    
    def _parse_ticker_data(self, data: Dict[str, Any], symbol: str) -> MarketData:
        """解析价格数据"""
        # OKX ticker可能没有change24h字段，使用计算值
        current_price = Decimal(data['last'])
        open_price = Decimal(data['open24h']) if 'open24h' in data else current_price
        price_change = current_price - open_price
        price_change_percent = (price_change / open_price * 100) if open_price > 0 else Decimal('0')
        
        return MarketData(
            symbol=data['instId'],
            current_price=current_price,
            previous_close=open_price,
            high_24h=Decimal(data['high24h']),
            low_24h=Decimal(data['low24h']),
            price_change=price_change,
            price_change_percent=price_change_percent,
            volume_24h=Decimal(data['vol24h']),
            quote_volume_24h=Decimal(data['volCcy24h']),
            timestamp=datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc)
        )
    
    def _parse_order_book_data(self, data: Dict[str, Any], symbol: str) -> OrderBook:
        """解析订单簿数据"""
        # OKX订单簿可能返回: [price, qty, level, ...] 我们只取前两个值
        bids = [(Decimal(bid[0]), Decimal(bid[1])) for bid in data['bids']]
        asks = [(Decimal(ask[0]), Decimal(ask[1])) for ask in data['asks']]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc)
        )
    
    def _parse_trade_data(self, data: Dict[str, Any], symbol: str) -> Trade:
        """解析交易数据"""
        side = OrderSide.SELL if data['side'] == 'sell' else OrderSide.BUY
        
        return Trade(
            id=data['tradeId'],
            symbol=symbol,
            price=Decimal(data['px']),
            quantity=Decimal(data['sz']),
            side=side,
            timestamp=datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc)
        )
    
    def _parse_kline_data(self, data: List[Any], symbol: str, interval: TimeInterval) -> Candle:
        """解析K线数据"""
        return Candle(
            symbol=symbol,
            interval=interval,
            open_time=datetime.fromtimestamp(int(data[0]) / 1000, tz=timezone.utc),
            close_time=datetime.fromtimestamp(int(data[6]) / 1000, tz=timezone.utc),
            open_price=Decimal(data[1]),
            high_price=Decimal(data[2]),
            low_price=Decimal(data[3]),
            close_price=Decimal(data[4]),
            volume=Decimal(data[5]),
            quote_volume=Decimal(data[7]),
            trades_count=int(data[8])
        )
    
    def validate_symbol(self, symbol: str, market_type: MarketType = MarketType.SPOT) -> bool:
        """验证交易对是否支持"""
        if market_type != MarketType.SPOT:
            return False
        
        if not self._supported_symbols:
            # 如果没有缓存的符号列表，返回True让API调用处理
            return True
        
        return symbol.upper() in self._supported_symbols
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查连接状态
            is_connected = await self.is_healthy()
            
            # 检查API响应时间
            start_time = datetime.utcnow()
            await self.get_spot_ticker("BTC-USDT")
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "exchange": self.exchange_name,
                "market_type": "spot",
                "is_connected": is_connected,
                "response_time_ms": round(response_time, 2),
                "is_testnet": self.is_testnet,
                "last_heartbeat": self._last_heartbeat.isoformat(),
                "status": "healthy" if is_connected and response_time < 5000 else "unhealthy"
            }
            
        except Exception as e:
            self.logger.error(f"OKX现货健康检查失败: {e}")
            return {
                "exchange": self.exchange_name,
                "market_type": "spot",
                "is_connected": False,
                "status": "error",
                "error": str(e)
            }