"""
币安期货交易适配器
实现期货市场的数据获取和交易功能
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode

import aiohttp
import structlog

from ...storage.models import MarketType, Exchange
from ..base import (
    ExchangeAdapterBase,
    MarketData, OrderBook, Trade, Candle,
    FundingRateData, OpenInterestData
)

logger = structlog.get_logger()


class BinanceFuturesAdapter(ExchangeAdapterBase):
    """币安期货适配器"""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        is_testnet: bool = True,
        base_url: Optional[str] = None
    ):
        super().__init__()
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_testnet = is_testnet
        
        # 设置API基础URL
        if base_url:
            self.base_url = base_url
        elif is_testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        # 会话管理
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_semaphore = asyncio.Semaphore(50)  # 限制并发请求数
        
        # 缓存
        self._symbol_info_cache: Dict[str, Dict] = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5分钟缓存
        
        self.exchange = Exchange.BINANCE.value
        self.market_type = MarketType.FUTURES
        
        logger.info("币安期货适配器初始化完成", base_url=self.base_url, testnet=is_testnet)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _ensure_session(self):
        """确保会话存在"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'X-MBX-APIKEY': self.api_key,
                    'Content-Type': 'application/json'
                }
            )
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _generate_signature(self, query_string: str) -> str:
        """生成API签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """发送API请求"""
        await self._ensure_session()
        async with self._request_semaphore:
            try:
                # 构建请求URL
                url = f"{self.base_url}{endpoint}"
                
                # 处理参数
                query_params = params.copy() if params else {}
                
                if signed:
                    query_params['timestamp'] = int(time.time() * 1000)
                    query_string = urlencode(query_params)
                    query_params['signature'] = self._generate_signature(query_string)
                
                # 发送请求
                if method.upper() == 'GET':
                    response = await self._session.get(url, params=query_params)
                elif method.upper() == 'POST':
                    response = await self._session.post(url, json=data, params=query_params)
                elif method.upper() == 'PUT':
                    response = await self._session.put(url, json=data, params=query_params)
                elif method.upper() == 'DELETE':
                    response = await self._session.delete(url, params=query_params)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                # 检查响应状态
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "API请求失败",
                        method=method,
                        endpoint=endpoint,
                        status=response.status,
                        error=error_text
                    )
                    raise Exception(f"API请求失败: {response.status} - {error_text}")
                
                # 解析响应
                response_data = await response.json()
                
                # 检查业务逻辑错误
                if isinstance(response_data, dict) and 'code' in response_data:
                    if response_data.get('code') != 0:
                        error_msg = response_data.get('msg', '未知错误')
                        raise ValueError(f"业务错误: {error_msg}")
                
                logger.debug(
                    "API请求成功",
                    method=method,
                    endpoint=endpoint,
                    has_data=bool(response_data)
                )
                
                return response_data
                
            except aiohttp.ClientError as e:
                logger.error("网络请求错误", endpoint=endpoint, error=str(e))
                raise Exception(f"网络请求错误: {str(e)}")
            except Exception as e:
                logger.error("请求处理错误", endpoint=endpoint, error=str(e))
                raise
    
    async def get_futures_ticker(self, symbol: str) -> MarketData:
        """获取期货价格信息"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/ticker/24hr",
                params={"symbol": symbol}
            )
            
            # 验证必要字段
            required_fields = ['symbol', 'lastPrice', 'volume', 'priceChange', 'priceChangePercent']
            for field in required_fields:
                if field not in response:
                    raise ValueError(f"响应中缺少必要字段: {field}")
            
            # 获取额外期货数据
            funding_rate_data = await self.get_funding_rate(symbol)
            open_interest_data = await self.get_open_interest(symbol)
            
            # 构建市场数据
            market_data = MarketData(
                symbol=symbol,
                current_price=float(response['lastPrice']),
                previous_close=float(response.get('prevClosePrice', response['lastPrice'])),
                high_24h=float(response['highPrice']),
                low_24h=float(response['lowPrice']),
                price_change=float(response['priceChange']),
                price_change_percent=float(response['priceChangePercent']),
                volume_24h=float(response['volume']),
                quote_volume_24h=float(response['quoteVolume']),
                timestamp=datetime.utcnow(),
                
                # 期货特有字段
                funding_rate=funding_rate_data.get('last_funding_rate') if funding_rate_data else None,
                open_interest=open_interest_data.get('open_interest') if open_interest_data else None,
                mark_price=float(response.get('markPrice', response['lastPrice'])),
                index_price=float(response.get('indexPrice', response['lastPrice'])),
            )
            
            logger.info("获取期货价格成功", symbol=symbol, price=market_data.current_price)
            return market_data
            
        except Exception as e:
            logger.error("获取期货价格失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_order_book(
        self,
        symbol: str,
        limit: int = 100
    ) -> OrderBook:
        """获取期货订单簿"""
        try:
            # 验证参数
            if limit not in [5, 10, 20, 50, 100, 500, 1000]:
                raise ValueError(f"不支持的订单簿深度: {limit}")
            
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/depth",
                params={
                    "symbol": symbol,
                    "limit": limit
                }
            )
            
            # 验证必要字段
            if 'bids' not in response or 'asks' not in response:
                raise ValueError("响应中缺少bids或asks字段")
            
            # 解析订单簿数据
            bids = [
                [float(price), float(qty)]
                for price, qty in response['bids']
            ]
            
            asks = [
                [float(price), float(qty)]
                for price, qty in response['asks']
            ]
            
            order_book = OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.utcnow()
            )
            
            logger.debug(
                "获取期货订单簿成功",
                symbol=symbol,
                bids_count=len(bids),
                asks_count=len(asks)
            )
            
            return order_book
            
        except Exception as e:
            logger.error("获取期货订单簿失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_trades(
        self,
        symbol: str,
        limit: int = 500,
        from_id: Optional[int] = None
    ) -> List[Trade]:
        """获取期货交易记录"""
        try:
            params = {
                "symbol": symbol,
                "limit": limit
            }
            
            if from_id:
                params["fromId"] = from_id
            
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/trades",
                params=params
            )
            
            trades = []
            for trade_data in response:
                # 确定交易方向
                is_buyer_maker = trade_data.get('isBuyerMaker', False)
                side = "sell" if is_buyer_maker else "buy"
                
                trade = Trade(
                    id=str(trade_data['id']),
                    symbol=symbol,
                    price=float(trade_data['price']),
                    quantity=float(trade_data['qty']),
                    side=side,
                    timestamp=datetime.fromtimestamp(trade_data['time'] / 1000)
                )
                
                trades.append(trade)
            
            logger.debug(
                "获取期货交易记录成功",
                symbol=symbol,
                trades_count=len(trades)
            )
            
            return trades
            
        except Exception as e:
            logger.error("获取期货交易记录失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Candle]:
        """获取期货K线数据"""
        try:
            # 验证时间间隔
            valid_intervals = [
                '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h',
                '1d', '3d', '1w', '1M'
            ]
            if interval not in valid_intervals:
                raise ValueError(f"不支持的时间间隔: {interval}")
            
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            if start_time:
                params["startTime"] = int(start_time.timestamp() * 1000)
            if end_time:
                params["endTime"] = int(end_time.timestamp() * 1000)
            
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/klines",
                params=params
            )
            
            candles = []
            for kline_data in response:
                candle = Candle(
                    symbol=symbol,
                    interval=interval,
                    open_time=datetime.fromtimestamp(kline_data[0] / 1000),
                    close_time=datetime.fromtimestamp(kline_data[6] / 1000),
                    open_price=float(kline_data[1]),
                    high_price=float(kline_data[2]),
                    low_price=float(kline_data[3]),
                    close_price=float(kline_data[4]),
                    volume=float(kline_data[5]),
                    quote_volume=float(kline_data[7]),
                    trades_count=int(kline_data[8])
                )
                
                candles.append(candle)
            
            logger.debug(
                "获取期货K线数据成功",
                symbol=symbol,
                interval=interval,
                candles_count=len(candles)
            )
            
            return candles
            
        except Exception as e:
            logger.error("获取期货K线数据失败", symbol=symbol, error=str(e))
            raise
    
    async def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取资金费率"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/premiumIndex",
                params={"symbol": symbol}
            )
            
            # 检查是否有资金费率数据
            if not response:
                return None
            
            return {
                "symbol": symbol,
                "last_funding_rate": float(response.get('lastFundingRate', 0)),
                "next_funding_rate": float(response.get('nextFundingRate', 0)),
                "funding_time": int(response.get('nextFundingTime', 0) / 1000) if response.get('nextFundingTime') else None,
                "mark_price": float(response.get('markPrice', 0)),
                "index_price": float(response.get('indexPrice', 0))
            }
            
        except Exception as e:
            logger.debug("获取资金费率失败", symbol=symbol, error=str(e))
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓量"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/openInterest",
                params={"symbol": symbol}
            )
            
            # 检查是否有持仓量数据
            if not response:
                return None
            
            return {
                "symbol": symbol,
                "open_interest": float(response.get('openInterest', 0)),
                "pair": response.get('pair'),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.debug("获取持仓量失败", symbol=symbol, error=str(e))
            return None
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易所信息"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/exchangeInfo"
            )
            
            return {
                "exchange": "binance",
                "symbols": [
                    {
                        "symbol": symbol_info['symbol'],
                        "base_asset": symbol_info['baseAsset'],
                        "quote_asset": symbol_info['quoteAsset'],
                        "contract_type": symbol_info.get('contractType', 'PERPETUAL'),
                        "delivery_date": symbol_info.get('deliveryDate'),
                        "status": symbol_info['status']
                    }
                    for symbol_info in response.get('symbols', [])
                ],
                "server_time": datetime.fromtimestamp(response['serverTime'] / 1000)
            }
            
        except Exception as e:
            logger.error("获取交易所信息失败", error=str(e))
            raise
    
    async def get_server_time(self) -> datetime:
        """获取服务器时间"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/fapi/v1/time"
            )
            
            return datetime.fromtimestamp(response['serverTime'] / 1000)
            
        except Exception as e:
            logger.error("获取服务器时间失败", error=str(e))
            raise
    
    async def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        try:
            # 这里可以使用系统状态API
            server_time = await self.get_server_time()
            
            return {
                "status": "operational",
                "server_time": server_time,
                "is_synchronized": True
            }
            
        except Exception as e:
            logger.error("获取服务器状态失败", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_server_time()
            logger.info("币安期货API连接测试成功")
            return True
        except Exception as e:
            logger.error("币安期货API连接测试失败", error=str(e))
            return False
    
    def _cache_key(self, method: str, endpoint: str, params: Dict) -> str:
        """生成缓存键"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{method}:{endpoint}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache_expiry:
            return False
        
        return time.time() < self._cache_expiry[cache_key]
    
    def _update_cache(self, cache_key: str, data: Any) -> None:
        """更新缓存"""
        self._cache_expiry[cache_key] = time.time() + self._cache_ttl
        # 注意：实际应用中应该将data存储到缓存中，这里简化为缓存过期时间控制
    
    async def __del__(self):
        """析构函数"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            asyncio.create_task(self.close())


# 测试代码
if __name__ == "__main__":
    async def test_futures_adapter():
        """测试期货适配器"""
        # 创建测试适配器（使用模拟API密钥）
        adapter = BinanceFuturesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            is_testnet=True
        )
        
        try:
            async with adapter:
                # 测试连接
                is_connected = await adapter.test_connection()
                print(f"连接测试: {'成功' if is_connected else '失败'}")
                
                if is_connected:
                    # 测试获取价格
                    ticker = await adapter.get_futures_ticker("BTCUSDT-PERP")
                    print(f"BTCUSDT-PERP 价格: {ticker.current_price}")
                    
                    # 测试订单簿
                    order_book = await adapter.get_futures_order_book("BTCUSDT-PERP", 10)
                    print(f"订单簿 - 买单数量: {len(order_book.bids)}, 卖单数量: {len(order_book.asks)}")
                    
                    # 测试资金费率
                    funding_rate = await adapter.get_funding_rate("BTCUSDT-PERP")
                    if funding_rate:
                        print(f"资金费率: {funding_rate.get('last_funding_rate', 0)}")
        
        except Exception as e:
            print(f"测试失败: {e}")
    
    # 运行测试
    asyncio.run(test_futures_adapter())