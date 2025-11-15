"""
网格策略测试文件
验证网格交易策略的基本功能
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from backend.src.strategies.spot.grid import GridStrategy, GridLevel
from backend.src.strategies.base import (
    StrategyConfig, StrategyType, MarketData, OrderRequest, 
    OrderSide, OrderType, OrderResult
)


class TestGridStrategy:
    """网格策略测试类"""
    
    @pytest.fixture
    def sample_config(self):
        """创建示例策略配置"""
        return StrategyConfig(
            strategy_id="test_grid_001",
            strategy_type=StrategyType.GRID,
            user_id=1001,
            account_id=2001,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.01'),
            grid_levels=5,
            grid_spacing=Decimal('0.02'),
            profit_target=Decimal('0.01'),
            stop_loss=Decimal('0.05'),
            max_daily_loss=Decimal('0.1'),
            max_position_size=Decimal('1.0')
        )
    
    @pytest.fixture
    def grid_strategy(self, sample_config):
        """创建网格策略实例"""
        return GridStrategy(sample_config)
    
    @pytest.fixture
    def mock_order_manager(self):
        """模拟订单管理器"""
        return Mock()
    
    @pytest.fixture
    def sample_market_data(self):
        """创建示例市场数据"""
        return MarketData(
            symbol="BTCUSDT",
            current_price=Decimal('50000.00'),
            bid_price=Decimal('49990.00'),
            ask_price=Decimal('50010.00'),
            volume_24h=Decimal('1000.0'),
            price_change_24h=Decimal('0.02'),
            timestamp=datetime.now(),
            high_24h=Decimal('50500.00'),
            low_24h=Decimal('49500.00')
        )
    
    def test_grid_strategy_initialization(self, grid_strategy, sample_config):
        """测试网格策略初始化"""
        assert grid_strategy.config == sample_config
        assert grid_strategy.config.strategy_type == StrategyType.GRID
        assert len(grid_strategy.grid_levels) == 0
        assert not grid_strategy.is_initialized
        assert grid_strategy.completed_cycles == 0
        assert grid_strategy.total_profit_from_cycles == Decimal('0')
    
    def test_grid_level_creation(self):
        """测试网格层级创建"""
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
    
    def test_grid_level_validation(self):
        """测试网格层级验证"""
        with pytest.raises(Exception):  # ValidationException
            GridLevel(
                level_id="test_level",
                price=Decimal('0'),  # 无效价格
                order_side=OrderSide.BUY,
                quantity=Decimal('0.01')
            )
        
        with pytest.raises(Exception):  # ValidationException
            GridLevel(
                level_id="test_level",
                price=Decimal('50000.00'),
                order_side=OrderSide.BUY,
                quantity=Decimal('0')  # 无效数量
            )
    
    @pytest.mark.asyncio
    async def test_strategy_initialization(self, grid_strategy):
        """测试策略初始化"""
        await grid_strategy.initialize()
        
        assert grid_strategy.is_initialized is True
        assert grid_strategy.state.status.value == "created"
    
    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, grid_strategy):
        """测试策略生命周期"""
        # 初始化
        result = await grid_strategy.initialize()
        assert result is True
        assert grid_strategy.state.status.value == "created"
        
        # 启动
        result = await grid_strategy.start()
        assert result is True
        assert grid_strategy.state.status.value == "running"
        
        # 暂停
        result = await grid_strategy.pause()
        assert result is True
        assert grid_strategy.state.status.value == "paused"
        
        # 恢复
        result = await grid_strategy.resume()
        assert result is True
        assert grid_strategy.state.status.value == "running"
        
        # 停止
        result = await grid_strategy.stop()
        assert result is True
        assert grid_strategy.state.status.value == "stopped"
    
    @pytest.mark.asyncio
    async def test_get_next_orders(self, grid_strategy, sample_market_data):
        """测试获取网格订单"""
        await grid_strategy.initialize()
        await grid_strategy.start()
        
        orders = await grid_strategy.get_next_orders(sample_market_data)
        
        # 应该生成网格订单
        assert len(orders) > 0
        
        # 验证订单格式
        for order in orders:
            assert isinstance(order, OrderRequest)
            assert order.symbol == "BTCUSDT"
            assert order.order_type == OrderType.LIMIT
            assert order.quantity > 0
            assert order.price is not None
            assert order.price > 0
    
    @pytest.mark.asyncio
    async def test_market_data_processing(self, grid_strategy, sample_market_data):
        """测试市场数据处理"""
        await grid_strategy.initialize()
        await grid_strategy.start()
        
        # 处理市场数据
        await grid_strategy.process_market_data(sample_market_data)
        
        # 验证市场数据缓存
        assert grid_strategy.last_market_data == sample_market_data
        assert len(grid_strategy.market_data_history) > 0
    
    @pytest.mark.asyncio
    async def test_order_result_processing(self, grid_strategy):
        """测试订单结果处理"""
        # 创建模拟订单结果
        order_result = OrderResult(
            success=True,
            order_id="test_order_001",
            filled_quantity=Decimal('0.01'),
            average_price=Decimal('50000.00'),
            commission=Decimal('0.1'),
            execution_time=datetime.now()
        )
        
        result = await grid_strategy.process_order_result(order_result)
        assert result is True
        
        # 验证状态更新
        assert grid_strategy.state.total_orders == 1
        assert grid_strategy.state.filled_orders == 1
    
    @pytest.mark.asyncio
    async def test_grid_rebuild(self, grid_strategy, sample_market_data):
        """测试网格重建"""
        await grid_strategy.initialize()
        await grid_strategy.start()
        
        # 第一次构建网格
        await grid_strategy._rebuild_grid(sample_market_data)
        
        assert grid_strategy.upper_price is not None
        assert grid_strategy.lower_price is not None
        assert grid_strategy.center_price is not None
        assert len(grid_strategy.grid_levels) > 0
        
        # 验证网格价格计算
        assert grid_strategy.upper_price > grid_strategy.lower_price
        assert grid_strategy.center_price == sample_market_data.current_price
    
    def test_grid_price_calculation(self, grid_strategy, sample_market_data):
        """测试网格价格计算"""
        current_price = sample_market_data.current_price
        
        # 模拟网格价格计算
        grid_range = current_price * grid_strategy.config.grid_spacing * Decimal(
            grid_strategy.config.grid_levels / 2
        )
        
        expected_upper = current_price + grid_range
        expected_lower = current_price - grid_range
        
        assert expected_upper > current_price
        assert expected_lower < current_price
    
    def test_grid_quantity_calculation(self, grid_strategy):
        """测试网格数量计算"""
        test_price = Decimal('50000.00')
        order_side = OrderSide.BUY
        
        quantity = grid_strategy._calculate_grid_quantity(test_price, order_side)
        
        # 验证数量在合理范围内
        assert quantity >= grid_strategy.config.min_order_size
        assert quantity <= grid_strategy.config.max_order_size
        assert quantity > 0
    
    def test_grid_status(self, grid_strategy, sample_market_data):
        """测试网格状态获取"""
        # 初始化并设置一些测试数据
        grid_strategy.is_initialized = True
        grid_strategy.center_price = sample_market_data.current_price
        grid_strategy.upper_price = Decimal('51000.00')
        grid_strategy.lower_price = Decimal('49000.00')
        grid_strategy.grid_size = Decimal('400.00')
        grid_strategy.completed_cycles = 1
        
        status = grid_strategy.get_grid_status()
        
        # 验证状态信息
        assert status['strategy_id'] == 'test_grid_001'
        assert status['symbol'] == 'BTCUSDT'
        assert status['center_price'] == '50000.00'
        assert status['upper_price'] == '51000.00'
        assert status['lower_price'] == '49000.00'
        assert status['completed_cycles'] == 1
        assert status['is_initialized'] is True
    
    def test_performance_metrics(self, grid_strategy):
        """测试性能指标"""
        # 设置一些测试数据
        grid_strategy.state.total_orders = 10
        grid_strategy.state.filled_orders = 8
        grid_strategy.state.realized_pnl = Decimal('100.00')
        grid_strategy.completed_cycles = 2
        grid_strategy.total_profit_from_cycles = Decimal('200.00')
        
        metrics = grid_strategy.get_performance_metrics()
        
        # 验证基础指标
        assert 'total_trades' in metrics
        assert 'successful_trades' in metrics
        assert 'success_rate' in metrics
        assert 'total_pnl' in metrics
        
        # 验证网格特定指标
        assert 'grid_cycles_completed' in metrics
        assert 'total_grid_profit' in metrics
        assert 'average_cycle_profit' in metrics
        
        assert metrics['grid_cycles_completed'] == 2
        assert metrics['total_grid_profit'] == 200.0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, grid_strategy):
        """测试错误处理"""
        # 测试无效配置
        invalid_config = StrategyConfig(
            strategy_id="invalid_grid",
            strategy_type=StrategyType.GRID,
            user_id=1001,
            account_id=2001,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.01'),
            grid_levels=0,  # 无效配置
            grid_spacing=Decimal('0.02')
        )
        
        with pytest.raises(Exception):
            invalid_strategy = GridStrategy(invalid_config)
            await invalid_strategy.initialize()
    
    def test_grid_validation_function(self):
        """测试网格配置验证函数"""
        from backend.src.strategies.spot.grid import validate_grid_config
        
        # 有效配置
        valid_config = StrategyConfig(
            strategy_id="test",
            strategy_type=StrategyType.GRID,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.01'),
            grid_levels=5,
            grid_spacing=Decimal('0.02')
        )
        
        assert validate_grid_config(valid_config) is True
        
        # 无效配置
        invalid_config = StrategyConfig(
            strategy_id="test",
            strategy_type=StrategyType.MARTINGALE,  # 错误类型
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.01')
        )
        
        assert validate_grid_config(invalid_config) is False


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])