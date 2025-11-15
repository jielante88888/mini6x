"""
策略性能跟踪和分析系统
负责收集、分析、存储和报告策略运行性能数据，提供深度分析和可视化支持
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

try:
    from .base import StrategyConfig, StrategyState, StrategyType, ValidationException
    from ..utils.exceptions import ValidationException as BaseValidationException
    ValidationException = BaseValidationException
except ImportError:
    # 当作为脚本直接运行时
    from typing import TYPE_CHECKING
    from enum import Enum
    if TYPE_CHECKING:
        from .base import StrategyConfig, StrategyState, StrategyType
    else:
        # 创建占位符类
        class StrategyConfig:
            pass
        class StrategyState:
            pass
        class StrategyType(Enum):
            GRID = "grid"
            MARTINGALE = "martingale" 
            ARBITRAGE = "arbitrage"
        ValidationException = Exception


logger = logging.getLogger(__name__)


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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetric':
        """从字典创建"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            value=Decimal(str(data['value'])),
            metric_type=MetricType(data['metric_type']),
            strategy_id=data['strategy_id'],
            symbol=data['symbol'],
            timeframe=TimeFrame(data['timeframe']),
            metadata=data.get('metadata', {})
        )


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
        
        logger.info(f"策略性能跟踪器初始化: {strategy_id}, {symbol}")
    
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
            
            logger.debug(f"添加交易记录: {trade.trade_id}, 净盈亏: {trade.net_profit_loss()}")
            
        except Exception as e:
            logger.error(f"添加交易记录失败: {e}")
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
        try:
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
            
            # 手续费总额
            self.add_metric(PerformanceMetric(
                timestamp=now,
                value=self.total_commission,
                metric_type=MetricType.PROFIT_LOSS,  # 可以扩展为新的手续费指标
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                timeframe=TimeFrame.HOUR_1,
                metadata={'is_commission': True}
            ))
            
        except Exception as e:
            logger.error(f"生成性能指标失败: {e}")
    
    def _generate_snapshot(self):
        """生成性能快照"""
        try:
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
            
        except Exception as e:
            logger.error(f"生成性能快照失败: {e}")
    
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
    
    def get_recent_metrics(self, metric_type: MetricType, limit: int = 50) -> List[PerformanceMetric]:
        """获取最近的指标"""
        metrics = self.performance_metrics.get(metric_type.value, [])
        return metrics[-limit:]
    
    def get_trade_history(self, limit: int = 100) -> List[TradeRecord]:
        """获取交易历史"""
        return self.trade_records[-limit:]
    
    def export_performance_data(self) -> Dict[str, Any]:
        """导出性能数据"""
        return {
            'strategy_summary': self.get_performance_summary(),
            'trades': [trade.__dict__ for trade in self.trade_records],
            'metrics': {
                metric_type: [metric.to_dict() for metric in metrics]
                for metric_type, metrics in self.performance_metrics.items()
            },
            'snapshots': [snapshot.__dict__ for snapshot in self.snapshots]
        }


class PerformanceAnalyticsEngine:
    """性能分析引擎"""
    
    def __init__(self):
        self.trackers: Dict[str, StrategyPerformanceTracker] = {}
        self.benchmark_data: Dict[str, List[BenchmarkData]] = defaultdict(list)
        self.analysis_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        logger.info("性能分析引擎初始化完成")
    
    def register_strategy(self, strategy_id: str, strategy_type: StrategyType, symbol: str) -> StrategyPerformanceTracker:
        """注册策略"""
        if strategy_id in self.trackers:
            logger.warning(f"策略 {strategy_id} 已存在，返回现有跟踪器")
            return self.trackers[strategy_id]
        
        tracker = StrategyPerformanceTracker(strategy_id, strategy_type, symbol)
        self.trackers[strategy_id] = tracker
        
        logger.info(f"策略注册完成: {strategy_id}, {symbol}")
        return tracker
    
    def add_trade_record(self, trade: TradeRecord):
        """添加交易记录"""
        if trade.strategy_id not in self.trackers:
            logger.warning(f"策略 {trade.strategy_id} 未注册，创建默认跟踪器")
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
            metrics = tracker.get_recent_metrics(metric, limit=100)
            
            if metrics:
                latest_metric = metrics[-1]
                comparison_results[strategy_id] = {
                    'strategy_id': strategy_id,
                    'metric_value': float(latest_metric.value),
                    'metric_type': metric.value,
                    'timestamp': latest_metric.timestamp.isoformat(),
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
    
    def generate_performance_report(self, strategy_id: str, time_range: timedelta = timedelta(days=30)) -> Dict[str, Any]:
        """生成性能报告"""
        tracker = self.trackers.get(strategy_id)
        if not tracker:
            raise ValidationException(f"策略 {strategy_id} 不存在")
        
        # 检查缓存
        cache_key = f"report_{strategy_id}_{int(time_range.total_seconds())}"
        if cache_key in self.analysis_cache:
            cache_time, cached_data = self.analysis_cache[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                return cached_data
        
        # 生成报告
        report = {
            'strategy_id': strategy_id,
            'report_generated_at': datetime.now().isoformat(),
            'time_range_days': time_range.days,
            'performance_summary': tracker.get_performance_summary(),
            'trade_analysis': self._analyze_trades(tracker.trade_records),
            'risk_analysis': self._analyze_risk(tracker),
            'return_analysis': self._analyze_returns(tracker),
            'benchmark_comparison': self._compare_with_benchmark(strategy_id, time_range),
            'recommendations': self._generate_recommendations(tracker)
        }
        
        # 缓存结果
        self.analysis_cache[cache_key] = (datetime.now(), report)
        
        return report
    
    def _analyze_trades(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """分析交易数据"""
        if not trades:
            return {}
        
        # 按时间分析
        trade_by_hour = defaultdict(int)
        trade_by_day = defaultdict(int)
        
        for trade in trades:
            hour = trade.timestamp.hour
            day = trade.timestamp.date()
            trade_by_hour[hour] += 1
            trade_by_day[day] += 1
        
        # 盈亏分析
        profitable_trades = [t for t in trades if t.net_profit_loss() > 0]
        losing_trades = [t for t in trades if t.net_profit_loss() < 0]
        
        # 平均交易分析
        avg_profit = sum(t.net_profit_loss() for t in profitable_trades) / len(profitable_trades) if profitable_trades else Decimal('0')
        avg_loss = sum(t.net_profit_loss() for t in losing_trades) / len(losing_trades) if losing_trades else Decimal('0')
        
        return {
            'total_trades': len(trades),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'avg_profit_per_winning_trade': float(avg_profit),
            'avg_loss_per_losing_trade': float(avg_loss),
            'profit_loss_ratio': float(abs(avg_profit / avg_loss)) if avg_loss != 0 else Decimal('0'),
            'trades_by_hour': dict(trade_by_hour),
            'trades_by_day': dict(trade_by_day),
            'total_commission': float(sum(t.commission for t in trades)),
            'commission_ratio': float(sum(t.commission for t in trades) / abs(sum(t.net_profit_loss() for t in trades))) if trades else Decimal('0')
        }
    
    def _analyze_risk(self, tracker: StrategyPerformanceTracker) -> Dict[str, Any]:
        """分析风险指标"""
        returns = tracker._calculate_returns()
        
        if not returns:
            return {}
        
        # 风险指标
        volatility = PerformanceAnalyzer.calculate_volatility(returns)
        sharpe = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
        sortino = PerformanceAnalyzer.calculate_sortino_ratio(returns)
        max_dd, _, _ = PerformanceAnalyzer.calculate_max_drawdown([float(tracker.current_portfolio_value)] * len(returns))
        
        # 风险等级评估
        risk_level = "LOW"
        if tracker.max_drawdown > Decimal('0.1'):
            risk_level = "HIGH"
        elif tracker.max_drawdown > Decimal('0.05'):
            risk_level = "MEDIUM"
        
        return {
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe),
            'sortino_ratio': float(sortino),
            'max_drawdown': float(tracker.max_drawdown),
            'current_drawdown': float(tracker.current_drawdown),
            'risk_level': risk_level,
            'risk_adjusted_return': float(sharpe * tracker.current_portfolio_value)
        }
    
    def _analyze_returns(self, tracker: StrategyPerformanceTracker) -> Dict[str, Any]:
        """分析收益率"""
        if not tracker.snapshots:
            return {}
        
        # 时间段分析
        recent_snapshots = [s for s in tracker.snapshots if s.timestamp >= datetime.now() - timedelta(days=30)]
        
        if len(recent_snapshots) < 2:
            return {}
        
        start_value = recent_snapshots[0].total_value
        end_value = recent_snapshots[-1].total_value
        
        total_return = (end_value - start_value) / start_value
        annualized_return = PerformanceAnalyzer.annualize_return(total_return, 30)
        
        # 收益率统计
        returns = tracker._calculate_returns()
        
        return {
            'total_return_30d': float(total_return),
            'annualized_return': float(annualized_return),
            'best_daily_return': float(max(returns)) if returns else Decimal('0'),
            'worst_daily_return': float(min(returns)) if returns else Decimal('0'),
            'positive_days': len([r for r in returns if r > 0]),
            'negative_days': len([r for r in returns if r < 0]),
            'average_daily_return': float(sum(returns) / len(returns)) if returns else Decimal('0')
        }
    
    def _compare_with_benchmark(self, strategy_id: str, time_range: timedelta) -> Dict[str, Any]:
        """与基准比较"""
        tracker = self.trackers.get(strategy_id)
        if not tracker:
            return {}
        
        # 获取基准数据
        benchmark_symbol = tracker.symbol
        benchmark_data = self.benchmark_data.get(benchmark_symbol, [])
        
        recent_benchmarks = [b for b in benchmark_data if b.timestamp >= datetime.now() - time_range]
        
        if not recent_benchmarks:
            return {'message': '没有可用的基准数据'}
        
        # 计算基准收益率
        if len(recent_benchmarks) >= 2:
            start_price = recent_benchmarks[0].value
            end_price = recent_benchmarks[-1].value
            benchmark_return = (end_price - start_price) / start_price
            
            # 计算策略收益率
            returns = tracker._calculate_returns()
            strategy_return = sum(returns) if returns else Decimal('0')
            
            # 计算超额收益
            excess_return = strategy_return - benchmark_return
            
            return {
                'benchmark_return': float(benchmark_return),
                'strategy_return': float(strategy_return),
                'excess_return': float(excess_return),
                'outperformance': float(strategy_return > benchmark_return),
                'information_ratio': float(PerformanceAnalyzer.calculate_information_ratio(returns, [benchmark_return] * len(returns)))
            }
        
        return {'message': '基准数据不足'}
    
    def _generate_recommendations(self, tracker: StrategyPerformanceTracker) -> List[str]:
        """生成策略建议"""
        recommendations = []
        
        # 基于胜率的建议
        win_rate = tracker.calculate_win_rate()
        if win_rate < Decimal('0.4'):
            recommendations.append("胜率较低，建议优化入场条件或策略参数")
        elif win_rate > Decimal('0.7'):
            recommendations.append("胜率较高，可考虑适当增加仓位规模")
        
        # 基于最大回撤的建议
        if tracker.max_drawdown > Decimal('0.15'):
            recommendations.append("最大回撤较大，建议降低风险敞口或改进止损策略")
        elif tracker.max_drawdown < Decimal('0.05'):
            recommendations.append("风险控制良好，可以考虑增加策略复杂度")
        
        # 基于盈利因子的建议
        profit_factor = tracker.calculate_profit_factor()
        if profit_factor < Decimal('1.2'):
            recommendations.append("盈利因子较低，建议优化盈利/亏损比")
        
        # 基于交易频率的建议
        if tracker.total_trades < 10:
            recommendations.append("交易频率较低，可考虑调整策略敏感性")
        elif tracker.total_trades > 1000:
            recommendations.append("交易频率较高，注意手续费成本")
        
        # 基于夏普比率的建议
        returns = tracker._calculate_returns()
        sharpe = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
        if sharpe < Decimal('0.5'):
            recommendations.append("夏普比率较低，风险调整后收益不佳")
        elif sharpe > Decimal('2.0'):
            recommendations.append("夏普比率优秀，策略表现良好")
        
        return recommendations if recommendations else ["策略运行正常，建议继续监控"]
    
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