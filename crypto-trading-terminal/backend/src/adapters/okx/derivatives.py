"""
OKX衍生品交易适配器
实现期货/期权等衍生品市场的数据获取和交易功能
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

import aiohttp
import structlog

from ...storage.models import MarketType, Exchange
from ..base import (
    ExchangeAdapterBase,
    MarketData, OrderBook, Trade, Candle,
    FundingRateData, OpenInterestData
)

logger = structlog.get_logger()


class OKXDerivativesAdapter(ExchangeAdapterBase):
    """OKX衍生品适配器"""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        is_paper: bool = True,
        base_url: Optional[str] = None
    ):
        super().__init__()
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.is_paper = is_paper
        
        # 设置API基础URL
        if base_url:
            self.base_url = base_url
        elif is_paper:
            self.base_url = "https://www.okx.com"  # OKX使用统一API，支持paper trading
        else:
            self.base_url = "https://www.okx.com"
        
        # 会话管理
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_semaphore = asyncio.Semaphore(30)  # 限制并发请求数
        
        # 缓存
        self._symbol_info_cache: Dict[str, Dict] = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5分钟缓存
        
        # 请求签名计数器
        self._timestamp = int(time.time() * 1000)
        
        self.exchange = Exchange.OKX.value
        self.market_type = MarketType.FUTURES
        
        logger.info("OKX衍生品适配器初始化完成", base_url=self.base_url, paper_trading=is_paper)
    
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
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        path: str,
        body: str = ""
    ) -> str:
        """生成API签名"""
        message = timestamp + method.upper() + path + body
        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')
    
    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """获取请求头"""
        self._timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(self._timestamp, method, path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': self._timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
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
                body_data = data.copy() if data else {}
                
                # 生成请求头
                if signed:
                    body_str = json.dumps(body_data) if body_data else ""
                    headers = self._get_headers(method, endpoint, body_str)
                else:
                    headers = {'Content-Type': 'application/json'}
                
                # 构建完整URL
                if method.upper() == 'GET' and query_params:
                    # GET请求使用查询参数
                    query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
                    url_with_params = f"{url}?{query_string}"
                else:
                    url_with_params = url
                
                # 发送请求
                if method.upper() == 'GET':
                    response = await self._session.get(url_with_params, headers=headers)
                elif method.upper() == 'POST':
                    response = await self._session.post(url_with_params, json=body_data, headers=headers)
                elif method.upper() == 'PUT':
                    response = await self._session.put(url_with_params, json=body_data, headers=headers)
                elif method.upper() == 'DELETE':
                    response = await self._session.delete(url_with_params, headers=headers)
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
                
                # 检查OKX业务逻辑错误
                if isinstance(response_data, dict):
                    code = response_data.get('code')
                    if code != '0':
                        error_msg = response_data.get('msg', '未知错误')
                        raise ValueError(f"OKX API错误: {code} - {error_msg}")
                
                logger.debug(
                    "API请求成功",
                    method=method,
                    endpoint=endpoint,
                    has_data=bool(response_data.get('data'))
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
                endpoint="/api/v5/market/ticker",
                params={"instId": symbol}
            )
            
            # 检查响应数据
            data = response.get('data', [])
            if not data:
                raise ValueError(f"未找到交易对 {symbol} 的数据")
            
            ticker_data = data[0]
            
            # 验证必要字段
            required_fields = ['instId', 'last', 'vol24h']
            for field in required_fields:
                if field not in ticker_data:
                    raise ValueError(f"响应中缺少必要字段: {field}")
            
            # 获取额外期货数据
            funding_rate_data = await self.get_funding_rate(symbol)
            open_interest_data = await self.get_open_interest(symbol)
            
            # 构建市场数据
            market_data = MarketData(
                symbol=symbol,
                current_price=float(ticker_data['last']),
                previous_close=float(ticker_data.get('open24h', ticker_data['last'])),
                high_24h=float(ticker_data['high24h']),
                low_24h=float(ticker_data['low24h']),
                price_change=float(ticker_data.get('ch', '0')),
                price_change_percent=float(ticker_data.get('chUsd', '0')),
                volume_24h=float(ticker_data['vol24h']),
                quote_volume_24h=float(ticker_data.get('volCcy24h', '0')),
                timestamp=datetime.fromtimestamp(int(ticker_data['ts']) / 1000),
                
                # 期货特有字段
                funding_rate=float(ticker_data.get('fundingRate', '0')),
                open_interest=float(ticker_data.get('oi', '0')) if ticker_data.get('oi') else None,
                mark_price=float(ticker_data.get('markPrice', ticker_data['last'])),
                index_price=float(ticker_data.get('indexPrice', ticker_data['last'])),
            )
            
            logger.info("获取OKX期货价格成功", symbol=symbol, price=market_data.current_price)
            return market_data
            
        except Exception as e:
            logger.error("获取OKX期货价格失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_order_book(
        self,
        symbol: str,
        limit: int = 400
    ) -> OrderBook:
        """获取期货订单簿"""
        try:
            # OKX支持的订单簿深度
            valid_sizes = [1, 20, 400]
            if limit not in valid_sizes:
                limit = 400  # 默认最大深度
            
            response = await self._request(
                method="GET",
                endpoint="/api/v5/market/books",
                params={
                    "instId": symbol,
                    "sz": str(limit)
                }
            )
            
            # 检查响应数据
            data = response.get('data', [])
            if not data:
                raise ValueError(f"未找到交易对 {symbol} 的订单簿数据")
            
            order_book_data = data[0]
            
            # 验证必要字段
            if 'bids' not in order_book_data or 'asks' not in order_book_data:
                raise ValueError("响应中缺少bids或asks字段")
            
            # 解析订单簿数据
            bids = [
                [float(price), float(qty)]
                for price, qty, _ in order_book_data['bids']  # OKX返回[价格, 数量, 数量(币)]
            ]
            
            asks = [
                [float(price), float(qty)]
                for price, qty, _ in order_book_data['asks']  # OKX返回[价格, 数量, 数量(币)]
            ]
            
            order_book = OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.fromtimestamp(int(order_book_data['ts']) / 1000)
            )
            
            logger.debug(
                "获取OKX期货订单簿成功",
                symbol=symbol,
                bids_count=len(bids),
                asks_count=len(asks)
            )
            
            return order_book
            
        except Exception as e:
            logger.error("获取OKX期货订单簿失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_trades(
        self,
        symbol: str,
        limit: int = 500
    ) -> List[Trade]:
        """获取期货交易记录"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/api/v5/market/trades",
                params={
                    "instId": symbol,
                    "limit": str(limit)
                }
            )
            
            # 检查响应数据
            data = response.get('data', [])
            
            trades = []
            for trade_data in data:
                # OKX的交易方向标识
                side = trade_data.get('side', 'buy')  # buy/sell
                
                trade = Trade(
                    id=trade_data['tradeId'],
                    symbol=symbol,
                    price=float(trade_data['px']),
                    quantity=float(trade_data['sz']),
                    side=side,
                    timestamp=datetime.fromtimestamp(int(trade_data['ts']) / 1000)
                )
                
                trades.append(trade)
            
            logger.debug(
                "获取OKX期货交易记录成功",
                symbol=symbol,
                trades_count=len(trades)
            )
            
            return trades
            
        except Exception as e:
            logger.error("获取OKX期货交易记录失败", symbol=symbol, error=str(e))
            raise
    
    async def get_futures_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Candle]:
        """获取期货K线数据"""
        try:
            # OKX支持的时间间隔
            valid_intervals = [
                '1m', '3m', '5m', '15m', '30m', '1H', '2H', '4H',
                '6H', '8H', '12H', '1D', '1W', '1M', '3M', '6M', '1Y'
            ]
            if interval not in valid_intervals:
                raise ValueError(f"不支持的时间间隔: {interval}")
            
            params = {
                "instId": symbol,
                "bar": interval,
                "limit": str(limit)
            }
            
            if start_time:
                params["after"] = str(int(start_time.timestamp() * 1000))
            if end_time:
                params["before"] = str(int(end_time.timestamp() * 1000))
            
            response = await self._request(
                method="GET",
                endpoint="/api/v5/market/candles",
                params=params
            )
            
            # 检查响应数据
            data = response.get('data', [])
            
            candles = []
            for kline_data in data:
                # OKX K线格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote]
                candle = Candle(
                    symbol=symbol,
                    interval=interval,
                    open_time=datetime.fromtimestamp(int(kline_data[0]) / 1000),
                    close_time=datetime.fromtimestamp(int(kline_data[0]) / 1000 + self._get_interval_seconds(interval)),
                    open_price=float(kline_data[1]),
                    high_price=float(kline_data[2]),
                    low_price=float(kline_data[3]),
                    close_price=float(kline_data[4]),
                    volume=float(kline_data[5]),
                    quote_volume=float(kline_data[7]),
                    trades_count=0  # OKX K线不包含交易计数
                )
                
                candles.append(candle)
            
            logger.debug(
                "获取OKX期货K线数据成功",
                symbol=symbol,
                interval=interval,
                candles_count=len(candles)
            )
            
            return candles
            
        except Exception as e:
            logger.error("获取OKX期货K线数据失败", symbol=symbol, error=str(e))
            raise
    
    def _get_interval_seconds(self, interval: str) -> int:
        """获取时间间隔对应的秒数"""
        interval_map = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800,
            '1H': 3600, '2H': 7200, '4H': 14400, '6H': 21600, '8H': 28800, '12H': 43200,
            '1D': 86400, '1W': 604800, '1M': 2592000, '3M': 7776000, '6M': 15552000, '1Y': 31536000
        }
        return interval_map.get(interval, 3600)
    
    async def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取资金费率"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/api/v5/public/funding-rate",
                params={"instId": symbol}
            )
            
            # 检查响应数据
            data = response.get('data', [])
            if not data:
                return None
            
            funding_data = data[0]
            
            return {
                "symbol": symbol,
                "last_funding_rate": float(funding_data.get('fundingRate', '0')),
                "next_funding_rate": float(funding_data.get('nextFundingRate', '0')),
                "funding_time": datetime.fromtimestamp(int(funding_data.get('fundingTime', '0')) / 1000) if funding_data.get('fundingTime') != '0' else None
            }
            
        except Exception as e:
            logger.debug("获取OKX资金费率失败", symbol=symbol, error=str(e))
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓量"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/api/v5/public/open-interest",
                params={"instId": symbol}
            )
            
            # 检查响应数据
            data = response.get('data', [])
            if not data:
                return None
            
            oi_data = data[0]
            
            return {
                "symbol": symbol,
                "open_interest": float(oi_data.get('oi', '0')),
                "open_interest_value": float(oi_data.get('oiCcy', '0')),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.debug("获取OKX持仓量失败", symbol=symbol, error=str(e))
            return None
    
    async def get_swap_instruments(self) -> List[Dict[str, Any]]:
        """获取永续合约列表"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/api/v5/public/instruments",
                params={"instType": "SWAP"}
            )
            
            # 检查响应数据
            data = response.get('data', [])
            
            instruments = []
            for inst_data in data:
                if inst_data.get('state') == 'live':  # 只包含活跃的合约
                    instrument = {
                        "instId": inst_data['instId'],
                        "base_ccy": inst_data['baseCcy'],
                        "quote_ccy": inst_data['quoteCcy'],
                        "contract_type": inst_data.get('ctType', 'linear'),
                        "contract_value": inst_data.get('ctVal', '1'),
                        "listing_time": inst_data.get('listTime'),
                        "delivery_time": inst_data.get('deliveryTime'),
                        "state": inst_data['state']
                    }
                    instruments.append(instrument)
            
            logger.debug("获取OKX永续合约列表成功", count=len(instruments))
            return instruments
            
        except Exception as e:
            logger.error("获取OKX永续合约列表失败", error=str(e))
            raise
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易所信息"""
        try:
            # 获取永续合约列表
            swap_instruments = await self.get_swap_instruments()
            
            return {
                "exchange": "okx",
                "futures_instruments": swap_instruments,
                "update_time": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("获取OKX交易所信息失败", error=str(e))
            raise
    
    async def get_server_time(self) -> datetime:
        """获取服务器时间"""
        try:
            response = await self._request(
                method="GET",
                endpoint="/api/v5/public/time"
            )
            
            return datetime.fromtimestamp(int(response['data'][0]['ts']) / 1000)
            
        except Exception as e:
            logger.error("获取OKX服务器时间失败", error=str(e))
            raise
    
    async def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        try:
            server_time = await self.get_server_time()
            
            return {
                "status": "operational",
                "server_time": server_time,
                "is_synchronized": True
            }
            
        except Exception as e:
            logger.error("获取OKX服务器状态失败", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_server_time()
            logger.info("OKX衍生品API连接测试成功")
            return True
        except Exception as e:
            logger.error("OKX衍生品API连接测试失败", error=str(e))
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
    async def test_derivatives_adapter():
        """测试衍生品适配器"""
        # 创建测试适配器（使用模拟API密钥）
        adapter = OKXDerivativesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
            is_paper=True
        )
        
        try:
            async with adapter:
                # 测试连接
                is_connected = await adapter.test_connection()
                print(f"连接测试: {'成功' if is_connected else '失败'}")
                
                if is_connected:
                    # 测试获取永续合约列表
                    instruments = await adapter.get_swap_instruments()
                    print(f"永续合约数量: {len(instruments)}")
                    
                    if instruments:
                        symbol = instruments[0]['instId']
                        
                        # 测试获取价格
                        ticker = await adapter.get_futures_ticker(symbol)
                        print(f"{symbol} 价格: {ticker.current_price}")
                        
                        # 测试订单簿
                        order_book = await adapter.get_futures_order_book(symbol, 20)
                        print(f"订单簿 - 买单数量: {len(order_book.bids)}, 卖单数量: {len(order_book.asks)}")
                        
                        # 测试资金费率
                        funding_rate = await adapter.get_funding_rate(symbol)
                        if funding_rate:
                            print(f"资金费率: {funding_rate.get('last_funding_rate', 0)}")
        
        except Exception as e:
            print(f"测试失败: {e}")
    
    # 运行测试
    asyncio.run(test_derivatives_adapter())