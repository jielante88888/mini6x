"""
OKX交易所适配器
支持现货和合约交易
"""

from .spot import OKXSpotAdapter
from .derivatives import OKXDerivativesAdapter

__all__ = ['OKXSpotAdapter', 'OKXDerivativesAdapter']