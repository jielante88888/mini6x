"""
币安交易所适配器
支持现货和合约交易
"""

from .spot import BinanceSpotAdapter
from .futures import BinanceFuturesAdapter

__all__ = ['BinanceSpotAdapter', 'BinanceFuturesAdapter']