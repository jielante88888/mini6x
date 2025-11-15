#!/usr/bin/env python3
"""
独立的策略性能分析系统测试
直接测试analytics.py的核心功能，避免依赖问题
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from collections import defaultdict, deque


# 简化的StrategyType定义
class StrategyType(Enum):
    GRID = "grid"
    MARTINGALE = "martingale"
    ARBITRAGE = "arbitrage"


# 简化的ValidationException
class ValidationException(Exception):
    pass


class MetricType(Enum):
    """指标类型"""
    PROFIT_LOSS = "profit_loss"
    SUCCESS_RATE = "success_rate"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    TOTAL_TRADES = "total_trades"
    AVERAGE_TRADE = "average_trade"
    VOLATILITY = "volatility"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    INFORMATION_RATIO = "information_ratio"


class TimeFrame(Enum):
    """时间框架"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class BenchmarkType(Enum):
    """基准类型"""
    BUY_AND_HOLD = "buy_and_hold"
    MARKET_INDEX = "market_index"
    STRATEGY_COMPARISON = "strategy_comparison"
    BENCHMARK_NONE = "none"


@dataclass
class PerformanceMetric:
    """性能指标数据点"""
    timestamp: datetime
    value: Decimal
    metric_type: MetricType
    strategy_id: str
    symbol: str
    timeframe: TimeFrame
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': float(self.value),
            'metric_type': self.metric_type.value,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe.value,
            'metadata': self.metadata
        }


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    strategy_id: str
    symbol: str
    trade_type: str  # buy, sell
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    profit_loss: Decimal
    commission: Decimal
    execution_time: Optional[float] = None
    slippage: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def net_profit_loss(self) -> Decimal:
        """净盈亏"""
        return self.profit_loss - self.commission


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    strategy_id: str
    timestamp: datetime
    total_value: Decimal
    total_pnl: Decimal
    daily_pnl: Decimal
    total_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    volatility: Decimal
    total_commission: Decimal
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkData:
    """基准数据"""
    timestamp: datetime
    value: Decimal
    benchmark_type: BenchmarkType
    symbol: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': float(self.value),
            'benchmark_type': self.benchmark_type.value,
            'symbol': self.symbol
        }


class PerformanceAnalyzer:
    """性能分析器"""
    
    @staticmethod
    def _standard_deviation(values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[Decimal], risk_free_rate: Decimal = Decimal('0.02')) -> Decimal:
        """计算夏普比率"""
        if not returns or len(returns) < 2:
            return Decimal('0')
        
        returns_array = [float(r) for r in returns]
        std_dev = PerformanceAnalyzer._standard_deviation(returns_array)
        
        if std_dev == 0:
            return Decimal('0')
        
        excess_returns = [r - float(risk_free_rate) for r in returns_array]
        mean_excess = sum(excess_returns) / len(excess_returns)
        
        return Decimal(str(mean_excess / std_dev))
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[Decimal], risk_free_rate: Decimal = Decimal('0.02')) -> Decimal:
        """计算索提诺比率"""
        if not returns or len(returns) < 2:
            return Decimal('0')
        
        returns_array = [float(r) for r in returns]
        excess_returns = [r - float(risk_free_rate) for r in returns_array]
        
        # 计算下行标准差
        downside_returns = [min(excess_return, 0) for excess_return in excess_returns]
        downside_std = PerformanceAnalyzer._standard_deviation(downside_returns)
        
        if downside_std == 0:
            return Decimal('0')
        
        mean_excess = sum(excess_returns) / len(excess_returns)
        return Decimal(str(mean_excess / downside_std))
    
    @staticmethod
    def calculate_max_drawdown(values: List[Decimal]) -> Tuple[Decimal, int, int]:
        """计算最大回撤"""
        if not values:
            return Decimal('0'), 0, 0
        
        values_array = [float(v) for v in values]
        peak = values_array[0]
        max_drawdown = 0.0
        max_dd_idx = 0
        start_idx = 0
        
        for i, value in enumerate(values_array):
            if value > peak:
                peak = value
                start_idx = i
            
            current_dd = (peak - value) / peak
            if current_dd > max_drawdown:
                max_drawdown = current_dd
                max_dd_idx = i
        
        return Decimal(str(max_drawdown)), start_idx, max_dd_idx
    
    @staticmethod
    def calculate_calmar_ratio(annualized_return: Decimal, max_drawdown: Decimal) -> Decimal:
        """计算卡玛比率"""
        if max_drawdown == 0:
            return Decimal('0')
        return annualized_return / max_drawdown
    
    @staticmethod
    def calculate_information_ratio(portfolio_returns: List[Decimal], benchmark_returns: List[Decimal]) -> Decimal:
        """计算信息比率"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return Decimal('0')
        
        portfolio_array = [float(r) for r in portfolio_returns]
        benchmark_array = [float(r) for r in benchmark_returns]
        
        excess_returns = [p - b for p, b in zip(portfolio_array, benchmark_array)]
        excess_std = PerformanceAnalyzer._standard_deviation(excess_returns)
        
        if excess_std == 0:
            return Decimal('0')
        
        mean_excess = sum(excess_returns) / len(excess_returns)
        return Decimal(str(mean_excess / excess_std))
    
    @staticmethod
    def calculate_win_rate(trades: List[TradeRecord]) -> Decimal:
        """计算胜率"""
        if not trades:
            return Decimal('0')
        
        winning_trades = [t for t in trades if t.net_profit_loss() > 0]
        return Decimal(str(len(winning_trades) / len(trades)))
    
    @staticmethod
    def calculate_profit_factor(trades: List[TradeRecord]) -> Decimal:
        """计算盈利因子"""
        if not trades:
            return Decimal('0')
        
        gross_profit = sum(t.profit_loss for t in trades if t.net_profit_loss() > 0)
        gross_loss = abs(sum(t.profit_loss for t in trades if t.net_profit_loss() < 0))
        
        if gross_loss == 0:
            return Decimal('inf') if gross_profit > 0 else Decimal('0')
        
        return gross_profit / gross_loss
    
    @staticmethod
    def calculate_volatility(returns: List[Decimal]) -> Decimal:
        """计算波动率"""
        if not returns or len(returns) < 2:
            return Decimal('0')
        
        returns_array = [float(r) for r in returns]
        std_dev = PerformanceAnalyzer._standard_deviation(returns_array)
        return Decimal(str(std_dev))
    
    @staticmethod
    def annualize_return(total_return: Decimal, days: int) -> Decimal:
        """年化收益率"""
        if days <= 0:
            return Decimal('0')
        
        annualized = (Decimal('1') + total_return) ** (Decimal('365') / Decimal(str(days))) - Decimal('1')
        return annualized


class StrategyPerformanceTracker:
    """策略性能跟踪器"""
    
    def __init__(self, strategy_id: str, strategy_type: StrategyType, symbol: str):
        self.strategy_id = strategy_id
        self.strategy_type = strategy_type
        self.symbol = symbol
        
        # 数据存储
        self.trade_records: List[TradeRecord] = []
        self.performance_metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.snapshots: List[PerformanceSnapshot] = []
        
        # 实时数据
        self.current_portfolio_value = Decimal('10000')  # 初始资金
        self.peak_value = self.current_portfolio_value
        self.current_drawdown = Decimal('0')
        self.max_drawdown = Decimal('0')
        
        # 统计信息
        self.total_trades = 0
        self.total_pnl = Decimal('0')
        self.total_commission = Decimal('0')
        self.avg_trade_duration = Decimal('0')
        
        # 性能窗口
        self.max_history_size = 10000
        self.metrics_history_size = 1000
    
    def add_trade(self, trade: TradeRecord):
        """添加交易记录"""
        try:
            # 验证交易记录
            if trade.strategy_id != self.strategy_id:
                raise ValidationException("交易记录策略ID不匹配")
            
            # 添加交易记录
            self.trade_records.append(trade)
            self.total_trades += 1
            self.total_pnl += trade.net_profit_loss()
            self.total_commission += trade.commission
            
            # 更新组合价值
            self.current_portfolio_value += trade.net_profit_loss()
            
            # 更新峰值和回撤
            if self.current_portfolio_value > self.peak_value:
                self.peak_value = self.current_portfolio_value
                self.current_drawdown = Decimal('0')
            else:
                self.current_drawdown = (self.peak_value - self.current_portfolio_value) / self.peak_value
            
            # 更新最大回撤
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
            
            # 保持数据在合理范围
            if len(self.trade_records) > self.max_history_size:
                self.trade_records = self.trade_records[-self.max_history_size//2:]
            
            # 生成性能指标
            self._generate_performance_metrics(trade)
            
            # 生成性能快照
            if self.total_trades % 10 == 0:  # 每10笔交易生成一次快照
                self._generate_snapshot()
            
        except Exception as e:
            raise
    
    def add_metric(self, metric: PerformanceMetric):
        """添加性能指标"""
        metric_key = metric.metric_type.value
        self.performance_metrics[metric_key].append(metric)
        
        # 保持历史数据在合理范围
        if len(self.performance_metrics[metric_key]) > self.metrics_history_size:
            self.performance_metrics[metric_key] = self.performance_metrics[metric_key][-self.metrics_history_size//2:]
    
    def _generate_performance_metrics(self, trade: TradeRecord):
        """生成性能指标"""
        now = datetime.now()
        
        # 基本指标
        self.add_metric(PerformanceMetric(
            timestamp=now,
            value=self.total_pnl,
            metric_type=MetricType.PROFIT_LOSS,
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timeframe=TimeFrame.HOUR_1,
            metadata={'trade_id': trade.trade_id}
        ))
        
        # 胜率
        win_rate = self.calculate_win_rate()
        self.add_metric(PerformanceMetric(
            timestamp=now,
            value=win_rate,
            metric_type=MetricType.WIN_RATE,
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timeframe=TimeFrame.HOUR_1
        ))
        
        # 最大回撤
        self.add_metric(PerformanceMetric(
            timestamp=now,
            value=self.max_drawdown,
            metric_type=MetricType.MAX_DRAWDOWN,
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timeframe=TimeFrame.HOUR_1
        ))
        
        # 成功率
        if self.total_trades > 0:
            success_rate = Decimal(str((self.total_trades - len([t for t in self.trade_records if t.net_profit_loss() < 0])) / self.total_trades))
            self.add_metric(PerformanceMetric(
                timestamp=now,
                value=success_rate,
                metric_type=MetricType.SUCCESS_RATE,
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                timeframe=TimeFrame.HOUR_1
            ))
        
        # 总交易次数
        self.add_metric(PerformanceMetric(
            timestamp=now,
            value=Decimal(str(self.total_trades)),
            metric_type=MetricType.TOTAL_TRADES,
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timeframe=TimeFrame.HOUR_1
        ))
    
    def _generate_snapshot(self):
        """生成性能快照"""
        now = datetime.now()
        
        # 计算综合指标
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()
        
        # 计算收益率序列
        returns = self._calculate_returns()
        sharpe_ratio = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
        volatility = PerformanceAnalyzer.calculate_volatility(returns)
        
        # 计算日盈亏
        daily_pnl = self._calculate_daily_pnl()
        
        snapshot = PerformanceSnapshot(
            strategy_id=self.strategy_id,
            timestamp=now,
            total_value=self.current_portfolio_value,
            total_pnl=self.total_pnl,
            daily_pnl=daily_pnl,
            total_trades=self.total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            total_commission=self.total_commission,
            metadata={
                'strategy_type': self.strategy_type.value,
                'symbol': self.symbol,
                'peak_value': float(self.peak_value),
                'current_drawdown': float(self.current_drawdown)
            }
        )
        
        self.snapshots.append(snapshot)
        
        # 保持快照在合理范围
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-50:]
    
    def _calculate_returns(self) -> List[Decimal]:
        """计算收益率序列"""
        if len(self.snapshots) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.snapshots)):
            prev_value = self.snapshots[i-1].total_value
            curr_value = self.snapshots[i].total_value
            if prev_value > 0:
                returns.append((curr_value - prev_value) / prev_value)
        
        return returns
    
    def _calculate_daily_pnl(self) -> Decimal:
        """计算当日盈亏"""
        if not self.snapshots:
            return Decimal('0')
        
        today = datetime.now().date()
        today_snapshots = [s for s in self.snapshots if s.timestamp.date() == today]
        
        if len(today_snapshots) < 2:
            return Decimal('0')
        
        return today_snapshots[-1].total_pnl - today_snapshots[0].total_pnl
    
    def calculate_win_rate(self) -> Decimal:
        """计算胜率"""
        return PerformanceAnalyzer.calculate_win_rate(self.trade_records)
    
    def calculate_profit_factor(self) -> Decimal:
        """计算盈利因子"""
        return PerformanceAnalyzer.calculate_profit_factor(self.trade_records)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        returns = self._calculate_returns()
        sharpe_ratio = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
        sortino_ratio = PerformanceAnalyzer.calculate_sortino_ratio(returns)
        calmar_ratio = PerformanceAnalyzer.calculate_calmar_ratio(
            PerformanceAnalyzer.annualize_return(
                self.total_pnl / self.current_portfolio_value,
                30  # 假设运行30天
            ),
            self.max_drawdown
        )
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': self.strategy_type.value,
            'symbol': self.symbol,
            'total_trades': self.total_trades,
            'total_pnl': float(self.total_pnl),
            'total_commission': float(self.total_commission),
            'net_pnl': float(self.total_pnl - self.total_commission),
            'current_portfolio_value': float(self.current_portfolio_value),
            'win_rate': float(self.calculate_win_rate()),
            'profit_factor': float(self.calculate_profit_factor()),
            'max_drawdown': float(self.max_drawdown),
            'current_drawdown': float(self.current_drawdown),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'volatility': float(PerformanceAnalyzer.calculate_volatility(returns)),
            'total_returns': float(self.total_pnl / self.current_portfolio_value),
            'created_at': self.snapshots[0].timestamp.isoformat() if self.snapshots else None,
            'last_updated': self.snapshots[-1].timestamp.isoformat() if self.snapshots else None
        }


class PerformanceAnalyticsEngine:
    """性能分析引擎"""
    
    def __init__(self):
        self.trackers: Dict[str, StrategyPerformanceTracker] = {}
        self.benchmark_data: Dict[str, List[BenchmarkData]] = defaultdict(list)
        self.analysis_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5分钟缓存
    
    def register_strategy(self, strategy_id: str, strategy_type: StrategyType, symbol: str) -> StrategyPerformanceTracker:
        """注册策略"""
        if strategy_id in self.trackers:
            return self.trackers[strategy_id]
        
        tracker = StrategyPerformanceTracker(strategy_id, strategy_type, symbol)
        self.trackers[strategy_id] = tracker
        
        return tracker
    
    def add_trade_record(self, trade: TradeRecord):
        """添加交易记录"""
        if trade.strategy_id not in self.trackers:
            # 创建默认跟踪器
            self.register_strategy(trade.strategy_id, StrategyType.GRID, trade.symbol)
        
        self.trackers[trade.strategy_id].add_trade(trade)
        
        # 清除相关缓存
        self._clear_cache_for_strategy(trade.strategy_id)
    
    def get_strategy_performance(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略性能"""
        tracker = self.trackers.get(strategy_id)
        if not tracker:
            return None
        
        return tracker.get_performance_summary()
    
    def compare_strategies(self, strategy_ids: List[str], metric: MetricType = MetricType.SHARPE_RATIO) -> Dict[str, Any]:
        """比较策略性能"""
        if not strategy_ids:
            return {}
        
        comparison_results = {}
        
        for strategy_id in strategy_ids:
            if strategy_id not in self.trackers:
                continue
            
            tracker = self.trackers[strategy_id]
            if tracker.trade_records:
                # 基于实际交易数据计算指标
                if metric == MetricType.WIN_RATE:
                    metric_value = float(tracker.calculate_win_rate())
                elif metric == MetricType.PROFIT_FACTOR:
                    metric_value = float(tracker.calculate_profit_factor())
                elif metric == MetricType.SHARPE_RATIO:
                    returns = tracker._calculate_returns()
                    metric_value = float(PerformanceAnalyzer.calculate_sharpe_ratio(returns))
                else:
                    # 默认使用总盈亏
                    metric_value = float(tracker.total_pnl)
                
                comparison_results[strategy_id] = {
                    'strategy_id': strategy_id,
                    'metric_value': metric_value,
                    'metric_type': metric.value,
                    'performance_summary': tracker.get_performance_summary()
                }
        
        # 按指标值排序
        sorted_results = sorted(
            comparison_results.items(),
            key=lambda x: x[1]['metric_value'],
            reverse=True
        )
        
        return {
            'comparison_results': dict(sorted_results),
            'ranking': [strategy_id for strategy_id, _ in sorted_results],
            'metric_type': metric.value
        }
    
    def _clear_cache_for_strategy(self, strategy_id: str):
        """清除策略相关缓存"""
        keys_to_remove = [k for k in self.analysis_cache.keys() if strategy_id in k]
        for key in keys_to_remove:
            del self.analysis_cache[key]
    
    def add_benchmark_data(self, benchmark: BenchmarkData):
        """添加基准数据"""
        self.benchmark_data[benchmark.symbol].append(benchmark)
        
        # 保持数据在合理范围
        if len(self.benchmark_data[benchmark.symbol]) > 10000:
            self.benchmark_data[benchmark.symbol] = self.benchmark_data[benchmark.symbol][-5000:]
    
    def get_all_strategies_performance(self) -> Dict[str, Any]:
        """获取所有策略性能"""
        results = {}
        
        for strategy_id, tracker in self.trackers.items():
            results[strategy_id] = tracker.get_performance_summary()
        
        return results


# 工厂函数
def create_performance_analytics_engine() -> PerformanceAnalyticsEngine:
    """创建性能分析引擎"""
    return PerformanceAnalyticsEngine()


# 辅助函数
def create_trade_record(
    trade_id: str,
    strategy_id: str,
    symbol: str,
    trade_type: str,
    quantity: Decimal,
    price: Decimal,
    profit_loss: Decimal,
    commission: Decimal,
    **kwargs
) -> TradeRecord:
    """创建交易记录"""
    return TradeRecord(
        trade_id=trade_id,
        strategy_id=strategy_id,
        symbol=symbol,
        trade_type=trade_type,
        quantity=quantity,
        price=price,
        timestamp=datetime.now(),
        profit_loss=profit_loss,
        commission=commission,
        **kwargs
    )


def create_benchmark_data(
    timestamp: datetime,
    value: Decimal,
    benchmark_type: BenchmarkType,
    symbol: str = ""
) -> BenchmarkData:
    """创建基准数据"""
    return BenchmarkData(
        timestamp=timestamp,
        value=value,
        benchmark_type=benchmark_type,
        symbol=symbol
    )


# 测试函数
def test_performance_analyzer():
    """测试性能分析器数学计算"""
    print("测试性能分析器...")
    
    # 测试夏普比率计算
    returns = [Decimal('0.01'), Decimal('0.02'), Decimal('-0.01'), Decimal('0.015'), Decimal('0.005')]
    sharpe = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
    print(f"夏普比率: {sharpe}")
    assert isinstance(sharpe, Decimal), "夏普比率计算结果类型错误"
    
    # 测试索提诺比率
    sortino = PerformanceAnalyzer.calculate_sortino_ratio(returns)
    print(f"索提诺比率: {sortino}")
    assert isinstance(sortino, Decimal), "索提诺比率计算结果类型错误"
    
    # 测试最大回撤
    values = [Decimal('10000'), Decimal('9500'), Decimal('9800'), Decimal('10500'), Decimal('10200')]
    max_dd, start_idx, end_idx = PerformanceAnalyzer.calculate_max_drawdown(values)
    print(f"最大回撤: {max_dd}")
    assert isinstance(max_dd, Decimal), "最大回撤计算结果类型错误"
    
    print("✓ 性能分析器测试通过")


def test_strategy_performance_tracker():
    """测试策略性能跟踪器"""
    print("\n测试策略性能跟踪器...")
    
    # 创建跟踪器
    tracker = StrategyPerformanceTracker(
        strategy_id="test_strategy_1",
        strategy_type=StrategyType.GRID,
        symbol="BTC/USDT"
    )
    
    # 添加交易记录
    trades = [
        create_trade_record(
            trade_id="trade_1",
            strategy_id="test_strategy_1",
            symbol="BTC/USDT",
            trade_type="buy",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            profit_loss=Decimal('100'),
            commission=Decimal('5')
        ),
        create_trade_record(
            trade_id="trade_2",
            strategy_id="test_strategy_1",
            symbol="BTC/USDT",
            trade_type="sell",
            quantity=Decimal('0.1'),
            price=Decimal('51000'),
            profit_loss=Decimal('150'),
            commission=Decimal('5')
        )
    ]
    
    for trade in trades:
        tracker.add_trade(trade)
    
    # 测试性能摘要
    summary = tracker.get_performance_summary()
    print(f"性能摘要: {summary}")
    assert 'strategy_id' in summary, "性能摘要缺少strategy_id"
    assert summary['strategy_id'] == "test_strategy_1", "策略ID不匹配"
    assert summary['total_trades'] == 2, "交易次数不匹配"
    
    # 测试胜率计算
    win_rate = tracker.calculate_win_rate()
    print(f"胜率: {win_rate}")
    assert isinstance(win_rate, Decimal), "胜率类型错误"
    
    print("✓ 策略性能跟踪器测试通过")


def test_performance_analytics_engine():
    """测试性能分析引擎"""
    print("\n测试性能分析引擎...")
    
    # 创建引擎
    engine = create_performance_analytics_engine()
    assert isinstance(engine, PerformanceAnalyticsEngine), "引擎类型错误"
    
    # 注册策略
    tracker = engine.register_strategy(
        strategy_id="test_strategy_2",
        strategy_type=StrategyType.MARTINGALE,
        symbol="ETH/USDT"
    )
    
    # 添加交易记录
    trade = create_trade_record(
        trade_id="trade_3",
        strategy_id="test_strategy_2",
        symbol="ETH/USDT",
        trade_type="buy",
        quantity=Decimal('1.0'),
        price=Decimal('3000'),
        profit_loss=Decimal('50'),
        commission=Decimal('3')
    )
    
    engine.add_trade_record(trade)
    
    # 测试获取策略性能
    performance = engine.get_strategy_performance("test_strategy_2")
    print(f"策略性能: {performance}")
    assert performance is not None, "策略性能为空"
    assert performance['strategy_id'] == "test_strategy_2", "策略ID不匹配"
    
    # 测试策略比较
    comparison = engine.compare_strategies(["test_strategy_1", "test_strategy_2"])
    print(f"策略比较结果: {comparison}")
    assert 'comparison_results' in comparison, "比较结果缺少comparison_results"
    
    print("✓ 性能分析引擎测试通过")


def test_benchmark_data():
    """测试基准数据"""
    print("\n测试基准数据...")
    
    engine = create_performance_analytics_engine()
    
    # 添加基准数据
    benchmark = create_benchmark_data(
        timestamp=datetime.now(),
        value=Decimal('50000'),
        benchmark_type=BenchmarkType.BUY_AND_HOLD,
        symbol="BTC/USDT"
    )
    
    engine.add_benchmark_data(benchmark)
    
    # 测试获取所有策略性能
    all_performance = engine.get_all_strategies_performance()
    print(f"所有策略性能: {all_performance}")
    assert isinstance(all_performance, dict), "所有策略性能返回类型错误"
    
    print("✓ 基准数据测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始运行策略性能分析系统测试\n")
    
    try:
        test_performance_analyzer()
        test_strategy_performance_tracker()
        test_performance_analytics_engine()
        test_benchmark_data()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过！策略性能分析系统工作正常")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
