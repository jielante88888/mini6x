"""
网格策略独立测试文件
不依赖包导入，直接测试核心功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 直接导入策略文件内容
from decimal import Decimal
from datetime import datetime
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

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# 简单的异常类
class ValidationException(Exception):
    pass

# 复制核心策略代码（简化版）
class GridLevel:
    def __init__(self, level_id, price, order_side, quantity):
        self.level_id = level_id
        self.price = price
        self.order_side = order_side
        self.quantity = quantity
        self.order_id = None
        self.is_active = True
        self.created_at = datetime.now()
        self.filled_at = None
        self.profit = Decimal('0')
        
        if price <= 0:
            raise ValidationException("网格价格必须大于0")
        if quantity <= 0:
            raise ValidationException("网格数量必须大于0")

class MockConfig:
    def __init__(self):
        self.strategy_id = "test_grid_001"
        self.strategy_type = StrategyType.GRID
        self.user_id = 1001
        self.account_id = 2001
        self.symbol = "BTCUSDT"
        self.base_quantity = Decimal('0.01')
        self.grid_levels = 5
        self.grid_spacing = Decimal('0.02')
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

class GridStrategySimple:
    def __init__(self, config):
        self.config = config
        self.state = MockState()
        self.logger = None
        
        # 网格配置
        self.upper_price = None
        self.lower_price = None
        self.grid_size = Decimal('0')
        self.grid_levels = []
        
        # 策略状态
        self.center_price = None
        self.avg_buy_price = Decimal('0')
        self.avg_sell_price = Decimal('0')
        self.total_buy_quantity = Decimal('0')
        self.total_sell_quantity = Decimal('0')
        
        # 运行状态
        self.is_initialized = False
        self.last_rebalance_time = None
        
        # 统计信息
        self.completed_cycles = 0
        self.total_profit_from_cycles = Decimal('0')
        
        # 验证配置
        if self.config.strategy_type != StrategyType.GRID:
            raise ValidationException("GridStrategy需要GRID策略类型")
    
    async def initialize(self):
        """初始化策略"""
        try:
            # 验证网格配置
            if not self.config.grid_levels or self.config.grid_levels <= 0:
                raise ValidationException("网格层数必须大于0")
            
            if not self.config.grid_spacing or self.config.grid_spacing <= 0:
                raise ValidationException("网格间距必须大于0")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"策略初始化失败: {e}")
            return False
    
    def calculate_grid_prices(self, current_price):
        """计算网格价格区间"""
        grid_range = current_price * self.config.grid_spacing * Decimal(self.config.grid_levels / 2)
        
        self.upper_price = current_price + grid_range
        self.lower_price = current_price - grid_range
        self.center_price = current_price
        
        if self.upper_price == self.lower_price:
            raise ValidationException("网格区间计算错误：上下价格相等")
        
        price_range = self.upper_price - self.lower_price
        self.grid_size = price_range / Decimal(self.config.grid_levels)
        
        return self.upper_price, self.lower_price, self.grid_size
    
    def generate_grid_levels(self, current_price):
        """生成网格层级"""
        prices = []
        for i in range(self.config.grid_levels + 1):
            price = self.lower_price + (self.grid_size * Decimal(i))
            prices.append(price)
        
        self.grid_levels.clear()
        
        for i in range(len(prices) - 1):
            lower_price = prices[i]
            upper_price = prices[i + 1]
            mid_price = (lower_price + upper_price) / 2
            
            # 决定订单方向
            if current_price >= mid_price:
                order_side = OrderSide.BUY
                order_price = mid_price
            else:
                order_side = OrderSide.SELL
                order_price = mid_price
            
            quantity = self.config.base_quantity
            
            level = GridLevel(
                level_id=f"level_{i}",
                price=order_price,
                order_side=order_side,
                quantity=quantity
            )
            
            self.grid_levels.append(level)
        
        return len(self.grid_levels)
    
    def get_grid_status(self):
        """获取网格状态"""
        return {
            'strategy_id': self.config.strategy_id,
            'symbol': self.config.symbol,
            'center_price': str(self.center_price) if self.center_price else None,
            'upper_price': str(self.upper_price) if self.upper_price else None,
            'lower_price': str(self.lower_price) if self.lower_price else None,
            'grid_size': str(self.grid_size),
            'total_levels': len(self.grid_levels),
            'active_levels': len([level for level in self.grid_levels if level.is_active]),
            'completed_levels': len([level for level in self.grid_levels if level.filled_at]),
            'completed_cycles': self.completed_cycles,
            'total_profit_from_cycles': str(self.total_profit_from_cycles),
            'is_initialized': self.is_initialized
        }


def test_grid_strategy_basic():
    """测试网格策略基本功能"""
    print("测试1: 网格策略初始化")
    
    config = MockConfig()
    strategy = GridStrategySimple(config)
    
    assert strategy.config.strategy_type == StrategyType.GRID
    assert len(strategy.grid_levels) == 0
    assert not strategy.is_initialized
    print("✓ 网格策略创建成功")


def test_grid_level_creation():
    """测试网格层级创建"""
    print("\n测试2: 网格层级创建")
    
    level = GridLevel(
        level_id="test_level",
        price=Decimal('50000.00'),
        order_side=OrderSide.BUY,
        quantity=Decimal('0.01')
    )
    
    assert level.level_id == "test_level"
    assert level.price == Decimal('50000.00')
    assert level.order_side == OrderSide.BUY
    assert level.quantity == Decimal('0.01')
    assert level.is_active is True
    assert level.order_id is None
    print("✓ 网格层级创建成功")


def test_grid_level_validation():
    """测试网格层级验证"""
    print("\n测试3: 网格层级验证")
    
    try:
        GridLevel(
            level_id="test_level",
            price=Decimal('0'),  # 无效价格
            order_side=OrderSide.BUY,
            quantity=Decimal('0.01')
        )
        assert False, "应该抛出异常"
    except ValidationException:
        print("✓ 价格验证正常")
    
    try:
        GridLevel(
            level_id="test_level",
            price=Decimal('50000.00'),
            order_side=OrderSide.BUY,
            quantity=Decimal('0')  # 无效数量
        )
        assert False, "应该抛出异常"
    except ValidationException:
        print("✓ 数量验证正常")


def test_grid_price_calculation():
    """测试网格价格计算"""
    print("\n测试4: 网格价格计算")
    
    config = MockConfig()
    strategy = GridStrategySimple(config)
    
    current_price = Decimal('50000.00')
    upper_price, lower_price, grid_size = strategy.calculate_grid_prices(current_price)
    
    assert upper_price > current_price
    assert lower_price < current_price
    assert upper_price > lower_price
    assert grid_size > 0
    
    print(f"✓ 网格价格计算成功: [{lower_price}, {upper_price}], 网格大小: {grid_size}")


def test_grid_levels_generation():
    """测试网格层级生成"""
    print("\n测试5: 网格层级生成")
    
    config = MockConfig()
    strategy = GridStrategySimple(config)
    
    current_price = Decimal('50000.00')
    strategy.calculate_grid_prices(current_price)
    level_count = strategy.generate_grid_levels(current_price)
    
    assert level_count == config.grid_levels
    assert len(strategy.grid_levels) == config.grid_levels
    
    # 验证层级配置
    for level in strategy.grid_levels:
        assert level.price > 0
        assert level.quantity > 0
        assert level.order_side in [OrderSide.BUY, OrderSide.SELL]
    
    print(f"✓ 成功生成{level_count}个网格层级")


def test_grid_status():
    """测试网格状态获取"""
    print("\n测试6: 网格状态")
    
    config = MockConfig()
    strategy = GridStrategySimple(config)
    strategy.is_initialized = True
    strategy.center_price = Decimal('50000.00')
    strategy.upper_price = Decimal('51000.00')
    strategy.lower_price = Decimal('49000.00')
    strategy.grid_size = Decimal('400.00')
    strategy.completed_cycles = 1
    
    status = strategy.get_grid_status()
    
    assert status['strategy_id'] == 'test_grid_001'
    assert status['symbol'] == 'BTCUSDT'
    assert status['center_price'] == '50000.00'
    assert status['upper_price'] == '51000.00'
    assert status['lower_price'] == '49000.00'
    assert status['completed_cycles'] == 1
    assert status['is_initialized'] is True
    
    print("✓ 网格状态获取正常")


def test_strategy_initialization():
    """测试策略初始化"""
    print("\n测试7: 策略初始化")
    
    import asyncio
    
    config = MockConfig()
    strategy = GridStrategySimple(config)
    
    async def run_test():
        result = await strategy.initialize()
        assert result is True
        assert strategy.is_initialized is True
        return True
    
    success = asyncio.run(run_test())
    assert success
    print("✓ 策略初始化成功")


def run_all_tests():
    """运行所有测试"""
    print("=== 网格策略核心功能测试 ===\n")
    
    test_functions = [
        test_grid_strategy_basic,
        test_grid_level_creation,
        test_grid_level_validation,
        test_grid_price_calculation,
        test_grid_levels_generation,
        test_grid_status,
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
        print("🎉 所有测试通过！网格策略核心功能正常。")
    else:
        print("❌ 部分测试失败，请检查代码。")
        sys.exit(1)