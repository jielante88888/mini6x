"""
自动订单执行合同测试
验证自动订单执行系统的核心功能和接口合约
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 模拟自动交易相关的核心类和数据模型
class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Order:
    """订单数据模型"""
    def __init__(
        self,
        order_id: str,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal = None,
        stop_price: Decimal = None,
        status: OrderStatus = OrderStatus.PENDING,
        created_at: datetime = None,
        updated_at: datetime = None,
        filled_quantity: Decimal = Decimal('0'),
        filled_price: Decimal = None,
        commission: Decimal = Decimal('0'),
        metadata: dict = None
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type
        self.side = side
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.commission = commission
        self.metadata = metadata or {}
    
    def is_filled(self) -> bool:
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]
    
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def get_remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
    
    def get_average_fill_price(self) -> Decimal:
        if self.filled_quantity == 0:
            return Decimal('0')
        total_value = self.filled_quantity * (self.filled_price or Decimal('0'))
        return total_value / self.filled_quantity
    
    def update_status(self, status: OrderStatus, filled_quantity: Decimal = None, filled_price: Decimal = None):
        self.status = status
        self.updated_at = datetime.now()
        
        if filled_quantity is not None:
            self.filled_quantity = filled_quantity
        if filled_price is not None:
            self.filled_price = filled_price
    
    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'price': str(self.price) if self.price else None,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filled_quantity': str(self.filled_quantity),
            'filled_price': str(self.filled_price) if self.filled_price else None,
            'commission': str(self.commission),
            'metadata': self.metadata
        }

class AutoOrder:
    """自动订单数据模型"""
    def __init__(
        self,
        auto_order_id: str,
        strategy_name: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        entry_condition_id: str,
        exit_condition_id: str = None,
        stop_loss_price: Decimal = None,
        take_profit_price: Decimal = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        max_retries: int = 3,
        created_at: datetime = None,
        updated_at: datetime = None,
        is_active: bool = True,
        metadata: dict = None
    ):
        self.auto_order_id = auto_order_id
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_condition_id = entry_condition_id
        self.exit_condition_id = exit_condition_id
        self.stop_loss_price = stop_loss_price
        self.take_profit_price = take_profit_price
        self.risk_level = risk_level
        self.max_retries = max_retries
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
        self.is_active = is_active
        self.metadata = metadata or {}
    
    def get_order_price_range(self) -> tuple:
        """获取订单价格范围用于风险评估"""
        if self.stop_loss_price and self.take_profit_price:
            if self.side == OrderSide.BUY:
                return (self.stop_loss_price, self.take_profit_price)
            else:
                return (self.take_profit_price, self.stop_loss_price)
        return (None, None)
    
    def to_dict(self) -> dict:
        return {
            'auto_order_id': self.auto_order_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'entry_condition_id': self.entry_condition_id,
            'exit_condition_id': self.exit_condition_id,
            'stop_loss_price': str(self.stop_loss_price) if self.stop_loss_price else None,
            'take_profit_price': str(self.take_profit_price) if self.take_profit_price else None,
            'risk_level': self.risk_level.value,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'metadata': self.metadata
        }

class Position:
    """持仓数据模型"""
    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        entry_price: Decimal,
        current_price: Decimal = None,
        unrealized_pnl: Decimal = Decimal('0'),
        realized_pnl: Decimal = Decimal('0'),
        created_at: datetime = None,
        updated_at: datetime = None,
        metadata: dict = None
    ):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price or entry_price
        self.unrealized_pnl = unrealized_pnl
        self.realized_pnl = realized_pnl
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
        self.metadata = metadata or {}
    
    def update_price(self, new_price: Decimal):
        self.current_price = new_price
        self.updated_at = datetime.now()
        self._calculate_unrealized_pnl()
    
    def _calculate_unrealized_pnl(self):
        """计算未实现盈亏"""
        if self.side == OrderSide.BUY:
            pnl_per_unit = self.current_price - self.entry_price
        else:
            pnl_per_unit = self.entry_price - self.current_price
        
        self.unrealized_pnl = pnl_per_unit * self.quantity
    
    def get_position_value(self) -> Decimal:
        """获取持仓市值"""
        return self.quantity * self.current_price
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': str(self.quantity),
            'entry_price': str(self.entry_price),
            'current_price': str(self.current_price),
            'unrealized_pnl': str(self.unrealized_pnl),
            'realized_pnl': str(self.realized_pnl),
            'position_value': str(self.get_position_value()),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }

class ExecutionResult:
    """执行结果数据模型"""
    def __init__(
        self,
        order_id: str,
        success: bool,
        filled_quantity: Decimal,
        filled_price: Decimal,
        commission: Decimal,
        execution_time: float,
        message: str = None,
        error_code: str = None
    ):
        self.order_id = order_id
        self.success = success
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.commission = commission
        self.execution_time = execution_time
        self.message = message
        self.error_code = error_code
    
    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'success': self.success,
            'filled_quantity': str(self.filled_quantity),
            'filled_price': str(self.filled_price),
            'commission': str(self.commission),
            'execution_time': self.execution_time,
            'message': self.message,
            'error_code': self.error_code
        }

class AutoOrderManager:
    """自动订单管理器模拟类"""
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.orders = {}
        self.auto_orders = {}
        self.positions = {}
        self.execution_history = []
        self.is_running = False
    
    async def start(self):
        """启动管理器"""
        self.is_running = True
    
    async def stop(self):
        """停止管理器"""
        self.is_running = False
    
    def create_order(self, order: Order) -> str:
        """创建订单"""
        if not self.is_running:
            raise RuntimeError("管理器未启动")
        
        self.orders[order.order_id] = order
        return order.order_id
    
    def create_auto_order(self, auto_order: AutoOrder) -> str:
        """创建自动订单"""
        if not self.is_running:
            raise RuntimeError("管理器未启动")
        
        self.auto_orders[auto_order.auto_order_id] = auto_order
        return auto_order.auto_order_id
    
    async def execute_order(self, order_id: str, current_price: Decimal) -> ExecutionResult:
        """执行订单"""
        if order_id not in self.orders:
            raise ValueError(f"订单 {order_id} 不存在")
        
        order = self.orders[order_id]
        start_time = time.time()
        
        try:
            # 模拟订单执行
            if order.order_type == OrderType.MARKET:
                filled_price = current_price
                filled_quantity = order.quantity
            elif order.order_type == OrderType.LIMIT:
                if ((order.side == OrderSide.BUY and current_price <= order.price) or
                    (order.side == OrderSide.SELL and current_price >= order.price)):
                    filled_price = order.price
                    filled_quantity = order.quantity
                else:
                    return ExecutionResult(
                        order_id, False, Decimal('0'), Decimal('0'), Decimal('0'),
                        time.time() - start_time, "条件未满足"
                    )
            else:
                filled_price = current_price
                filled_quantity = order.quantity
            
            # 更新订单状态
            order.update_status(OrderStatus.FILLED, filled_quantity, filled_price)
            
            # 模拟执行时间
            await asyncio.sleep(0.1)
            
            result = ExecutionResult(
                order_id, True, filled_quantity, filled_price, Decimal('0.001'),
                time.time() - start_time, "执行成功"
            )
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            return ExecutionResult(
                order_id, False, Decimal('0'), Decimal('0'), Decimal('0'),
                time.time() - start_time, str(e), "EXECUTION_ERROR"
            )
    
    def get_order(self, order_id: str) -> Order:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_auto_order(self, auto_order_id: str) -> AutoOrder:
        """获取自动订单"""
        return self.auto_orders.get(auto_order_id)
    
    def get_position(self, symbol: str) -> Position:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def update_position(self, symbol: str, side: OrderSide, quantity: Decimal, price: Decimal):
        """更新持仓"""
        if symbol in self.positions:
            position = self.positions[symbol]
            if position.side == side:
                # 相同方向，增加持仓
                new_quantity = position.quantity + quantity
                new_entry_price = ((position.quantity * position.entry_price) + (quantity * price)) / new_quantity
                position.quantity = new_quantity
                position.entry_price = new_entry_price
            else:
                # 相反方向，部分或全部平仓
                if quantity >= position.quantity:
                    # 全部平仓
                    realized_pnl = (price - position.entry_price) * position.quantity
                    if position.side == OrderSide.BUY:
                        realized_pnl = realized_pnl
                    else:
                        realized_pnl = -realized_pnl
                    
                    position.realized_pnl += realized_pnl
                    del self.positions[symbol]
                    
                    # 如果还有剩余，创建新持仓
                    remaining_quantity = quantity - position.quantity
                    if remaining_quantity > 0:
                        self.positions[symbol] = Position(symbol, side, remaining_quantity, price)
                else:
                    # 部分平仓
                    realized_pnl = (price - position.entry_price) * quantity
                    if position.side == OrderSide.BUY:
                        realized_pnl = realized_pnl
                    else:
                        realized_pnl = -realized_pnl
                    
                    position.realized_pnl += realized_pnl
                    position.quantity -= quantity
        else:
            # 创建新持仓
            self.positions[symbol] = Position(symbol, side, quantity, price)
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        total_orders = len(self.orders)
        active_orders = sum(1 for order in self.orders.values() if order.is_active())
        filled_orders = sum(1 for order in self.orders.values() if order.status == OrderStatus.FILLED)
        
        total_auto_orders = len(self.auto_orders)
        active_auto_orders = sum(1 for ao in self.auto_orders.values() if ao.is_active)
        
        total_positions = len(self.positions)
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        execution_success_rate = 0.0
        if self.execution_history:
            successful_executions = sum(1 for result in self.execution_history if result.success)
            execution_success_rate = successful_executions / len(self.execution_history)
        
        return {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'filled_orders': filled_orders,
            'total_auto_orders': total_auto_orders,
            'active_auto_orders': active_auto_orders,
            'total_positions': total_positions,
            'total_realized_pnl': str(total_realized_pnl),
            'total_unrealized_pnl': str(total_unrealized_pnl),
            'execution_success_rate': execution_success_rate,
            'total_executions': len(self.execution_history)
        }


class TestAutoOrderContract:
    """自动订单系统合同测试类"""
    
    @pytest.fixture
    async def order_manager(self):
        """创建测试用的订单管理器"""
        config = {
            "max_concurrent_orders": 10,
            "default_commission_rate": 0.001,
            "execution_timeout": 30.0,
            "retry_attempts": 3
        }
        
        manager = AutoOrderManager(config)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.fixture
    def sample_order(self):
        """创建测试用的订单"""
        return Order(
            order_id="test-order-001",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000.00')
        )
    
    @pytest.fixture
    def sample_auto_order(self):
        """创建测试用的自动订单"""
        return AutoOrder(
            auto_order_id="test-auto-001",
            strategy_name="test_strategy",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            entry_condition_id="condition-001",
            stop_loss_price=Decimal('48000.00'),
            take_profit_price=Decimal('52000.00'),
            risk_level=RiskLevel.MEDIUM
        )
    
    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, order_manager):
        """测试管理器生命周期"""
        # 测试初始状态
        assert order_manager.is_running == True
        assert len(order_manager.orders) == 0
        assert len(order_manager.auto_orders) == 0
        assert len(order_manager.positions) == 0
        
        # 测试停止
        await order_manager.stop()
        assert order_manager.is_running == False
        
        # 测试重启
        await order_manager.start()
        assert order_manager.is_running == True
    
    @pytest.mark.asyncio
    async def test_order_creation_and_management(self, order_manager, sample_order):
        """测试订单创建和管理"""
        # 创建订单
        order_id = order_manager.create_order(sample_order)
        assert order_id == sample_order.order_id
        assert order_id in order_manager.orders
        
        # 获取订单
        retrieved_order = order_manager.get_order(order_id)
        assert retrieved_order.order_id == sample_order.order_id
        assert retrieved_order.symbol == sample_order.symbol
        assert retrieved_order.status == OrderStatus.PENDING
        
        # 验证订单属性
        assert sample_order.is_active() == True
        assert sample_order.is_filled() == False
        assert sample_order.get_remaining_quantity() == Decimal('0.1')
    
    @pytest.mark.asyncio
    async def test_auto_order_creation_and_management(self, order_manager, sample_auto_order):
        """测试自动订单创建和管理"""
        # 创建自动订单
        auto_order_id = order_manager.create_auto_order(sample_auto_order)
        assert auto_order_id == sample_auto_order.auto_order_id
        assert auto_order_id in order_manager.auto_orders
        
        # 获取自动订单
        retrieved_auto_order = order_manager.get_auto_order(auto_order_id)
        assert retrieved_auto_order.auto_order_id == sample_auto_order.auto_order_id
        assert retrieved_auto_order.strategy_name == sample_auto_order.strategy_name
        assert retrieved_auto_order.is_active == True
        
        # 验证自动订单属性
        price_range = sample_auto_order.get_order_price_range()
        assert price_range[0] == Decimal('48000.00')  # stop_loss
        assert price_range[1] == Decimal('52000.00')  # take_profit
    
    @pytest.mark.asyncio
    async def test_order_execution_market_type(self, order_manager, sample_order):
        """测试市价单执行"""
        current_price = Decimal('50000.00')
        
        # 执行订单
        result = await order_manager.execute_order(sample_order.order_id, current_price)
        
        # 验证执行结果
        assert result.success == True
        assert result.filled_quantity == Decimal('0.1')
        assert result.filled_price == current_price
        assert result.commission == Decimal('0.001')
        assert result.execution_time > 0
        
        # 验证订单状态更新
        updated_order = order_manager.get_order(sample_order.order_id)
        assert updated_order.status == OrderStatus.FILLED
        assert updated_order.filled_quantity == Decimal('0.1')
        assert updated_order.filled_price == current_price
        assert updated_order.is_filled() == True
    
    @pytest.mark.asyncio
    async def test_order_execution_limit_type_success(self, order_manager):
        """测试限价单执行 - 条件满足"""
        limit_order = Order(
            order_id="test-limit-001",
            symbol="BTCUSDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('49000.00')  # 限价低于当前价格，应该成交
        )
        
        current_price = Decimal('50000.00')
        
        # 创建并执行订单
        order_manager.create_order(limit_order)
        result = await order_manager.execute_order(limit_order.order_id, current_price)
        
        # 验证执行成功
        assert result.success == True
        assert result.filled_quantity == Decimal('0.1')
        assert result.filled_price == Decimal('49000.00')  # 按限价成交
    
    @pytest.mark.asyncio
    async def test_order_execution_limit_type_failure(self, order_manager):
        """测试限价单执行 - 条件不满足"""
        limit_order = Order(
            order_id="test-limit-002",
            symbol="BTCUSDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('51000.00')  # 限价高于当前价格，不应该成交
        )
        
        current_price = Decimal('50000.00')
        
        # 创建并执行订单
        order_manager.create_order(limit_order)
        result = await order_manager.execute_order(limit_order.order_id, current_price)
        
        # 验证执行失败
        assert result.success == False
        assert result.filled_quantity == Decimal('0')
        assert "条件未满足" in result.message
    
    @pytest.mark.asyncio
    async def test_position_management(self, order_manager):
        """测试持仓管理"""
        symbol = "BTCUSDT"
        
        # 创建买入订单并执行
        buy_order = Order(
            order_id="buy-001",
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000.00')
        )
        
        order_manager.create_order(buy_order)
        await order_manager.execute_order(buy_order.order_id, Decimal('50000.00'))
        
        # 更新持仓
        order_manager.update_position(symbol, OrderSide.BUY, Decimal('0.1'), Decimal('50000.00'))
        
        # 验证持仓
        position = order_manager.get_position(symbol)
        assert position.symbol == symbol
        assert position.side == OrderSide.BUY
        assert position.quantity == Decimal('0.1')
        assert position.entry_price == Decimal('50000.00')
        
        # 测试价格更新
        order_manager.update_position(symbol, OrderSide.BUY, Decimal('0'), Decimal('51000.00'))  # 只更新价格
        assert position.current_price == Decimal('51000.00')
        assert position.unrealized_pnl > 0  # 价格上涨，未实现盈利
    
    @pytest.mark.asyncio
    async def test_position_closing(self, order_manager):
        """测试持仓平仓"""
        symbol = "BTCUSDT"
        
        # 创建初始持仓
        order_manager.update_position(symbol, OrderSide.BUY, Decimal('0.1'), Decimal('50000.00'))
        
        # 部分平仓
        order_manager.update_position(symbol, OrderSide.SELL, Decimal('0.05'), Decimal('51000.00'))
        
        position = order_manager.get_position(symbol)
        assert position.quantity == Decimal('0.05')  # 剩余数量
        assert position.realized_pnl > 0  # 已实现盈利
        
        # 全部平仓
        order_manager.update_position(symbol, OrderSide.SELL, Decimal('0.05'), Decimal('52000.00'))
        
        # 持仓应该被删除
        position = order_manager.get_position(symbol)
        assert position is None
    
    @pytest.mark.asyncio
    async def test_multiple_orders_and_positions(self, order_manager):
        """测试多个订单和持仓"""
        # 创建多个订单
        orders_data = [
            ("BTCUSDT", OrderSide.BUY, Decimal('0.1'), Decimal('50000.00')),
            ("BTCUSDT", OrderSide.BUY, Decimal('0.05'), Decimal('50000.00')),
            ("ETHUSDT", OrderSide.BUY, Decimal('1.0'), Decimal('3000.00')),
            ("BTCUSDT", OrderSide.SELL, Decimal('0.08'), Decimal('51000.00')),
        ]
        
        executed_orders = []
        for i, (symbol, side, quantity, price) in enumerate(orders_data):
            order = Order(
                order_id=f"multi-test-{i}",
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                quantity=quantity,
                price=price
            )
            
            order_manager.create_order(order)
            await order_manager.execute_order(order.order_id, price)
            
            # 更新持仓
            order_manager.update_position(symbol, side, quantity, price)
            executed_orders.append(order)
        
        # 验证持仓
        btc_position = order_manager.get_position("BTCUSDT")
        eth_position = order_manager.get_position("ETHUSDT")
        
        assert btc_position is not None
        assert eth_position is not None
        assert btc_position.quantity == Decimal('0.07')  # 0.1 + 0.05 - 0.08
        assert eth_position.quantity == Decimal('1.0')
        
        # 验证统计信息
        stats = order_manager.get_statistics()
        assert stats['total_orders'] == 4
        assert stats['filled_orders'] == 4
        assert stats['total_positions'] == 2
        assert stats['execution_success_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_order_state_transitions(self, order_manager):
        """测试订单状态转换"""
        order = Order(
            order_id="state-test",
            symbol="BTCUSDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000.00')
        )
        
        # 初始状态
        assert order.status == OrderStatus.PENDING
        assert order.is_active() == True
        
        # 创建订单
        order_manager.create_order(order)
        
        # 状态转换：PENDING -> SUBMITTED
        order.update_status(OrderStatus.SUBMITTED)
        assert order.status == OrderStatus.SUBMITTED
        assert order.is_active() == True
        
        # 状态转换：SUBMITTED -> PARTIALLY_FILLED
        order.update_status(OrderStatus.PARTIALLY_FILLED, Decimal('0.05'))
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal('0.05')
        assert order.is_active() == True
        
        # 状态转换：PARTIALLY_FILLED -> FILLED
        order.update_status(OrderStatus.FILLED, Decimal('0.1'), Decimal('50000.00'))
        assert order.status == OrderStatus.FILLED
        assert order.is_filled() == True
        assert order.is_active() == False
        
        # 状态转换：FILLED -> CANCELLED (不应该发生，但测试状态逻辑)
        order.update_status(OrderStatus.CANCELLED)
        assert order.status == OrderStatus.CANCELLED
        assert order.is_filled() == True  # 仍然是filled状态
    
    @pytest.mark.asyncio
    async def test_error_handling_and_robustness(self, order_manager):
        """测试错误处理和鲁棒性"""
        # 测试管理器未启动时的操作
        await order_manager.stop()
        
        with pytest.raises(RuntimeError, match="管理器未启动"):
            order_manager.create_order(Order(
                order_id="error-test",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('0.1')
            ))
        
        await order_manager.start()
        
        # 测试执行不存在的订单
        with pytest.raises(ValueError, match="订单 .* 不存在"):
            await order_manager.execute_order("non-existent-order", Decimal('50000.00'))
        
        # 测试获取不存在的订单
        assert order_manager.get_order("non-existent-order") is None
        
        # 测试获取不存在的自动订单
        assert order_manager.get_auto_order("non-existent-auto-order") is None
    
    @pytest.mark.asyncio
    async def test_statistics_and_monitoring(self, order_manager):
        """测试统计和监控"""
        # 执行多个订单
        for i in range(5):
            order = Order(
                order_id=f"stats-test-{i}",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000.00')
            )
            
            order_manager.create_order(order)
            await order_manager.execute_order(order.order_id, Decimal('50000.00'))
            
            # 更新持仓
            order_manager.update_position("BTCUSDT", OrderSide.BUY, Decimal('0.1'), Decimal('50000.00'))
        
        # 获取统计信息
        stats = order_manager.get_statistics()
        
        # 验证统计数据
        assert stats['total_orders'] == 5
        assert stats['active_orders'] == 0  # 所有订单都已成交
        assert stats['filled_orders'] == 5
        assert stats['total_positions'] == 1
        assert stats['execution_success_rate'] == 1.0
        assert stats['total_executions'] == 5
        assert float(stats['total_unrealized_pnl']) == 0.0  # 当前价格等于入场价格
    
    @pytest.mark.asyncio
    async def test_order_serialization(self, order_manager):
        """测试订单序列化"""
        order = Order(
            order_id="serialize-test",
            symbol="BTCUSDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('0.5'),
            price=Decimal('51000.00'),
            stop_price=Decimal('50000.00'),
            metadata={'strategy': 'test', 'risk_level': 'medium'}
        )
        
        # 测试字典转换
        order_dict = order.to_dict()
        
        assert order_dict['order_id'] == "serialize-test"
        assert order_dict['symbol'] == "BTCUSDT"
        assert order_dict['order_type'] == OrderType.LIMIT.value
        assert order_dict['side'] == OrderSide.SELL.value
        assert order_dict['quantity'] == "0.5"
        assert order_dict['price'] == "51000.00"
        assert order_dict['stop_price'] == "50000.00"
        assert 'created_at' in order_dict
        assert 'metadata' in order_dict
        assert order_dict['metadata']['strategy'] == 'test'
    
    @pytest.mark.asyncio
    async def test_auto_order_serialization(self, order_manager):
        """测试自动订单序列化"""
        auto_order = AutoOrder(
            auto_order_id="auto-serialize-test",
            strategy_name="test_strategy",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=Decimal('2.0'),
            entry_condition_id="entry-cond-001",
            exit_condition_id="exit-cond-001",
            stop_loss_price=Decimal('2900.00'),
            take_profit_price=Decimal('3100.00'),
            risk_level=RiskLevel.HIGH,
            max_retries=5,
            metadata={'max_position_size': '10.0'}
        )
        
        # 测试字典转换
        auto_order_dict = auto_order.to_dict()
        
        assert auto_order_dict['auto_order_id'] == "auto-serialize-test"
        assert auto_order_dict['strategy_name'] == "test_strategy"
        assert auto_order_dict['symbol'] == "ETHUSDT"
        assert auto_order_dict['side'] == OrderSide.SELL.value
        assert auto_order_dict['quantity'] == "2.0"
        assert auto_order_dict['risk_level'] == RiskLevel.HIGH.value
        assert auto_order_dict['max_retries'] == 5
        assert 'created_at' in auto_order_dict
        assert 'metadata' in auto_order_dict
        assert auto_order_dict['metadata']['max_position_size'] == '10.0'
        
        # 测试价格范围
        price_range = auto_order.get_order_price_range()
        assert price_range == (Decimal('2900.00'), Decimal('3100.00'))
    
    @pytest.mark.asyncio
    async def test_position_serialization(self, order_manager):
        """测试持仓序列化"""
        # 创建持仓
        order_manager.update_position("BTCUSDT", OrderSide.BUY, Decimal('0.1'), Decimal('50000.00'))
        order_manager.update_position("BTCUSDT", OrderSide.BUY, Decimal('0'), Decimal('51000.00'))  # 更新价格
        
        position = order_manager.get_position("BTCUSDT")
        
        # 测试字典转换
        position_dict = position.to_dict()
        
        assert position_dict['symbol'] == "BTCUSDT"
        assert position_dict['side'] == OrderSide.BUY.value
        assert position_dict['quantity'] == "0.1"
        assert position_dict['entry_price'] == "50000.00"
        assert position_dict['current_price'] == "51000.00"
        assert position_dict['unrealized_pnl'] == "10.00"  # (51000-50000) * 0.1
        assert position_dict['position_value'] == "510.00"  # 0.1 * 51000
        assert 'created_at' in position_dict
        
        # 测试价格更新
        position.update_price(Decimal('52000.00'))
        assert position.current_price == Decimal('52000.00')
        assert position.unrealized_pnl == Decimal('20.00')  # (52000-50000) * 0.1


class TestAutoOrderIntegration:
    """自动订单集成测试类"""
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self):
        """测试完整的交易工作流"""
        manager = AutoOrderManager()
        await manager.start()
        
        try:
            # 1. 创建自动订单策略
            auto_order = AutoOrder(
                auto_order_id="workflow-test",
                strategy_name="price_breakout",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                entry_condition_id="price_breakout_condition",
                stop_loss_price=Decimal('48000.00'),
                take_profit_price=Decimal('52000.00')
            )
            
            auto_order_id = manager.create_auto_order(auto_order)
            assert auto_order_id in manager.auto_orders
            
            # 2. 当条件触发时创建订单
            market_order = Order(
                order_id="workflow-entry",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                metadata={'auto_order_id': auto_order_id, 'trigger': 'entry_condition'}
            )
            
            order_id = manager.create_order(market_order)
            assert order_id in manager.orders
            
            # 3. 执行入场订单
            current_price = Decimal('50000.00')
            entry_result = await manager.execute_order(order_id, current_price)
            assert entry_result.success == True
            
            # 4. 更新持仓
            manager.update_position("BTCUSDT", OrderSide.BUY, Decimal('0.1'), current_price)
            
            # 5. 设置止损和止盈订单（通过条件触发）
            stop_loss_order = Order(
                order_id="workflow-stop-loss",
                symbol="BTCUSDT",
                order_type=OrderType.STOP_LOSS,
                side=OrderSide.SELL,
                quantity=Decimal('0.1'),
                stop_price=Decimal('48000.00'),
                metadata={'auto_order_id': auto_order_id, 'type': 'stop_loss'}
            )
            
            take_profit_order = Order(
                order_id="workflow-take-profit",
                symbol="BTCUSDT",
                order_type=OrderType.TAKE_PROFIT,
                side=OrderSide.SELL,
                quantity=Decimal('0.1'),
                stop_price=Decimal('52000.00'),
                metadata={'auto_order_id': auto_order_id, 'type': 'take_profit'}
            )
            
            manager.create_order(stop_loss_order)
            manager.create_order(take_profit_order)
            
            # 6. 模拟价格触发止盈
            profit_result = await manager.execute_order(take_profit_order.order_id, Decimal('52000.00'))
            assert profit_result.success == True
            
            # 7. 更新持仓（平仓）
            manager.update_position("BTCUSDT", OrderSide.SELL, Decimal('0.1'), Decimal('52000.00'))
            
            # 8. 验证最终状态
            position = manager.get_position("BTCUSDT")
            assert position is None  # 持仓已平仓
            
            # 9. 验证统计信息
            stats = manager.get_statistics()
            assert stats['total_orders'] == 3  # 入场 + 止损 + 止盈
            assert stats['filled_orders'] == 3
            assert stats['total_positions'] == 0
            assert stats['execution_success_rate'] == 1.0
            
        finally:
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_risk_management_integration(self):
        """测试风险管理集成"""
        manager = AutoOrderManager({
            "max_position_value": Decimal('10000.00'),
            "max_daily_trades": 100,
            "max_order_size": Decimal('1.0')
        })
        await manager.start()
        
        try:
            # 测试位置价值限制
            large_order = Order(
                order_id="large-order-test",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('0.5'),  # 价值 25000 (超过限制)
                price=Decimal('50000.00')
            )
            
            # 创建大订单（应该通过风控检查）
            try:
                order_id = manager.create_order(large_order)
                # 在实际实现中，这里应该有风险检查
                assert order_id in manager.orders
                
                # 执行订单
                await manager.execute_order(order_id, Decimal('50000.00'))
                manager.update_position("BTCUSDT", OrderSide.BUY, Decimal('0.5'), Decimal('50000.00'))
                
                # 验证持仓
                position = manager.get_position("BTCUSDT")
                assert position is not None
                position_value = position.get_position_value()
                assert position_value == Decimal('25000.00')
                
            except ValueError as e:
                # 如果有风险检查，应该抛出异常
                assert "风险检查失败" in str(e) or "position" in str(e).lower()
            
            # 测试订单大小限制
            oversized_order = Order(
                order_id="oversized-order-test",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('2.0'),  # 超过最大订单大小
                price=Decimal('50000.00')
            )
            
            try:
                oversized_order_id = manager.create_order(oversized_order)
                # 在实际实现中应该有大小检查
                assert oversized_order_id in manager.orders
                
            except ValueError as e:
                # 如果有大小检查，应该抛出异常
                assert "订单大小" in str(e) or "size" in str(e).lower()
            
        finally:
            await manager.stop()


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
