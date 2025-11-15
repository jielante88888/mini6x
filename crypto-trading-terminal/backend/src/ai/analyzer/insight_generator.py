"""
Insight Generator
Generates comprehensive insights and recommendations from AI analysis results
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from .market_analyzer import MarketAnalyzer, MarketInsight
from .signal_analyzer import SignalAnalyzer, SignalInsight
from .performance_analyzer import PerformanceAnalyzer, PerformanceInsight

logger = structlog.get_logger()


class InsightType(Enum):
    """Types of insights"""
    MARKET_TREND = "market_trend"
    TRADING_SIGNAL = "trading_signal"
    RISK_ALERT = "risk_alert"
    OPPORTUNITY = "opportunity"
    PERFORMANCE = "performance"
    STRATEGY = "strategy"
    SYSTEM = "system"


class InsightPriority(Enum):
    """Insight priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class GeneratedInsight:
    """Generated insight with comprehensive information"""
    insight_id: str
    insight_type: InsightType
    priority: InsightPriority
    title: str
    description: str
    summary: str
    recommendations: List[str]
    supporting_data: Dict[str, Any]
    confidence: Decimal
    timestamp: datetime
    entity_id: str
    expires_at: Optional[datetime]
    tags: List[str]


class InsightGenerator:
    """Advanced insight generation from AI analysis results"""
    
    def __init__(self, market_analyzer: MarketAnalyzer, signal_analyzer: SignalAnalyzer,
                 performance_analyzer: PerformanceAnalyzer,
                 config: Optional[Dict[str, Any]] = None):
        self.market_analyzer = market_analyzer
        self.signal_analyzer = signal_analyzer
        self.performance_analyzer = performance_analyzer
        self.config = config or {
            "insight_generation_interval_minutes": 15,
            "confidence_threshold": 0.6,
            "priority_threshold": 0.7,
            "max_insights_per_cycle": 10,
            "insight_expiry_hours": 24,
            "min_signal_strength": 0.5
        }
        
        # Insight management
        self.generated_insights: Dict[str, GeneratedInsight] = {}
        self.insight_history: List[GeneratedInsight] = []
        self.active_alerts: Dict[str, GeneratedInsight] = {}
        
        # Pattern detection
        self.pattern_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.anomaly_detection_enabled = True
        
        # Statistics
        self.total_insights_generated = 0
        self.insight_accuracy_rate = Decimal("0.0")
        self.avg_confidence = Decimal("0.0")
        
        logger.info("洞察生成器初始化完成", config=self.config)
    
    async def generate_comprehensive_insights(self, market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate comprehensive insights from all analysis components"""
        symbol = market_data.get("symbol", "BTCUSDT")
        generation_start = datetime.now(timezone.utc)
        
        try:
            logger.debug("开始生成综合洞察", symbol=symbol)
            
            # Run all analyses in parallel
            market_insight, signal_insight = await asyncio.gather(
                self.market_analyzer.analyze_market(market_data),
                self.signal_analyzer.analyze_signals(market_data)
            )
            
            # Generate insights from each component
            insights = []
            
            # Market insights
            market_insights = await self._generate_market_insights(market_insight, market_data)
            insights.extend(market_insights)
            
            # Signal insights
            signal_insights = await self._generate_signal_insights(signal_insight, market_data)
            insights.extend(signal_insights)
            
            # Cross-component insights
            cross_insights = await self._generate_cross_component_insights(
                market_insight, signal_insight, market_data
            )
            insights.extend(cross_insights)
            
            # Pattern-based insights
            pattern_insights = await self._generate_pattern_insights(symbol, market_data)
            insights.extend(pattern_insights)
            
            # Risk insights
            risk_insights = await self._generate_risk_insights(
                market_insight, signal_insight, market_data
            )
            insights.extend(risk_insights)
            
            # Performance insights
            performance_insights = await self._generate_performance_insights(symbol, market_data)
            insights.extend(performance_insights)
            
            # Filter and prioritize insights
            filtered_insights = await self._filter_and_prioritize_insights(insights)
            
            # Store insights
            for insight in filtered_insights:
                await self._store_insight(insight)
            
            self.total_insights_generated += len(filtered_insights)
            
            logger.info("综合洞察生成完成",
                       symbol=symbol,
                       insights_count=len(filtered_insights),
                       generation_time=(datetime.now(timezone.utc) - generation_start).total_seconds())
            
            return filtered_insights
            
        except Exception as e:
            logger.error("洞察生成失败", symbol=symbol, error=str(e))
            raise e
    
    async def _generate_market_insights(self, market_insight: MarketInsight,
                                      market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate insights from market analysis"""
        insights = []
        
        # Strong trend insight
        if market_insight.confidence > Decimal("0.8") and market_insight.trend_direction.value != "neutral":
            insight = GeneratedInsight(
                insight_id=f"market_trend_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.MARKET_TREND,
                priority=InsightPriority.HIGH,
                title=f"{market_insight.symbol} 强势趋势信号",
                description=f"市场分析显示 {market_insight.symbol} 呈现{market_insight.trend_direction.value}趋势，置信度 {float(market_insight.confidence):.2%}",
                summary=f"检测到{market_insight.trend_direction.value}趋势，建议关注相关交易机会",
                recommendations=await self._generate_trend_recommendations(market_insight),
                supporting_data={
                    "trend_direction": market_insight.trend_direction.value,
                    "confidence": float(market_insight.confidence),
                    "market_regime": market_insight.regime.value,
                    "key_factors": market_insight.key_factors
                },
                confidence=market_insight.confidence,
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
                tags=["market", "trend", market_insight.symbol.lower()]
            )
            insights.append(insight)
        
        # Regime change insight
        if market_insight.regime.value in ["high_volatility", "bull_market", "bear_market"]:
            insight = GeneratedInsight(
                insight_id=f"regime_change_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MEDIUM,
                title=f"{market_insight.symbol} 市场状态变化",
                description=f"市场进入 {market_insight.regime.value} 状态，需要调整交易策略",
                summary=f"市场状态变化为 {market_insight.regime.value}，可能带来新的交易机会",
                recommendations=await self._generate_regime_recommendations(market_insight.regime),
                supporting_data={
                    "previous_regime": "sideways",  # Placeholder
                    "current_regime": market_insight.regime.value,
                    "volatility_level": float(market_insight.confidence)
                },
                confidence=Decimal("0.7"),
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
                tags=["market", "regime", "opportunity"]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_signal_insights(self, signal_insight: SignalInsight,
                                      market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate insights from signal analysis"""
        insights = []
        
        # High confidence signal insight
        if signal_insight.confidence > Decimal("0.75") and signal_insight.quality.value in ["good", "excellent"]:
            priority = InsightPriority.HIGH if signal_insight.signal_strength.value in ["strong", "very_strong"] else InsightPriority.MEDIUM
            
            insight = GeneratedInsight(
                insight_id=f"signal_{signal_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.TRADING_SIGNAL,
                priority=priority,
                title=f"{signal_insight.symbol} 交易信号确认",
                description=f"检测到 {signal_insight.primary_signal.value} 信号，强度: {signal_insight.signal_strength.value}, 质量: {signal_insight.quality.value}",
                summary=f"多模型确认 {signal_insight.primary_signal.value} 信号，建议{self._get_signal_action(signal_insight.primary_signal.value)}",
                recommendations=await self._generate_signal_recommendations(signal_insight),
                supporting_data={
                    "signal_type": signal_insight.primary_signal.value,
                    "signal_strength": signal_insight.signal_strength.value,
                    "quality": signal_insight.quality.value,
                    "entry_points": {k: float(v) for k, v in signal_insight.entry_points.items()},
                    "exit_points": {k: float(v) for k, v in signal_insight.exit_points.items()},
                    "supporting_indicators": signal_insight.supporting_indicators,
                    "conflicting_indicators": signal_insight.conflicting_indicators
                },
                confidence=signal_insight.confidence,
                timestamp=datetime.now(timezone.utc),
                entity_id=signal_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                tags=["signal", "trading", signal_insight.symbol.lower()]
            )
            insights.append(insight)
        
        # Risk alert from conflicting indicators
        if len(signal_insight.conflicting_indicators) > 2:
            insight = GeneratedInsight(
                insight_id=f"signal_conflict_{signal_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.RISK_ALERT,
                priority=InsightPriority.MEDIUM,
                title=f"{signal_insight.symbol} 信号冲突警告",
                description=f"检测到 {len(signal_insight.conflicting_indicators)} 个冲突指标，建议谨慎交易",
                summary="多个指标显示矛盾信号，存在较高的假突破风险",
                recommendations=[
                    "等待更明确的信号确认",
                    "降低仓位规模",
                    "设置更严格的止损",
                    "考虑观望等待"
                ],
                supporting_data={
                    "conflicting_count": len(signal_insight.conflicting_indicators),
                    "conflicting_indicators": signal_insight.conflicting_indicators,
                    "risk_level": "high"
                },
                confidence=Decimal("0.8"),
                timestamp=datetime.now(timezone.utc),
                entity_id=signal_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
                tags=["risk", "warning", signal_insight.symbol.lower()]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_cross_component_insights(self, market_insight: MarketInsight,
                                               signal_insight: SignalInsight,
                                               market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate insights from multiple analysis components"""
        insights = []
        
        # Agreement analysis
        market_trend = market_insight.trend_direction.value
        signal_type = signal_insight.primary_signal.value
        
        agreement_score = await self._calculate_signal_agreement(market_trend, signal_type)
        
        if agreement_score > 0.8:
            # Strong agreement insight
            insight = GeneratedInsight(
                insight_id=f"agreement_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.OPPORTUNITY,
                priority=InsightPriority.HIGH,
                title=f"{market_insight.symbol} 多模型信号确认",
                description=f"市场和信号分析高度一致，确认 {signal_type} 方向",
                summary="多个AI模型信号一致，增强交易信心",
                recommendations=await self._generate_consensus_recommendations(market_insight, signal_insight),
                supporting_data={
                    "agreement_score": agreement_score,
                    "market_trend": market_trend,
                    "signal_type": signal_type,
                    "market_confidence": float(market_insight.confidence),
                    "signal_confidence": float(signal_insight.confidence)
                },
                confidence=Decimal(str(min(float(market_insight.confidence), float(signal_insight.confidence)) + 0.1)),
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=3),
                tags=["consensus", "opportunity", market_insight.symbol.lower()]
            )
            insights.append(insight)
        
        elif agreement_score < 0.3:
            # Disagreement insight
            insight = GeneratedInsight(
                insight_id=f"disagreement_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.RISK_ALERT,
                priority=InsightPriority.MEDIUM,
                title=f"{market_insight.symbol} 模型信号分歧",
                description=f"市场趋势 ({market_trend}) 与信号分析 ({signal_type}) 存在分歧",
                summary="AI模型之间存在信号分歧，建议谨慎观望",
                recommendations=[
                    "等待信号一致性确认",
                    "减少交易频率",
                    "密切关注市场变化",
                    "准备双向对冲策略"
                ],
                supporting_data={
                    "agreement_score": agreement_score,
                    "disagreement_level": "high" if agreement_score < 0.1 else "medium",
                    "market_trend": market_trend,
                    "signal_type": signal_type
                },
                confidence=Decimal("0.7"),
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
                tags=["disagreement", "risk", market_insight.symbol.lower()]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_pattern_insights(self, symbol: str, market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate insights based on pattern detection"""
        insights = []
        
        # Analyze recent price action patterns
        if symbol in self.pattern_cache:
            patterns = self.pattern_cache[symbol]
            
            # Detect breakout pattern
            breakout_pattern = await self._detect_breakout_pattern(patterns, market_data)
            if breakout_pattern:
                insight = GeneratedInsight(
                    insight_id=f"breakout_{symbol}_{int(datetime.now().timestamp())}",
                    insight_type=InsightType.OPPORTUNITY,
                    priority=InsightPriority.HIGH,
                    title=f"{symbol} 突破模式识别",
                    description=breakout_pattern["description"],
                    summary="检测到经典突破模式，可能预示价格突破",
                    recommendations=breakout_pattern["recommendations"],
                    supporting_data=breakout_pattern["data"],
                    confidence=Decimal(str(breakout_pattern["confidence"])),
                    timestamp=datetime.now(timezone.utc),
                    entity_id=symbol,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
                    tags=["pattern", "breakout", "opportunity"]
                )
                insights.append(insight)
        
        # Update pattern cache
        await self._update_pattern_cache(symbol, market_data)
        
        return insights
    
    async def _generate_risk_insights(self, market_insight: MarketInsight,
                                    signal_insight: SignalInsight,
                                    market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate risk-related insights"""
        insights = []
        
        # High volatility risk
        volatility = float(market_data.get("volatility", 0.02))
        if volatility > 0.08:
            insight = GeneratedInsight(
                insight_id=f"volatility_risk_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.RISK_ALERT,
                priority=InsightPriority.HIGH,
                title=f"{market_insight.symbol} 高波动性风险警告",
                description=f"市场波动性达到 {volatility:.2%}，显著高于正常水平",
                summary="高波动性环境增加交易风险，建议调整策略",
                recommendations=[
                    "减少仓位规模",
                    "增加止损距离",
                    "考虑对冲策略",
                    "等待波动性回归正常"
                ],
                supporting_data={
                    "current_volatility": volatility,
                    "normal_volatility": 0.02,
                    "risk_multiplier": volatility / 0.02
                },
                confidence=Decimal("0.9"),
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
                tags=["risk", "volatility", "high-risk"]
            )
            insights.append(insight)
        
        # Low liquidity risk
        volume = float(market_data.get("volume", 0))
        volume_sma = float(market_data.get("volume_sma", 1000))
        if volume < volume_sma * 0.3:
            insight = GeneratedInsight(
                insight_id=f"liquidity_risk_{market_insight.symbol}_{int(datetime.now().timestamp())}",
                insight_type=InsightType.RISK_ALERT,
                priority=InsightPriority.MEDIUM,
                title=f"{market_insight.symbol} 流动性不足警告",
                description=f"交易量仅为平均水平的 {(volume/volume_sma)*100:.1f}%，流动性偏低",
                summary="低流动性环境可能影响交易执行和价格稳定性",
                recommendations=[
                    "避免大额交易",
                    "使用限价单而非市价单",
                    "考虑分批执行",
                    "设置更宽松的滑点容忍度"
                ],
                supporting_data={
                    "current_volume": volume,
                    "average_volume": volume_sma,
                    "liquidity_ratio": volume / volume_sma
                },
                confidence=Decimal("0.8"),
                timestamp=datetime.now(timezone.utc),
                entity_id=market_insight.symbol,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
                tags=["risk", "liquidity", market_insight.symbol.lower()]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_performance_insights(self, symbol: str, market_data: Dict[str, Any]) -> List[GeneratedInsight]:
        """Generate performance-related insights"""
        insights = []
        
        # Check if we have performance data for this entity
        perf_summary = await self.performance_analyzer.get_performance_summary(symbol)
        
        if perf_summary:
            current_level = perf_summary["current_performance"]["level"]
            trend = perf_summary["current_performance"]["trend"]
            
            # Performance decline alert
            if trend == "declining" and current_level in ["poor", "critical"]:
                insight = GeneratedInsight(
                    insight_id=f"performance_decline_{symbol}_{int(datetime.now().timestamp())}",
                    insight_type=InsightType.STRATEGY,
                    priority=InsightPriority.HIGH,
                    title=f"{symbol} 策略性能下降警告",
                    description=f"策略性能呈下降趋势，当前评级: {current_level}",
                    summary="需要立即审查和调整交易策略",
                    recommendations=[
                        "暂停当前策略执行",
                        "分析近期失败交易",
                        "调整策略参数",
                        "考虑策略组合优化"
                    ],
                    supporting_data={
                        "current_level": current_level,
                        "trend": trend,
                        "recent_score": perf_summary["current_performance"]["score"],
                        "performance_history": perf_summary.get("recent_history", [])
                    },
                    confidence=Decimal("0.8"),
                    timestamp=datetime.now(timezone.utc),
                    entity_id=symbol,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                    tags=["performance", "strategy", "critical"]
                )
                insights.append(insight)
        
        return insights
    
    async def _generate_trend_recommendations(self, market_insight: MarketInsight) -> List[str]:
        """Generate recommendations based on trend analysis"""
        recommendations = []
        
        trend = market_insight.trend_direction.value
        confidence = float(market_insight.confidence)
        
        if trend in ["strong_bullish", "bullish"]:
            if confidence > 0.8:
                recommendations = [
                    "考虑增加看涨仓位",
                    "设置动态止盈",
                    "关注突破阻力位",
                    "准备加仓时机"
                ]
            else:
                recommendations = [
                    "谨慎增加仓位",
                    "等待更强确认信号",
                    "设置止损保护",
                    "监控市场变化"
                ]
        
        elif trend in ["strong_bearish", "bearish"]:
            if confidence > 0.8:
                recommendations = [
                    "考虑增加看跌仓位",
                    "设置反弹阻力位卖出",
                    "关注支撑位突破",
                    "准备空头策略"
                ]
            else:
                recommendations = [
                    "谨慎建立空头",
                    "等待更强确认",
                    "设置反弹止损",
                    "监控空头力量"
                ]
        
        else:  # Neutral
            recommendations = [
                "保持观望态度",
                "等待明确方向信号",
                "准备双向策略",
                "关注市场转折点"
            ]
        
        return recommendations
    
    async def _generate_regime_recommendations(self, regime) -> List[str]:
        """Generate recommendations based on market regime"""
        regime_recommendations = {
            "bull_market": [
                "采用趋势跟随策略",
                "增加看涨仓位权重",
                "关注突破买入机会",
                "延长持有时间"
            ],
            "bear_market": [
                "采用逆向投资策略",
                "增加看跌仓位权重",
                "关注反弹卖出机会",
                "缩短持有时间"
            ],
            "sideways": [
                "采用区间交易策略",
                "高抛低吸操作",
                "关注支撑阻力位",
                "保持中性仓位"
            ],
            "high_volatility": [
                "减少仓位规模",
                "增加止损距离",
                "使用期权对冲",
                "避免追涨杀跌"
            ],
            "low_volatility": [
                "适当增加仓位",
                "缩小止损距离",
                "关注突破时机",
                "准备趋势跟踪"
            ]
        }
        
        return regime_recommendations.get(regime.value, ["保持谨慎", "密切关注市场变化"])
    
    async def _generate_signal_recommendations(self, signal_insight) -> List[str]:
        """Generate recommendations based on signal analysis"""
        recommendations = []
        
        signal_type = signal_insight.primary_signal.value
        strength = signal_insight.signal_strength.value
        quality = signal_insight.quality.value
        
        if signal_type == "buy":
            if strength in ["strong", "very_strong"] and quality in ["good", "excellent"]:
                recommendations = [
                    "立即考虑买入",
                    "使用分批建仓",
                    "设置合理止损",
                    "关注后续确认"
                ]
            else:
                recommendations = [
                    "谨慎考虑买入",
                    "等待更强信号",
                    "小仓位试探",
                    "设置严格止损"
                ]
        
        elif signal_type == "sell":
            if strength in ["strong", "very_strong"] and quality in ["good", "excellent"]:
                recommendations = [
                    "考虑减仓或平仓",
                    "设置反弹卖点",
                    "关注空头信号",
                    "准备做空机会"
                ]
            else:
                recommendations = [
                    "谨慎考虑减仓",
                    "等待更强确认",
                    "部分获利了结",
                    "设置反弹止损"
                ]
        
        else:  # hold
            recommendations = [
                "保持当前仓位",
                "继续监控市场",
                "等待明确信号",
                "准备方向选择"
            ]
        
        return recommendations
    
    async def _generate_consensus_recommendations(self, market_insight, signal_insight) -> List[str]:
        """Generate recommendations when multiple models agree"""
        return [
            "多模型确认增强信心",
            "可以考虑较大仓位",
            "设置动态调整策略",
            "密切关注执行细节",
            "准备风险管理措施"
        ]
    
    def _get_signal_action(self, signal_type: str) -> str:
        """Get action description for signal type"""
        action_map = {
            "buy": "买入",
            "sell": "卖出",
            "hold": "观望",
            "weak_buy": "谨慎买入",
            "weak_sell": "谨慎卖出"
        }
        return action_map.get(signal_type, "观望")
    
    async def _calculate_signal_agreement(self, market_trend: str, signal_type: str) -> float:
        """Calculate agreement score between market trend and signal"""
        # Define agreement matrix
        agreement_matrix = {
            ("strong_bullish", "buy"): 1.0,
            ("bullish", "buy"): 0.8,
            ("strong_bullish", "weak_buy"): 0.7,
            ("bullish", "weak_buy"): 0.6,
            ("neutral", "hold"): 0.8,
            ("strong_bearish", "sell"): 1.0,
            ("bearish", "sell"): 0.8,
            ("strong_bearish", "weak_sell"): 0.7,
            ("bearish", "weak_sell"): 0.6,
        }
        
        # Check direct agreement
        key = (market_trend, signal_type)
        if key in agreement_matrix:
            return agreement_matrix[key]
        
        # Check partial agreement
        if "bullish" in market_trend and signal_type in ["buy", "weak_buy"]:
            return 0.7
        elif "bearish" in market_trend and signal_type in ["sell", "weak_sell"]:
            return 0.7
        elif market_trend == "neutral" and signal_type == "hold":
            return 0.6
        
        # No agreement
        return 0.3
    
    async def _detect_breakout_pattern(self, patterns: List[Dict[str, Any]], market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect breakout patterns in price action"""
        if len(patterns) < 10:
            return None
        
        # Simple breakout detection logic
        recent_prices = [p.get("price", 0) for p in patterns[-10:]]
        
        if len(recent_prices) < 10:
            return None
        
        # Check for consolidation followed by breakout
        first_half = recent_prices[:5]
        second_half = recent_prices[5:]
        
        first_range = max(first_half) - min(first_half)
        second_range = max(second_half) - min(second_half)
        price_change = (second_half[-1] - first_half[0]) / first_half[0]
        
        # Detect upward breakout
        if first_range < 0.02 and second_range > 0.03 and price_change > 0.02:
            return {
                "description": "检测到向上突破模式，价格突破震荡区间",
                "confidence": 0.75,
                "recommendations": [
                    "考虑买入突破",
                    "设置合理止损",
                    "关注成交量确认",
                    "准备趋势跟随"
                ],
                "data": {
                    "breakout_direction": "upward",
                    "consolidation_range": first_range,
                    "breakout_range": second_range,
                    "price_change": price_change
                }
            }
        
        # Detect downward breakout
        elif first_range < 0.02 and second_range > 0.03 and price_change < -0.02:
            return {
                "description": "检测到向下突破模式，价格跌破震荡区间",
                "confidence": 0.75,
                "recommendations": [
                    "考虑卖出或做空",
                    "设置反弹止损",
                    "关注空头确认",
                    "准备下跌趋势"
                ],
                "data": {
                    "breakout_direction": "downward",
                    "consolidation_range": first_range,
                    "breakout_range": second_range,
                    "price_change": price_change
                }
            }
        
        return None
    
    async def _update_pattern_cache(self, symbol: str, market_data: Dict[str, Any]):
        """Update pattern detection cache"""
        if symbol not in self.pattern_cache:
            self.pattern_cache[symbol] = []
        
        pattern_entry = {
            "timestamp": datetime.now(timezone.utc),
            "price": market_data.get("current_price", 0),
            "volume": market_data.get("volume", 0),
            "volatility": market_data.get("volatility", 0.02),
            "rsi": market_data.get("rsi", 50),
            "trend": market_data.get("trend_direction", "neutral")
        }
        
        self.pattern_cache[symbol].append(pattern_entry)
        
        # Keep only recent patterns
        if len(self.pattern_cache[symbol]) > 100:
            self.pattern_cache[symbol] = self.pattern_cache[symbol][-100:]
    
    async def _filter_and_prioritize_insights(self, insights: List[GeneratedInsight]) -> List[GeneratedInsight]:
        """Filter and prioritize generated insights"""
        # Remove expired insights
        current_time = datetime.now(timezone.utc)
        valid_insights = [
            insight for insight in insights 
            if insight.expires_at is None or insight.expires_at > current_time
        ]
        
        # Sort by priority and confidence
        priority_order = {
            InsightPriority.CRITICAL: 0,
            InsightPriority.HIGH: 1,
            InsightPriority.MEDIUM: 2,
            InsightPriority.LOW: 3,
            InsightPriority.INFO: 4
        }
        
        valid_insights.sort(key=lambda x: (
            priority_order[x.priority],
            -float(x.confidence)
        ))
        
        # Limit to max insights per cycle
        return valid_insights[:self.config["max_insights_per_cycle"]]
    
    async def _store_insight(self, insight: GeneratedInsight):
        """Store insight in history and active alerts"""
        self.generated_insights[insight.insight_id] = insight
        self.insight_history.append(insight)
        
        # Keep only recent history
        if len(self.insight_history) > 1000:
            self.insight_history = self.insight_history[-1000:]
        
        # Add to active alerts if high priority
        if insight.priority in [InsightPriority.CRITICAL, InsightPriority.HIGH]:
            self.active_alerts[insight.insight_id] = insight
    
    async def get_insights_summary(self, symbol: Optional[str] = None, 
                                 insight_type: Optional[InsightType] = None,
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """Get insights summary with optional filtering"""
        filtered_insights = self.insight_history
        
        # Filter by symbol
        if symbol:
            filtered_insights = [i for i in filtered_insights if i.entity_id == symbol]
        
        # Filter by type
        if insight_type:
            filtered_insights = [i for i in filtered_insights if i.insight_type == insight_type]
        
        # Sort by timestamp (most recent first)
        filtered_insights.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "insight_id": insight.insight_id,
                "type": insight.insight_type.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "summary": insight.summary,
                "confidence": float(insight.confidence),
                "entity_id": insight.entity_id,
                "timestamp": insight.timestamp.isoformat(),
                "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
                "tags": insight.tags
            }
            for insight in filtered_insights[:limit]
        ]
    
    def clear_insights(self, symbol: Optional[str] = None):
        """Clear insights data"""
        if symbol:
            # Remove insights for specific symbol
            self.insight_history = [i for i in self.insight_history if i.entity_id != symbol]
            self.generated_insights = {
                k: v for k, v in self.generated_insights.items() 
                if v.entity_id != symbol
            }
            self.active_alerts = {
                k: v for k, v in self.active_alerts.items() 
                if v.entity_id != symbol
            }
        else:
            self.insight_history.clear()
            self.generated_insights.clear()
            self.active_alerts.clear()
        
        logger.info("清除洞察数据", symbol=symbol or "all")