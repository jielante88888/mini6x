"""
币安现货交易适配器
实现币安现货市场的所有核心功能
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any, AsyncGenerator, Tuple
from urllib.parse import urlencode

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


@register_exchange("binance")
class BinanceSpotAdapter(BaseExchangeAdapter):
    """币安现货交易适配器"""
    
    # API配置
    BASE_URL = "https://api.binance.com"
    TESTNET_URL = "https://testnet.binance.vision"
    SPOT_WS_URL = "wss://stream.binance.com:9443/ws"
    SPOT_WS_TESTNET_URL = "wss://testnet.binance.vision/ws"
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 passphrase: Optional[str] = None, is_testnet: bool = True):
        """
        初始化币安现货适配器
        
        Args:
            api_key: 币安API密钥
            secret_key: 币安密钥
            passphrase: 币安不需要密码短语
            is_testnet: 是否使用测试网
        """
        super().__init__(api_key, secret_key, passphrase, is_testnet)
        
        # 配置CCXT实例
        ccxt_config = {
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'sandbox': self.is_testnet,
            'enableRateLimit': True,
        }
        
        self.ccxt_client = ccxt.binance(ccxt_config)
        self.session = None
        
        # WebSocket连接管理
        self.ws_connections: Dict[str, Any] = {}
        self.ws_subscribers: Dict[str, List] = {}
        
        # 缓存
        self._exchange_info: Optional[Dict[str, Any]] = None
        self._supported_symbols: List[str] = []
        
    @property
    def exchange_name(self) -> str:
        return "binance"
    
    @property
    def exchange_info(self) -> ExchangeInfo:
        """币安交易所信息"""
        # 返回交易所基本信息 - 实际应用中应该从缓存或配置获取
        return ExchangeInfo(
            name="Binance",
            is_testnet=self.is_testnet,
            spot_supported=True,
            futures_supported=False,  # 这是现货适配器
            rate_limits={
                'weight': 1200,
                'orders': 50,
                'interval': 'minute'
            },
            supported_intervals=[
                TimeInterval.MINUTE_1, TimeInterval.MINUTE_3, TimeInterval.MINUTE_5,
                TimeInterval.MINUTE_15, TimeInterval.MINUTE_30, TimeInterval.HOUR_1,
                TimeInterval.HOUR_2, TimeInterval.HOUR_4, TimeInterval.HOUR_6,
                TimeInterval.HOUR_8, TimeInterval.HOUR_12, TimeInterval.DAY_1,
                TimeInterval.WEEK_1, TimeInterval.MONTH_1
            ]
        )
    
    async def connect(self) -> bool:
        """连接到币安API"""
        try:
            self.logger.info("正在连接币安现货API...")
            
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 测试连接 - 获取交易所状态
            await self._fetch_exchange_info()
            
            self._is_connected = True
            self._last_heartbeat = datetime.utcnow()
            
            self.logger.info("币安现货API连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接币安现货API失败: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            self.logger.info("正在断开币安现货API连接...")
            
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
            self.logger.info("币安现货API连接已断开")
            
        except Exception as e:
            self.logger.error(f"断开币安现货连接时出错: {e}")
    
    async def is_healthy(self) -> bool:
        """检查连接健康状态"""
        try:
            if not self._is_connected or not self.session:
                return False
            
            # 简单的API调用测试
            async with self.session.get(f"{self._get_api_base_url()}/api/v3/ping") as response:
                if response.status == 200:
                    self._last_heartbeat = datetime.utcnow()
                    return True
                return False
                
        except Exception as e:
            self.logger.warning(f"健康检查失败: {e}")
            return False
    
    async def get_spot_ticker(self, symbol: str) -> MarketData:
        """获取现货价格信息"""
        try:
            url = f"{self._get_api_base_url()}/api/v3/ticker/24hr"
            params = {'symbol': symbol.upper()}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_ticker_data(data, symbol)
                else:
                    raise Exception(f"获取{symbol}价格信息失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货价格失败 {symbol}: {e}")
            raise
    
    async def get_spot_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """获取现货订单簿"""
        try:
            if limit not in [5, 10, 20, 50, 100, 500, 1000]:
                limit = 100  # 默认值
            
            url = f"{self._get_api_base_url()}/api/v3/depth"
            params = {'symbol': symbol.upper(), 'limit': limit}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_order_book_data(data, symbol)
                else:
                    raise Exception(f"获取{symbol}订单簿失败: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"获取现货订单簿失败 {symbol}: {e}")
            raise
    
    async def get_spot_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """获取现货交易记录"""
        try:
            url = f"{self._get_api_base_url()}/api/v3/trades"
            params = {'symbol': symbol.upper(), 'limit': limit}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [self._parse_trade_data(trade, symbol) for trade in data]
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
            url = f"{self._get_api_base_url()}/api/v3/klines"
            
            params = {
                'symbol': symbol.upper(),
                'interval': interval.value,
                'limit': min(limit, 1000)  # 币安限制
            }
            
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [self._parse_kline_data(kline, symbol, interval) for kline in data]
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
        stream_name = f"{symbol.lower()}@ticker"
        return await self._subscribe_stream(stream_name, self._parse_ws_ticker, MarketData)
    
    async def subscribe_futures_ticker(self, symbol: str) -> AsyncGenerator[MarketData, None]:
        """现货适配器不支持期货价格流"""
        raise NotImplementedError("现货适配器不支持期货数据")
    
    async def subscribe_spot_order_book(self, symbol: str) -> AsyncGenerator[OrderBook, None]:
        """订阅现货订单簿流"""
        stream_name = f"{symbol.lower()}@depth"
        return await self._subscribe_stream(stream_name, self._parse_ws_order_book, OrderBook)
    
    async def subscribe_futures_order_book(self, symbol: str) -> AsyncGenerator[OrderBook, None]:
        """现货适配器不支持期货订单簿"""
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
            
            order_params = {
                'symbol': symbol.upper(),
                'side': side.value.upper(),
                'type': order_type.value.upper(),
                'quantity': str(quantity)
            }
            
            if price is not None:
                order_params['price'] = str(price)
            
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            # 使用CCXT创建订单
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
    
    def _get_api_base_url(self) -> str:
        """获取API基础URL"""
        return self.TESTNET_URL if self.is_testnet else self.BASE_URL
    
    def _get_ws_url(self) -> str:
        """获取WebSocket URL"""
        return self.SPOT_WS_TESTNET_URL if self.is_testnet else self.SPOT_WS_URL
    
    async def _fetch_exchange_info(self) -> None:
        """获取交易所信息"""
        try:
            url = f"{self._get_api_base_url()}/api/v3/exchangeInfo"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self._exchange_info = data
                    
                    # 提取支持的现货交易对
                    self._supported_symbols = [
                        symbol_info['symbol'] 
                        for symbol_info in data['symbols']
                        if symbol_info.get('contractType') == 'SPOT'
                    ]
                    
                    self.logger.info(f"获取到{len(self._supported_symbols)}个现货交易对")
                else:
                    raise Exception(f"获取交易所信息失败: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"获取交易所信息失败: {e}")
            raise
    
    def _parse_ticker_data(self, data: Dict[str, Any], symbol: str) -> MarketData:
        """解析价格数据"""
        return MarketData(
            symbol=data['symbol'],
            current_price=Decimal(data['lastPrice']),
            previous_close=Decimal(data['prevClosePrice']),
            high_24h=Decimal(data['highPrice']),
            low_24h=Decimal(data['lowPrice']),
            price_change=Decimal(data['priceChange']),
            price_change_percent=Decimal(data['priceChangePercent']),
            volume_24h=Decimal(data['volume']),
            quote_volume_24h=Decimal(data['quoteVolume']),
            timestamp=datetime.utcnow().replace(tzinfo=timezone.utc)
        )
    
    def _parse_order_book_data(self, data: Dict[str, Any], symbol: str) -> OrderBook:
        """解析订单簿数据"""
        bids = [(Decimal(price), Decimal(qty)) for price, qty in data['bids']]
        asks = [(Decimal(price), Decimal(qty)) for price, qty in data['asks']]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow().replace(tzinfo=timezone.utc)
        )
    
    def _parse_trade_data(self, data: Dict[str, Any], symbol: str) -> Trade:
        """解析交易数据"""
        return Trade(
            id=data['id'],
            symbol=symbol,
            price=Decimal(data['price']),
            quantity=Decimal(data['qty']),
            side=OrderSide.SELL if data['isBuyerMaker'] else OrderSide.BUY,
            timestamp=datetime.fromtimestamp(data['time'] / 1000, tz=timezone.utc)
        )
    
    def _parse_kline_data(self, data: List[Any], symbol: str, interval: TimeInterval) -> Candle:
        """解析K线数据"""
        return Candle(
            symbol=symbol,
            interval=interval,
            open_time=datetime.fromtimestamp(data[0] / 1000, tz=timezone.utc),
            close_time=datetime.fromtimestamp(data[6] / 1000, tz=timezone.utc),
            open_price=Decimal(data[1]),
            high_price=Decimal(data[2]),
            low_price=Decimal(data[3]),
            close_price=Decimal(data[4]),
            volume=Decimal(data[5]),
            quote_volume=Decimal(data[7]),
            trades_count=int(data[8])
        )
    
    def _parse_ws_ticker(self, data: Dict[str, Any]) -> MarketData:
        """解析WebSocket价格数据"""
        return MarketData(
            symbol=data['s'],
            current_price=Decimal(data['c']),
            previous_close=Decimal(data['o']),
            high_24h=Decimal(data['h']),
            low_24h=Decimal(data['l']),
            price_change=Decimal(data['p']),
            price_change_percent=Decimal(data['P']),
            volume_24h=Decimal(data['v']),
            quote_volume_24h=Decimal(data['q']),
            timestamp=datetime.fromtimestamp(data['E'] / 1000, tz=timezone.utc)
        )
    
    def _parse_ws_order_book(self, data: Dict[str, Any]) -> OrderBook:
        """解析WebSocket订单簿数据"""
        bids = [(Decimal(price), Decimal(qty)) for price, qty in data['b']]
        asks = [(Decimal(price), Decimal(qty)) for price, qty in data['a']]
        
        return OrderBook(
            symbol=data['s'],
            bids=bids,
            asks=asks,
            timestamp=datetime.fromtimestamp(data['E'] / 1000, tz=timezone.utc)
        )
    
    async def _subscribe_stream(self, stream_name: str, parser_func, data_class):
        """订阅WebSocket流"""
        if stream_name in self.ws_connections:
            # 已存在连接，返回生成器
            yield data_class  # 占位符
            return
        
        try:
            ws_url = f"{self._get_ws_url()}/{stream_name}"
            async with ws_connect(ws_url) as websocket:
                self.ws_connections[stream_name] = websocket
                self.logger.info(f"已连接到WebSocket流: {stream_name}")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        parsed_data = parser_func(data)
                        yield parsed_data
                    except Exception as e:
                        self.logger.warning(f"解析WebSocket数据失败: {e}")
                        continue
                        
        except ConnectionClosed:
            self.logger.warning(f"WebSocket连接关闭: {stream_name}")
        except Exception as e:
            self.logger.error(f"WebSocket错误 {stream_name}: {e}")
        finally:
            if stream_name in self.ws_connections:
                del self.ws_connections[stream_name]
    
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
            await self.get_spot_ticker("BTCUSDT")
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
            self.logger.error(f"币安现货健康检查失败: {e}")
            return {
                "exchange": self.exchange_name,
                "market_type": "spot",
                "is_connected": False,
                "status": "error",
                "error": str(e)
            }