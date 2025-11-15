"""
Signal Analyzer
Advanced signal analysis combining multiple AI models and technical indicators
"""

import asyncio
import numpy as np
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from ..models.signal_scorer import SignalScorer, SignalType
from ..models.price_predictor import PricePredictor

logger = structlog.get_logger()


class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    VERY_WEAK = "very_weak"


class SignalQuality(Enum):
    """Signal quality assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


@dataclass
class SignalInsight:
    """Comprehensive signal insight"""
    symbol: str
    primary_signal: SignalType
    signal_strength: SignalStrength
    quality: SignalQuality
    confidence: Decimal
    supporting_indicators: List[str]
    conflicting_indicators: List[str]
    entry_points: Dict[str, Decimal]
    exit_points: Dict[str, Decimal]
    risk_factors: List[str]
    timestamp: datetime
    timeframe: str


class SignalAnalyzer:
    """Advanced signal analysis using multiple AI models"""
    
    def __init__(self, signal_scorer: SignalScorer, price_predictor: PricePredictor,
                 config: Optional[Dict[str, Any]] = None):
        self.signal_scorer = signal_scorer
        self.price_predictor = price_predictor
        self.config = config or {
            "signal_agreement_threshold": 0.7,
            "strength_threshold": 0.6,
            "quality_threshold": 0.5,
            "entry_confidence_threshold": 0.7,
            "risk_reward_ratio": 2.0,
            "max_risk_percent": 0.02
        }
        
        # Signal tracking
        self.signal_history: Dict[str, List[SignalInsight]] = {}
        self.active_signals: Dict[str, SignalInsight] = {}
        self.signal_patterns: Dict[str, List[Dict[str, Any]]] = {}
        
        # Analysis statistics
        self.total_analyses = 0
        self.successful_predictions = 0
        self.accuracy_rate = Decimal("0.0")
        
        logger.info("信号分析器初始化完成", config=self.config)
    
    async def analyze_signals(self, market_data: Dict[str, Any]) -> SignalInsight:
        """Perform comprehensive signal analysis"""
        symbol = market_data.get("symbol", "BTCUSDT")
        analysis_start = datetime.now(timezone.utc)
        
        try:
            logger.debug("开始信号分析", symbol=symbol)
            
            # Run parallel signal analysis
            ai_signal, price_signal, technical_signals = await asyncio.gather(
                self._analyze_ai_signals(market_data),
                self._analyze_price_signals(market_data),
                self._analyze_technical_signals(market_data)
            )
            
            # Combine and evaluate signals
            signal_consensus = await self._evaluate_signal_consensus(
                ai_signal, price_signal, technical_signals
            )
            
            # Determine signal strength
            signal_strength = await self._calculate_signal_strength(
                signal_consensus, market_data
            )
            
            # Assess signal quality
            signal_quality = await self._assess_signal_quality(
                signal_consensus, technical_signals, market_data
            )
            
            # Generate entry and exit points
            entry_exit_points = await self._generate_entry_exit_points(
                signal_consensus, market_data
            )
            
            # Identify risk factors
            risk_factors = await self._identify_risk_factors(
                signal_consensus, market_data
            )
            
            # Create signal insight
            insight = SignalInsight(
                symbol=symbol,
                primary_signal=signal_consensus["primary_signal"],
                signal_strength=signal_strength,
                quality=signal_quality,
                confidence=signal_consensus["confidence"],
                supporting_indicators=signal_consensus["supporting_indicators"],
                conflicting_indicators=signal_consensus["conflicting_indicators"],
                entry_points=entry_exit_points["entry_points"],
                exit_points=entry_exit_points["exit_points"],
                risk_factors=risk_factors,
                timestamp=analysis_start,
                timeframe="1h"
            )
            
            # Store in history
            await self._store_signal_history(symbol, insight)
            
            # Update active signals if quality is good enough
            if signal_quality in [SignalQuality.GOOD, SignalQuality.EXCELLENT]:
                self.active_signals[symbol] = insight
            
            self.total_analyses += 1
            
            logger.info("信号分析完成",
                       symbol=symbol,
                       signal=signal_consensus["primary_signal"].value,
                       strength=signal_strength.value,
                       quality=signal_quality.value,
                       confidence=float(signal_considence["confidence"]))
            
            return insight
            
        except Exception as e:
            logger.error("信号分析失败", symbol=symbol, error=str(e))
            raise e
    
    async def _analyze_ai_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze signals using AI models"""
        symbol = market_data.get("symbol", "BTCUSDT")
        
        try:
            # Prepare signal data for AI models
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
            
            # Get AI signal analysis
            ai_analysis = await self.signal_scorer.predict(signal_data)
            
            return {
                "signal_type": SignalType(ai_analysis.get("signal_type", "hold")),
                "score": Decimal(str(ai_analysis.get("score", 0.5))),
                "confidence": Decimal(str(ai_analysis.get("confidence", 0.5))),
                "reasoning": ai_analysis.get("reasoning", []),
                "model": "AI_SignalScorer"
            }
            
        except Exception as e:
            logger.warning("AI信号分析失败", symbol=symbol, error=str(e))
            return {
                "signal_type": SignalType.HOLD,
                "score": Decimal("0.5"),
                "confidence": Decimal("0.3"),
                "reasoning": [f"AI分析失败: {str(e)}"],
                "model": "AI_SignalScorer"
            }
    
    async def _analyze_price_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze signals using price prediction model"""
        symbol = market_data.get("symbol", "BTCUSDT")
        
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
            price_prediction = await self.price_predictor.predict(prediction_data)
            
            # Convert prediction to signal
            prediction_change = float(price_prediction.get("prediction_change_percent", 0))
            
            if prediction_change > 1.0:
                signal_type = SignalType.BUY
            elif prediction_change < -1.0:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # Calculate signal score based on prediction confidence
            confidence = float(price_prediction.get("confidence", 0.5))
            score = Decimal(str(abs(prediction_change) / 100 * confidence))
            
            return {
                "signal_type": signal_type,
                "score": score,
                "confidence": Decimal(str(confidence)),
                "prediction_change": prediction_change,
                "model": "AI_PricePredictor"
            }
            
        except Exception as e:
            logger.warning("价格信号分析失败", symbol=symbol, error=str(e))
            return {
                "signal_type": SignalType.HOLD,
                "score": Decimal("0.5"),
                "confidence": Decimal("0.3"),
                "prediction_change": 0.0,
                "model": "AI_PricePredictor"
            }
    
    async def _analyze_technical_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze traditional technical signals"""
        signals = {}
        supporting = []
        conflicting = []
        
        # RSI Analysis
        rsi = float(market_data.get("rsi", 50))
        if rsi < 30:
            signals["rsi"] = {"signal": SignalType.BUY, "strength": 0.8}
            supporting.append(f"RSI超卖 ({rsi:.1f})")
        elif rsi > 70:
            signals["rsi"] = {"signal": SignalType.SELL, "strength": 0.8}
            supporting.append(f"RSI超买 ({rsi:.1f})")
        elif 40 <= rsi <= 60:
            signals["rsi"] = {"signal": SignalType.HOLD, "strength": 0.3}
        
        # MACD Analysis
        macd = float(market_data.get("macd", 0))
        if macd > 0.5:
            signals["macd"] = {"signal": SignalType.BUY, "strength": 0.6}
            supporting.append(f"MACD看涨 ({macd:.2f})")
        elif macd < -0.5:
            signals["macd"] = {"signal": SignalType.SELL, "strength": 0.6}
            supporting.append(f"MACD看跌 ({macd:.2f})")
        
        # Bollinger Bands Analysis
        bb_position = float(market_data.get("bb_position", 0.5))
        if bb_position < 0.2:
            signals["bollinger"] = {"signal": SignalType.BUY, "strength": 0.7}
            supporting.append("价格接近下轨")
        elif bb_position > 0.8:
            signals["bollinger"] = {"signal": SignalType.SELL, "strength": 0.7}
            supporting.append("价格接近上轨")
        
        # Volume Analysis
        volume = float(market_data.get("volume", 0))
        volume_sma = float(market_data.get("volume_sma", 1000))
        if volume > volume_sma * 1.5:
            signals["volume"] = {"signal": SignalType.HOLD, "strength": 0.4}
            supporting.append("高交易量确认")
        
        # Volatility Analysis
        volatility = float(market_data.get("volatility", 0.02))
        if volatility > 0.05:
            signals["volatility"] = {"signal": SignalType.HOLD, "strength": 0.3}
            conflicting.append("高波动性风险")
        
        return {
            "signals": signals,
            "supporting": supporting,
            "conflicting": conflicting
        }
    
    async def _evaluate_signal_consensus(self, ai_signal: Dict[str, Any],
                                       price_signal: Dict[str, Any],
                                       technical_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate consensus among different signal sources"""
        all_signals = [ai_signal["signal_type"], price_signal["signal_type"]]
        
        # Add technical signals
        for indicator, signal_data in technical_signals["signals"].items():
            all_signals.append(signal_data["signal"])
        
        # Count signal types
        buy_signals = all_signals.count(SignalType.BUY)
        sell_signals = all_signals.count(SignalType.SELL)
        hold_signals = all_signals.count(SignalType.HOLD)
        weak_buy_signals = all_signals.count(SignalType.WEAK_BUY)
        weak_sell_signals = all_signals.count(SignalType.WEAK_SELL)
        
        # Determine consensus
        total_signals = len(all_signals)
        
        if buy_signals + weak_buy_signals >= total_signals * 0.6:
            primary_signal = SignalType.BUY
            confidence = Decimal(str(min(1.0, (buy_signals + weak_buy_signals) / total_signals + 0.2)))
        elif sell_signals + weak_sell_signals >= total_signals * 0.6:
            primary_signal = SignalType.SELL
            confidence = Decimal(str(min(1.0, (sell_signals + weak_sell_signals) / total_signals + 0.2)))
        else:
            primary_signal = SignalType.HOLD
            confidence = Decimal(str(hold_signals / total_signals))
        
        # Combine reasoning
        supporting_indicators = []
        supporting_indicators.extend(ai_signal.get("reasoning", []))
        supporting_indicators.extend(technical_signals["supporting"])
        
        conflicting_indicators = technical_signals["conflicting"]
        
        # Add price prediction reasoning
        if price_signal["signal_type"] != SignalType.HOLD:
            prediction_change = price_signal.get("prediction_change", 0)
            supporting_indicators.append(f"价格预测: {prediction_change:.2f}%")
        
        return {
            "primary_signal": primary_signal,
            "confidence": confidence,
            "supporting_indicators": supporting_indicators[:5],  # Limit to 5
            "conflicting_indicators": conflicting_indicators[:3],  # Limit to 3
            "signal_breakdown": {
                "buy": buy_signals,
                "sell": sell_signals,
                "hold": hold_signals,
                "weak_buy": weak_buy_signals,
                "weak_sell": weak_sell_signals,
                "total": total_signals
            }
        }
    
    async def _calculate_signal_strength(self, consensus: Dict[str, Any],
                                       market_data: Dict[str, Any]) -> SignalStrength:
        """Calculate overall signal strength"""
        base_confidence = float(consensus["confidence"])
        
        # Adjust for signal agreement
        breakdown = consensus["signal_breakdown"]
        total = breakdown["total"]
        max_signal_count = max(breakdown["buy"], breakdown["sell"])
        agreement_ratio = max_signal_count / total
        
        # Volume factor
        volume = float(market_data.get("volume", 0))
        volume_sma = float(market_data.get("volume_sma", 1000))
        volume_factor = min(volume / volume_sma, 2.0) / 2.0  # Normalize to 0-1
        
        # Volatility factor
        volatility = float(market_data.get("volatility", 0.02))
        volatility_factor = 1.0 - min(volatility / 0.1, 1.0)  # Lower volatility = higher strength
        
        # Calculate final strength score
        strength_score = (
            base_confidence * 0.4 +
            agreement_ratio * 0.3 +
            volume_factor * 0.2 +
            volatility_factor * 0.1
        )
        
        if strength_score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif strength_score >= 0.6:
            return SignalStrength.STRONG
        elif strength_score >= 0.4:
            return SignalStrength.MODERATE
        elif strength_score >= 0.2:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    async def _assess_signal_quality(self, consensus: Dict[str, Any],
                                   technical_signals: Dict[str, Any],
                                   market_data: Dict[str, Any]) -> SignalQuality:
        """Assess overall signal quality"""
        # Base quality from confidence
        confidence = float(consensus["confidence"])
        
        # Check for conflicting indicators
        conflicting_count = len(consensus["conflicting_indicators"])
        
        # Data quality checks
        rsi = float(market_data.get("rsi", 50))
        volume = float(market_data.get("volume", 0))
        volatility = float(market_data.get("volatility", 0.02))
        
        quality_factors = []
        
        # Confidence factor
        if confidence >= 0.8:
            quality_factors.append(0.9)
        elif confidence >= 0.6:
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.5)
        
        # Conflict penalty
        if conflicting_count > 2:
            quality_factors.append(0.3)
        elif conflicting_count > 0:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.9)
        
        # Data quality penalty
        if rsi == 50 and volume == 0:  # Default values
            quality_factors.append(0.4)  # Poor data quality
        else:
            quality_factors.append(0.8)  # Good data quality
        
        # Volatility check
        if volatility > 0.1:
            quality_factors.append(0.5)  # High volatility reduces quality
        else:
            quality_factors.append(0.8)
        
        # Calculate overall quality
        avg_quality = sum(quality_factors) / len(quality_factors)
        
        if avg_quality >= 0.8:
            return SignalQuality.EXCELLENT
        elif avg_quality >= 0.65:
            return SignalQuality.GOOD
        elif avg_quality >= 0.5:
            return SignalQuality.FAIR
        elif avg_quality >= 0.3:
            return SignalQuality.POOR
        else:
            return SignalQuality.INVALID
    
    async def _generate_entry_exit_points(self, consensus: Dict[str, Any],
                                        market_data: Dict[str, Any]) -> Dict[str, Dict[str, Decimal]]:
        """Generate entry and exit points for signals"""
        current_price = Decimal(str(market_data.get("current_price", 50000)))
        volatility = float(market_data.get("volatility", 0.02))
        
        entry_points = {}
        exit_points = {}
        
        signal_type = consensus["primary_signal"]
        confidence = float(consensus["confidence"])
        
        # Adjust points based on confidence and volatility
        volatility_adjustment = volatility * confidence
        
        if signal_type == SignalType.BUY:
            # Entry strategies
            entry_points["immediate"] = current_price
            entry_points["pullback"] = current_price * Decimal(str(1 - volatility_adjustment))
            entry_points["breakout"] = current_price * Decimal(str(1 + volatility_adjustment))
            
            # Exit strategies
            profit_target = self.config["risk_reward_ratio"] * volatility_adjustment
            exit_points["profit_target"] = current_price * Decimal(str(1 + profit_target))
            exit_points["stop_loss"] = current_price * Decimal(str(1 - volatility_adjustment))
            exit_points["trailing_stop"] = current_price * Decimal(str(1 + profit_target * 0.5))
            
        elif signal_type == SignalType.SELL:
            # Entry strategies
            entry_points["immediate"] = current_price
            entry_points["pullback"] = current_price * Decimal(str(1 + volatility_adjustment))
            entry_points["breakdown"] = current_price * Decimal(str(1 - volatility_adjustment))
            
            # Exit strategies
            profit_target = self.config["risk_reward_ratio"] * volatility_adjustment
            exit_points["profit_target"] = current_price * Decimal(str(1 - profit_target))
            exit_points["stop_loss"] = current_price * Decimal(str(1 + volatility_adjustment))
            exit_points["trailing_stop"] = current_price * Decimal(str(1 - profit_target * 0.5))
            
        else:  # HOLD
            entry_points["none"] = current_price
            exit_points["monitor"] = current_price
        
        return {
            "entry_points": entry_points,
            "exit_points": exit_points
        }
    
    async def _identify_risk_factors(self, consensus: Dict[str, Any],
                                   market_data: Dict[str, Any]) -> List[str]:
        """Identify potential risk factors for the signal"""
        risk_factors = []
        
        # Volatility risk
        volatility = float(market_data.get("volatility", 0.02))
        if volatility > 0.05:
            risk_factors.append(f"高波动性 ({volatility:.3f}) 增加风险")
        elif volatility < 0.005:
            risk_factors.append(f"低波动性可能导致假突破")
        
        # Confidence risk
        confidence = float(consensus["confidence"])
        if confidence < 0.5:
            risk_factors.append("信号置信度较低")
        elif confidence > 0.9:
            risk_factors.append("极高置信度可能预示反转")
        
        # Technical risk
        conflicting_count = len(consensus["conflicting_indicators"])
        if conflicting_count > 1:
            risk_factors.append(f"存在{conflicting_count}个冲突指标")
        
        # Market regime risk
        volume = float(market_data.get("volume", 0))
        volume_sma = float(market_data.get("volume_sma", 1000))
        if volume < volume_sma * 0.5:
            risk_factors.append("交易量偏低，市场流动性不足")
        
        # Time-based risk
        current_time = datetime.now(timezone.utc)
        if 0 <= current_time.hour <= 6:  # Low liquidity hours
            risk_factors.append("当前为低流动性时段")
        
        return risk_factors[:5]  # Limit to 5 risk factors
    
    async def _store_signal_history(self, symbol: str, insight: SignalInsight):
        """Store signal analysis in history"""
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        
        self.signal_history[symbol].append(insight)
        
        # Keep only recent history (last 50 analyses)
        if len(self.signal_history[symbol]) > 50:
            self.signal_history[symbol] = self.signal_history[symbol][-50:]
    
    async def get_signal_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive signal summary for a symbol"""
        if symbol not in self.signal_history:
            return None
        
        recent_signals = self.signal_history[symbol][-10:]  # Last 10 signals
        active_signal = self.active_signals.get(symbol)
        
        if not recent_signals:
            return None
        
        # Calculate statistics
        signal_counts = {}
        strength_counts = {}
        quality_counts = {}
        
        for signal in recent_signals:
            signal_type = signal.primary_signal.value
            strength = signal.signal_strength.value
            quality = signal.quality.value
            
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
            strength_counts[strength] = strength_counts.get(strength, 0) + 1
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        # Determine most common signal
        most_common_signal = max(signal_counts.items(), key=lambda x: x[1])[0]
        most_common_strength = max(strength_counts.items(), key=lambda x: x[1])[0]
        most_common_quality = max(quality_counts.items(), key=lambda x: x[1])[0]
        
        # Calculate average confidence
        avg_confidence = sum(float(s.confidence) for s in recent_signals) / len(recent_signals)
        
        return {
            "symbol": symbol,
            "most_common_signal": most_common_signal,
            "most_common_strength": most_common_strength,
            "most_common_quality": most_common_quality,
            "average_confidence": round(avg_confidence, 3),
            "signal_distribution": signal_counts,
            "strength_distribution": strength_counts,
            "quality_distribution": quality_counts,
            "total_analyses": len(recent_signals),
            "active_signal": {
                "signal": active_signal.primary_signal.value,
                "strength": active_signal.signal_strength.value,
                "quality": active_signal.quality.value,
                "confidence": float(active_signal.confidence),
                "timestamp": active_signal.timestamp.isoformat()
            } if active_signal else None,
            "recent_signals": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "signal": s.primary_signal.value,
                    "strength": s.signal_strength.value,
                    "confidence": float(s.confidence)
                }
                for s in recent_signals[-5:]  # Last 5 signals
            ]
        }
    
    def clear_signals(self, symbol: Optional[str] = None):
        """Clear signal history and active signals"""
        if symbol:
            if symbol in self.signal_history:
                del self.signal_history[symbol]
            if symbol in self.active_signals:
                del self.active_signals[symbol]
        else:
            self.signal_history.clear()
            self.active_signals.clear()
        
        logger.info("清除信号数据", symbol=symbol or "all")