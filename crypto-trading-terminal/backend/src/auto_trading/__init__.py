"""自动交易模块

包含自动交易相关的服务类，包括风险检查、订单管理、执行引擎、仓位管理等功能
"""

from .risk_checker import RiskCheckerService, RiskCheckResult
from .order_manager import OrderManager
from .execution_engine import (
    ExecutionEngine, HighPerformanceExecutionEngine, ExecutionRequest, 
    ExecutionResult, ExecutionConfig, RetryStrategy
)
from .position_manager import (
    PositionManager, PositionRiskMetrics, PositionRiskLevel,
    StopLossConfig, TakeProfitConfig
)

__all__ = [
    'RiskCheckerService',
    'RiskCheckResult',
    'OrderManager',
    'ExecutionEngine',
    'HighPerformanceExecutionEngine',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionConfig',
    'RetryStrategy',
    'PositionManager',
    'PositionRiskMetrics',
    'PositionRiskLevel',
    'StopLossConfig',
    'TakeProfitConfig'
]