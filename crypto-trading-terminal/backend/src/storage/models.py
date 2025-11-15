"""
数据库模型定义
支持现货和合约交易的核心数据模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from enum import Enum
import uuid

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Float, Text, 
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

Base = declarative_base()


class MarketType(Enum):
    """市场类型"""
    SPOT = "spot"
    FUTURES = "futures"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED_PENDING = "partially_filled_pending"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionResultStatus(Enum):
    """执行结果状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    REJECTED = "rejected"


class Exchange(Enum):
    """支持的交易所"""
    BINANCE = "binance"
    OKX = "okx"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户信息
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # 账户状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 创建和更新时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    
    # 关联关系
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    """账户模型 - 支持多交易所多账户"""
    __tablename__ = "accounts"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 交易所信息
    exchange: Mapped[Exchange] = mapped_column(String(20), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # main, isolated, etc.
    
    # API配置
    api_key: Mapped[str] = mapped_column(String(255), nullable=True)  # 加密存储
    api_secret: Mapped[str] = mapped_column(Text, nullable=True)  # 加密存储
    passphrase: Mapped[str] = mapped_column(String(255), nullable=True)  # OKX需要
    
    # 账户状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 创建和更新时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    
    # 关联关系
    user = relationship("User", back_populates="accounts")
    trading_pairs = relationship("TradingPair", back_populates="account")
    market_data = relationship("MarketData", back_populates="account")
    orders = relationship("Order", back_populates="account")


class TradingPair(Base):
    """交易对模型"""
    __tablename__ = "trading_pairs"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 账户关联
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # 交易对基本信息
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # BTCUSDT, BTCUSDT-PERP
    base_asset: Mapped[str] = mapped_column(String(20), nullable=False)  # BTC
    quote_asset: Mapped[str] = mapped_column(String(20), nullable=False)  # USDT
    
    # 市场类型
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False, index=True)
    
    # 交易规则
    min_qty: Mapped[Decimal] = mapped_column(Float, nullable=False)
    max_qty: Mapped[Decimal] = mapped_column(Float, nullable=False)
    step_size: Mapped[Decimal] = mapped_column(Float, nullable=False)
    min_price: Mapped[Decimal] = mapped_column(Float, nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Float, nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(Float, nullable=False)
    
    # 是否支持现货/合约交易
    is_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 创建和更新时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    
    # 关联关系
    account = relationship("Account", back_populates="trading_pairs")
    
    # 索引
    __table_args__ = (
        UniqueConstraint('account_id', 'symbol', name='uq_account_symbol'),
        Index('idx_symbol_market', 'symbol', 'market_type'),
    )


class MarketData(Base):
    """市场数据模型 - 存储实时价格、涨跌幅等信息"""
    __tablename__ = "market_data"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 账户关联
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    trading_pair_id: Mapped[int] = mapped_column(Integer, ForeignKey("trading_pairs.id"), nullable=False)
    
    # 基本价格信息
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # 价格数据
    current_price: Mapped[Decimal] = mapped_column(Float, nullable=False, index=True)
    previous_close: Mapped[Decimal] = mapped_column(Float, nullable=False)
    high_24h: Mapped[Decimal] = mapped_column(Float, nullable=False)
    low_24h: Mapped[Decimal] = mapped_column(Float, nullable=False)
    
    # 涨跌信息
    price_change: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 价格变化
    price_change_percent: Mapped[Decimal] = mapped_column(Float, nullable=False, index=True)  # 涨跌百分比
    
    # 交易量信息
    volume_24h: Mapped[Decimal] = mapped_column(Float, nullable=False)
    quote_volume_24h: Mapped[Decimal] = mapped_column(Float, nullable=False)
    
    # 合约特有字段 (期货)
    funding_rate: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 资金费率
    open_interest: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 持仓量
    index_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 标记价格
    mark_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 标记价格
    
    # 数据时间戳
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    
    # 数据源
    exchange: Mapped[Exchange] = mapped_column(String(20), nullable=False, index=True)
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False)
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # 关联关系
    account = relationship("Account", back_populates="market_data")
    trading_pair = relationship("TradingPair")
    
    # 索引
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_exchange_market', 'exchange', 'market_type'),
    )


class Order(Base):
    """订单模型 - 支持现货和合约订单"""
    __tablename__ = "orders"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 账户关联
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # 订单标识
    client_order_id: Mapped[str] = mapped_column(String(100), nullable=True)  # 客户端订单ID
    exchange_order_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)  # 交易所订单ID
    
    # 交易对信息
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False)
    
    # 订单详情
    order_type: Mapped[OrderType] = mapped_column(String(20), nullable=False)
    order_side: Mapped[OrderSide] = mapped_column(String(10), nullable=False, index=True)
    
    # 价格和数量
    price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 限价单价格
    quantity: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 数量
    quantity_filled: Mapped[Decimal] = mapped_column(Float, default=0)  # 已成交数量
    quantity_remaining: Mapped[Decimal] = mapped_column(Float)  # 剩余数量
    
    # 订单状态
    status: Mapped[OrderStatus] = mapped_column(String(30), nullable=False, index=True)
    
    # 成交信息
    average_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 平均成交价
    total_filled: Mapped[Decimal] = mapped_column(Float, default=0)  # 总成交额
    commission: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 手续费
    
    # 时间信息
    order_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    
    # 合约特有字段
    leverage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 杠杆倍数
    position_side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 仓位方向
    
    # 元数据
    metadata_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # 关联关系
    account = relationship("Account", back_populates="orders")
    
    # 索引
    __table_args__ = (
        Index('idx_account_symbol', 'account_id', 'symbol'),
        Index('idx_symbol_status', 'symbol', 'status'),
        Index('idx_order_time', 'order_time'),
    )


class AlertCondition(Base):
    """条件触发模型 - 价格、指标等条件"""
    __tablename__ = "alert_conditions"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 条件基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 交易对和市场类型
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False)
    
    # 条件表达式 (JSON格式存储)
    condition_expression: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # 通知配置
    notification_channels: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # popup,desktop,telegram,email,sound
    
    # 执行状态
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 创建和更新时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    
    # 索引
    __table_args__ = (
        Index('idx_user_active', 'user_id', 'is_active'),
        Index('idx_symbol_active', 'symbol', 'is_active'),
    )


class SystemLog(Base):
    """系统日志模型"""
    __tablename__ = "system_logs"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 日志级别和消息
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 日志上下文
    module: Mapped[str] = mapped_column(String(100), nullable=True)
    function: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # 额外信息
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    
    # 索引
    __table_args__ = (
        Index('idx_level_timestamp', 'level', 'timestamp'),
        Index('idx_module_function', 'module', 'function'),
    )


# 创建索引 (MySQL优化)
Index('idx_market_data_symbol_timestamp', MarketData.symbol, MarketData.timestamp)
Index('idx_orders_account_status', Order.account_id, Order.status)
Index('idx_accounts_exchange_type', Account.exchange, Account.account_type)


class AutoOrder(Base):
    """自动订单模型 - 支持条件触发和自动执行"""
    __tablename__ = "auto_orders"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户和账户关联
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # 自动订单标识
    auto_order_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 策略名称
    
    # 交易对信息
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False)
    
    # 订单配置
    order_side: Mapped[OrderSide] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Float, nullable=False)
    
    # 条件触发
    entry_condition_id: Mapped[int] = mapped_column(Integer, ForeignKey("alert_conditions.id"), nullable=False)
    
    # 风险控制
    stop_loss_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 止损价格
    take_profit_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 止盈价格
    max_slippage: Mapped[Decimal] = mapped_column(Float, default=0.01)  # 最大滑点
    max_spread: Mapped[Decimal] = mapped_column(Float, default=0.005)  # 最大点差
    
    # 执行状态
    status: Mapped[OrderStatus] = mapped_column(String(30), nullable=False, default=OrderStatus.NEW, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 执行统计
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 执行结果
    last_execution_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 时间信息
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 关联关系
    user = relationship("User")
    account = relationship("Account")
    entry_condition = relationship("AlertCondition")
    
    # 索引
    __table_args__ = (
        Index('idx_auto_orders_user_active', 'user_id', 'is_active'),
        Index('idx_auto_orders_symbol_active', 'symbol', 'is_active'),
        Index('idx_auto_orders_status', 'status'),
        Index('idx_auto_orders_strategy', 'strategy_name'),
    )


class RiskManagement(Base):
    """风险管理配置模型"""
    __tablename__ = "risk_management"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户和账户关联
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # 风险配置标识
    config_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 订单限制
    max_order_size: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 最大订单大小
    max_position_size: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 最大仓位大小
    max_daily_trades: Mapped[int] = mapped_column(Integer, nullable=False)  # 最大日交易次数
    max_daily_volume: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 最大日交易量
    
    # 风险阈值
    max_loss_per_trade: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 单笔最大亏损
    max_total_exposure: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 最大总敞口
    stop_loss_percentage: Mapped[Decimal] = mapped_column(Float, default=0.05)  # 默认止损百分比
    take_profit_percentage: Mapped[Decimal] = mapped_column(Float, default=0.10)  # 默认止盈百分比
    
    # 风险等级
    default_risk_level: Mapped[RiskLevel] = mapped_column(String(20), default=RiskLevel.MEDIUM)
    
    # 时间限制
    trading_hours_start: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 交易开始时间
    trading_hours_end: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 交易结束时间
    
    # 配置详情
    additional_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    user = relationship("User")
    account = relationship("Account")
    
    # 索引
    __table_args__ = (
        Index('idx_risk_user_account', 'user_id', 'account_id'),
        Index('idx_risk_active', 'is_active'),
        Index('idx_risk_config_name', 'config_name'),
    )


class Position(Base):
    """仓位模型 - 跟踪当前持仓"""
    __tablename__ = "positions"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 账户和用户关联
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 交易对信息
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_type: Mapped[MarketType] = mapped_column(String(20), nullable=False)
    
    # 仓位信息
    quantity: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 当前持仓数量
    quantity_available: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 可用数量
    quantity_frozen: Mapped[Decimal] = mapped_column(Float, default=0)  # 冻结数量
    
    # 成本信息
    avg_price: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 平均成本价
    entry_price: Mapped[Decimal] = mapped_column(Float, nullable=False)  # 入场价格
    
    # 盈亏信息
    unrealized_pnl: Mapped[Decimal] = mapped_column(Float, default=0)  # 未实现盈亏
    realized_pnl: Mapped[Decimal] = mapped_column(Float, default=0)  # 已实现盈亏
    
    # 杠杆信息 (期货)
    leverage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # LONG, SHORT
    
    # 仓位状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, closed, partial
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    account = relationship("Account")
    user = relationship("User")
    
    # 索引
    __table_args__ = (
        Index('idx_positions_account_symbol', 'account_id', 'symbol'),
        Index('idx_positions_user_symbol', 'user_id', 'symbol'),
        Index('idx_positions_active', 'is_active'),
    )


class OrderExecution(Base):
    """订单执行记录模型"""
    __tablename__ = "order_executions"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 订单关联
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    auto_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("auto_orders.id"), nullable=True)
    
    # 执行标识
    execution_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # 执行结果
    status: Mapped[ExecutionResultStatus] = mapped_column(String(20), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 执行详情
    filled_quantity: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    average_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    commission: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    
    # 时间信息
    execution_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 执行延迟
    
    # 性能指标
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 错误信息
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    order = relationship("Order")
    auto_order = relationship("AutoOrder")
    
    # 索引
    __table_args__ = (
        Index('idx_executions_order', 'order_id'),
        Index('idx_executions_auto_order', 'auto_order_id'),
        Index('idx_executions_status', 'status'),
        Index('idx_executions_time', 'execution_time'),
    )


class RiskAlert(Base):
    """风险警告模型"""
    __tablename__ = "risk_alerts"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # 警告标识
    alert_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # 警告信息
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # INFO, WARNING, CRITICAL, BLOCKED
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # order_size, position_size, daily_limit, etc.
    
    # 关联信息
    symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    auto_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("auto_orders.id"), nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # 警告详情
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    current_value: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    limit_value: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    
    # 状态管理
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 处理状态
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 通知状态
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_channels: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 时间戳
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    user = relationship("User")
    account = relationship("Account")
    auto_order = relationship("AutoOrder")
    order = relationship("Order")
    
    # 索引
    __table_args__ = (
        Index('idx_risk_alerts_user', 'user_id'),
        Index('idx_risk_alerts_account', 'account_id'),
        Index('idx_risk_alerts_severity', 'severity'),
        Index('idx_risk_alerts_unacknowledged', 'user_id', 'is_acknowledged'),
        Index('idx_risk_alerts_unresolved', 'is_resolved', 'severity'),
    )


class OrderHistory(Base):
    """订单执行历史模型 - 记录订单的完整执行过程"""
    __tablename__ = "order_history"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 关联订单
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    auto_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("auto_orders.id"), nullable=True)
    
    # 基本信息
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # 订单信息
    order_type: Mapped[OrderType] = mapped_column(String(20), nullable=False)
    order_side: Mapped[OrderSide] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Float, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    
    # 执行状态
    execution_status: Mapped[ExecutionResultStatus] = mapped_column(String(20), nullable=False, index=True)
    
    # 执行详情
    filled_quantity: Mapped[Decimal] = mapped_column(Float, default=0)
    average_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    commission: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # 执行时间
    execution_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 执行时长（秒）
    
    # 交易所信息
    exchange: Mapped[Exchange] = mapped_column(String(20), nullable=False)
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    client_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 元数据
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    order = relationship("Order")
    auto_order = relationship("AutoOrder")
    account = relationship("Account")
    user = relationship("User")
    
    # 索引
    __table_args__ = (
        Index('idx_order_history_order_id', 'order_id'),
        Index('idx_order_history_auto_order_id', 'auto_order_id'),
        Index('idx_order_history_user_status', 'user_id', 'execution_status'),
        Index('idx_order_history_symbol_time', 'symbol', 'execution_start_time'),
        Index('idx_order_history_account_time', 'account_id', 'execution_start_time'),
        Index('idx_order_history_exchange_status', 'exchange', 'execution_status'),
    )


class ExecutionStatusLog(Base):
    """执行状态变更日志模型"""
    __tablename__ = "execution_status_logs"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 关联订单和历史记录
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    order_history_id: Mapped[int] = mapped_column(Integer, ForeignKey("order_history.id"), nullable=False)
    auto_order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("auto_orders.id"), nullable=True)
    
    # 状态变更信息
    previous_status: Mapped[Optional[ExecutionStatus]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[ExecutionStatus] = mapped_column(String(20), nullable=False, index=True)
    
    # 变更详情
    status_change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # 执行指标
    current_filled_quantity: Mapped[Decimal] = mapped_column(Float, default=0)
    current_average_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    
    # 时间戳
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    order = relationship("Order")
    order_history = relationship("OrderHistory")
    auto_order = relationship("AutoOrder")
    
    # 索引
    __table_args__ = (
        Index('idx_status_logs_order_time', 'order_id', 'status_changed_at'),
        Index('idx_status_logs_history_time', 'order_history_id', 'status_changed_at'),
        Index('idx_status_logs_status_time', 'new_status', 'status_changed_at'),
    )


class TradingStatistics(Base):
    """交易统计模型"""
    __tablename__ = "trading_statistics"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 账户和用户关联
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 统计周期
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # 交易统计
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    successful_trades: Mapped[int] = mapped_column(Integer, default=0)
    failed_trades: Mapped[int] = mapped_column(Integer, default=0)
    
    # 交易量统计
    total_volume: Mapped[Decimal] = mapped_column(Float, default=0)
    buy_volume: Mapped[Decimal] = mapped_column(Float, default=0)
    sell_volume: Mapped[Decimal] = mapped_column(Float, default=0)
    
    # 盈亏统计
    total_pnl: Mapped[Decimal] = mapped_column(Float, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Float, default=0)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Float, default=0)
    commission_paid: Mapped[Decimal] = mapped_column(Float, default=0)
    
    # 性能指标
    win_rate: Mapped[Decimal] = mapped_column(Float, default=0)  # 胜率
    avg_trade_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 平均交易时长(秒)
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)  # 最大回撤
    
    # 交易对统计
    symbols_traded: Mapped[int] = mapped_column(Integer, default=0)
    most_traded_symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    account = relationship("Account")
    user = relationship("User")
    
    # 索引
    __table_args__ = (
        Index('idx_trading_stats_account_period', 'account_id', 'period_start', 'period_end'),
        Index('idx_trading_stats_user_period', 'user_id', 'period_start', 'period_end'),
        Index('idx_trading_stats_period_type', 'period_type'),
    )