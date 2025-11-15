"""
合约交易策略模块
提供合约交易策略的通用接口、数据模型和基础功能
"""

from .base_futures_strategy import (
    FuturesMarketData, FuturesStrategyConfig, FuturesStrategyState,
    FuturesOrderRequest, FuturesOrderResult, BaseFuturesStrategy,
    PositionSide, ContractType, LeverageMode, FundingRateMode,
    ValidationException, RiskManagementException
)
from .trend import TrendFollowingStrategy
from .swing import SwingStrategy
from .funding_rate_arbitrage import FundingRateArbitrageStrategy
from .leverage_manager import (
    LeverageManager, DynamicLeverageManager, LeverageConfig, 
    PositionMetrics
)

__all__ = [
    'FuturesMarketData',
    'FuturesStrategyConfig', 
    'FuturesStrategyState',
    'FuturesOrderRequest',
    'FuturesOrderResult',
    'BaseFuturesStrategy',
    'PositionSide',
    'ContractType',
    'LeverageMode',
    'FundingRateMode',
    'ValidationException',
    'RiskManagementException',
    'TrendFollowingStrategy',
    'SwingStrategy',
    'FundingRateArbitrageStrategy',
    'LeverageManager',
    'DynamicLeverageManager',
    'LeverageConfig',
    'PositionMetrics'
]