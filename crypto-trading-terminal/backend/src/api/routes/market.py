"""
市场数据API路由
提供现货和合约市场数据的REST API接口
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import structlog

from ...storage.database import get_db_session
from ...storage.redis_cache import get_market_cache, MarketDataCache
from ...core.data_aggregator import get_data_aggregator
from ...utils.exceptions import ExchangeConnectionError, ValidationError

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic模型定义
class MarketDataResponse(BaseModel):
    """市场数据响应模型"""
    symbol: str
    current_price: float
    previous_close: float
    high_24h: float
    low_24h: float
    price_change: float
    price_change_percent: float
    volume_24h: float
    quote_volume_24h: float
    timestamp: datetime
    
    # 合约特有字段
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    index_price: Optional[float] = None
    mark_price: Optional[float] = None


class OrderBookResponse(BaseModel):
    """订单簿响应模型"""
    symbol: str
    bids: List[List[float]]  # [价格, 数量]
    asks: List[List[float]]  # [价格, 数量]
    timestamp: datetime


class TradeResponse(BaseModel):
    """交易记录响应模型"""
    id: str
    symbol: str
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    timestamp: datetime


class CandleResponse(BaseModel):
    """K线数据响应模型"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: float
    trades_count: int


# 依赖注入
def get_market_cache_dep():
    """获取市场缓存依赖"""
    cache = get_market_cache()
    if not cache:
        raise HTTPException(status_code=503, detail="Redis缓存不可用")
    return cache


# 现货市场数据API
@router.get("/spot/ticker", response_model=MarketDataResponse)
async def get_spot_ticker(
    symbol: str = Query(..., description="交易对符号，如BTCUSDT"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取现货市场价格信息"""
    try:
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 从数据聚合器获取现货价格数据
        market_data = await data_aggregator.get_market_data(exchange, "spot", symbol)
        
        if market_data is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的市场数据")
        
        # 转换为API响应格式
        return MarketDataResponse(
            symbol=market_data.symbol,
            current_price=float(market_data.current_price),
            previous_close=float(market_data.previous_close),
            high_24h=float(market_data.high_24h),
            low_24h=float(market_data.low_24h),
            price_change=float(market_data.price_change),
            price_change_percent=float(market_data.price_change_percent),
            volume_24h=float(market_data.volume_24h),
            quote_volume_24h=float(market_data.quote_volume_24h),
            timestamp=market_data.timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取现货价格失败: {str(e)}")


@router.get("/spot/tickers", response_model=List[MarketDataResponse])
async def get_spot_tickers(
    symbols: Optional[List[str]] = Query(None, description="交易对符号列表"),
    exchange: str = Query("binance", description="交易所名称")
):
    """批量获取现货市场价格信息"""
    try:
        # 默认获取热门交易对
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
        
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 批量获取市场数据
        market_data_dict = await data_aggregator.get_multiple_market_data(exchange, "spot", symbols)
        
        # 转换为API响应格式
        responses = []
        for symbol, market_data in market_data_dict.items():
            if market_data is not None:
                response = MarketDataResponse(
                    symbol=market_data.symbol,
                    current_price=float(market_data.current_price),
                    previous_close=float(market_data.previous_close),
                    high_24h=float(market_data.high_24h),
                    low_24h=float(market_data.low_24h),
                    price_change=float(market_data.price_change),
                    price_change_percent=float(market_data.price_change_percent),
                    volume_24h=float(market_data.volume_24h),
                    quote_volume_24h=float(market_data.quote_volume_24h),
                    timestamp=market_data.timestamp
                )
                responses.append(response)
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量获取现货价格失败: {str(e)}")


@router.get("/spot/orderbook", response_model=OrderBookResponse)
async def get_spot_order_book(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=5, le=1000, description="订单簿深度")
):
    """获取现货订单簿信息"""
    try:
        # 获取适配器
        from ...adapters.base import ExchangeAdapterFactory
        exchange_key = f"{exchange}_spot"
        
        if exchange_key not in ExchangeAdapterFactory.get_supported_exchanges():
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        adapter = ExchangeAdapterFactory.create_adapter(exchange_key, is_testnet=True)
        
        # 获取订单簿数据
        order_book = await adapter.get_spot_order_book(symbol, limit)
        
        # 转换为API响应格式
        return OrderBookResponse(
            symbol=order_book.symbol,
            bids=[[float(price), float(qty)] for price, qty in order_book.bids],
            asks=[[float(price), float(qty)] for price, qty in order_book.asks],
            timestamp=order_book.timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取现货订单簿失败: {str(e)}")


@router.get("/spot/trades", response_model=List[TradeResponse])
async def get_spot_trades(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数")
):
    """获取现货交易记录"""
    try:
        # TODO: 实现交易记录获取逻辑
        raise HTTPException(status_code=501, detail="现货交易记录API正在实现中")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取现货交易记录失败: {str(e)}")


@router.get("/spot/klines", response_model=List[CandleResponse])
async def get_spot_klines(
    symbol: str = Query(..., description="交易对符号"),
    interval: str = Query(..., description="时间间隔，如1m, 5m, 1h, 1d"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=1, le=1000, description="K线数量"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """获取现货K线数据"""
    try:
        # TODO: 实现K线数据获取逻辑
        raise HTTPException(status_code=501, detail="现货K线数据API正在实现中")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取现货K线数据失败: {str(e)}")


# 资金费率响应模型
class FundingRateResponse(BaseModel):
    """资金费率响应模型"""
    symbol: str
    funding_rate: float
    next_funding_time: datetime
    exchange: str
    timestamp: datetime


# 持仓量响应模型
class OpenInterestResponse(BaseModel):
    """持仓量响应模型"""
    symbol: str
    open_interest: float
    open_interest_value: float
    exchange: str
    timestamp: datetime


# 合约市场数据API
@router.get("/futures/ticker", response_model=MarketDataResponse)
async def get_futures_ticker(
    symbol: str = Query(..., description="交易对符号，如BTCUSDT-PERP"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取期货市场价格信息"""
    try:
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 使用期货数据聚合器获取期货价格数据
        futures_data = await data_aggregator.futures_aggregator.get_futures_market_data(exchange, symbol)
        
        if futures_data is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的期货市场数据")
        
        # 转换为API响应格式
        return MarketDataResponse(
            symbol=futures_data.symbol,
            current_price=float(futures_data.current_price),
            previous_close=float(futures_data.previous_close),
            high_24h=float(futures_data.high_24h),
            low_24h=float(futures_data.low_24h),
            price_change=float(futures_data.price_change),
            price_change_percent=float(futures_data.price_change_percent),
            volume_24h=float(futures_data.volume_24h),
            quote_volume_24h=float(futures_data.quote_volume_24h),
            timestamp=futures_data.timestamp,
            
            # 期货特有字段
            funding_rate=float(futures_data.funding_rate) if futures_data.funding_rate else None,
            open_interest=float(futures_data.open_interest) if futures_data.open_interest else None,
            index_price=float(futures_data.index_price) if futures_data.index_price else None,
            mark_price=float(futures_data.mark_price) if futures_data.mark_price else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取期货价格失败: {str(e)}")


@router.get("/futures/tickers", response_model=List[MarketDataResponse])
async def get_futures_tickers(
    symbols: Optional[List[str]] = Query(None, description="交易对符号列表"),
    exchange: str = Query("binance", description="交易所名称")
):
    """批量获取期货市场价格信息"""
    try:
        # 默认获取热门期货交易对
        if symbols is None:
            symbols = ["BTCUSDT-PERP", "ETHUSDT-PERP", "BNBUSDT-PERP", "ADAUSDT-PERP", "SOLUSDT-PERP"]
        
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 批量获取期货市场数据
        futures_data_dict = {}
        for symbol in symbols:
            try:
                futures_data = await data_aggregator.futures_aggregator.get_futures_market_data(exchange, symbol)
                if futures_data:
                    futures_data_dict[symbol] = futures_data
            except Exception as e:
                logger.warning(f"获取期货数据失败 {symbol}: {e}")
                continue
        
        # 转换为API响应格式
        responses = []
        for symbol, futures_data in futures_data_dict.items():
            response = MarketDataResponse(
                symbol=futures_data.symbol,
                current_price=float(futures_data.current_price),
                previous_close=float(futures_data.previous_close),
                high_24h=float(futures_data.high_24h),
                low_24h=float(futures_data.low_24h),
                price_change=float(futures_data.price_change),
                price_change_percent=float(futures_data.price_change_percent),
                volume_24h=float(futures_data.volume_24h),
                quote_volume_24h=float(futures_data.quote_volume_24h),
                timestamp=futures_data.timestamp,
                
                # 期货特有字段
                funding_rate=float(futures_data.funding_rate) if futures_data.funding_rate else None,
                open_interest=float(futures_data.open_interest) if futures_data.open_interest else None,
                index_price=float(futures_data.index_price) if futures_data.index_price else None,
                mark_price=float(futures_data.mark_price) if futures_data.mark_price else None
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量获取期货价格失败: {str(e)}")


@router.get("/futures/orderbook", response_model=OrderBookResponse)
async def get_futures_order_book(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=5, le=1000, description="订单簿深度")
):
    """获取期货订单簿信息"""
    try:
        # TODO: 实现订单簿获取逻辑
        raise HTTPException(status_code=501, detail="期货订单簿API正在实现中")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取期货订单簿失败: {str(e)}")


@router.get("/futures/trades", response_model=List[TradeResponse])
async def get_futures_trades(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数")
):
    """获取期货交易记录"""
    try:
        # TODO: 实现交易记录获取逻辑
        raise HTTPException(status_code=501, detail="期货交易记录API正在实现中")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取期货交易记录失败: {str(e)}")


@router.get("/futures/klines", response_model=List[CandleResponse])
async def get_futures_klines(
    symbol: str = Query(..., description="交易对符号"),
    interval: str = Query(..., description="时间间隔，如1m, 5m, 1h, 1d"),
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(100, ge=1, le=1000, description="K线数量"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """获取期货K线数据"""
    try:
        # TODO: 实现K线数据获取逻辑
        raise HTTPException(status_code=501, detail="期货K线数据API正在实现中")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取期货K线数据失败: {str(e)}")


@router.get("/futures/funding-rate", response_model=FundingRateResponse)
async def get_futures_funding_rate(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取期货资金费率"""
    try:
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 获取资金费率数据
        funding_data = await data_aggregator.futures_aggregator.get_funding_rate_data(exchange, symbol)
        
        if funding_data is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的资金费率数据")
        
        return FundingRateResponse(
            symbol=funding_data.get('symbol', symbol),
            funding_rate=float(funding_data.get('last_funding_rate', 0)),
            next_funding_time=funding_data.get('next_funding_time', datetime.utcnow()),
            exchange=exchange,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资金费率失败: {str(e)}")


@router.get("/futures/open-interest", response_model=OpenInterestResponse)
async def get_futures_open_interest(
    symbol: str = Query(..., description="交易对符号"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取期货持仓量"""
    try:
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 获取持仓量数据
        oi_data = await data_aggregator.futures_aggregator.get_open_interest_data(exchange, symbol)
        
        if oi_data is None:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的持仓量数据")
        
        return OpenInterestResponse(
            symbol=oi_data.get('symbol', symbol),
            open_interest=float(oi_data.get('open_interest', 0)),
            open_interest_value=float(oi_data.get('open_interest_value', 0)),
            exchange=exchange,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取持仓量失败: {str(e)}")


@router.get("/futures/summary")
async def get_futures_summary(
    symbols: Optional[List[str]] = Query(None, description="交易对符号列表"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取期货市场摘要信息"""
    try:
        # 默认获取热门期货交易对
        if symbols is None:
            symbols = ["BTCUSDT-PERP", "ETHUSDT-PERP", "BNBUSDT-PERP"]
        
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 获取期货摘要数据
        summary = await data_aggregator.futures_aggregator.get_futures_summary(exchange, symbols)
        
        return {
            "exchange": exchange,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取期货摘要失败: {str(e)}")


# 市场概览API
@router.get("/overview")
async def get_market_overview():
    """获取市场概览信息"""
    try:
        # 获取数据聚合器
        data_aggregator = await get_data_aggregator()
        
        # 获取主流现货交易对数据
        spot_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT"]
        futures_symbols = ["BTCUSDT-PERP", "ETHUSDT-PERP", "BNBUSDT-PERP", "ADAUSDT-PERP", "SOLUSDT-PERP"]
        
        # 获取现货市场数据
        spot_data = await data_aggregator.get_multiple_market_data("binance", "spot", spot_symbols)
        
        # 处理现货市场数据
        spot_markets = []
        spot_gainers = []
        spot_losers = []
        
        for symbol, market_data in spot_data.items():
            if market_data is not None:
                market_info = {
                    "symbol": symbol,
                    "price": float(market_data.current_price),
                    "change_percent": float(market_data.price_change_percent),
                    "volume": float(market_data.volume_24h),
                    "high_24h": float(market_data.high_24h),
                    "low_24h": float(market_data.low_24h)
                }
                spot_markets.append(market_info)
                
                # 分类涨跌
                if market_data.price_change_percent > 0:
                    spot_gainers.append(market_info)
                elif market_data.price_change_percent < 0:
                    spot_losers.append(market_info)
        
        # 获取期货市场数据
        futures_markets = []
        futures_gainers = []
        futures_losers = []
        
        try:
            for symbol in futures_symbols:
                futures_data = await data_aggregator.futures_aggregator.get_futures_market_data("binance", symbol)
                if futures_data:
                    market_info = {
                        "symbol": symbol,
                        "price": float(futures_data.current_price),
                        "change_percent": float(futures_data.price_change_percent),
                        "volume": float(futures_data.volume_24h),
                        "high_24h": float(futures_data.high_24h),
                        "low_24h": float(futures_data.low_24h),
                        "funding_rate": float(futures_data.funding_rate) if futures_data.funding_rate else None,
                        "open_interest": float(futures_data.open_interest) if futures_data.open_interest else None
                    }
                    futures_markets.append(market_info)
                    
                    # 分类涨跌
                    if futures_data.price_change_percent > 0:
                        futures_gainers.append(market_info)
                    elif futures_data.price_change_percent < 0:
                        futures_losers.append(market_info)
        except Exception as e:
            logger.warning(f"获取期货市场数据失败: {e}")
        
        # 按涨跌幅排序
        spot_gainers.sort(key=lambda x: x["change_percent"], reverse=True)
        spot_losers.sort(key=lambda x: x["change_percent"])
        futures_gainers.sort(key=lambda x: x["change_percent"], reverse=True)
        futures_losers.sort(key=lambda x: x["change_percent"])
        
        return {
            "spot_markets": {
                "count": len(spot_markets),
                "markets": spot_markets,
                "top_gainers": spot_gainers[:5],  # 前5个涨幅
                "top_losers": spot_losers[:5]    # 前5个跌幅
            },
            "futures_markets": {
                "count": len(futures_markets),
                "markets": futures_markets,
                "top_gainers": futures_gainers[:5],
                "top_losers": futures_losers[:5]
            },
            "global_market_status": "open",
            "timestamp": datetime.utcnow().isoformat(),
            "total_market_cap": 1000000000,  # 模拟数据
            "bitcoin_dominance": 45.2       # 模拟数据
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场概览失败: {str(e)}")


# 支持的交易对API
@router.get("/symbols")
async def get_supported_symbols(
    market_type: str = Query(..., regex="^(spot|futures)$", description="市场类型"),
    exchange: str = Query("binance", description="交易所名称")
):
    """获取支持的交易对列表"""
    try:
        # TODO: 实现交易对获取逻辑
        return {
            "exchange": exchange,
            "market_type": market_type,
            "symbols": [],
            "count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易对列表失败: {str(e)}")


# 交易所状态API
@router.get("/exchanges/status")
async def get_exchange_status():
    """获取交易所连接状态"""
    try:
        # TODO: 实现交易所状态检查逻辑
        return {
            "binance": {
                "status": "operational",
                "spot_api": "connected",
                "futures_api": "connected",
                "websocket": "connected"
            },
            "okx": {
                "status": "operational",
                "spot_api": "connected",
                "futures_api": "connected", 
                "websocket": "connected"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易所状态失败: {str(e)}")


# WebSocket升级端点
@router.websocket("/spot/ws/{symbol}")
async def spot_websocket_endpoint(websocket, symbol: str):
    """现货市场WebSocket端点"""
    # TODO: 实现WebSocket逻辑
    await websocket.close()


@router.websocket("/futures/ws/{symbol}")
async def futures_websocket_endpoint(websocket, symbol: str):
    """期货市场WebSocket端点"""
    # TODO: 实现WebSocket逻辑
    await websocket.close()