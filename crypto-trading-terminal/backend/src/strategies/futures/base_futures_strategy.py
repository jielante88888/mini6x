"""
合约交易策略基础类
提供合约交易策略的通用接口、数据模型和基础功能
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
import uuid

# 避免循环导入，直接定义需要的枚举类型
class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PENDING = "pending"
    SUBMITTED = "submitted"

class MarketType(Enum):
    SPOT = "spot"
    FUTURES = "futures"


logger = logging.getLogger(__name__)


class ValidationException(Exception):
    """验证异常"""
    pass


class RiskManagementException(Exception):
    """风险管理异常"""
    pass


# ===== 合约特定枚举类型定义 =====

class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


class ContractType(Enum):
    """合约类型"""
    PERPETUAL = "perpetual"  # 永续合约
    DELIVERY = "delivery"    # 交割合约


class LeverageMode(Enum):
    """杠杆模式"""
    ONE_WAY = "one_way"      # 单向模式
    HEDGE = "hedge"          # 对冲模式


class FundingRateMode(Enum):
    """资金费率模式"""
    TRADING_FEE = "trading_fee"  # 交易费率模式
    INSURANCE_FUND = "insurance_fund"  # 保险基金模式


class FuturesStrategyType(Enum):
    """合约策略类型"""
    TREND_FOLLOWING = "trend_following"
    SWING = "swing"
    GRID = "grid"
    MARTINGALE = "martingale"
    ARBITRAGE = "arbitrage"
    DCA = "dollar_cost_averaging"
    SCALPING = "scalping"
    MEAN_REVERSION = "mean_reversion"


class FuturesStrategyStatus(Enum):
    """策略状态"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class FuturesRiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ===== 合约数据模型定义 =====

@dataclass
class FuturesMarketData:
    """合约市场数据模型"""
    symbol: str
    current_price: Decimal
    bid_price: Decimal
    ask_price: Decimal
    volume_24h: Decimal
    price_change_24h: Decimal
    timestamp: datetime
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    
    # 合约特定数据
    funding_rate: Decimal = Decimal('0')  # 当前资金费率
    next_funding_time: Optional[datetime] = None  # 下期资金费率结算时间
    open_interest: Decimal = Decimal('0')  # 持仓量
    implied_volatility: Optional[Decimal] = None  # 隐含波动率
    mark_price: Decimal = Decimal('0')  # 标记价格
    contract_value: Decimal = Decimal('0')  # 合约面值
    contract_size: Decimal = Decimal('0')  # 合约规模
    max_leverage: Decimal = Decimal('1')  # 最大杠杆
    liquidation_price: Optional[Decimal] = None  # 强平价格
    
    def __post_init__(self):
        if self.current_price <= 0:
            raise ValidationException("当前价格必须大于0")
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise ValidationException("买卖价格必须大于0")
        if self.bid_price > self.ask_price:
            raise ValidationException("买价不能高于卖价")


@dataclass
class FuturesPosition:
    """合约持仓信息"""
    symbol: str
    quantity: Decimal  # 正数为多头，负数为空头
    average_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    entry_price: Optional[Decimal] = None
    margin_used: Decimal = Decimal('0')
    liquidation_price: Optional[Decimal] = None
    position_side: PositionSide = PositionSide.BOTH
    contract_type: ContractType = ContractType.PERPETUAL
    leverage: Decimal = Decimal('1')
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_position_size(self) -> Decimal:
        """获取持仓规模"""
        return abs(self.quantity)
    
    def get_position_side_name(self) -> str:
        """获取持仓方向名称"""
        if self.quantity > 0:
            return "LONG"
        elif self.quantity < 0:
            return "SHORT"
        else:
            return "FLAT"
    
    def get_unrealized_pnl_percentage(self) -> Decimal:
        """获取未实现盈亏百分比"""
        if self.margin_used > 0:
            return self.unrealized_pnl / self.margin_used
        return Decimal('0')


@dataclass
class FuturesAccountBalance:
    """期货账户余额信息"""
    user_id: int
    account_id: int
    symbol: str
    wallet_balance: Decimal = Decimal('0')  # 钱包余额
    available_balance: Decimal = Decimal('0')  # 可用余额
    margin_balance: Decimal = Decimal('0')  # 保证金余额
    position_initial_margin: Decimal = Decimal('0')  # 持仓占用的初始保证金
    position_maintenance_margin: Decimal = Decimal('0')  # 持仓维持保证金
    unrealized_pnl: Decimal = Decimal('0')  # 总未实现盈亏
    realized_pnl: Decimal = Decimal('0')  # 总已实现盈亏
    total_commission: Decimal = Decimal('0')  # 总手续费
    total_funding_fee: Decimal = Decimal('0')  # 总资金费率费用
    available_margin: Decimal = Decimal('0')  # 可用保证金
    max_withdraw_amount: Decimal = Decimal('0')  # 最大可提现金额
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_total_balance(self) -> Decimal:
        """获取总余额"""
        return self.wallet_balance + self.unrealized_pnl
    
    def get_margin_ratio(self, position_value: Decimal = Decimal('0')) -> Decimal:
        """获取保证金比例"""
        if position_value > 0:
            return (self.wallet_balance / position_value) * 100
        return Decimal('0')
    
    def get_available_margin(self) -> Decimal:
        """获取可用保证金"""
        total_margin_used = self.position_initial_margin + self.position_maintenance_margin
        available = self.wallet_balance - total_margin_used + self.unrealized_pnl
        return max(available, Decimal('0'))
    
    def update_balance(self, new_wallet_balance: Decimal, new_unrealized_pnl: Decimal = None):
        """更新余额信息"""
        self.wallet_balance = new_wallet_balance
        if new_unrealized_pnl is not None:
            self.unrealized_pnl = new_unrealized_pnl
        self.available_balance = self.get_available_margin()
        self.margin_balance = self.wallet_balance + self.unrealized_pnl
        self.available_margin = self.get_available_margin()
        self.timestamp = datetime.now()


@dataclass
class FuturesStrategyConfig:
    """合约策略配置"""
    strategy_id: str
    strategy_type: FuturesStrategyType
    user_id: int
    account_id: int
    symbol: str
    base_quantity: Decimal
    
    # 杠杆设置
    leverage: Decimal = Decimal('1')
    leverage_mode: LeverageMode = LeverageMode.ONE_WAY
    max_leverage: Decimal = Decimal('20')
    position_side: PositionSide = PositionSide.BOTH
    
    # 风险控制
    max_orders: int = 100
    profit_target: Decimal = Decimal('0.02')  # 2%目标利润
    stop_loss: Decimal = Decimal('0.03')      # 3%止损
    max_daily_loss: Decimal = Decimal('0.05')  # 5%日最大亏损
    max_position_size: Decimal = Decimal('1.0')  # 最大仓位大小
    max_margin_usage: Decimal = Decimal('0.8')   # 最大保证金使用率
    
    # 合约特定参数
    max_funding_rate: Decimal = Decimal('0.01')  # 最大资金费率容忍度
    liquidation_buffer: Decimal = Decimal('0.05')  # 强平缓冲
    min_maintenance_margin: Decimal = Decimal('0.005')  # 最小维持保证金率
    
    # 趋势策略参数
    trend_period: int = 20
    trend_confirmation_periods: int = 3
    trend_strength_threshold: Decimal = Decimal('0.02')
    
    # 波动率参数
    volatility_period: int = 14
    volatility_threshold: Decimal = Decimal('0.03')
    
    # 交易设置
    min_order_size: Decimal = Decimal('0.001')
    max_order_size: Decimal = Decimal('10.0')
    order_timeout_seconds: int = 300
    max_retry_count: int = 3
    
    # 监控设置
    performance_check_interval: int = 60
    risk_check_interval: int = 30
    log_level: str = "INFO"
    
    # 状态控制
    is_active: bool = True
    is_paper_trading: bool = False
    
    # 回调函数
    order_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    performance_callback: Optional[Callable] = None
    risk_callback: Optional[Callable] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """配置验证"""
        if not self.strategy_id:
            raise ValidationException("策略ID不能为空")
        
        if self.base_quantity <= 0:
            raise ValidationException("基础交易量必须大于0")
        
        if self.leverage <= 0 or self.leverage > self.max_leverage:
            raise ValidationException(f"杠杆倍数必须在(0, {self.max_leverage}]之间")
        
        if self.profit_target <= 0 or self.profit_target > Decimal('1.0'):
            raise ValidationException("利润目标必须在(0, 100%]之间")
        
        if self.stop_loss <= 0 or self.stop_loss > Decimal('1.0'):
            raise ValidationException("止损率必须在(0, 100%]之间")
        
        if self.max_position_size <= 0:
            raise ValidationException("最大仓位大小必须大于0")
        
        if self.max_margin_usage <= 0 or self.max_margin_usage > Decimal('1.0'):
            raise ValidationException("最大保证金使用率必须在(0, 100%]之间")


@dataclass
class FuturesStrategyState:
    """合约策略状态"""
    strategy_id: str
    status: FuturesStrategyStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # 交易统计
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    failed_orders: int = 0
    
    # 盈亏统计
    total_profit: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    commission_paid: Decimal = Decimal('0')
    funding_rate_paid: Decimal = Decimal('0')  # 资金费率成本
    
    # 持仓统计
    current_position: FuturesPosition = field(default_factory=lambda: FuturesPosition("", Decimal('0'), Decimal('0')))
    max_position_size: Decimal = Decimal('0')
    total_margin_used: Decimal = Decimal('0')
    available_margin: Decimal = Decimal('0')
    
    # 风险指标
    max_drawdown: Decimal = Decimal('0')
    current_drawdown: Decimal = Decimal('0')
    daily_pnl: Decimal = Decimal('0')
    daily_trades: int = 0
    max_daily_loss_reached: bool = False
    margin_level: Decimal = Decimal('0')  # 保证金水平
    
    # 性能指标
    success_rate: Decimal = Decimal('0')
    win_rate: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    consecutive_losses: int = 0
    
    # 风险监控
    last_risk_check: Optional[datetime] = None
    liquidation_risk_level: FuturesRiskLevel = FuturesRiskLevel.LOW
    funding_rate_exposure: Decimal = Decimal('0')
    
    # 运行统计
    uptime_seconds: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    # 错误信息
    last_error: Optional[str] = None
    error_count: int = 0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_performance_metrics(self):
        """更新性能指标"""
        # 计算成功率
        if self.total_orders > 0:
            self.success_rate = Decimal(self.filled_orders) / Decimal(self.total_orders)
        
        # 计算胜率
        if self.filled_orders > 0:
            winning_trades = max(0, self.filled_orders - self.failed_orders)
            self.win_rate = Decimal(winning_trades) / Decimal(self.filled_orders)
        
        # 计算盈亏比
        if self.commission_paid > 0:
            gross_profit = self.realized_pnl + self.commission_paid
            if gross_profit > 0:
                self.profit_factor = self.realized_pnl / self.commission_paid
        
        # 计算保证金水平
        if self.total_margin_used > 0:
            self.margin_level = (self.total_margin_used + self.unrealized_pnl) / self.total_margin_used
        
        # 计算运行时间
        if self.started_at:
            self.uptime_seconds = int((datetime.now() - self.started_at).total_seconds())
        
        self.last_update = datetime.now()
    
    def is_trading_allowed(self) -> bool:
        """检查是否允许交易"""
        if self.status != FuturesStrategyStatus.RUNNING:
            return False
        
        if self.max_daily_loss_reached:
            return False
        
        if self.daily_trades >= 1000:
            return False
        
        # 检查保证金充足性
        if self.margin_level < Decimal('1.1'):  # 低于110%保证金水平
            return False
        
        return True
    
    def should_stop_loss(self) -> bool:
        """检查是否应该止损"""
        if self.stop_loss > 0 and self.current_drawdown >= self.stop_loss:
            return True
        
        # 检查保证金水平
        if self.margin_level < Decimal('1.2'):  # 低于120%保证金水平
            return True
        
        return False
    
    def should_reduce_position(self) -> bool:
        """检查是否应该减仓"""
        if self.liquidation_risk_level in [FuturesRiskLevel.HIGH, FuturesRiskLevel.CRITICAL]:
            return True
        
        if self.margin_level < Decimal('1.3'):  # 低于130%保证金水平
            return True
        
        return False
    
    def update_daily_stats(self):
        """更新日统计"""
        now = datetime.now()
        if self.started_at and now.date() != self.started_at.date():
            self.daily_pnl = Decimal('0')
            self.daily_trades = 0
            self.max_daily_loss_reached = False
    
    def update_risk_metrics(self, market_data: FuturesMarketData):
        """更新风险指标"""
        # 更新强平风险等级
        if self.current_position and self.current_position.liquidation_price:
            self._update_liquidation_risk(market_data)
        
        # 更新资金费率风险
        self._update_funding_rate_risk(market_data)
    
    def _update_liquidation_risk(self, market_data: FuturesMarketData):
        """更新强平风险"""
        if not self.current_position.liquidation_price:
            return
        
        current_price = market_data.current_price
        liquidation_price = self.current_position.liquidation_price
        
        # 计算到强平价的距离
        if self.current_position.quantity > 0:  # 多头
            distance = (current_price - liquidation_price) / current_price
        else:  # 空头
            distance = (liquidation_price - current_price) / current_price
        
        # 更新风险等级
        if distance < 0.05:  # 5%以内
            self.liquidation_risk_level = FuturesRiskLevel.CRITICAL
        elif distance < 0.1:  # 10%以内
            self.liquidation_risk_level = FuturesRiskLevel.HIGH
        elif distance < 0.2:  # 20%以内
            self.liquidation_risk_level = FuturesRiskLevel.MEDIUM
        else:
            self.liquidation_risk_level = FuturesRiskLevel.LOW
    
    def _update_funding_rate_risk(self, market_data: FuturesMarketData):
        """更新资金费率风险"""
        # 计算资金费率敞口
        if self.current_position.quantity != 0:
            position_value = abs(self.current_position.quantity) * market_data.current_price
            self.funding_rate_exposure = position_value * abs(market_data.funding_rate)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_id': self.strategy_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'total_orders': self.total_orders,
            'filled_orders': self.filled_orders,
            'success_rate': float(self.success_rate),
            'total_profit': float(self.total_profit),
            'realized_pnl': float(self.realized_pnl),
            'unrealized_pnl': float(self.unrealized_pnl),
            'current_position': {
                'symbol': self.current_position.symbol,
                'quantity': float(self.current_position.quantity),
                'side': self.current_position.get_position_side_name(),
                'margin_used': float(self.current_position.margin_used)
            },
            'max_drawdown': float(self.max_drawdown),
            'current_drawdown': float(self.current_drawdown),
            'daily_pnl': float(self.daily_pnl),
            'margin_level': float(self.margin_level),
            'liquidation_risk': self.liquidation_risk_level.value,
            'funding_rate_exposure': float(self.funding_rate_exposure),
            'uptime_seconds': self.uptime_seconds,
            'consecutive_losses': self.consecutive_losses,
            'is_trading_allowed': self.is_trading_allowed(),
            'should_stop_loss': self.should_stop_loss(),
            'should_reduce_position': self.should_reduce_position()
        }


@dataclass
class FuturesOrderRequest:
    """合约订单请求"""
    order_id: str
    symbol: str
    order_type: OrderType
    order_side: OrderSide
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None  # 止损价格
    client_order_id: Optional[str] = None
    position_side: PositionSide = PositionSide.BOTH
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())
        
        if self.quantity <= 0:
            raise ValidationException("订单数量必须大于0")
        
        if self.order_type == OrderType.LIMIT and (not self.price or self.price <= 0):
            raise ValidationException("限价单必须提供有效价格")
        
        if self.order_type == OrderType.STOP and (not self.stop_price or self.stop_price <= 0):
            raise ValidationException("止损单必须提供有效止损价格")


@dataclass
class FuturesOrderResult:
    """合约订单执行结果"""
    success: bool
    order_id: str
    filled_quantity: Decimal
    average_price: Decimal
    commission: Decimal
    execution_time: datetime
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    exchange_order_id: Optional[str] = None
    fill_time: Optional[datetime] = None
    funding_rate: Optional[Decimal] = None  # 执行时的资金费率
    
    def __post_init__(self):
        if self.filled_quantity < 0:
            raise ValidationException("成交数量不能为负数")
        
        if self.average_price < 0:
            raise ValidationException("成交价格不能为负数")
        
        if self.commission < 0:
            raise ValidationException("手续费不能为负数")


# ===== 策略接口定义 =====

class FuturesStrategyInterface(ABC):
    """合约策略接口"""
    
    def __init__(self, config: FuturesStrategyConfig):
        self.config = config
        self.state = FuturesStrategyState(
            strategy_id=config.strategy_id,
            status=FuturesStrategyStatus.CREATED,
            created_at=datetime.now()
        )
        self.order_manager = None  # Will be set after strategy initialization
        self.running_tasks: List[asyncio.Task] = []
        self.performance_history: List[Dict[str, Any]] = []
        self.order_history: List[FuturesOrderRequest] = []
        
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化策略"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """启动策略"""
        pass
    
    @abstractmethod
    async def pause(self) -> bool:
        """暂停策略"""
        pass
    
    @abstractmethod
    async def resume(self) -> bool:
        """恢复策略"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止策略"""
        pass
    
    @abstractmethod
    async def get_next_orders(self, market_data: FuturesMarketData) -> List[FuturesOrderRequest]:
        """获取下一批订单"""
        pass
    
    @abstractmethod
    async def process_order_result(self, order_result: FuturesOrderResult) -> bool:
        """处理订单执行结果"""
        pass
    
    def get_state(self) -> FuturesStrategyState:
        """获取策略状态"""
        self.state.update_performance_metrics()
        return self.state
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'total_trades': self.state.total_orders,
            'successful_trades': self.state.filled_orders,
            'success_rate': float(self.state.success_rate),
            'win_rate': float(self.state.win_rate),
            'total_pnl': float(self.state.total_profit),
            'realized_pnl': float(self.state.realized_pnl),
            'unrealized_pnl': float(self.state.unrealized_pnl),
            'funding_rate_cost': float(self.state.funding_rate_paid),
            'max_drawdown': float(self.state.max_drawdown),
            'sharpe_ratio': float(self.state.sharpe_ratio),
            'profit_factor': float(self.state.profit_factor),
            'margin_level': float(self.state.margin_level),
            'liquidation_risk': self.state.liquidation_risk_level.value,
            'consecutive_losses': self.state.consecutive_losses
        }


class BaseFuturesStrategy(FuturesStrategyInterface):
    """合约策略基类"""
    
    def __init__(self, config: FuturesStrategyConfig, order_manager: Optional[Any] = None):
        super().__init__(config)
        self.order_manager = order_manager
        self.logger = logging.getLogger(f"futures_strategy.{config.strategy_type}.{config.strategy_id}")
        
        # 性能监控
        self.performance_monitor_task: Optional[asyncio.Task] = None
        self.risk_monitor_task: Optional[asyncio.Task] = None
        
        # 市场数据缓存
        self.last_market_data: Optional[FuturesMarketData] = None
        self.market_data_history: List[FuturesMarketData] = []
        
        # 技术指标缓存
        self.technical_indicators: Dict[str, List[Decimal]] = {}
        
    async def initialize(self) -> bool:
        """初始化策略"""
        try:
            self.logger.info(f"初始化合约策略 {self.config.strategy_id}")
            self.state.status = FuturesStrategyStatus.INITIALIZING
            
            # 验证配置
            self._validate_config()
            
            # 初始化子类特定功能
            await self._initialize_specific()
            
            self.state.status = FuturesStrategyStatus.CREATED
            self.logger.info(f"合约策略 {self.config.strategy_id} 初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"合约策略初始化失败: {e}")
            self.state.status = FuturesStrategyStatus.ERROR
            self.state.last_error = str(e)
            return False
    
    async def start(self) -> bool:
        """启动策略"""
        try:
            if self.state.status != FuturesStrategyStatus.CREATED:
                self.logger.warning(f"策略状态不正确: {self.state.status}")
                return False
            
            self.logger.info(f"启动合约策略 {self.config.strategy_id}")
            
            # 启动监控任务
            self._start_monitoring_tasks()
            
            # 启动子类特定功能
            await self._start_specific()
            
            self.state.status = FuturesStrategyStatus.RUNNING
            self.state.started_at = datetime.now()
            
            self.logger.info(f"合约策略 {self.config.strategy_id} 启动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"合约策略启动失败: {e}")
            self.state.status = FuturesStrategyStatus.ERROR
            self.state.last_error = str(e)
            return False
    
    async def pause(self) -> bool:
        """暂停策略"""
        try:
            if self.state.status != FuturesStrategyStatus.RUNNING:
                return False
            
            self.logger.info(f"暂停合约策略 {self.config.strategy_id}")
            
            # 停止监控任务
            self._stop_monitoring_tasks()
            
            # 暂停子类特定功能
            await self._pause_specific()
            
            self.state.status = FuturesStrategyStatus.PAUSED
            
            self.logger.info(f"合约策略 {self.config.strategy_id} 暂停完成")
            return True
            
        except Exception as e:
            self.logger.error(f"合约策略暂停失败: {e}")
            return False
    
    async def resume(self) -> bool:
        """恢复策略"""
        try:
            if self.state.status != FuturesStrategyStatus.PAUSED:
                return False
            
            self.logger.info(f"恢复合约策略 {self.config.strategy_id}")
            
            # 恢复子类特定功能
            await self._resume_specific()
            
            # 重新启动监控
            self._start_monitoring_tasks()
            
            self.state.status = FuturesStrategyStatus.RUNNING
            
            self.logger.info(f"合约策略 {self.config.strategy_id} 恢复完成")
            return True
            
        except Exception as e:
            self.logger.error(f"合约策略恢复失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止策略"""
        try:
            if self.state.status not in [FuturesStrategyStatus.RUNNING, FuturesStrategyStatus.PAUSED]:
                return False
            
            self.logger.info(f"停止合约策略 {self.config.strategy_id}")
            
            # 停止所有任务
            await self._stop_all_tasks()
            
            # 停止子类特定功能
            await self._stop_specific()
            
            self.state.status = FuturesStrategyStatus.STOPPED
            self.state.stopped_at = datetime.now()
            self.state.update_performance_metrics()
            
            self.logger.info(f"合约策略 {self.config.strategy_id} 停止完成")
            return True
            
        except Exception as e:
            self.logger.error(f"合约策略停止失败: {e}")
            return False
    
    async def process_market_data(self, market_data: FuturesMarketData):
        """处理市场数据"""
        try:
            # 缓存市场数据
            self.last_market_data = market_data
            self.market_data_history.append(market_data)
            
            # 保持历史数据在合理范围内
            if len(self.market_data_history) > 200:
                self.market_data_history = self.market_data_history[-100:]
            
            # 更新风险指标
            self.state.update_risk_metrics(market_data)
            
            # 检查是否可以交易
            if not self.state.is_trading_allowed():
                return
            
            # 检查风险条件
            if self.state.should_stop_loss():
                self.logger.warning("达到止损条件，停止策略")
                await self.stop()
                return
            
            # 检查是否应该减仓
            if self.state.should_reduce_position():
                self.logger.info("风险较高，考虑减仓")
            
            # 获取订单建议
            orders = await self.get_next_orders(market_data)
            
            # 执行订单
            for order_request in orders:
                await self._execute_order(order_request)
            
        except Exception as e:
            self.logger.error(f"处理市场数据失败: {e}")
            self.state.error_count += 1
            self.state.last_error = str(e)
    
    async def _execute_order(self, order_request: FuturesOrderRequest) -> bool:
        """执行订单"""
        try:
            if not self.order_manager:
                self.logger.warning("订单管理器未设置，跳过订单执行")
                return False
            
            # 创建订单
            order = await self.order_manager.create_order(
                user_id=self.config.user_id,
                account_id=self.config.account_id,
                symbol=order_request.symbol,
                order_side=order_request.order_side,
                quantity=order_request.quantity,
                order_type=order_request.order_type,
                price=order_request.price,
                stop_price=order_request.stop_price,
                position_side=order_request.position_side,
                client_order_id=order_request.client_order_id
            )
            
            # 执行订单
            success = await self.order_manager.execute_order(
                order_id=order.id,
                user_id=self.config.user_id,
                account_id=self.config.account_id,
                current_price=self.last_market_data.current_price if self.last_market_data else None
            )
            
            # 处理结果
            order_result = FuturesOrderResult(
                success=success,
                order_id=order_request.order_id,
                filled_quantity=order.quantity_filled,
                average_price=order.average_price or Decimal('0'),
                commission=order.commission or Decimal('0'),
                execution_time=datetime.now(),
                funding_rate=self.last_market_data.funding_rate if self.last_market_data else None
            )
            
            await self.process_order_result(order_result)
            
            # 触发回调
            if self.config.order_callback:
                await self._safe_callback(self.config.order_callback, order_result)
            
            return success
            
        except Exception as e:
            self.logger.error(f"订单执行失败: {e}")
            self.state.error_count += 1
            self.state.last_error = str(e)
            
            # 触发错误回调
            if self.config.error_callback:
                await self._safe_callback(self.config.error_callback, str(e))
            
            return False
    
    async def _safe_callback(self, callback: Callable, *args):
        """安全执行回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.logger.error(f"回调函数执行失败: {e}")
    
    def _start_monitoring_tasks(self):
        """启动监控任务"""
        # 性能监控
        self.performance_monitor_task = asyncio.create_task(self._performance_monitoring_loop())
        
        # 风险监控
        self.risk_monitor_task = asyncio.create_task(self._risk_monitoring_loop())
        
        self.running_tasks.extend([self.performance_monitor_task, self.risk_monitor_task])
    
    def _stop_monitoring_tasks(self):
        """停止监控任务"""
        for task in [self.performance_monitor_task, self.risk_monitor_task]:
            if task and not task.done():
                task.cancel()
                self.running_tasks.remove(task)
    
    async def _stop_all_tasks(self):
        """停止所有任务"""
        # 取消所有运行中的任务
        for task in self.running_tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)
        
        self.running_tasks.clear()
        self.performance_monitor_task = None
        self.risk_monitor_task = None
    
    async def _performance_monitoring_loop(self):
        """性能监控循环"""
        while self.state.status == FuturesStrategyStatus.RUNNING:
            try:
                await asyncio.sleep(self.config.performance_check_interval)
                
                # 更新性能统计
                self.state.update_performance_metrics()
                
                # 检查性能回调
                if self.config.performance_callback:
                    await self._safe_callback(self.config.performance_callback, self.get_performance_metrics())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"性能监控错误: {e}")
    
    async def _risk_monitoring_loop(self):
        """风险监控循环"""
        while self.state.status == FuturesStrategyStatus.RUNNING:
            try:
                await asyncio.sleep(self.config.risk_check_interval)
                
                # 检查保证金水平
                if self.state.margin_level < Decimal('1.15'):  # 低于115%
                    self.logger.warning(f"保证金水平过低: {self.state.margin_level}")
                    
                    # 触发风险回调
                    if self.config.risk_callback:
                        await self._safe_callback(self.config.risk_callback, {
                            'margin_level': self.state.margin_level,
                            'liquidation_risk': self.state.liquidation_risk_level.value,
                            'action': 'margin_low'
                        })
                
                # 检查资金费率风险
                if self.last_market_data and abs(self.last_market_data.funding_rate) > self.config.max_funding_rate:
                    self.logger.warning(f"资金费率过高: {self.last_market_data.funding_rate}")
                
                # 检查日亏损限制
                if self.state.daily_pnl <= -self.config.max_daily_loss:
                    self.state.max_daily_loss_reached = True
                    self.logger.warning(f"达到日亏损限制: {self.state.daily_pnl}")
                
                # 检查连续亏损
                if self.state.consecutive_losses >= 10:
                    self.logger.warning("连续亏损次数过多，考虑暂停策略")
                
                # 更新日统计
                self.state.update_daily_stats()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"风险监控错误: {e}")
    
    def _validate_config(self):
        """验证配置"""
        if not self.config.user_id or not self.config.account_id:
            raise ValidationException("用户ID和账户ID不能为空")
        
        if self.config.min_order_size > self.config.max_order_size:
            raise ValidationException("最小订单大小不能大于最大订单大小")
        
        if self.config.leverage > self.config.max_leverage:
            raise ValidationException(f"杠杆倍数不能超过最大杠杆: {self.config.max_leverage}")
    
    async def _initialize_specific(self):
        """初始化子类特定功能"""
        pass
    
    async def _start_specific(self):
        """启动子类特定功能"""
        pass
    
    async def _pause_specific(self):
        """暂停子类特定功能"""
        pass
    
    async def _resume_specific(self):
        """恢复子类特定功能"""
        pass
    
    async def _stop_specific(self):
        """停止子类特定功能"""
        pass
    
    # 抽象方法实现
    @abstractmethod
    async def get_next_orders(self, market_data: FuturesMarketData) -> List[FuturesOrderRequest]:
        """获取下一批订单"""
        pass
    
    @abstractmethod
    async def process_order_result(self, order_result: FuturesOrderResult) -> bool:
        """处理订单执行结果"""
        pass