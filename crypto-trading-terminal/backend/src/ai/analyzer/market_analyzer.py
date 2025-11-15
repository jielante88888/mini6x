"""
Market Analyzer
Real-time market analysis using AI models for trend detection and prediction
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from ..models.price_predictor import PricePredictor
from ..models.signal_scorer import SignalScorer

logger = structlog.get_logger()


class TrendDirection(Enum):
    """Market trend directions"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class MarketRegime(Enum):
    """Market regime identification"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class MarketInsight:
    """Market analysis insight"""
    symbol: str
    trend_direction: TrendDirection
    confidence: Decimal
    key_factors: List[str]
    prediction: Dict[str, Any]
    timestamp: datetime
    timeframe: str
    regime: MarketRegime


class MarketAnalyzer:
    """Real-time market analysis using AI models"""
    
    def __init__(self, price_predictor: PricePredictor, signal_scorer: SignalScorer,
                 config: Optional[Dict[str, Any]] = None):
        self.price_predictor = price_predictor
        self.signal_scorer = signal_scorer
        self.config = config or {
            "analysis_interval_seconds": 30,
            "trend_detection_window": 20,
            "volatility_threshold": 0.02,
            "volume_threshold": 1000,
            "confidence_threshold": 0.6
        }
        
        # Market state tracking
        self.market_history: Dict[str, List[Dict[str, Any]]] = {}
        self.current_regimes: Dict[str, MarketRegime] = {}
        self.trend_cache: Dict[str, MarketInsight] = {}
        
        # Analysis statistics
        self.analysis_count = 0
        self.error_count = 0
        self.last_analysis_time: Dict[str, datetime] = {}
        
        logger.info("市场分析器初始化完成", config=self.config)
    
    async def analyze_market(self, market_data: Dict[str, Any]) -> MarketInsight:
        """Perform comprehensive market analysis"""
        symbol = market_data.get("symbol", "BTCUSDT")
        analysis_start = datetime.now(timezone.utc)
        
        try:
            logger.debug("开始市场分析", symbol=symbol)
            
            # Update market history
            await self._update_market_history(symbol, market_data)
            
            # Run parallel AI analysis
            price_prediction, signal_analysis = await asyncio.gather(
                self._analyze_price_trend(symbol, market_data),
                self._analyze_market_signals(symbol, market_data)
            )
            
            # Determine trend direction
            trend_direction = await self._determine_trend_direction(
                price_prediction, signal_analysis, market_data
            )
            
            # Identify market regime
            market_regime = await self._identify_market_regime(symbol)
            
            # Calculate overall confidence
            confidence = await self._calculate_market_confidence(
                price_prediction, signal_analysis, trend_direction
            )
            
            # Generate key factors
            key_factors = await self._generate_key_factors(
                market_data, price_prediction, signal_analysis
            )
            
            # Create market insight
            insight = MarketInsight(
                symbol=symbol,
                trend_direction=trend_direction,
                confidence=confidence,
                key_factors=key_factors,
                prediction=await self._compile_prediction_data(price_prediction, signal_analysis),
                timestamp=analysis_start,
                timeframe="1h",
                regime=market_regime
            )
            
            # Cache result
            self.trend_cache[symbol] = insight
            
            # Update statistics
            self.analysis_count += 1
            self.last_analysis_time[symbol] = analysis_start
            
            logger.info("市场分析完成",
                       symbol=symbol,
                       trend=trend_direction.value,
                       confidence=float(confidence),
                       regime=market_regime.value)
            
            return insight
            
        except Exception as e:
            self.error_count += 1
            logger.error("市场分析失败", symbol=symbol, error=str(e))
            raise e
    
    async def _update_market_history(self, symbol: str, market_data: Dict[str, Any]):
        """Update market data history"""
        if symbol not in self.market_history:
            self.market_history[symbol] = []
        
        # Add current data point
        history_entry = {
            "timestamp": market_data.get("timestamp", datetime.now(timezone.utc)),
            "price": market_data.get("current_price", 0),
            "volume": market_data.get("volume", 0),
            "volatility": market_data.get("volatility", 0.02),
            "rsi": market_data.get("rsi", 50),
            "macd": market_data.get("macd", 0)
        }
        
        self.market_history[symbol].append(history_entry)
        
        # Keep only recent history (last 100 data points)
        if len(self.market_history[symbol]) > 100:
            self.market_history[symbol] = self.market_history[symbol][-100:]
    
    async def _analyze_price_trend(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price trends using price predictor model"""
        try:
            # Prepare prediction data
            prediction_data = {
                "symbol": symbol,
                "current_price": market_data.get("current_price", 50000),
                "volume": market_data.get("volume", 1000),
                "rsi": market_data.get("rsi", 50),
                "macd": market_data.get("macd", 0),
                "volatility": market_data.get("volatility", 0.02),
                "prediction_horizon": "1h"
            }
            
            # Get price prediction
            prediction = await self.price_predictor.predict(prediction_data)
            
            return {
                "predicted_price": prediction.get("predicted_price", 0),
                "prediction_change": prediction.get("prediction_change_percent", 0),
                "confidence": prediction.get("confidence", 0.5),
                "risk_score": prediction.get("risk_score", 0.5),
                "timeframe": "1h"
            }
            
        except Exception as e:
            logger.warning("价格趋势分析失败", symbol=symbol, error=str(e))
            return {
                "predicted_price": market_data.get("current_price", 0),
                "prediction_change": 0,
                "confidence": 0.3,
                "risk_score": 0.5,
                "error": str(e)
            }
    
    async def _analyze_market_signals(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market signals using signal scorer model"""
        try:
            # Prepare signal data
            signal_data = {
                "symbol": symbol,
                "rsi": market_data.get("rsi", 50),
                "macd": market_data.get("macd", 0),
                "bb_position": market_data.get("bb_position", 0.5),
                "volume_sma": market_data.get("volume_sma", 1000),
                "price_momentum": market_data.get("price_momentum", 0),
                "volatility": market_data.get("volatility", 0.02),
                "atr": market_data.get("atr", 0.02)
            }
            
            # Get signal analysis
            signal_analysis = await self.signal_scorer.predict(signal_data)
            
            return {
                "signal_type": signal_analysis.get("signal_type", "hold"),
                "score": signal_analysis.get("score", 0.5),
                "confidence": signal_analysis.get("confidence", 0.5),
                "reasoning": signal_analysis.get("reasoning", [])
            }
            
        except Exception as e:
            logger.warning("市场信号分析失败", symbol=symbol, error=str(e))
            return {
                "signal_type": "hold",
                "score": 0.5,
                "confidence": 0.3,
                "reasoning": [f"分析失败: {str(e)}"]
            }
    
    async def _determine_trend_direction(self, price_prediction: Dict[str, Any],
                                       signal_analysis: Dict[str, Any],
                                       market_data: Dict[str, Any]) -> TrendDirection:
        """Determine overall trend direction"""
        # Combine signals from price prediction and signal analysis
        price_change = float(price_prediction.get("prediction_change", 0))
        signal_score = float(signal_analysis.get("score", 0.5))
        confidence = (float(price_prediction.get("confidence", 0.5)) + 
                     float(signal_analysis.get("confidence", 0.5))) / 2
        
        # Current market conditions
        rsi = float(market_data.get("rsi", 50))
        volatility = float(market_data.get("volatility", 0.02))
        
        # Determine trend
        if confidence < 0.4:
            # Low confidence - neutral
            return TrendDirection.NEUTRAL
        
        # Strong signals
        if price_change > 2.0 and signal_score > 0.8 and rsi < 70:
            return TrendDirection.STRONG_BULLISH
        elif price_change < -2.0 and signal_score < 0.2 and rsi > 30:
            return TrendDirection.STRONG_BEARISH
        # Moderate signals
        elif price_change > 1.0 and signal_score > 0.6:
            return TrendDirection.BULLISH
        elif price_change < -1.0 and signal_score < 0.4:
            return TrendDirection.BEARISH
        # Weak or conflicting signals
        elif abs(price_change) < 0.5 or abs(signal_score - 0.5) < 0.1:
            return TrendDirection.NEUTRAL
        else:
            # Default to neutral if signals are unclear
            return TrendDirection.NEUTRAL
    
    async def _identify_market_regime(self, symbol: str) -> MarketRegime:
        """Identify current market regime"""
        if symbol not in self.market_history or len(self.market_history[symbol]) < 20:
            return MarketRegime.SIDEWAYS
        
        history = self.market_history[symbol]
        recent_data = history[-20:]  # Last 20 data points
        
        # Calculate volatility
        prices = [float(entry["price"]) for entry in recent_data]
        price_changes = [abs((prices[i] - prices[i-1]) / prices[i-1]) 
                        for i in range(1, len(prices))]
        avg_volatility = np.mean(price_changes)
        
        # Calculate trend
        price_trend = (prices[-1] - prices[0]) / prices[0]
        
        # Determine regime
        if avg_volatility > 0.05:  # High volatility threshold
            return MarketRegime.HIGH_VOLATILITY
        elif avg_volatility < 0.01:  # Low volatility threshold
            return MarketRegime.LOW_VOLATILITY
        elif price_trend > 0.15:  # Strong upward trend
            return MarketRegime.BULL_MARKET
        elif price_trend < -0.15:  # Strong downward trend
            return MarketRegime.BEAR_MARKET
        else:
            return MarketRegime.SIDEWAYS
    
    async def _calculate_market_confidence(self, price_prediction: Dict[str, Any],
                                         signal_analysis: Dict[str, Any],
                                         trend_direction: TrendDirection) -> Decimal:
        """Calculate overall market analysis confidence"""
        price_confidence = float(price_prediction.get("confidence", 0.5))
        signal_confidence = float(signal_analysis.get("confidence", 0.5))
        
        # Average the confidences
        base_confidence = (price_confidence + signal_confidence) / 2
        
        # Adjust based on signal agreement
        price_change = float(price_prediction.get("prediction_change", 0))
        signal_score = float(signal_analysis.get("score", 0.5))
        
        # Check if signals agree
        if (price_change > 0 and signal_score > 0.6) or (price_change < 0 and signal_score < 0.4):
            agreement_bonus = 0.1
        else:
            agreement_bonus = -0.1
        
        final_confidence = base_confidence + agreement_bonus
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        return Decimal(str(round(final_confidence, 3)))
    
    async def _generate_key_factors(self, market_data: Dict[str, Any],
                                  price_prediction: Dict[str, Any],
                                  signal_analysis: Dict[str, Any]) -> List[str]:
        """Generate key factors influencing the market analysis"""
        factors = []
        
        # Price prediction factors
        if "error" not in price_prediction:
            price_change = float(price_prediction.get("prediction_change", 0))
            if abs(price_change) > 1.0:
                factors.append(f"预期价格变化: {price_change:.2f}%")
        
        # Signal analysis factors
        if "error" not in signal_analysis:
            signal_type = signal_analysis.get("signal_type", "hold")
            reasoning = signal_analysis.get("reasoning", [])
            if reasoning:
                factors.extend(reasoning[:3])  # Top 3 reasoning points
        
        # Technical indicator factors
        rsi = float(market_data.get("rsi", 50))
        if rsi > 70:
            factors.append(f"RSI过高 ({rsi:.1f}) - 超买状态")
        elif rsi < 30:
            factors.append(f"RSI过低 ({rsi:.1f}) - 超卖状态")
        
        volatility = float(market_data.get("volatility", 0.02))
        if volatility > 0.05:
            factors.append(f"高波动性 ({volatility:.3f}) - 市场不稳定")
        elif volatility < 0.01:
            factors.append(f"低波动性 ({volatility:.3f}) - 市场平静")
        
        volume = float(market_data.get("volume", 0))
        if volume > 5000:
            factors.append("高交易量 - 市场活跃")
        elif volume < 500:
            factors.append("低交易量 - 市场不活跃")
        
        return factors[:5]  # Limit to top 5 factors
    
    async def _compile_prediction_data(self, price_prediction: Dict[str, Any],
                                     signal_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive prediction data"""
        prediction_data = {
            "price_prediction": {
                "predicted_price": price_prediction.get("predicted_price"),
                "change_percent": price_prediction.get("prediction_change"),
                "confidence": price_prediction.get("confidence"),
                "risk_score": price_prediction.get("risk_score"),
                "timeframe": price_prediction.get("timeframe", "1h")
            },
            "signal_analysis": {
                "signal_type": signal_analysis.get("signal_type"),
                "score": signal_analysis.get("score"),
                "confidence": signal_analysis.get("confidence")
            },
            "composite_score": (float(price_prediction.get("confidence", 0.5)) + 
                               float(signal_analysis.get("confidence", 0.5))) / 2
        }
        
        return prediction_data
    
    async def get_market_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive market summary for a symbol"""
        if symbol not in self.trend_cache:
            return None
        
        insight = self.trend_cache[symbol]
        
        return {
            "symbol": symbol,
            "current_trend": insight.trend_direction.value,
            "confidence": float(insight.confidence),
            "market_regime": insight.regime.value,
            "prediction": insight.prediction,
            "key_factors": insight.key_factors,
            "analysis_timestamp": insight.timestamp.isoformat(),
            "timeframe": insight.timeframe,
            "market_data_quality": {
                "history_points": len(self.market_history.get(symbol, [])),
                "last_update": self.last_analysis_time.get(symbol, datetime.min).isoformat() if symbol in self.last_analysis_time else None
            },
            "analysis_statistics": {
                "total_analyses": self.analysis_count,
                "error_rate": self.error_count / max(1, self.analysis_count),
                "cache_size": len(self.trend_cache)
            }
        }
    
    async def get_trend_history(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trend analysis history"""
        if symbol not in self.market_history:
            return []
        
        history = self.market_history[symbol]
        recent_data = history[-limit:] if len(history) >= limit else history
        
        return [
            {
                "timestamp": data["timestamp"].isoformat() if hasattr(data["timestamp"], "isoformat") else str(data["timestamp"]),
                "price": data["price"],
                "volume": data["volume"],
                "volatility": data["volatility"],
                "rsi": data["rsi"],
                "macd": data["macd"]
            }
            for data in recent_data
        ]
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear analysis cache"""
        if symbol:
            if symbol in self.trend_cache:
                del self.trend_cache[symbol]
            if symbol in self.market_history:
                del self.market_history[symbol]
            if symbol in self.current_regimes:
                del self.current_regimes[symbol]
        else:
            self.trend_cache.clear()
            self.market_history.clear()
            self.current_regimes.clear()
        
        logger.info("清除分析缓存", symbol=symbol or "all")