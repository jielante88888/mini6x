"""
Performance Analyzer
Real-time performance tracking and analysis for trading strategies and AI models
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class PerformanceLevel(Enum):
    """Performance levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class MetricType(Enum):
    """Performance metric types"""
    PROFITABILITY = "profitability"
    RISK = "risk"
    EFFICIENCY = "efficiency"
    CONSISTENCY = "consistency"
    RELIABILITY = "reliability"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_return: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal
    volatility: Decimal
    beta: Decimal
    alpha: Decimal
    sortino_ratio: Decimal
    var_95: Decimal
    expected_shortfall: Decimal
    hit_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    recovery_factor: Decimal


@dataclass
class PerformanceInsight:
    """Performance analysis insight"""
    entity_id: str
    entity_type: str
    overall_score: Decimal
    performance_level: PerformanceLevel
    metrics: PerformanceMetrics
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    trend: str  # "improving", "stable", "declining"
    timestamp: datetime
    timeframe: str


class PerformanceAnalyzer:
    """Real-time performance analysis and tracking system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "lookback_periods": 252,  # 1 year of trading days
            "benchmark_symbol": "BTCUSDT",
            "risk_free_rate": 0.02,  # 2% annual risk-free rate
            "confidence_level": 0.95,
            "min_trades_for_analysis": 10,
            "performance_thresholds": {
                "excellent": {"return": 0.15, "sharpe": 1.5, "drawdown": 0.05},
                "good": {"return": 0.10, "sharpe": 1.0, "drawdown": 0.10},
                "fair": {"return": 0.05, "sharpe": 0.5, "drawdown": 0.15},
                "poor": {"return": 0.0, "sharpe": 0.0, "drawdown": 0.25}
            }
        }
        
        # Performance tracking
        self.performance_history: Dict[str, List[PerformanceInsight]] = {}
        self.trade_history: Dict[str, List[Dict[str, Any]]] = {}
        self.model_performance: Dict[str, Dict[str, Decimal]] = {}
        self.strategy_performance: Dict[str, Dict[str, Decimal]] = {}
        
        # Real-time tracking
        self.current_performance: Dict[str, PerformanceMetrics] = {}
        self.active_entities: Dict[str, str] = {}  # entity_id -> entity_type
        
        # Benchmark data
        self.benchmark_data: List[Dict[str, Any]] = []
        
        logger.info("性能分析器初始化完成", config=self.config)
    
    async def analyze_performance(self, entity_id: str, entity_type: str,
                                performance_data: Dict[str, Any]) -> PerformanceInsight:
        """Analyze performance for a trading entity"""
        analysis_start = datetime.now(timezone.utc)
        
        try:
            logger.debug("开始性能分析", entity_id=entity_id, entity_type=entity_type)
            
            # Update trade history if provided
            if "trades" in performance_data:
                await self._update_trade_history(entity_id, performance_data["trades"])
            
            # Calculate performance metrics
            metrics = await self._calculate_performance_metrics(entity_id, entity_type)
            
            # Determine performance level
            performance_level = await self._determine_performance_level(metrics)
            
            # Generate insights
            strengths, weaknesses = await self._analyze_strengths_weaknesses(metrics)
            recommendations = await self._generate_recommendations(metrics, performance_level)
            
            # Determine performance trend
            trend = await self._determine_performance_trend(entity_id, metrics)
            
            # Calculate overall score
            overall_score = await self._calculate_overall_score(metrics)
            
            # Create performance insight
            insight = PerformanceInsight(
                entity_id=entity_id,
                entity_type=entity_type,
                overall_score=overall_score,
                performance_level=performance_level,
                metrics=metrics,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
                trend=trend,
                timestamp=analysis_start,
                timeframe="1d"
            )
            
            # Store in history
            await self._store_performance_history(entity_id, insight)
            
            # Update current performance
            self.current_performance[entity_id] = metrics
            
            # Track active entities
            self.active_entities[entity_id] = entity_type
            
            logger.info("性能分析完成",
                       entity_id=entity_id,
                       entity_type=entity_type,
                       overall_score=float(overall_score),
                       level=performance_level.value,
                       trend=trend)
            
            return insight
            
        except Exception as e:
            logger.error("性能分析失败", entity_id=entity_id, error=str(e))
            raise e
    
    async def _update_trade_history(self, entity_id: str, trades: List[Dict[str, Any]]):
        """Update trade history for an entity"""
        if entity_id not in self.trade_history:
            self.trade_history[entity_id] = []
        
        # Add new trades
        for trade in trades:
            trade_entry = {
                "timestamp": trade.get("timestamp", datetime.now(timezone.utc)),
                "symbol": trade.get("symbol", "BTCUSDT"),
                "side": trade.get("side", "buy"),
                "quantity": Decimal(str(trade.get("quantity", 0))),
                "price": Decimal(str(trade.get("price", 0))),
                "pnl": Decimal(str(trade.get("pnl", 0))),
                "commission": Decimal(str(trade.get("commission", 0))),
                "strategy": trade.get("strategy", "unknown")
            }
            self.trade_history[entity_id].append(trade_entry)
        
        # Sort by timestamp
        self.trade_history[entity_id].sort(key=lambda x: x["timestamp"])
        
        # Keep only recent history
        if len(self.trade_history[entity_id]) > 1000:
            self.trade_history[entity_id] = self.trade_history[entity_id][-1000:]
    
    async def _calculate_performance_metrics(self, entity_id: str, entity_type: str) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        trades = self.trade_history.get(entity_id, [])
        
        if len(trades) < self.config["min_trades_for_analysis"]:
            # Return default metrics if insufficient data
            return await self._get_default_metrics()
        
        # Extract trade data
        trade_df = pd.DataFrame([
            {
                "timestamp": trade["timestamp"],
                "pnl": float(trade["pnl"]),
                "quantity": float(trade["quantity"]),
                "price": float(trade["price"])
            }
            for trade in trades
        ])
        
        # Calculate basic metrics
        total_return = await self._calculate_total_return(trade_df)
        win_rate = await self._calculate_win_rate(trade_df)
        profit_factor = await self._calculate_profit_factor(trade_df)
        
        # Calculate risk metrics
        volatility = await self._calculate_volatility(trade_df)
        max_drawdown = await self._calculate_max_drawdown(trade_df)
        sharpe_ratio = await self._calculate_sharpe_ratio(trade_df, volatility)
        sortino_ratio = await self._calculate_sortino_ratio(trade_df)
        calmar_ratio = await self._calculate_calmar_ratio(total_return, max_drawdown)
        
        # Calculate advanced metrics
        var_95 = await self._calculate_var(trade_df, 0.95)
        expected_shortfall = await self._calculate_expected_shortfall(trade_df, 0.95)
        
        # Calculate trade-specific metrics
        hit_rate = win_rate
        avg_win, avg_loss = await self._calculate_avg_win_loss(trade_df)
        largest_win, largest_loss = await self._calculate_largest_win_loss(trade_df)
        
        # Calculate recovery factor
        recovery_factor = await self._calculate_recovery_factor(total_return, max_drawdown)
        
        # Calculate beta and alpha (if benchmark data available)
        beta, alpha = await self._calculate_beta_alpha(trade_df)
        
        return PerformanceMetrics(
            total_return=Decimal(str(total_return)),
            win_rate=Decimal(str(win_rate)),
            profit_factor=Decimal(str(profit_factor)),
            sharpe_ratio=Decimal(str(sharpe_ratio)),
            max_drawdown=Decimal(str(max_drawdown)),
            calmar_ratio=Decimal(str(calmar_ratio)),
            volatility=Decimal(str(volatility)),
            beta=Decimal(str(beta)),
            alpha=Decimal(str(alpha)),
            sortino_ratio=Decimal(str(sortino_ratio)),
            var_95=Decimal(str(var_95)),
            expected_shortfall=Decimal(str(expected_shortfall)),
            hit_rate=Decimal(str(hit_rate)),
            avg_win=Decimal(str(avg_win)),
            avg_loss=Decimal(str(avg_loss)),
            largest_win=Decimal(str(largest_win)),
            largest_loss=Decimal(str(largest_loss)),
            recovery_factor=Decimal(str(recovery_factor))
        )
    
    async def _get_default_metrics(self) -> PerformanceMetrics:
        """Return default metrics for insufficient data"""
        return PerformanceMetrics(
            total_return=Decimal("0.0"),
            win_rate=Decimal("0.5"),
            profit_factor=Decimal("1.0"),
            sharpe_ratio=Decimal("0.0"),
            max_drawdown=Decimal("0.0"),
            calmar_ratio=Decimal("0.0"),
            volatility=Decimal("0.02"),
            beta=Decimal("1.0"),
            alpha=Decimal("0.0"),
            sortino_ratio=Decimal("0.0"),
            var_95=Decimal("0.02"),
            expected_shortfall=Decimal("0.03"),
            hit_rate=Decimal("0.5"),
            avg_win=Decimal("0.0"),
            avg_loss=Decimal("0.0"),
            largest_win=Decimal("0.0"),
            largest_loss=Decimal("0.0"),
            recovery_factor=Decimal("0.0")
        )
    
    async def _calculate_total_return(self, trade_df: pd.DataFrame) -> float:
        """Calculate total return from trades"""
        total_pnl = trade_df["pnl"].sum()
        
        # Assume initial capital of $10,000 for calculation
        initial_capital = 10000.0
        
        if initial_capital <= 0:
            return 0.0
        
        return total_pnl / initial_capital
    
    async def _calculate_win_rate(self, trade_df: pd.DataFrame) -> float:
        """Calculate win rate (percentage of profitable trades)"""
        winning_trades = (trade_df["pnl"] > 0).sum()
        total_trades = len(trade_df)
        
        if total_trades == 0:
            return 0.0
        
        return winning_trades / total_trades
    
    async def _calculate_profit_factor(self, trade_df: pd.DataFrame) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = trade_df[trade_df["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(trade_df[trade_df["pnl"] < 0]["pnl"].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 1.0
        
        return gross_profit / gross_loss
    
    async def _calculate_volatility(self, trade_df: pd.DataFrame) -> float:
        """Calculate annualized volatility of returns"""
        if len(trade_df) < 2:
            return 0.02  # Default 2% volatility
        
        # Calculate daily returns (assuming each trade is one day)
        returns = trade_df["pnl"].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.02
        
        # Annualize the volatility
        daily_volatility = returns.std()
        annualized_volatility = daily_volatility * np.sqrt(252)  # 252 trading days per year
        
        return annualized_volatility if not np.isnan(annualized_volatility) else 0.02
    
    async def _calculate_max_drawdown(self, trade_df: pd.DataFrame) -> float:
        """Calculate maximum drawdown"""
        if len(trade_df) < 2:
            return 0.0
        
        # Calculate cumulative P&L
        cumulative_pnl = trade_df["pnl"].cumsum()
        
        # Calculate running maximum
        running_max = cumulative_pnl.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative_pnl - running_max) / running_max.replace(0, np.nan)
        
        # Return maximum drawdown (most negative value)
        max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0.0
        
        return max_drawdown if not np.isnan(max_drawdown) else 0.0
    
    async def _calculate_sharpe_ratio(self, trade_df: pd.DataFrame, volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if volatility == 0:
            return 0.0
        
        # Calculate excess return (total return - risk-free rate)
        total_return = await self._calculate_total_return(trade_df)
        risk_free_rate = self.config["risk_free_rate"]
        excess_return = total_return - risk_free_rate
        
        # Annualized Sharpe ratio
        sharpe_ratio = excess_return / volatility
        
        return sharpe_ratio if not np.isnan(sharpe_ratio) else 0.0
    
    async def _calculate_sortino_ratio(self, trade_df: pd.DataFrame) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(trade_df) < 2:
            return 0.0
        
        returns = trade_df["pnl"].pct_change().dropna()
        
        # Calculate downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')  # No downside risk
        
        downside_deviation = downside_returns.std()
        
        if downside_deviation == 0:
            return 0.0
        
        # Calculate excess return
        total_return = await self._calculate_total_return(trade_df)
        risk_free_rate = self.config["risk_free_rate"]
        excess_return = total_return - risk_free_rate
        
        # Sortino ratio
        sortino_ratio = excess_return / (downside_deviation * np.sqrt(252))
        
        return sortino_ratio if not np.isnan(sortino_ratio) else 0.0
    
    async def _calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio (return / max drawdown)"""
        if max_drawdown == 0:
            return float('inf') if total_return > 0 else 0.0
        
        return total_return / max_drawdown
    
    async def _calculate_var(self, trade_df: pd.DataFrame, confidence_level: float) -> float:
        """Calculate Value at Risk (VaR)"""
        if len(trade_df) < 2:
            return 0.02
        
        returns = trade_df["pnl"].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.02
        
        # Calculate VaR at given confidence level
        var = np.percentile(returns, (1 - confidence_level) * 100)
        
        return abs(var) if not np.isnan(var) else 0.02
    
    async def _calculate_expected_shortfall(self, trade_df: pd.DataFrame, confidence_level: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(trade_df) < 2:
            return 0.03
        
        returns = trade_df["pnl"].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.03
        
        # Calculate VaR threshold
        var_threshold = np.percentile(returns, (1 - confidence_level) * 100)
        
        # Calculate Expected Shortfall (average of returns below VaR threshold)
        tail_returns = returns[returns <= var_threshold]
        
        if len(tail_returns) == 0:
            return abs(var_threshold)
        
        expected_shortfall = abs(tail_returns.mean())
        
        return expected_shortfall if not np.isnan(expected_shortfall) else 0.03
    
    async def _calculate_avg_win_loss(self, trade_df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate average winning and losing trade amounts"""
        winning_trades = trade_df[trade_df["pnl"] > 0]["pnl"]
        losing_trades = trade_df[trade_df["pnl"] < 0]["pnl"]
        
        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0.0
        avg_loss = abs(losing_trades.mean()) if len(losing_trades) > 0 else 0.0
        
        return (avg_win if not np.isnan(avg_win) else 0.0,
                avg_loss if not np.isnan(avg_loss) else 0.0)
    
    async def _calculate_largest_win_loss(self, trade_df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate largest winning and losing trades"""
        winning_trades = trade_df[trade_df["pnl"] > 0]["pnl"]
        losing_trades = trade_df[trade_df["pnl"] < 0]["pnl"]
        
        largest_win = winning_trades.max() if len(winning_trades) > 0 else 0.0
        largest_loss = abs(losing_trades.min()) if len(losing_trades) > 0 else 0.0
        
        return (largest_win if not np.isnan(largest_win) else 0.0,
                largest_loss if not np.isnan(largest_loss) else 0.0)
    
    async def _calculate_recovery_factor(self, total_return: float, max_drawdown: float) -> float:
        """Calculate recovery factor (return / max drawdown)"""
        if max_drawdown == 0:
            return float('inf') if total_return > 0 else 0.0
        
        return total_return / max_drawdown
    
    async def _calculate_beta_alpha(self, trade_df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate beta and alpha relative to benchmark"""
        # For now, return default values as benchmark data is not implemented
        return 1.0, 0.0
    
    async def _determine_performance_level(self, metrics: PerformanceMetrics) -> PerformanceLevel:
        """Determine overall performance level"""
        thresholds = self.config["performance_thresholds"]
        
        total_return = float(metrics.total_return)
        sharpe_ratio = float(metrics.sharpe_ratio)
        max_drawdown = float(metrics.max_drawdown)
        
        # Check if meets excellent criteria
        if (total_return >= thresholds["excellent"]["return"] and
            sharpe_ratio >= thresholds["excellent"]["sharpe"] and
            max_drawdown <= thresholds["excellent"]["drawdown"]):
            return PerformanceLevel.EXCELLENT
        
        # Check if meets good criteria
        if (total_return >= thresholds["good"]["return"] and
            sharpe_ratio >= thresholds["good"]["sharpe"] and
            max_drawdown <= thresholds["good"]["drawdown"]):
            return PerformanceLevel.GOOD
        
        # Check if meets fair criteria
        if (total_return >= thresholds["fair"]["return"] and
            sharpe_ratio >= thresholds["fair"]["sharpe"] and
            max_drawdown <= thresholds["fair"]["drawdown"]):
            return PerformanceLevel.FAIR
        
        # Check if meets poor criteria
        if (total_return >= thresholds["poor"]["return"] and
            max_drawdown <= thresholds["poor"]["drawdown"]):
            return PerformanceLevel.POOR
        
        # Otherwise, critical
        return PerformanceLevel.CRITICAL
    
    async def _analyze_strengths_weaknesses(self, metrics: PerformanceMetrics) -> Tuple[List[str], List[str]]:
        """Analyze performance strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        total_return = float(metrics.total_return)
        win_rate = float(metrics.win_rate)
        sharpe_ratio = float(metrics.sharpe_ratio)
        max_drawdown = float(metrics.max_drawdown)
        profit_factor = float(metrics.profit_factor)
        
        # Analyze strengths
        if total_return > 0.15:
            strengths.append("出色的总回报率")
        elif total_return > 0.10:
            strengths.append("良好的总回报率")
        
        if win_rate > 0.7:
            strengths.append("高胜率")
        elif win_rate > 0.6:
            strengths.append("中等偏上的胜率")
        
        if sharpe_ratio > 1.5:
            strengths.append("优秀的风险调整收益")
        elif sharpe_ratio > 1.0:
            strengths.append("良好的风险调整收益")
        
        if profit_factor > 2.0:
            strengths.append("强劲的利润因子")
        elif profit_factor > 1.5:
            strengths.append("健康的利润因子")
        
        if max_drawdown < 0.05:
            strengths.append("极低的回撤")
        elif max_drawdown < 0.10:
            strengths.append("较低的回撤")
        
        # Analyze weaknesses
        if total_return < 0:
            weaknesses.append("负回报率")
        elif total_return < 0.05:
            weaknesses.append("回报率较低")
        
        if win_rate < 0.4:
            weaknesses.append("胜率偏低")
        
        if sharpe_ratio < 0.5:
            weaknesses.append("风险调整收益不佳")
        
        if profit_factor < 1.2:
            weaknesses.append("利润因子偏低")
        
        if max_drawdown > 0.20:
            weaknesses.append("高回撤风险")
        elif max_drawdown > 0.15:
            weaknesses.append("回撤偏高")
        
        return strengths, weaknesses
    
    async def _generate_recommendations(self, metrics: PerformanceMetrics,
                                      level: PerformanceLevel) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        total_return = float(metrics.total_return)
        win_rate = float(metrics.win_rate)
        sharpe_ratio = float(metrics.sharpe_ratio)
        max_drawdown = float(metrics.max_drawdown)
        profit_factor = float(metrics.profit_factor)
        
        # Return-based recommendations
        if total_return < 0.05:
            recommendations.append("考虑调整策略以提高盈利能力")
        elif total_return > 0.15 and max_drawdown > 0.15:
            recommendations.append("在保持收益的同时降低风险")
        
        # Win rate recommendations
        if win_rate < 0.5:
            recommendations.append("提高信号准确性或优化入场时机")
        elif win_rate > 0.8 and profit_factor < 1.5:
            recommendations.append("提高盈亏比，即使降低胜率")
        
        # Risk-based recommendations
        if max_drawdown > 0.20:
            recommendations.append("立即实施更严格的风险管理措施")
        elif max_drawdown > 0.15:
            recommendations.append("考虑降低仓位规模以减少回撤")
        
        # Sharpe ratio recommendations
        if sharpe_ratio < 0.5:
            recommendations.append("优化风险调整收益，考虑更稳健的策略")
        
        # Profit factor recommendations
        if profit_factor < 1.3:
            recommendations.append("提高盈亏比或优化止损止盈设置")
        
        # General recommendations based on performance level
        if level == PerformanceLevel.CRITICAL:
            recommendations.append("建议暂停交易并全面审查策略")
        elif level == PerformanceLevel.POOR:
            recommendations.append("考虑策略调整或参数优化")
        elif level == PerformanceLevel.EXCELLENT:
            recommendations.append("当前表现优秀，可考虑适当增加仓位")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    async def _determine_performance_trend(self, entity_id: str, current_metrics: PerformanceMetrics) -> str:
        """Determine if performance is improving, stable, or declining"""
        if entity_id not in self.performance_history:
            return "stable"
        
        history = self.performance_history[entity_id]
        
        if len(history) < 3:
            return "stable"
        
        # Compare recent performance with earlier performance
        recent_metrics = history[-3:]  # Last 3 analyses
        earlier_metrics = history[:-3] if len(history) > 3 else history[:max(1, len(history)//2)]
        
        if not earlier_metrics:
            return "stable"
        
        # Calculate average metrics
        recent_return = np.mean([float(m.metrics.total_return) for m in recent_metrics])
        earlier_return = np.mean([float(m.metrics.total_return) for m in earlier_metrics])
        
        recent_sharpe = np.mean([float(m.metrics.sharpe_ratio) for m in recent_metrics])
        earlier_sharpe = np.mean([float(m.metrics.sharpe_ratio) for m in earlier_metrics])
        
        # Determine trend
        return_improvement = recent_return - earlier_return
        sharpe_improvement = recent_sharpe - earlier_sharpe
        
        if return_improvement > 0.02 and sharpe_improvement > 0.2:
            return "improving"
        elif return_improvement < -0.02 and sharpe_improvement < -0.2:
            return "declining"
        else:
            return "stable"
    
    async def _calculate_overall_score(self, metrics: PerformanceMetrics) -> Decimal:
        """Calculate overall performance score"""
        scores = []
        
        # Return score (0-25 points)
        total_return = float(metrics.total_return)
        if total_return > 0.2:
            scores.append(25)
        elif total_return > 0.1:
            scores.append(20)
        elif total_return > 0.05:
            scores.append(15)
        elif total_return > 0:
            scores.append(10)
        else:
            scores.append(0)
        
        # Sharpe ratio score (0-25 points)
        sharpe_ratio = float(metrics.sharpe_ratio)
        if sharpe_ratio > 2.0:
            scores.append(25)
        elif sharpe_ratio > 1.5:
            scores.append(20)
        elif sharpe_ratio > 1.0:
            scores.append(15)
        elif sharpe_ratio > 0.5:
            scores.append(10)
        else:
            scores.append(0)
        
        # Win rate score (0-20 points)
        win_rate = float(metrics.win_rate)
        if win_rate > 0.8:
            scores.append(20)
        elif win_rate > 0.7:
            scores.append(16)
        elif win_rate > 0.6:
            scores.append(12)
        elif win_rate > 0.5:
            scores.append(8)
        else:
            scores.append(0)
        
        # Drawdown score (0-15 points)
        max_drawdown = float(metrics.max_drawdown)
        if max_drawdown < 0.05:
            scores.append(15)
        elif max_drawdown < 0.10:
            scores.append(12)
        elif max_drawdown < 0.15:
            scores.append(9)
        elif max_drawdown < 0.20:
            scores.append(6)
        else:
            scores.append(0)
        
        # Profit factor score (0-15 points)
        profit_factor = float(metrics.profit_factor)
        if profit_factor > 3.0:
            scores.append(15)
        elif profit_factor > 2.0:
            scores.append(12)
        elif profit_factor > 1.5:
            scores.append(9)
        elif profit_factor > 1.2:
            scores.append(6)
        else:
            scores.append(0)
        
        # Calculate weighted average
        total_score = sum(scores)
        
        return Decimal(str(round(total_score, 1)))
    
    async def _store_performance_history(self, entity_id: str, insight: PerformanceInsight):
        """Store performance insight in history"""
        if entity_id not in self.performance_history:
            self.performance_history[entity_id] = []
        
        self.performance_history[entity_id].append(insight)
        
        # Keep only recent history (last 100 analyses)
        if len(self.performance_history[entity_id]) > 100:
            self.performance_history[entity_id] = self.performance_history[entity_id][-100:]
    
    async def get_performance_summary(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive performance summary for an entity"""
        if entity_id not in self.performance_history:
            return None
        
        history = self.performance_history[entity_id]
        
        if not history:
            return None
        
        recent_insight = history[-1]
        
        # Calculate trends
        if len(history) >= 5:
            recent_scores = [float(i.overall_score) for i in history[-5:]]
            score_trend = "improving" if recent_scores[-1] > recent_scores[0] else "declining"
        else:
            score_trend = "stable"
        
        # Calculate average metrics over time
        avg_metrics = {}
        for metric_field in recent_insight.metrics.__dataclass_fields__.keys():
            values = [getattr(i.metrics, metric_field) for i in history]
            avg_value = sum(float(v) for v in values) / len(values)
            avg_metrics[metric_field] = round(avg_value, 4)
        
        return {
            "entity_id": entity_id,
            "entity_type": recent_insight.entity_type,
            "current_performance": {
                "level": recent_insight.performance_level.value,
                "score": float(recent_insight.overall_score),
                "trend": recent_insight.trend,
                "timestamp": recent_insight.timestamp.isoformat()
            },
            "average_metrics": avg_metrics,
            "performance_trend": score_trend,
            "total_analyses": len(history),
            "strengths": recent_insight.strengths,
            "weaknesses": recent_insight.weaknesses,
            "recommendations": recent_insight.recommendations,
            "recent_history": [
                {
                    "timestamp": i.timestamp.isoformat(),
                    "score": float(i.overall_score),
                    "level": i.performance_level.value,
                    "total_return": float(i.metrics.total_return),
                    "sharpe_ratio": float(i.metrics.sharpe_ratio),
                    "max_drawdown": float(i.metrics.max_drawdown)
                }
                for i in history[-10:]  # Last 10 analyses
            ]
        }
    
    def clear_performance_data(self, entity_id: Optional[str] = None):
        """Clear performance data"""
        if entity_id:
            if entity_id in self.performance_history:
                del self.performance_history[entity_id]
            if entity_id in self.trade_history:
                del self.trade_history[entity_id]
            if entity_id in self.current_performance:
                del self.current_performance[entity_id]
            if entity_id in self.active_entities:
                del self.active_entities[entity_id]
        else:
            self.performance_history.clear()
            self.trade_history.clear()
            self.current_performance.clear()
            self.active_entities.clear()
        
        logger.info("清除性能数据", entity_id=entity_id or "all")