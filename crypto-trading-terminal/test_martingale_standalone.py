"""
马丁格尔策略独立测试文件
不依赖包导入，直接测试核心功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

# 定义需要的枚举类型
class StrategyType(Enum):
    GRID = "grid"
    MARTINGALE = "martingale"
    ARBITRAGE = "arbitrage"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class StrategyStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

class ValidationException(Exception):
    pass

# 简化的配置类
class MockConfig:
    def __init__(self):
        self.strategy_id = "test_martingale_001"
        self.strategy_type = StrategyType.MARTINGALE
        self.user_id = 1001
        self.account_id = 2001
        self.symbol = "BTCUSDT"
        self.base_quantity = Decimal('0.01')
        self.martingale_multiplier = Decimal('2.0')
        self.max_martingale_steps = 5
        self.profit_target = Decimal('0.01')
        self.stop_loss = Decimal('0.05')
        self.max_daily_loss = Decimal('0.1')
        self.max_position_size = Decimal('1.0')
        self.min_order_size = Decimal('0.001')
        self.max_order_size = Decimal('10.0')
        self.performance_check_interval = 60
        self.risk_check_interval = 30

class MockState:
    def __init__(self):
        self.status = StrategyStatus.CREATED
        self.total_orders = 0
        self.filled_orders = 0
        self.realized_pnl = Decimal('0')
        self.total_profit = Decimal('0')
        self.unrealized_pnl = Decimal('0')
        self.commission_paid = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.daily_trades = 0
        self.max_daily_loss_reached = False
        self.consecutive_losses = 0
        
    def update_performance_metrics(self):
        pass
    
    def is_trading_allowed(self):
        return self.status == StrategyStatus.RUNNING
    
    def should_stop_loss(self):
        return False

# 马丁格尔步骤类
class MartingaleStep:
    def __init__(self, step_id, order_side, quantity, entry_price):
        self.step_id = step_id
        self.order_side = order_side
        self.quantity = quantity
        self.entry_price = entry_price
        self.is_winning_step = False
        self.profit_loss = Decimal('0')
        self.created_at = datetime.now()
        self.closed_at = None
        self.order_id = None
        
        if quantity <= 0:
            raise ValidationException("仓位数量必须大于0")
        if entry_price <= 0:
            raise ValidationException("入场价格必须大于0")
    
    def calculate_profit_loss(self, exit_price):
        """计算盈亏"""
        if self.order_side == OrderSide.BUY:
            return (exit_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - exit_price) * self.quantity

# 马丁格尔策略简化版
class MartingaleStrategySimple:
    def __init__(self, config):
        self.config = config
        self.state = MockState()
        
        # 马丁格尔配置
        self.current_step = 0
        self.consecutive_losses = 0
        self.steps_history = []
        
        # 仓位管理
        self.current_position = Decimal('0')
        self.average_entry_price = Decimal('0')
        self.total_invested = Decimal('0')
        self.total_realized_pnl = Decimal('0')
        
        # 策略方向
        self.trend_direction = None
        self.last_direction = None
        
        # 风险控制
        self.max_consecutive_losses = 10
        self.profit_target_reached = False
        
        # 运行状态
        self.is_in_position = False
        self.last_trade_time = None
        
        # 计算最大总投资
        self.max_total_invested = self.config.base_quantity * \
            sum(Decimal(str(self.config.martingale_multiplier ** i)) 
                for i in range(self.config.max_martingale_steps + 1))
        
        # 验证配置
        if self.config.strategy_type != StrategyType.MARTINGALE:
            raise ValidationException("MartingaleStrategy需要MARTINGALE策略类型")
    
    async def initialize(self):
        """初始化策略"""
        try:
            if not self.config.martingale_multiplier or self.config.martingale_multiplier <= Decimal('1.0'):
                raise ValidationException("马丁格尔倍数必须大于1")
            
            if self.config.max_martingale_steps > 20:
                raise ValidationException("最大马丁格尔步数不能超过20")
            
            return True
            
        except Exception as e:
            print(f"策略初始化失败: {e}")
            return False
    
    def reset_strategy(self):
        """重置策略状态"""
        self.current_step = 0
        self.consecutive_losses = 0
        self.steps_history.clear()
        self.current_position = Decimal('0')
        self.average_entry_price = Decimal('0')
        self.total_invested = Decimal('0')
        self.is_in_position = False
        self.profit_target_reached = False
    
    def calculate_martingale_quantity(self):
        """计算马丁格尔仓位大小"""
        multiplier_factor = Decimal(str(self.config.martingale_multiplier ** self.current_step))
        quantity = self.config.base_quantity * multiplier_factor
        
        # 确保在订单大小限制内
        quantity = max(self.config.min_order_size, 
                      min(quantity, self.config.max_order_size))
        
        return quantity
    
    def determine_trade_direction(self, current_price, previous_price=None):
        """确定交易方向（自适应）"""
        if not previous_price:
            return OrderSide.BUY  # 第一次交易，默认为买入
        
        # 基于价格变化趋势
        price_change = (current_price - previous_price) / previous_price
        
        if price_change > Decimal('0.001'):  # 价格上涨0.1%
            return OrderSide.BUY  # 追涨
        elif price_change < Decimal('-0.001'):  # 价格下跌0.1%
            return OrderSide.SELL  # 追跌
        else:
            # 横盘，继续当前方向或默认为买入
            return self.last_direction or OrderSide.BUY
    
    def should_close_position(self, current_price):
        """检查是否应该平仓"""
        if not self.is_in_position or not self.current_position:
            return False
        
        # 简单的盈利检查
        if self.current_position > 0:  # 多头仓位
            current_pnl = (current_price - self.average_entry_price) * self.current_position
            if current_pnl >= self.config.profit_target:
                return True
        else:  # 空头仓位
            current_pnl = (self.average_entry_price - current_price) * abs(self.current_position)
            if current_pnl >= self.config.profit_target:
                return True
        
        return False
    
    def should_start_new_cycle(self):
        """检查是否应该启动新的马丁格尔周期"""
        # 检查是否已达到最大连续亏损
        if self.consecutive_losses >= self.config.max_martingale_steps:
            return False
        
        # 检查总投资限制
        if self.total_invested >= self.max_total_invested:
            return False
        
        # 检查是否盈利目标已达成
        if self.profit_target_reached:
            return False
        
        return not self.is_in_position
    
    def create_martingale_step(self, order_side, quantity, entry_price):
        """创建马丁格尔步骤"""
        step = MartingaleStep(
            step_id=f"step_{self.current_step}_{int(datetime.now().timestamp())}",
            order_side=order_side,
            quantity=quantity,
            entry_price=entry_price
        )
        
        self.steps_history.append(step)
        self.last_direction = order_side
        self.last_trade_time = datetime.now()
        
        return step
    
    def update_martingale_state(self, step, profit_loss):
        """更新马丁格尔状态"""
        # 更新累计盈亏
        self.total_realized_pnl += profit_loss
        self.state.realized_pnl = self.total_realized_pnl
        self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
        
        # 更新连续亏损计数
        if profit_loss < 0:
            self.consecutive_losses += 1
            self.state.consecutive_losses = self.consecutive_losses
        else:
            self.consecutive_losses = 0
            self.state.consecutive_losses = 0
        
        # 更新当前仓位和平均价格
        if step.order_side == OrderSide.BUY:
            if self.current_position >= 0:
                # 增加多头仓位
                total_cost = self.average_entry_price * self.current_position + step.entry_price * step.quantity
                self.current_position += step.quantity
                self.average_entry_price = total_cost / self.current_position
            else:
                # 减空头仓位
                if step.quantity >= abs(self.current_position):
                    # 完全平仓
                    self.current_position = Decimal('0')
                    self.average_entry_price = Decimal('0')
                else:
                    self.current_position += step.quantity  # 空头减少
            
            self.total_invested += step.quantity
        else:  # SELL
            if self.current_position <= 0:
                # 增加空头仓位
                total_cost = self.average_entry_price * abs(self.current_position) + step.entry_price * step.quantity
                self.current_position -= step.quantity  # 空头增加（负值）
                self.average_entry_price = total_cost / abs(self.current_position)
            else:
                # 减多头仓位
                if step.quantity >= self.current_position:
                    # 完全平仓
                    self.current_position = Decimal('0')
                    self.average_entry_price = Decimal('0')
                else:
                    self.current_position -= step.quantity
            
            self.total_invested += step.quantity
        
        # 更新持仓状态
        self.is_in_position = abs(self.current_position) > Decimal('0.0001')
        
        # 步骤计数
        self.current_step += 1
        
        # 检查是否需要重置
        if profit_loss > 0 or self.current_step >= self.config.max_martingale_steps:
            self.current_step = 0
    
    def get_martingale_status(self):
        """获取马丁格尔策略状态"""
        active_steps = [step for step in self.steps_history if not step.closed_at]
        completed_steps = [step for step in self.steps_history if step.closed_at]
        winning_steps = [step for step in completed_steps if step.is_winning_step]
        
        return {
            'strategy_id': self.config.strategy_id,
            'symbol': self.config.symbol,
            'current_step': self.current_step,
            'consecutive_losses': self.consecutive_losses,
            'max_martingale_steps': self.config.max_martingale_steps,
            'martingale_multiplier': str(self.config.martingale_multiplier),
            'current_position': str(self.current_position),
            'average_entry_price': str(self.average_entry_price),
            'total_invested': str(self.total_invested),
            'total_realized_pnl': str(self.total_realized_pnl),
            'is_in_position': self.is_in_position,
            'trend_direction': self.trend_direction.value if self.trend_direction else 'adaptive',
            'active_steps_count': len(active_steps),
            'completed_steps_count': len(completed_steps),
            'winning_steps_count': len(winning_steps),
            'max_total_invested': str(self.max_total_invested)
        }


def test_martingale_strategy_basic():
    """测试马丁格尔策略基本功能"""
    print("测试1: 马丁格尔策略初始化")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    assert strategy.config.strategy_type == StrategyType.MARTINGALE
    assert len(strategy.steps_history) == 0
    assert strategy.current_step == 0
    assert strategy.consecutive_losses == 0
    assert not strategy.is_in_position
    print("✓ 马丁格尔策略创建成功")


def test_martingale_step_creation():
    """测试马丁格尔步骤创建"""
    print("\n测试2: 马丁格尔步骤创建")
    
    step = MartingaleStep(
        step_id="step_001",
        order_side=OrderSide.BUY,
        quantity=Decimal('0.01'),
        entry_price=Decimal('50000.00')
    )
    
    assert step.step_id == "step_001"
    assert step.order_side == OrderSide.BUY
    assert step.quantity == Decimal('0.01')
    assert step.entry_price == Decimal('50000.00')
    assert not step.is_winning_step
    assert step.profit_loss == Decimal('0')
    print("✓ 马丁格尔步骤创建成功")


def test_martingale_step_validation():
    """测试马丁格尔步骤验证"""
    print("\n测试3: 马丁格尔步骤验证")
    
    try:
        MartingaleStep(
            step_id="step_001",
            order_side=OrderSide.BUY,
            quantity=Decimal('0'),  # 无效数量
            entry_price=Decimal('50000.00')
        )
        assert False, "应该抛出异常"
    except ValidationException:
        print("✓ 数量验证正常")
    
    try:
        MartingaleStep(
            step_id="step_001",
            order_side=OrderSide.BUY,
            quantity=Decimal('0.01'),
            entry_price=Decimal('0')  # 无效价格
        )
        assert False, "应该抛出异常"
    except ValidationException:
        print("✓ 价格验证正常")


def test_martingale_quantity_calculation():
    """测试马丁格尔仓位大小计算"""
    print("\n测试4: 马丁格尔仓位大小计算")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    # 测试不同步骤的仓位大小
    for step in range(6):
        strategy.current_step = step
        quantity = strategy.calculate_martingale_quantity()
        
        expected_quantity = config.base_quantity * (config.martingale_multiplier ** step)
        
        assert quantity == expected_quantity
        assert quantity >= config.min_order_size
        assert quantity <= config.max_order_size
    
    print("✓ 马丁格尔仓位大小计算正确")


def test_martingale_direction_determination():
    """测试马丁格尔方向确定"""
    print("\n测试5: 马丁格尔方向确定")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    # 测试趋势判断
    current_price = Decimal('50000.00')
    previous_price = Decimal('49900.00')  # 价格上涨
    
    direction = strategy.determine_trade_direction(current_price, previous_price)
    assert direction == OrderSide.BUY  # 追涨
    
    previous_price = Decimal('50100.00')  # 价格下跌
    direction = strategy.determine_trade_direction(current_price, previous_price)
    assert direction == OrderSide.SELL  # 追跌
    
    previous_price = Decimal('50000.00')  # 横盘
    direction = strategy.determine_trade_direction(current_price, previous_price)
    assert direction == OrderSide.BUY  # 默认买入
    
    print("✓ 马丁格尔方向确定正确")


def test_profit_loss_calculation():
    """测试盈亏计算"""
    print("\n测试6: 盈亏计算")
    
    # 测试多头盈亏
    buy_step = MartingaleStep(
        step_id="buy_step",
        order_side=OrderSide.BUY,
        quantity=Decimal('0.01'),
        entry_price=Decimal('50000.00')
    )
    
    profit = buy_step.calculate_profit_loss(Decimal('51000.00'))  # 价格上涨
    assert profit == Decimal('10.00')  # (51000-50000) * 0.01
    
    loss = buy_step.calculate_profit_loss(Decimal('49000.00'))  # 价格下跌
    assert loss == Decimal('-10.00')  # (49000-50000) * 0.01
    
    # 测试空头盈亏
    sell_step = MartingaleStep(
        step_id="sell_step",
        order_side=OrderSide.SELL,
        quantity=Decimal('0.01'),
        entry_price=Decimal('50000.00')
    )
    
    profit = sell_step.calculate_profit_loss(Decimal('49000.00'))  # 价格下跌，空头盈利
    assert profit == Decimal('10.00')  # (50000-49000) * 0.01
    
    loss = sell_step.calculate_profit_loss(Decimal('51000.00'))  # 价格上涨，空头亏损
    assert loss == Decimal('-10.00')  # (50000-51000) * 0.01
    
    print("✓ 盈亏计算正确")


def test_strategy_state_management():
    """测试策略状态管理"""
    print("\n测试7: 策略状态管理")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    # 测试重置
    strategy.current_step = 3
    strategy.consecutive_losses = 2
    strategy.total_invested = Decimal('0.05')
    strategy.is_in_position = True
    
    strategy.reset_strategy()
    
    assert strategy.current_step == 0
    assert strategy.consecutive_losses == 0
    assert strategy.total_invested == Decimal('0')
    assert not strategy.is_in_position
    assert len(strategy.steps_history) == 0
    
    print("✓ 策略状态管理正常")


def test_martingale_status():
    """测试马丁格尔状态获取"""
    print("\n测试8: 马丁格尔状态")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    # 添加一些测试数据
    strategy.current_step = 2
    strategy.consecutive_losses = 1
    strategy.current_position = Decimal('0.05')
    strategy.total_invested = Decimal('0.07')
    strategy.total_realized_pnl = Decimal('0.02')
    strategy.is_in_position = True
    
    # 创建一些步骤记录
    step1 = strategy.create_martingale_step(OrderSide.BUY, Decimal('0.01'), Decimal('50000.00'))
    step1.closed_at = datetime.now()
    step1.profit_loss = Decimal('5.00')
    step1.is_winning_step = True
    
    step2 = strategy.create_martingale_step(OrderSide.BUY, Decimal('0.02'), Decimal('50100.00'))
    
    status = strategy.get_martingale_status()
    
    # 验证状态信息
    assert status['strategy_id'] == 'test_martingale_001'
    assert status['symbol'] == 'BTCUSDT'
    assert status['current_step'] == 2
    assert status['consecutive_losses'] == 1
    assert status['martingale_multiplier'] == '2.0'
    assert status['current_position'] == '0.05'
    assert status['total_invested'] == '0.07'
    assert status['is_in_position'] is True
    assert status['active_steps_count'] == 1
    assert status['completed_steps_count'] == 1
    assert status['winning_steps_count'] == 1
    
    print("✓ 马丁格尔状态获取正常")


def test_martingale_cycle_simulation():
    """测试马丁格尔周期模拟"""
    print("\n测试9: 马丁格尔周期模拟")
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    # 模拟一个简单的马丁格尔周期
    prices = [Decimal('50000.00'), Decimal('49900.00'), Decimal('49800.00'), Decimal('50200.00')]
    
    for i, price in enumerate(prices):
        # 确定方向和数量
        previous_price = prices[i-1] if i > 0 else None
        direction = strategy.determine_trade_direction(price, previous_price)
        quantity = strategy.calculate_martingale_quantity()
        
        # 创建步骤
        step = strategy.create_martingale_step(direction, quantity, price)
        
        # 模拟平仓盈亏
        exit_price = price + Decimal('100.00') if direction == OrderSide.BUY else price - Decimal('100.00')
        profit_loss = step.calculate_profit_loss(exit_price)
        step.profit_loss = profit_loss
        step.is_winning_step = profit_loss > 0
        step.closed_at = datetime.now()
        
        # 更新策略状态
        strategy.update_martingale_state(step, profit_loss)
        
        print(f"步骤 {i}: {direction.value} {quantity}@{price}, 盈亏: {profit_loss}")
    
    # 验证最终状态
    assert len(strategy.steps_history) == len(prices)
    assert strategy.current_step == 0  # 重置了
    assert strategy.total_invested > 0
    assert len([s for s in strategy.steps_history if s.closed_at]) == len(prices)
    
    print("✓ 马丁格尔周期模拟成功")


def test_strategy_initialization():
    """测试策略初始化"""
    print("\n测试10: 策略初始化")
    
    import asyncio
    
    config = MockConfig()
    strategy = MartingaleStrategySimple(config)
    
    async def run_test():
        result = await strategy.initialize()
        assert result is True
        return True
    
    success = asyncio.run(run_test())
    assert success
    print("✓ 策略初始化成功")


def run_all_tests():
    """运行所有测试"""
    print("=== 马丁格尔策略核心功能测试 ===\n")
    
    test_functions = [
        test_martingale_strategy_basic,
        test_martingale_step_creation,
        test_martingale_step_validation,
        test_martingale_quantity_calculation,
        test_martingale_direction_determination,
        test_profit_loss_calculation,
        test_strategy_state_management,
        test_martingale_status,
        test_martingale_cycle_simulation,
        test_strategy_initialization
    ]
    
    passed = 0
    total = len(test_functions)
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {test_func.__name__} - {e}")
    
    print(f"\n=== 测试完成: {passed}/{total} 通过 ===")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("🎉 所有测试通过！马丁格尔策略核心功能正常。")
    else:
        print("❌ 部分测试失败，请检查代码。")
        sys.exit(1)
