"""
现货交易策略基础类
提供现货交易策略的通用接口、数据模型和基础功能
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


# ===== 枚举类型定义 =====

class StrategyType(Enum):
    """策略类型"""
    GRID = "grid"
    MARTINGALE = "martingale"
    ARBITRAGE = "arbitrage"
    DCA = "dollar_cost_averaging"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"
    SWING = "swing"


class StrategyStatus(Enum):
    """策略状态"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ===== 数据模型定义 =====

@dataclass
class MarketData:
    """市场数据模型"""
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
    
    def __post_init__(self):
        if self.current_price <= 0:
            raise ValidationException("当前价格必须大于0")
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise ValidationException("买卖价格必须大于0")
        if self.bid_price > self.ask_price:
            raise ValidationException("买价不能高于卖价")


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    strategy_type: StrategyType
    user_id: int
    account_id: int
    symbol: str
    base_quantity: Decimal
    
    # 风险控制
    max_orders: int = 100
    profit_target: Decimal = Decimal('0.01')  # 1%目标利润
    stop_loss: Decimal = Decimal('0.05')      # 5%止损
    max_daily_loss: Decimal = Decimal('0.1')  # 10%日最大亏损
    max_position_size: Decimal = Decimal('1.0')  # 最大仓位大小
    
    # 策略特定参数
    grid_levels: int = 10                     # 网格层数
    grid_spacing: Decimal = Decimal('0.02')   # 网格间距
    martingale_multiplier: Decimal = Decimal('2.0')  # 马丁格尔倍数
    max_martingale_steps: int = 5             # 最大马丁格尔步数
    arbitrage_threshold: Decimal = Decimal('0.005')  # 套利阈值
    dca_interval_hours: int = 24              # 定投间隔
    trend_period: int = 20                    # 趋势周期
    mean_reversion_period: int = 14           # 均值回归周期
    
    # 交易设置
    min_order_size: Decimal = Decimal('0.001')
    max_order_size: Decimal = Decimal('10.0')
    order_timeout_seconds: int = 300          # 5分钟
    max_retry_count: int = 3
    
    # 监控设置
    performance_check_interval: int = 60      # 60秒检查一次
    risk_check_interval: int = 30             # 30秒风险检查一次
    log_level: str = "INFO"
    
    # 状态控制
    is_active: bool = True
    is_paper_trading: bool = False           # 模拟交易模式
    
    # 回调函数
    order_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    performance_callback: Optional[Callable] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """配置验证"""
        if not self.strategy_id:
            raise ValidationException("策略ID不能为空")
        
        if self.base_quantity <= 0:
            raise ValidationException("基础交易量必须大于0")
        
        if self.profit_target <= 0 or self.profit_target > Decimal('1.0'):
            raise ValidationException("利润目标必须在(0, 100%]之间")
        
        if self.stop_loss <= 0 or self.stop_loss > Decimal('1.0'):
            raise ValidationException("止损率必须在(0, 100%]之间")
        
        if self.max_position_size <= 0:
            raise ValidationException("最大仓位大小必须大于0")
        
        # 验证策略特定参数
        if self.strategy_type == StrategyType.GRID:
            if self.grid_levels <= 0:
                raise ValidationException("网格层数必须大于0")
            if self.grid_spacing <= 0:
                raise ValidationException("网格间距必须大于0")
        
        elif self.strategy_type == StrategyType.MARTINGALE:
            if self.martingale_multiplier <= Decimal('1.0'):
                raise ValidationException("马丁格尔倍数必须大于1")
            if self.max_martingale_steps <= 0:
                raise ValidationException("最大马丁格尔步数必须大于0")
        
        elif self.strategy_type == StrategyType.ARBITRAGE:
            if self.arbitrage_threshold <= 0:
                raise ValidationException("套利阈值必须大于0")


@dataclass
class StrategyState:
    """策略状态"""
    strategy_id: str
    status: StrategyStatus
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
    
    # 仓位统计
    current_position: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')
    entry_price: Optional[Decimal] = None
    
    # 性能指标
    success_rate: Decimal = Decimal('0')
    win_rate: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    current_drawdown: Decimal = Decimal('0')
    
    # 风险指标
    daily_pnl: Decimal = Decimal('0')
    daily_trades: int = 0
    max_daily_loss_reached: bool = False
    
    # 性能监控
    last_performance_check: Optional[datetime] = None
    last_risk_check: Optional[datetime] = None
    consecutive_losses: int = 0
    
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
        
        # 计算胜率（简化计算）
        if self.filled_orders > 0:
            winning_trades = max(0, self.filled_orders - self.failed_orders)
            self.win_rate = Decimal(winning_trades) / Decimal(self.filled_orders)
        
        # 计算盈亏比
        if self.commission_paid > 0:
            gross_profit = self.realized_pnl + self.commission_paid
            if gross_profit > 0:
                self.profit_factor = self.realized_pnl / self.commission_paid
        
        # 计算运行时间
        if self.started_at:
            self.uptime_seconds = int((datetime.now() - self.started_at).total_seconds())
        
        self.last_update = datetime.now()
    
    def is_trading_allowed(self) -> bool:
        """检查是否允许交易"""
        if self.status != StrategyStatus.RUNNING:
            return False
        
        if self.max_daily_loss_reached:
            return False
        
        if self.daily_trades >= 1000:  # 防止过度交易
            return False
        
        return True
    
    def should_stop_loss(self) -> bool:
        """检查是否应该止损"""
        if self.stop_loss > 0 and self.current_drawdown >= self.stop_loss:
            return True
        
        return False
    
    def update_daily_stats(self):
        """更新日统计"""
        # 重置日统计（如果跨天了）
        now = datetime.now()
        if self.started_at and now.date() != self.started_at.date():
            self.daily_pnl = Decimal('0')
            self.daily_trades = 0
            self.max_daily_loss_reached = False
    
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
            'current_position': float(self.current_position),
            'average_price': float(self.average_price),
            'max_drawdown': float(self.max_drawdown),
            'current_drawdown': float(self.current_drawdown),
            'daily_pnl': float(self.daily_pnl),
            'uptime_seconds': self.uptime_seconds,
            'consecutive_losses': self.consecutive_losses,
            'is_trading_allowed': self.is_trading_allowed(),
            'should_stop_loss': self.should_stop_loss()
        }


@dataclass
class OrderRequest:
    """订单请求"""
    order_id: str
    symbol: str
    order_type: OrderType
    order_side: OrderSide
    quantity: Decimal
    price: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())
        
        if self.quantity <= 0:
            raise ValidationException("订单数量必须大于0")
        
        if self.order_type == OrderType.LIMIT and (not self.price or self.price <= 0):
            raise ValidationException("限价单必须提供有效价格")


@dataclass
class OrderResult:
    """订单执行结果"""
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
    
    def __post_init__(self):
        if self.filled_quantity < 0:
            raise ValidationException("成交数量不能为负数")
        
        if self.average_price < 0:
            raise ValidationException("成交价格不能为负数")
        
        if self.commission < 0:
            raise ValidationException("手续费不能为负数")


# ===== 策略接口定义 =====

class SpotStrategyInterface(ABC):
    """现货策略接口"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = StrategyState(
            strategy_id=config.strategy_id,
            status=StrategyStatus.CREATED,
            created_at=datetime.now()
        )
        self.order_manager = None  # Will be set after strategy initialization
        self.running_tasks: List[asyncio.Task] = []
        self.performance_history: List[Dict[str, Any]] = []
        self.order_history: List[OrderRequest] = []
        
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
    async def get_next_orders(self, market_data: MarketData) -> List[OrderRequest]:
        """获取下一批订单"""
        pass
    
    @abstractmethod
    async def process_order_result(self, order_result: OrderResult) -> bool:
        """处理订单执行结果"""
        pass
    
    def get_state(self) -> StrategyState:
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
            'max_drawdown': float(self.state.max_drawdown),
            'sharpe_ratio': float(self.state.sharpe_ratio),
            'profit_factor': float(self.state.profit_factor),
            'consecutive_losses': self.state.consecutive_losses
        }
    
    def update_state_after_order(self, order_result: OrderResult, market_data: Optional[MarketData] = None):
        """更新策略状态（订单执行后）"""
        self.state.total_orders += 1
        
        if order_result.success:
            self.state.filled_orders += 1
            
            # 更新盈亏
            if market_data:
                # 简化计算：基于当前市场价格计算未实现盈亏
                current_value = order_result.filled_quantity * market_data.current_price
                cost_value = order_result.filled_quantity * order_result.average_price
                self.state.unrealized_pnl = current_value - cost_value
            
            self.state.realized_pnl += order_result.average_price * order_result.filled_quantity - order_result.commission
            self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
            self.state.commission_paid += order_result.commission
            
        else:
            self.state.failed_orders += 1
        
        # 更新性能指标
        self.state.update_performance_metrics()
        
        # 记录历史
        self.performance_history.append({
            'timestamp': datetime.now(),
            'order_id': order_result.order_id,
            'success': order_result.success,
            'pnl': float(self.state.total_profit),
            'drawdown': float(self.state.current_drawdown)
        })
        
        # 保持历史记录在合理范围内
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]


class BaseSpotStrategy(SpotStrategyInterface):
    """现货策略基类"""
    
    def __init__(self, config: StrategyConfig, order_manager: Optional[OrderManager] = None):
        super().__init__(config)
        self.order_manager = order_manager
        self.logger = logging.getLogger(f"strategy.{config.strategy_type}.{config.strategy_id}")
        
        # 性能监控
        self.performance_monitor_task: Optional[asyncio.Task] = None
        self.risk_monitor_task: Optional[asyncio.Task] = None
        
        # 市场数据缓存
        self.last_market_data: Optional[MarketData] = None
        self.market_data_history: List[MarketData] = []
        
    async def initialize(self) -> bool:
        """初始化策略"""
        try:
            self.logger.info(f"初始化策略 {self.config.strategy_id}")
            self.state.status = StrategyStatus.INITIALIZING
            
            # 验证配置
            self._validate_config()
            
            # 初始化子类特定功能
            await self._initialize_specific()
            
            self.state.status = StrategyStatus.CREATED
            self.logger.info(f"策略 {self.config.strategy_id} 初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略初始化失败: {e}")
            self.state.status = StrategyStatus.ERROR
            self.state.last_error = str(e)
            return False
    
    async def start(self) -> bool:
        """启动策略"""
        try:
            if self.state.status != StrategyStatus.CREATED:
                self.logger.warning(f"策略状态不正确: {self.state.status}")
                return False
            
            self.logger.info(f"启动策略 {self.config.strategy_id}")
            
            # 启动监控任务
            self._start_monitoring_tasks()
            
            # 启动子类特定功能
            await self._start_specific()
            
            self.state.status = StrategyStatus.RUNNING
            self.state.started_at = datetime.now()
            
            self.logger.info(f"策略 {self.config.strategy_id} 启动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略启动失败: {e}")
            self.state.status = StrategyStatus.ERROR
            self.state.last_error = str(e)
            return False
    
    async def pause(self) -> bool:
        """暂停策略"""
        try:
            if self.state.status != StrategyStatus.RUNNING:
                return False
            
            self.logger.info(f"暂停策略 {self.config.strategy_id}")
            
            # 停止监控任务
            self._stop_monitoring_tasks()
            
            # 暂停子类特定功能
            await self._pause_specific()
            
            self.state.status = StrategyStatus.PAUSED
            
            self.logger.info(f"策略 {self.config.strategy_id} 暂停完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略暂停失败: {e}")
            return False
    
    async def resume(self) -> bool:
        """恢复策略"""
        try:
            if self.state.status != StrategyStatus.PAUSED:
                return False
            
            self.logger.info(f"恢复策略 {self.config.strategy_id}")
            
            # 恢复子类特定功能
            await self._resume_specific()
            
            # 重新启动监控
            self._start_monitoring_tasks()
            
            self.state.status = StrategyStatus.RUNNING
            
            self.logger.info(f"策略 {self.config.strategy_id} 恢复完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略恢复失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止策略"""
        try:
            if self.state.status not in [StrategyStatus.RUNNING, StrategyStatus.PAUSED]:
                return False
            
            self.logger.info(f"停止策略 {self.config.strategy_id}")
            
            # 停止所有任务
            await self._stop_all_tasks()
            
            # 停止子类特定功能
            await self._stop_specific()
            
            self.state.status = StrategyStatus.STOPPED
            self.state.stopped_at = datetime.now()
            self.state.update_performance_metrics()
            
            self.logger.info(f"策略 {self.config.strategy_id} 停止完成")
            return True
            
        except Exception as e:
            self.logger.error(f"策略停止失败: {e}")
            return False
    
    async def process_market_data(self, market_data: MarketData):
        """处理市场数据"""
        try:
            # 缓存市场数据
            self.last_market_data = market_data
            self.market_data_history.append(market_data)
            
            # 保持历史数据在合理范围内
            if len(self.market_data_history) > 100:
                self.market_data_history = self.market_data_history[-50:]
            
            # 检查是否可以交易
            if not self.state.is_trading_allowed():
                return
            
            # 检查风险条件
            if self.state.should_stop_loss():
                self.logger.warning("达到止损条件，停止策略")
                await self.stop()
                return
            
            # 获取订单建议
            orders = await self.get_next_orders(market_data)
            
            # 执行订单
            for order_request in orders:
                await self._execute_order(order_request)
            
        except Exception as e:
            self.logger.error(f"处理市场数据失败: {e}")
            self.state.error_count += 1
            self.state.last_error = str(e)
    
    async def _execute_order(self, order_request: OrderRequest) -> bool:
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
            order_result = OrderResult(
                success=success,
                order_id=order_request.order_id,
                filled_quantity=order.quantity_filled,
                average_price=order.average_price or Decimal('0'),
                commission=order.commission or Decimal('0'),
                execution_time=datetime.now()
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
        while self.state.status == StrategyStatus.RUNNING:
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
        while self.state.status == StrategyStatus.RUNNING:
            try:
                await asyncio.sleep(self.config.risk_check_interval)
                
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
    async def get_next_orders(self, market_data: MarketData) -> List[OrderRequest]:
        """获取下一批订单"""
        pass
    
    @abstractmethod
    async def process_order_result(self, order_result: OrderResult) -> bool:
        """处理订单执行结果"""
        pass