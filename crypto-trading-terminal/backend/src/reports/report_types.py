"""
Report data types and models for comprehensive reporting system
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Union
from enum import Enum


class ReportType(Enum):
    """Types of reports that can be generated"""
    ACCOUNT_SUMMARY = "account_summary"
    POSITION_DETAIL = "position_detail"
    PNL_ANALYSIS = "pnl_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    RISK_ASSESSMENT = "risk_assessment"
    TRADE_HISTORY = "trade_history"
    PORTFOLIO_SUMMARY = "portfolio_summary"


class ExportFormat(Enum):
    """Export formats available"""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


@dataclass
class AccountBalance:
    """Account balance information"""
    asset: str
    free_balance: Decimal
    locked_balance: Decimal
    total_balance: Decimal
    usd_value: Optional[Decimal] = None
    exchange: Optional[str] = None
    account_type: Optional[str] = None  # spot, futures


@dataclass
class Position:
    """Position information"""
    symbol: str
    exchange: str
    side: str  # long, short
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    leverage: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None
    unrealized_pnl: Decimal = Decimal("0")
    liquidation_price: Optional[Decimal] = None
    account_type: str = "spot"  # spot, futures


@dataclass
class TradeRecord:
    """Individual trade record"""
    id: str
    symbol: str
    exchange: str
    side: str  # buy, sell
    quantity: Decimal
    price: Decimal
    fee: Decimal
    timestamp: datetime
    realized_pnl: Optional[Decimal] = None
    exchange_order_id: Optional[str] = None


@dataclass
class PnLSummary:
    """PnL summary information"""
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    total_pnl: Decimal
    daily_pnl: Decimal
    weekly_pnl: Decimal
    monthly_pnl: Decimal
    win_rate: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class PerformanceMetrics:
    """Performance metrics data"""
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    annualized_return: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None


@dataclass
class RiskMetrics:
    """Risk assessment metrics"""
    value_at_risk_1d: Optional[Decimal] = None
    value_at_risk_7d: Optional[Decimal] = None
    max_position_risk: Optional[Decimal] = None
    leverage_utilization: Optional[Decimal] = None
    liquidation_risk: Optional[Decimal] = None
    concentration_risk: Optional[Decimal] = None
    overall_risk_score: Optional[Decimal] = None


@dataclass
class AccountReport:
    """Account summary report data"""
    report_id: str
    generated_at: datetime
    report_period: Dict[str, datetime]  # start_date, end_date
    accounts: List[AccountBalance]
    total_portfolio_value: Decimal
    total_daily_change: Decimal
    total_daily_change_percent: Decimal
    exchange_breakdown: Dict[str, Decimal]
    asset_allocation: Dict[str, Decimal]
    top_performers: List[Dict[str, Union[str, Decimal]]]
    top_losers: List[Dict[str, Union[str, Decimal]]]


@dataclass
class PositionReport:
    """Position detail report data"""
    report_id: str
    generated_at: datetime
    positions: List[Position]
    total_positions: int
    total_margin_used: Decimal
    total_unrealized_pnl: Decimal
    position_concentration: Dict[str, Decimal]
    leverage_distribution: Dict[str, Decimal]
    risk_distribution: Dict[str, Decimal]


@dataclass
class PnLReport:
    """PnL analysis report data"""
    report_id: str
    generated_at: datetime
    pnl_summary: PnLSummary
    pnl_by_exchange: Dict[str, Decimal]
    pnl_by_asset: Dict[str, Decimal]
    pnl_by_strategy: Optional[Dict[str, Decimal]] = None
    pnl_time_series: Optional[List[Dict[str, Union[str, Decimal]]]] = None
    best_performing_trades: List[TradeRecord] = None
    worst_performing_trades: List[TradeRecord] = None


@dataclass
class PerformanceReport:
    """Performance metrics report data"""
    report_id: str
    generated_at: datetime
    period_performance: Dict[str, PerformanceMetrics]
    benchmark_performance: Optional[PerformanceMetrics] = None
    performance_comparison: Optional[Dict[str, Decimal]] = None
    attribution_analysis: Optional[Dict[str, Decimal]] = None


@dataclass
class RiskReport:
    """Risk assessment report data"""
    report_id: str
    generated_at: datetime
    risk_metrics: RiskMetrics
    risk_by_exchange: Dict[str, RiskMetrics]
    risk_by_asset: Dict[str, RiskMetrics]
    risk_alerts: List[Dict[str, str]]
    recommendations: List[str]
    stress_test_results: Optional[Dict[str, Decimal]] = None


@dataclass
class ReportRequest:
    """Report generation request"""
    report_type: ReportType
    export_format: ExportFormat
    start_date: datetime
    end_date: datetime
    exchanges: Optional[List[str]] = None
    assets: Optional[List[str]] = None
    include_charts: bool = True
    template_id: Optional[str] = None
    custom_parameters: Optional[Dict[str, str]] = None


@dataclass
class ReportResponse:
    """Report generation response"""
    report_id: str
    file_path: str
    file_size: int
    download_url: str
    expires_at: datetime
    generation_time: float
    format: ExportFormat
    report_type: ReportType