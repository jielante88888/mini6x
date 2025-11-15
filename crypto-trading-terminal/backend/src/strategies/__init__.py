"""
现货交易策略模块
提供网格策略、马丁格尔策略、套利策略等现货交易策略的实现
"""

from .base import (
    StrategyType,
    StrategyStatus,
    RiskLevel,
    MarketData,
    StrategyConfig,
    StrategyState,
    OrderRequest,
    OrderResult,
    SpotStrategyInterface,
    BaseSpotStrategy
)

__all__ = [
    'StrategyType',
    'StrategyStatus', 
    'RiskLevel',
    'MarketData',
    'StrategyConfig',
    'StrategyState',
    'OrderRequest',
    'OrderResult',
    'SpotStrategyInterface',
    'BaseSpotStrategy'
]

__version__ = '1.0.0'