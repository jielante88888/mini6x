#!/usr/bin/env python3
"""
套利策略测试脚本
测试套利策略的基本功能和性能
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

# 导入策略模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

from strategies.spot.arbitrage import (
    ArbitrageStrategy, 
    ExchangeName, 
    ExchangePrice, 
    ArbitrageOpportunity
)
from strategies.base import (
    StrategyConfig, 
    StrategyType, 
    MarketData,
    OrderSide,
    OrderType,
    ValidationException
)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockOrderManager:
    """模拟订单管理器"""
    
    def __init__(self):
        self.orders = {}
        self.order_counter = 0
    
    async def create_order(self, user_id, account_id, symbol, order_side, quantity, order_type, price=None, client_order_id=None):
        self.order_counter += 1
        order_id = f"mock_order_{self.order_counter}"
        
        order = type('MockOrder', (), {
            'id': order_id,
            'user_id': user_id,
            'account_id': account_id,
            'symbol': symbol,
            'order_side': order_side.value if hasattr(order_side, 'value') else order_side,
            'quantity': quantity,
            'order_type': order_type.value if hasattr(order_type, 'value') else order_type,
            'price': price,
            'quantity_filled': quantity,
            'average_price': price or Decimal('50000'),
            'commission': price * quantity * Decimal('0.001') if price else Decimal('50'),
            'status': 'filled'
        })()
        
        self.orders[order_id] = order
        return order
    
    async def execute_order(self, order_id, user_id, account_id, current_price=None):
        return True


async def test_arbitrage_strategy_initialization():
    """测试套利策略初始化"""
    logger.info("测试套利策略初始化...")
    
    try:
        # 创建策略配置
        config = StrategyConfig(
            strategy_id="arb_test_001",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.005')  # 0.5%
        )
        
        # 创建订单管理器
        order_manager = MockOrderManager()
        
        # 创建套利策略
        strategy = ArbitrageStrategy(config, order_manager)
        
        # 初始化策略
        success = await strategy.initialize()
        
        assert success, "策略初始化应该成功"
        
        # 检查策略状态
        state = strategy.get_state()
        assert state.status.value == "created", f"策略状态应该是created，实际是{state.status.value}"
        
        logger.info("✓ 套利策略初始化测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利策略初始化测试失败: {e}")
        return False


async def test_arbitrage_opportunity_calculation():
    """测试套利机会计算"""
    logger.info("测试套利机会计算...")
    
    try:
        config = StrategyConfig(
            strategy_id="arb_calc_test",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.005')
        )
        
        strategy = ArbitrageStrategy(config)
        
        # 创建价格数据
        binance_price = ExchangePrice(
            exchange=ExchangeName.BINANCE,
            symbol="BTCUSDT",
            bid_price=Decimal('50000'),
            ask_price=Decimal('50100'),
            bid_quantity=Decimal('10'),
            ask_quantity=Decimal('10'),
            timestamp=datetime.now()
        )
        
        okx_price = ExchangePrice(
            exchange=ExchangeName.OKX,
            symbol="BTCUSDT",
            bid_price=Decimal('50150'),
            ask_price=Decimal('50250'),
            bid_quantity=Decimal('5'),
            ask_quantity=Decimal('5'),
            timestamp=datetime.now()
        )
        
        # 更新价格数据
        strategy.update_exchange_price(ExchangeName.BINANCE, {
            'symbol': 'BTCUSDT',
            'bid_price': '50000',
            'ask_price': '50100',
            'bid_quantity': '10',
            'ask_quantity': '10'
        })
        
        strategy.update_exchange_price(ExchangeName.OKX, {
            'symbol': 'BTCUSDT',
            'bid_price': '50150',
            'ask_price': '50250',
            'bid_quantity': '5',
            'ask_quantity': '5'
        })
        
        # 计算套利机会
        opportunity = strategy._calculate_arbitrage_opportunity(binance_price, okx_price)
        
        assert opportunity is not None, "应该检测到套利机会"
        assert opportunity.buy_exchange == ExchangeName.BINANCE, "买入交易所应该是binance"
        assert opportunity.sell_exchange == ExchangeName.OKX, "卖出交易所应该是okx"
        assert opportunity.buy_price < opportunity.sell_price, "买入价格应该低于卖出价格"
        
        logger.info(f"✓ 检测到套利机会: 买入价{opportunity.buy_price}, 卖出价{opportunity.sell_price}")
        logger.info(f"✓ 预期盈利: {opportunity.potential_profit}, 净盈利: {opportunity.net_profit_after_fees}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利机会计算测试失败: {e}")
        return False


async def test_arbitrage_strategy_lifecycle():
    """测试套利策略生命周期"""
    logger.info("测试套利策略生命周期...")
    
    try:
        config = StrategyConfig(
            strategy_id="arb_lifecycle_test",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001')
        )
        
        order_manager = MockOrderManager()
        strategy = ArbitrageStrategy(config, order_manager)
        
        # 初始化
        await strategy.initialize()
        assert strategy.state.status.value == "created"
        
        # 启动
        success = await strategy.start()
        assert success, "策略启动应该成功"
        assert strategy.state.status.value == "running"
        assert strategy.is_monitoring, "策略监控应该启用"
        
        # 暂停
        success = await strategy.pause()
        assert success, "策略暂停应该成功"
        assert strategy.state.status.value == "paused"
        assert not strategy.is_monitoring, "策略监控应该停止"
        
        # 恢复
        success = await strategy.resume()
        assert success, "策略恢复应该成功"
        assert strategy.state.status.value == "running"
        assert strategy.is_monitoring, "策略监控应该重新启用"
        
        # 停止
        success = await strategy.stop()
        assert success, "策略停止应该成功"
        assert strategy.state.status.value == "stopped"
        
        logger.info("✓ 套利策略生命周期测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利策略生命周期测试失败: {e}")
        return False


async def test_arbitrage_performance_metrics():
    """测试套利策略性能指标"""
    logger.info("测试套利策略性能指标...")
    
    try:
        config = StrategyConfig(
            strategy_id="arb_metrics_test",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001')
        )
        
        strategy = ArbitrageStrategy(config)
        
        # 模拟一些套利活动
        strategy.total_arbitrage_cycles = 10
        strategy.successful_arbitrage_cycles = 8
        strategy.total_arbitrage_profit = Decimal('0.005')
        strategy.average_execution_time = Decimal('2.5')
        
        # 获取性能指标
        metrics = strategy.get_performance_metrics()
        
        assert 'arbitrage_cycles_completed' in metrics, "应该包含套利周期数"
        assert 'arbitrage_success_rate' in metrics, "应该包含套利成功率"
        assert 'total_arbitrage_profit' in metrics, "应该包含总套利盈利"
        assert metrics['arbitrage_success_rate'] == 0.8, f"成功率应该是0.8，实际是{metrics['arbitrage_success_rate']}"
        
        # 获取状态信息
        status = strategy.get_arbitrage_status()
        assert 'active_opportunities' in status, "应该包含活跃机会数"
        assert 'exchanges_monitored' in status, "应该包含监控交易所数"
        
        logger.info(f"✓ 性能指标测试通过: 成功率{metrics['arbitrage_success_rate']}")
        logger.info(f"✓ 总套利盈利: {metrics['total_arbitrage_profit']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利策略性能指标测试失败: {e}")
        return False


async def test_arbitrage_config_validation():
    """测试套利策略配置验证"""
    logger.info("测试套利策略配置验证...")
    
    try:
        from strategies.spot.arbitrage import validate_arbitrage_config
        
        # 有效配置
        valid_config = StrategyConfig(
            strategy_id="valid_arb",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.005')
        )
        
        assert validate_arbitrage_config(valid_config), "有效配置应该通过验证"
        
        # 无效配置 - 错误的策略类型
        invalid_config1 = StrategyConfig(
            strategy_id="invalid_arb1",
            strategy_type=StrategyType.GRID,  # 错误的策略类型
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001')
        )
        
        assert not validate_arbitrage_config(invalid_config1), "错误策略类型应该验证失败"
        
        # 无效配置 - 过高的阈值
        invalid_config2 = StrategyConfig(
            strategy_id="invalid_arb2",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.2')  # 20% 超过限制
        )
        
        assert not validate_arbitrage_config(invalid_config2), "过高阈值应该验证失败"
        
        logger.info("✓ 套利策略配置验证测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利策略配置验证测试失败: {e}")
        return False


async def test_arbitrage_strategy_integration():
    """测试套利策略集成"""
    logger.info("测试套利策略集成...")
    
    try:
        config = StrategyConfig(
            strategy_id="arb_integration_test",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.01')  # 1%
        )
        
        order_manager = MockOrderManager()
        strategy = ArbitrageStrategy(config, order_manager)
        
        # 初始化和启动策略
        await strategy.initialize()
        await strategy.start()
        
        # 创建市场数据
        market_data = MarketData(
            symbol="BTCUSDT",
            current_price=Decimal('50000'),
            bid_price=Decimal('49900'),
            ask_price=Decimal('50100'),
            volume_24h=Decimal('1000000'),
            price_change_24h=Decimal('0.02'),
            timestamp=datetime.now()
        )
        
        # 设置一些价格数据来模拟套利机会
        strategy.update_exchange_price(ExchangeName.BINANCE, {
            'symbol': 'BTCUSDT',
            'bid_price': '49900',  # 低买
            'ask_price': '50000',
            'bid_quantity': '10',
            'ask_quantity': '10',
            'fee_rate': '0.001'
        })
        
        strategy.update_exchange_price(ExchangeName.OKX, {
            'symbol': 'BTCUSDT',
            'bid_price': '50100',  # 高卖
            'ask_price': '50200',
            'bid_quantity': '10',
            'ask_quantity': '10',
            'fee_rate': '0.001'
        })
        
        # 处理市场数据
        await strategy.process_market_data(market_data)
        
        # 检查是否有订单生成
        orders = await strategy.get_next_orders(market_data)
        logger.info(f"生成了 {len(orders)} 个订单")
        
        # 获取策略状态
        status = strategy.get_arbitrage_status()
        logger.info(f"策略状态: 活跃机会{status['active_opportunities']}, 活跃订单{status['active_orders']}")
        
        # 停止策略
        await strategy.stop()
        
        logger.info("✓ 套利策略集成测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 套利策略集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始套利策略测试")
    logger.info("=" * 60)
    
    tests = [
        ("套利策略初始化", test_arbitrage_strategy_initialization),
        ("套利机会计算", test_arbitrage_opportunity_calculation),
        ("套利策略生命周期", test_arbitrage_strategy_lifecycle),
        ("套利策略性能指标", test_arbitrage_performance_metrics),
        ("套利策略配置验证", test_arbitrage_config_validation),
        ("套利策略集成", test_arbitrage_strategy_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 运行测试: {test_name}")
        try:
            success = await test_func()
            if success:
                passed += 1
                logger.info(f"✅ {test_name} 测试通过")
            else:
                failed += 1
                logger.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} 测试异常: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"测试完成: 通过 {passed} 个, 失败 {failed} 个")
    logger.info("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(run_all_tests())
    if result:
        logger.info("🎉 所有套利策略测试通过!")
        exit(0)
    else:
        logger.error("💥 存在测试失败!")
        exit(1)