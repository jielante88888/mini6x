"""
账户管理数据模型
提供统一的多交易所账户、持仓和盈亏分析管理功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
import uuid

from ...core.exceptions import ValidationException, StorageException


class ExchangeType(Enum):
    """交易所类型"""
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"
    FTX = "ftx"


class AccountType(Enum):
    """账户类型"""
    SPOT = "spot"
    FUTURES = "futures"
    MARGIN = "margin"
    DERIVATIVES = "derivatives"


class PositionType(Enum):
    """持仓类型"""
    SPOT = "spot"
    FUTURES = "futures"
    OPTIONS = "options"
    MARGIN = "margin"


class PnLType(Enum):
    """盈亏类型"""
    REALIZED = "realized"
    UNREALIZED = "unrealized"
    DAILY = "daily"
    TOTAL = "total"


class BalanceStatus(Enum):
    """余额状态"""
    ACTIVE = "active"
    FROZEN = "frozen"
    WITHDRAWING = "withdrawing"
    DEPOSIT_ONLY = "deposit_only"


@dataclass
class AccountBalance:
    """账户余额信息"""
    symbol: str
    free_balance: Decimal = Decimal('0')      # 可用余额
    locked_balance: Decimal = Decimal('0')    # 冻结余额
    total_balance: Decimal = Decimal('0')     # 总余额
    usdt_value: Decimal = Decimal('0')        # 折合USDT价值
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.total_balance = self.free_balance + self.locked_balance
    
    def update_balance(self, free: Decimal, locked: Decimal = Decimal('0')):
        """更新余额"""
        self.free_balance = free
        self.locked_balance = locked
        self.total_balance = free + locked
        self.last_updated = datetime.now()
    
    def get_available_balance(self) -> Decimal:
        """获取可用余额"""
        return self.free_balance
    
    def get_percentage(self, total_portfolio_value: Decimal) -> Decimal:
        """获取占总资产百分比"""
        if total_portfolio_value > 0:
            return (self.usdt_value / total_portfolio_value) * 100
        return Decimal('0')


@dataclass
class Account:
    """统一账户管理"""
    account_id: str
    user_id: int
    exchange: ExchangeType
    account_type: AccountType
    account_name: str = ""
    
    # 账户基本信息
    is_active: bool = True
    is_verified: bool = False
    max_leverage: Decimal = Decimal('1')
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    
    # 余额信息
    balances: Dict[str, AccountBalance] = field(default_factory=dict)
    
    # 统计数据
    total_balance_usdt: Decimal = Decimal('0')
    available_balance_usdt: Decimal = Decimal('0')
    daily_pnl: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    total_commission_paid: Decimal = Decimal('0')
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    last_sync_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # API配置
    api_key_configured: bool = False
    testnet_mode: bool = False
    
    def add_balance(self, symbol: str, free: Decimal, locked: Decimal = Decimal('0')):
        """添加或更新余额"""
        if symbol in self.balances:
            self.balances[symbol].update_balance(free, locked)
        else:
            self.balances[symbol] = AccountBalance(symbol=symbol, free_balance=free, locked_balance=locked)
        
        self._update_total_balances()
        self.last_updated = datetime.now()
    
    def remove_balance(self, symbol: str):
        """移除余额"""
        if symbol in self.balances:
            del self.balances[symbol]
            self._update_total_balances()
    
    def get_balance(self, symbol: str) -> Optional[AccountBalance]:
        """获取特定币种余额"""
        return self.balances.get(symbol)
    
    def get_all_balances(self) -> List[AccountBalance]:
        """获取所有余额"""
        return list(self.balances.values())
    
    def get_non_zero_balances(self) -> List[AccountBalance]:
        """获取非零余额"""
        return [balance for balance in self.balances.values() if balance.total_balance > 0]
    
    def _update_total_balances(self):
        """更新总余额统计"""
        self.total_balance_usdt = sum(balance.usdt_value for balance in self.balances.values())
        self.available_balance_usdt = sum(balance.free_balance for balance in self.balances.values())
    
    def update_usdt_values(self, market_prices: Dict[str, Decimal]):
        """更新USDT估值"""
        for symbol, balance in self.balances.items():
            if symbol == 'USDT':
                balance.usdt_value = balance.total_balance
            else:
                price = market_prices.get(f"{symbol}USDT", market_prices.get(f"USDT{symbol}", Decimal('0')))
                if price > 0:
                    balance.usdt_value = balance.total_balance * price
        
        self._update_total_balances()
    
    def get_portfolio_diversification(self) -> Dict[str, Any]:
        """获取投资组合分散度"""
        non_zero_balances = self.get_non_zero_balances()
        if not non_zero_balances:
            return {'diversification_score': 0, 'top_holdings': []}
        
        total_value = sum(balance.usdt_value for balance in non_zero_balances)
        if total_value == 0:
            return {'diversification_score': 0, 'top_holdings': []}
        
        # 计算各资产占比
        holdings = []
        for balance in non_zero_balances:
            percentage = (balance.usdt_value / total_value) * 100
            holdings.append({
                'symbol': balance.symbol,
                'value': balance.usdt_value,
                'percentage': percentage,
                'balance': balance.total_balance
            })
        
        # 按价值排序
        holdings.sort(key=lambda x: x['value'], reverse=True)
        
        # 计算多样化评分（赫芬达尔指数的反面）
        hhi = sum((holding['percentage'] / 100) ** 2 for holding in holdings)
        diversification_score = max(0, 1 - hhi)
        
        return {
            'diversification_score': diversification_score,
            'total_holdings': len(holdings),
            'top_holdings': holdings[:5],
            'largest_position_pct': holdings[0]['percentage'] if holdings else 0
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        non_zero_balances = self.get_non_zero_balances()
        if not non_zero_balances:
            return {'risk_score': 0, 'risk_level': 'LOW', 'concentration_risk': 'LOW'}
        
        # 集中度风险
        total_value = sum(balance.usdt_value for balance in non_zero_balances)
        if total_value == 0:
            return {'risk_score': 0, 'risk_level': 'LOW', 'concentration_risk': 'LOW'}
        
        # 单一资产最大占比
        max_concentration = max(balance.usdt_value / total_value for balance in non_zero_balances)
        
        concentration_risk = 'LOW'
        if max_concentration > 0.8:
            concentration_risk = 'HIGH'
        elif max_concentration > 0.5:
            concentration_risk = 'MEDIUM'
        
        # 计算风险评分
        risk_score = max_concentration * 100
        
        # 确定风险等级
        risk_level = 'LOW'
        if risk_score > 70:
            risk_level = 'HIGH'
        elif risk_score > 40:
            risk_level = 'MEDIUM'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'concentration_risk': concentration_risk,
            'max_concentration_pct': max_concentration * 100,
            'total_positions': len(non_zero_balances),
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'account_id': self.account_id,
            'user_id': self.user_id,
            'exchange': self.exchange.value,
            'account_type': self.account_type.value,
            'account_name': self.account_name,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'max_leverage': float(self.max_leverage),
            'risk_level': self.risk_level,
            'balances': {symbol: {
                'symbol': balance.symbol,
                'free_balance': float(balance.free_balance),
                'locked_balance': float(balance.locked_balance),
                'total_balance': float(balance.total_balance),
                'usdt_value': float(balance.usdt_value),
                'last_updated': balance.last_updated.isoformat()
            } for symbol, balance in self.balances.items()},
            'total_balance_usdt': float(self.total_balance_usdt),
            'available_balance_usdt': float(self.available_balance_usdt),
            'daily_pnl': float(self.daily_pnl),
            'total_pnl': float(self.total_pnl),
            'total_commission_paid': float(self.total_commission_paid),
            'created_at': self.created_at.isoformat(),
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_updated': self.last_updated.isoformat(),
            'api_key_configured': self.api_key_configured,
            'testnet_mode': self.testnet_mode
        }


@dataclass
class Position:
    """统一持仓管理"""
    position_id: str
    account_id: str
    symbol: str
    position_type: PositionType
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal = Decimal('0')
    
    # 持仓信息
    side: str = "LONG"  # LONG, SHORT, BOTH
    leverage: Decimal = Decimal('1')
    margin_used: Decimal = Decimal('0')
    
    # 盈亏信息
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    funding_fee: Decimal = Decimal('0')
    commission_paid: Decimal = Decimal('0')
    
    # 风险信息
    liquidation_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    
    # 合约特定信息（仅合约持仓）
    contract_value: Decimal = Decimal('1')
    maintenance_margin: Decimal = Decimal('0')
    position_initial_margin: Decimal = Decimal('0')
    position_maintenance_margin: Decimal = Decimal('0')
    
    # 时间戳
    opened_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_current_price(self, new_price: Decimal):
        """更新当前价格和未实现盈亏"""
        if new_price <= 0:
            raise ValidationException("价格必须大于0")
        
        old_price = self.current_price
        self.current_price = new_price
        self._calculate_unrealized_pnl()
        self.last_updated = datetime.now()
    
    def _calculate_unrealized_pnl(self):
        """计算未实现盈亏"""
        if self.position_type == PositionType.SPOT:
            if self.quantity > 0:
                # 多头现货
                self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
            else:
                # 空头现货（如果支持）
                self.unrealized_pnl = (self.entry_price - self.current_price) * abs(self.quantity)
        else:
            # 合约持仓
            if self.side == "LONG":
                self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity * self.contract_value
            else:  # SHORT
                self.unrealized_pnl = (self.entry_price - self.current_price) * abs(self.quantity) * self.contract_value
    
    def get_position_value(self) -> Decimal:
        """获取持仓价值"""
        return abs(self.quantity) * self.current_price
    
    def get_leverage_ratio(self) -> Decimal:
        """获取实际杠杆比例"""
        if self.margin_used > 0:
            return self.get_position_value() / self.margin_used
        return Decimal('1')
    
    def get_pnl_percentage(self) -> Decimal:
        """获取盈亏百分比"""
        if self.entry_price > 0:
            if self.position_type == PositionType.SPOT:
                return ((self.current_price - self.entry_price) / self.entry_price) * 100
            else:
                # 合约：考虑杠杆效应
                return self.get_leverage_ratio() * ((self.current_price - self.entry_price) / self.entry_price) * 100
        return Decimal('0')
    
    def get_margin_level(self) -> Decimal:
        """获取保证金水平"""
        if self.margin_used > 0:
            total_margin = self.margin_used + self.unrealized_pnl
            if total_margin >= 0:
                return (self.margin_used + abs(self.unrealized_pnl)) / self.margin_used
            else:
                return Decimal('0')
        return Decimal('0')
    
    def get_risk_assessment(self) -> Dict[str, Any]:
        """获取风险评估"""
        risk_level = "LOW"
        risk_score = 0
        
        # 保证金水平风险
        margin_level = self.get_margin_level()
        if margin_level < 1.1:  # 110%
            risk_level = "CRITICAL"
            risk_score = 100
        elif margin_level < 1.2:  # 120%
            risk_level = "HIGH"
            risk_score = 80
        elif margin_level < 1.3:  # 130%
            risk_level = "MEDIUM"
            risk_score = 50
        elif margin_level < 1.5:  # 150%
            risk_level = "LOW"
            risk_score = 20
        
        # 杠杆风险
        current_leverage = self.get_leverage_ratio()
        if current_leverage > 20:
            risk_score = min(100, risk_score + 20)
        elif current_leverage > 10:
            risk_score = min(100, risk_score + 10)
        
        # 流动性风险（基于价格变化幅度）
        if self.current_price > 0 and self.entry_price > 0:
            price_change = abs((self.current_price - self.entry_price) / self.entry_price)
            if price_change > 0.5:  # 50%价格变化
                risk_score = min(100, risk_score + 15)
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'margin_level': margin_level,
            'leverage_ratio': current_leverage,
            'unrealized_pnl_pct': self.get_pnl_percentage(),
            'position_value': self.get_position_value(),
            'total_pnl': self.unrealized_pnl + self.realized_pnl,
            'liquidation_distance': self._calculate_liquidation_distance()
        }
    
    def _calculate_liquidation_distance(self) -> Decimal:
        """计算到强平价的距离百分比"""
        if not self.liquidation_price or self.current_price <= 0:
            return Decimal('100')
        
        if self.side == "LONG":
            distance = (self.current_price - self.liquidation_price) / self.current_price
        else:  # SHORT
            distance = (self.liquidation_price - self.current_price) / self.current_price
        
        return distance * 100
    
    def should_add_margin(self) -> bool:
        """是否需要追加保证金"""
        return self.get_margin_level() < 1.2  # 120%以下需要关注
    
    def should_close_position(self) -> bool:
        """是否应该平仓"""
        return self.get_margin_level() < 1.1  # 110%以下建议平仓
    
    def close_position(self, close_price: Decimal, quantity: Optional[Decimal] = None) -> Dict[str, Any]:
        """平仓"""
        close_quantity = quantity or abs(self.quantity)
        
        if close_quantity > abs(self.quantity):
            raise ValidationException("平仓数量不能超过持仓数量")
        
        # 计算平仓盈亏
        if self.side == "LONG":
            pnl_per_unit = (close_price - self.entry_price) * self.contract_value
        else:  # SHORT
            pnl_per_unit = (self.entry_price - close_price) * self.contract_value
        
        realized_pnl = pnl_per_unit * close_quantity
        
        # 更新持仓
        if close_quantity == abs(self.quantity):
            # 完全平仓
            self.realized_pnl += realized_pnl
            self.quantity = Decimal('0')
        else:
            # 部分平仓
            self.realized_pnl += realized_pnl
            self.quantity = self.quantity - (close_quantity if self.quantity > 0 else -close_quantity)
        
        self.last_updated = datetime.now()
        
        return {
            'close_quantity': close_quantity,
            'close_price': close_price,
            'realized_pnl': realized_pnl,
            'remaining_quantity': self.quantity,
            'total_realized_pnl': self.realized_pnl
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'position_id': self.position_id,
            'account_id': self.account_id,
            'symbol': self.symbol,
            'position_type': self.position_type.value,
            'quantity': float(self.quantity),
            'entry_price': float(self.entry_price),
            'current_price': float(self.current_price),
            'side': self.side,
            'leverage': float(self.leverage),
            'margin_used': float(self.margin_used),
            'unrealized_pnl': float(self.unrealized_pnl),
            'realized_pnl': float(self.realized_pnl),
            'funding_fee': float(self.funding_fee),
            'commission_paid': float(self.commission_paid),
            'liquidation_price': float(self.liquidation_price) if self.liquidation_price else None,
            'stop_loss_price': float(self.stop_loss_price) if self.stop_loss_price else None,
            'take_profit_price': float(self.take_profit_price) if self.take_profit_price else None,
            'contract_value': float(self.contract_value),
            'maintenance_margin': float(self.maintenance_margin),
            'position_initial_margin': float(self.position_initial_margin),
            'position_maintenance_margin': float(self.position_maintenance_margin),
            'opened_at': self.opened_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'position_value': float(self.get_position_value()),
            'leverage_ratio': float(self.get_leverage_ratio()),
            'pnl_percentage': float(self.get_pnl_percentage()),
            'margin_level': float(self.get_margin_level()),
            'risk_assessment': self.get_risk_assessment()
        }


@dataclass
class PnLRecord:
    """盈亏记录"""
    record_id: str
    account_id: str
    position_id: Optional[str]
    symbol: str
    pnl_type: PnLType
    
    # 盈亏金额
    pnl_amount: Decimal
    pnl_percentage: Decimal = Decimal('0')
    
    # 基础信息
    base_amount: Decimal = Decimal('0')  # 计算盈亏的基数（如投入本金）
    quantity: Decimal = Decimal('0')     # 涉及数量
    
    # 时间信息
    period_start: datetime
    period_end: datetime
    recorded_at: datetime = field(default_factory=datetime.now)
    
    # 详细信息
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    commission: Decimal = Decimal('0')
    funding_fee: Decimal = Decimal('0')
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_net_pnl(self) -> Decimal:
        """获取净盈亏（扣除费用）"""
        return self.pnl_amount - self.commission - self.funding_fee
    
    def get_pnl_with_fees(self) -> Decimal:
        """获取包含费用的盈亏"""
        return self.pnl_amount - self.commission - self.funding_fee
    
    def get_roi(self) -> Decimal:
        """计算投资回报率"""
        if self.base_amount > 0:
            return (self.get_net_pnl() / self.base_amount) * 100
        return Decimal('0')
    
    def get_cost_basis(self) -> Decimal:
        """获取成本基数"""
        if self.quantity > 0 and self.entry_price:
            return self.entry_price * self.quantity
        return self.base_amount
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'record_id': self.record_id,
            'account_id': self.account_id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'pnl_type': self.pnl_type.value,
            'pnl_amount': float(self.pnl_amount),
            'pnl_percentage': float(self.pnl_percentage),
            'base_amount': float(self.base_amount),
            'quantity': float(self.quantity),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'recorded_at': self.recorded_at.isoformat(),
            'entry_price': float(self.entry_price) if self.entry_price else None,
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'commission': float(self.commission),
            'funding_fee': float(self.funding_fee),
            'net_pnl': float(self.get_net_pnl()),
            'roi': float(self.get_roi()),
            'cost_basis': float(self.get_cost_basis()),
            'metadata': self.metadata
        }


@dataclass
class PnLSummary:
    """盈亏汇总"""
    account_id: str
    summary_period: str  # daily, weekly, monthly, yearly, all
    
    # 基本统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    
    # 盈亏统计
    total_realized_pnl: Decimal = Decimal('0')
    total_unrealized_pnl: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    
    # 费用统计
    total_commission: Decimal = Decimal('0')
    total_funding_fee: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    
    # 性能指标
    win_rate: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')
    largest_win: Decimal = Decimal('0')
    largest_loss: Decimal = Decimal('0')
    
    # 风险指标
    max_drawdown: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    total_return_pct: Decimal = Decimal('0')
    
    # 时间信息
    period_start: datetime
    period_end: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def calculate_performance_metrics(self):
        """计算性能指标"""
        # 计算胜率
        if self.total_trades > 0:
            self.win_rate = (Decimal(self.winning_trades) / Decimal(self.total_trades)) * 100
        
        # 计算盈亏比
        total_wins = self.total_realized_pnl if self.total_realized_pnl > 0 else Decimal('0')
        total_losses = abs(self.total_realized_pnl) if self.total_realized_pnl < 0 else Decimal('0')
        
        if total_losses > 0:
            self.profit_factor = total_wins / total_losses
        
        # 计算平均盈亏
        if self.winning_trades > 0:
            self.average_win = self.total_realized_pnl / Decimal(self.winning_trades)
        
        if self.losing_trades > 0:
            self.average_loss = total_losses / Decimal(self.losing_trades)
        
        # 计算总回报率
        if self.total_fees > 0:
            net_pnl = self.total_pnl - self.total_fees
            if net_pnl > 0:
                self.total_return_pct = (net_pnl / (net_pnl - self.total_pnl)) * 100 if (net_pnl - self.total_pnl) != 0 else Decimal('0')
    
    def get_performance_grade(self) -> str:
        """获取性能评级"""
        if self.total_return_pct > 50:
            return "A+"
        elif self.total_return_pct > 25:
            return "A"
        elif self.total_return_pct > 10:
            return "B+"
        elif self.total_return_pct > 0:
            return "B"
        elif self.total_return_pct > -10:
            return "C"
        else:
            return "D"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'account_id': self.account_id,
            'summary_period': self.summary_period,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'breakeven_trades': self.breakeven_trades,
            'total_realized_pnl': float(self.total_realized_pnl),
            'total_unrealized_pnl': float(self.total_unrealized_pnl),
            'total_pnl': float(self.total_pnl),
            'total_commission': float(self.total_commission),
            'total_funding_fee': float(self.total_funding_fee),
            'total_fees': float(self.total_fees),
            'win_rate': float(self.win_rate),
            'profit_factor': float(self.profit_factor),
            'average_win': float(self.average_win),
            'average_loss': float(self.average_loss),
            'largest_win': float(self.largest_win),
            'largest_loss': float(self.largest_loss),
            'max_drawdown': float(self.max_drawdown),
            'sharpe_ratio': float(self.sharpe_ratio),
            'total_return_pct': float(self.total_return_pct),
            'performance_grade': self.get_performance_grade(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }


class AccountManager:
    """账户管理器"""
    
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.positions: Dict[str, Position] = {}
        self.pnl_records: Dict[str, List[PnLRecord]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def create_account(
        self,
        user_id: int,
        exchange: ExchangeType,
        account_type: AccountType,
        account_name: str = ""
    ) -> Account:
        """创建账户"""
        try:
            account_id = str(uuid.uuid4())
            
            account = Account(
                account_id=account_id,
                user_id=user_id,
                exchange=exchange,
                account_type=account_type,
                account_name=account_name
            )
            
            self.accounts[account_id] = account
            self.pnl_records[account_id] = []
            
            self.logger.info(f"创建账户成功: {account_id} ({exchange.value} {account_type.value})")
            return account
            
        except Exception as e:
            self.logger.error(f"创建账户失败: {e}")
            raise StorageException(f"创建账户失败: {e}")
    
    async def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        return self.accounts.get(account_id)
    
    async def get_user_accounts(self, user_id: int) -> List[Account]:
        """获取用户的所有账户"""
        return [account for account in self.accounts.values() if account.user_id == user_id]
    
    async def update_account_balance(
        self,
        account_id: str,
        symbol: str,
        free_balance: Decimal,
        locked_balance: Decimal = Decimal('0')
    ) -> bool:
        """更新账户余额"""
        try:
            account = self.accounts.get(account_id)
            if not account:
                raise ValidationException(f"账户不存在: {account_id}")
            
            account.add_balance(symbol, free_balance, locked_balance)
            return True
            
        except Exception as e:
            self.logger.error(f"更新账户余额失败: {e}")
            return False
    
    async def create_position(
        self,
        account_id: str,
        symbol: str,
        position_type: PositionType,
        quantity: Decimal,
        entry_price: Decimal,
        side: str = "LONG",
        leverage: Decimal = Decimal('1')
    ) -> Position:
        """创建持仓"""
        try:
            position_id = str(uuid.uuid4())
            
            position = Position(
                position_id=position_id,
                account_id=account_id,
                symbol=symbol,
                position_type=position_type,
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,  # 初始等于入场价
                side=side,
                leverage=leverage
            )
            
            # 计算保证金
            if position_type != PositionType.SPOT:
                position_value = abs(quantity) * entry_price * position.contract_value
                position.margin_used = position_value / leverage
            
            self.positions[position_id] = position
            
            self.logger.info(f"创建持仓成功: {position_id} {symbol} {quantity}@{entry_price}")
            return position
            
        except Exception as e:
            self.logger.error(f"创建持仓失败: {e}")
            raise StorageException(f"创建持仓失败: {e}")
    
    async def get_account_positions(self, account_id: str) -> List[Position]:
        """获取账户的所有持仓"""
        return [pos for pos in self.positions.values() if pos.account_id == account_id]
    
    async def update_position_price(self, position_id: str, new_price: Decimal) -> bool:
        """更新持仓价格"""
        try:
            position = self.positions.get(position_id)
            if not position:
                return False
            
            position.update_current_price(new_price)
            return True
            
        except Exception as e:
            self.logger.error(f"更新持仓价格失败: {e}")
            return False
    
    async def create_pnl_record(
        self,
        account_id: str,
        symbol: str,
        pnl_type: PnLType,
        pnl_amount: Decimal,
        period_start: datetime,
        period_end: datetime,
        **kwargs
    ) -> PnLRecord:
        """创建盈亏记录"""
        try:
            record_id = str(uuid.uuid4())
            
            record = PnLRecord(
                record_id=record_id,
                account_id=account_id,
                position_id=kwargs.get('position_id'),
                symbol=symbol,
                pnl_type=pnl_type,
                pnl_amount=pnl_amount,
                pnl_percentage=kwargs.get('pnl_percentage', Decimal('0')),
                base_amount=kwargs.get('base_amount', Decimal('0')),
                quantity=kwargs.get('quantity', Decimal('0')),
                period_start=period_start,
                period_end=period_end,
                entry_price=kwargs.get('entry_price'),
                exit_price=kwargs.get('exit_price'),
                commission=kwargs.get('commission', Decimal('0')),
                funding_fee=kwargs.get('funding_fee', Decimal('0')),
                metadata=kwargs.get('metadata', {})
            )
            
            if account_id not in self.pnl_records:
                self.pnl_records[account_id] = []
            
            self.pnl_records[account_id].append(record)
            
            self.logger.info(f"创建盈亏记录成功: {record_id} {symbol} {pnl_amount}")
            return record
            
        except Exception as e:
            self.logger.error(f"创建盈亏记录失败: {e}")
            raise StorageException(f"创建盈亏记录失败: {e}")
    
    async def get_pnl_summary(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime,
        period_type: str = "daily"
    ) -> PnLSummary:
        """获取盈亏汇总"""
        try:
            records = self.pnl_records.get(account_id, [])
            
            # 筛选时间段内的记录
            period_records = [
                record for record in records
                if period_start <= record.recorded_at <= period_end
            ]
            
            # 创建汇总
            summary = PnLSummary(
                account_id=account_id,
                summary_period=period_type,
                period_start=period_start,
                period_end=period_end
            )
            
            # 统计交易数量
            summary.total_trades = len(period_records)
            for record in period_records:
                if record.pnl_amount > 0:
                    summary.winning_trades += 1
                elif record.pnl_amount < 0:
                    summary.losing_trades += 1
                else:
                    summary.breakeven_trades += 1
            
            # 统计盈亏
            for record in period_records:
                summary.total_pnl += record.pnl_amount
                summary.total_commission += record.commission
                summary.total_funding_fee += record.funding_fee
                
                if record.pnl_type == PnLType.REALIZED:
                    summary.total_realized_pnl += record.pnl_amount
                elif record.pnl_type == PnLType.UNREALIZED:
                    summary.total_unrealized_pnl += record.pnl_amount
            
            summary.total_fees = summary.total_commission + summary.total_funding_fee
            
            # 计算性能指标
            summary.calculate_performance_metrics()
            
            return summary
            
        except Exception as e:
            self.logger.error(f"获取盈亏汇总失败: {e}")
            raise StorageException(f"获取盈亏汇总失败: {e}")
    
    async def get_portfolio_overview(self, user_id: int) -> Dict[str, Any]:
        """获取投资组合总览"""
        try:
            user_accounts = await self.get_user_accounts(user_id)
            
            total_balance = Decimal('0')
            total_pnl = Decimal('0')
            account_summaries = []
            
            for account in user_accounts:
                # 账户余额汇总
                account_balance = account.total_balance_usdt
                account_pnl = account.daily_pnl
                
                total_balance += account_balance
                total_pnl += account_pnl
                
                # 持仓汇总
                positions = await self.get_account_positions(account.account_id)
                
                position_summaries = []
                for position in positions:
                    position_summaries.append({
                        'position_id': position.position_id,
                        'symbol': position.symbol,
                        'quantity': float(position.quantity),
                        'entry_price': float(position.entry_price),
                        'current_price': float(position.current_price),
                        'unrealized_pnl': float(position.unrealized_pnl),
                        'position_value': float(position.get_position_value()),
                        'pnl_percentage': float(position.get_pnl_percentage()),
                        'risk_level': position.get_risk_assessment()['risk_level']
                    })
                
                account_summaries.append({
                    'account_id': account.account_id,
                    'exchange': account.exchange.value,
                    'account_type': account.account_type.value,
                    'balance_usdt': float(account_balance),
                    'daily_pnl': float(account_pnl),
                    'total_pnl': float(account.total_pnl),
                    'positions': position_summaries,
                    'risk_level': account.get_risk_metrics()['risk_level']
                })
            
            return {
                'user_id': user_id,
                'total_accounts': len(user_accounts),
                'total_balance_usdt': float(total_balance),
                'total_pnl': float(total_pnl),
                'pnl_percentage': float((total_pnl / total_balance) * 100) if total_balance > 0 else 0,
                'accounts': account_summaries,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取投资组合总览失败: {e}")
            raise StorageException(f"获取投资组合总览失败: {e}")


# 全局账户管理器实例
account_manager = AccountManager()