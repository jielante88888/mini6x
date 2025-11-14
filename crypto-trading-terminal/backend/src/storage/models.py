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