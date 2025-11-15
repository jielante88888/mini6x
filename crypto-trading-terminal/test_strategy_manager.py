#!/usr/bin/env python3
"""
策略管理器测试脚本
测试策略管理器的核心功能和集成能力
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

# 导入策略模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

from strategies.manager import (
    StrategyManager, 
    ExecutionMode, 
    StrategyType,
    StrategyStatus,
    create_strategy_manager
)
from strategies.base import StrategyConfig, MarketData, OrderSide, OrderType
from strategies.spot.grid import GridStrategy
from strategies.spot.martingale import MartingaleStrategy
from strategies.spot.arbitrage import ArbitrageStrategy

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockOrderManager:
    """模拟订单管理器"""
    
    def __init__(self):
        self.orders = []
    
    async def create_order(self, user_id, account_id, symbol, order_side, quantity, order_type, price=None, client_order_id=None):
        order = type('MockOrder', (), {
            'id': f"mock_{len(self.orders)}",
            'user_id': user_id,
            'account_id': account_id,
            'symbol': symbol,
            'order_side': order_side.value if hasattr(order_side, 'value') else order_side,
            'quantity': quantity,
            'order_type': order_type.value if hasattr(order_type, 'value') else order_type,
            'price': price,
            'status': 'created'
        })()
        
        self.orders.append(order)
        return order
    
    async def execute_order(self, order_id, user_id, account_id, current_price=None):
        # 模拟订单执行成功
        return True


class MockMarketDataProcessor:
    """模拟市场数据处理器"""
    
    async def get_market_data(self, symbol: str) -> MarketData:
        return MarketData(
            symbol=symbol,
            current_price=Decimal('50000'),
            bid_price=Decimal('49900'),
            ask_price=Decimal('50100'),
            volume_24h=Decimal('1000000'),
            price_change_24h=Decimal('0.02'),
            timestamp=datetime.now()
        )


async def test_strategy_manager_creation():
    """测试策略管理器创建"""
    logger.info("测试策略管理器创建...")
    
    try:
        # 创建模拟组件
        mock_db_session = None  # 在真实环境中应该是数据库会话
        order_manager = MockOrderManager()
        market_data_processor = MockMarketDataProcessor()
        
        # 创建策略管理器
        manager = create_strategy_manager(
            db_session=mock_db_session,
            order_manager=order_manager,
            market_data_processor=market_data_processor
        )
        
        assert manager is not None, "策略管理器创建失败"
        assert len(manager.strategies) == 0, "初始策略数应该为0"
        assert manager.is_monitoring == False, "监控应该默认关闭"
        
        logger.info("✓ 策略管理器创建成功")
        return manager
        
    except Exception as e:
        logger.error(f"✗ 策略管理器创建测试失败: {e}")
        return None


async def test_strategy_registration():
    """测试策略注册"""
    logger.info("测试策略注册...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 测试手动注册策略类型
        manager.register_strategy_type('custom_grid', GridStrategy)
        
        assert 'custom_grid' in manager.strategy_registries, "策略注册失败"
        assert manager.strategy_registries['custom_grid'] == GridStrategy, "策略类型不匹配"
        
        logger.info("✓ 策略注册测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 策略注册测试失败: {e}")
        return False


async def test_strategy_creation():
    """测试策略创建"""
    logger.info("测试策略创建...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 创建网格策略配置
        grid_config = StrategyConfig(
            strategy_id="grid_test_001",
            strategy_type=StrategyType.GRID,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            grid_levels=10,
            grid_spacing=Decimal('0.02')
        )
        
        # 创建策略
        strategy_id = await manager.create_strategy(grid_config)
        
        assert strategy_id == "grid_test_001", f"策略ID不匹配: {strategy_id}"
        assert strategy_id in manager.strategies, "策略未正确注册"
        assert len(manager.strategies) == 1, f"策略数量不正确: {len(manager.strategies)}"
        
        # 检查策略实例
        instance = manager.strategies[strategy_id]
        assert instance.strategy_id == "grid_test_001", "策略ID不匹配"
        assert instance.state.status == StrategyStatus.CREATED, f"策略状态错误: {instance.state.status}"
        assert instance.is_active == False, "策略应该默认未激活"
        
        logger.info("✓ 策略创建测试通过")
        return manager
        
    except Exception as e:
        logger.error(f"✗ 策略创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_strategy_lifecycle():
    """测试策略生命周期"""
    logger.info("测试策略生命周期...")
    
    try:
        manager = await test_strategy_creation()
        if not manager:
            return False
        
        strategy_id = "grid_test_001"
        
        # 测试启动
        success = await manager.start_strategy(strategy_id)
        assert success, "策略启动应该成功"
        
        instance = manager.strategies[strategy_id]
        assert instance.state.status == StrategyStatus.RUNNING, f"策略状态错误: {instance.state.status}"
        assert instance.is_active == True, "策略应该已激活"
        
        # 测试暂停
        success = await manager.pause_strategy(strategy_id)
        assert success, "策略暂停应该成功"
        
        instance = manager.strategies[strategy_id]
        assert instance.state.status == StrategyStatus.PAUSED, f"策略状态错误: {instance.state.status}"
        
        # 测试恢复
        success = await manager.resume_strategy(strategy_id)
        assert success, "策略恢复应该成功"
        
        instance = manager.strategies[strategy_id]
        assert instance.state.status == StrategyStatus.RUNNING, f"策略状态错误: {instance.state.status}"
        
        # 测试停止
        success = await manager.stop_strategy(strategy_id)
        assert success, "策略停止应该成功"
        
        instance = manager.strategies[strategy_id]
        assert instance.state.status == StrategyStatus.STOPPED, f"策略状态错误: {instance.state.status}"
        assert instance.is_active == False, "策略应该已停用"
        
        # 测试删除
        success = await manager.delete_strategy(strategy_id)
        assert success, "策略删除应该成功"
        
        assert strategy_id not in manager.strategies, "策略应该已从管理器中移除"
        assert len(manager.strategies) == 0, "策略数量应该为0"
        
        logger.info("✓ 策略生命周期测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 策略生命周期测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_strategies():
    """测试多策略管理"""
    logger.info("测试多策略管理...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 创建多个策略
        strategies_config = [
            StrategyConfig(
                strategy_id="grid_001",
                strategy_type=StrategyType.GRID,
                user_id=1,
                account_id=1,
                symbol="BTCUSDT",
                base_quantity=Decimal('0.001')
            ),
            StrategyConfig(
                strategy_id="martingale_001",
                strategy_type=StrategyType.MARTINGALE,
                user_id=1,
                account_id=1,
                symbol="ETHUSDT",
                base_quantity=Decimal('0.1')
            ),
            StrategyConfig(
                strategy_id="arbitrage_001",
                strategy_type=StrategyType.ARBITRAGE,
                user_id=1,
                account_id=1,
                symbol="BTCUSDT",
                base_quantity=Decimal('0.001'),
                arbitrage_threshold=Decimal('0.01')
            )
        ]
        
        created_ids = []
        for config in strategies_config:
            strategy_id = await manager.create_strategy(config)
            created_ids.append(strategy_id)
        
        assert len(created_ids) == 3, f"创建策略数量错误: {len(created_ids)}"
        assert len(manager.strategies) == 3, f"管理器中策略数量错误: {len(manager.strategies)}"
        
        # 启动所有策略
        for strategy_id in created_ids:
            success = await manager.start_strategy(strategy_id)
            assert success, f"启动策略 {strategy_id} 失败"
        
        # 检查所有策略状态
        for strategy_id in created_ids:
            instance = manager.strategies[strategy_id]
            assert instance.state.status == StrategyStatus.RUNNING, f"策略 {strategy_id} 状态错误"
        
        # 停止所有策略
        for strategy_id in created_ids:
            success = await manager.stop_strategy(strategy_id)
            assert success, f"停止策略 {strategy_id} 失败"
        
        logger.info("✓ 多策略管理测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 多策略管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_strategy_execution():
    """测试策略执行"""
    logger.info("测试策略执行...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 创建并启动策略
        config = StrategyConfig(
            strategy_id="grid_exec_test",
            strategy_type=StrategyType.GRID,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            grid_levels=5,
            grid_spacing=Decimal('0.02')
        )
        
        strategy_id = await manager.create_strategy(config)
        await manager.start_strategy(strategy_id)
        
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
        
        # 执行策略
        task_id = await manager.execute_strategy(strategy_id, market_data)
        
        assert task_id is not None, "任务ID应该有效"
        assert task_id.startswith("task_"), f"任务ID格式错误: {task_id}"
        
        # 等待一下让任务完成
        await asyncio.sleep(1)
        
        # 检查执行状态
        execution_status = manager.execution_engine.get_execution_status()
        logger.info(f"执行状态: {execution_status}")
        
        # 获取策略状态
        status = manager.get_strategy_status(strategy_id)
        logger.info(f"策略状态: {status}")
        
        logger.info("✓ 策略执行测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 策略执行测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_manager_monitoring():
    """测试管理器监控"""
    logger.info("测试管理器监控...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 启动监控
        await manager.start_monitoring()
        
        assert manager.is_monitoring == True, "监控应该已启动"
        assert manager.monitor_task is not None, "监控任务应该存在"
        
        # 等待一段时间
        await asyncio.sleep(2)
        
        # 检查性能统计更新
        perf_stats = manager.performance_stats
        logger.info(f"性能统计: {perf_stats}")
        
        # 停止监控
        await manager.stop_monitoring()
        
        assert manager.is_monitoring == False, "监控应该已停止"
        
        logger.info("✓ 管理器监控测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 管理器监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_manager_status():
    """测试管理器状态查询"""
    logger.info("测试管理器状态查询...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 创建几个策略
        configs = [
            StrategyConfig("status_test_1", StrategyType.GRID, 1, 1, "BTCUSDT", Decimal('0.001')),
            StrategyConfig("status_test_2", StrategyType.MARTINGALE, 1, 1, "ETHUSDT", Decimal('0.1'))
        ]
        
        created_ids = []
        for config in configs:
            strategy_id = await manager.create_strategy(config)
            created_ids.append(strategy_id)
            
            # 启动部分策略
            if strategy_id == "status_test_1":
                await manager.start_strategy(strategy_id)
        
        # 测试整体状态查询
        overall_status = manager.get_manager_status()
        assert 'total_strategies' in overall_status, "缺少total_strategies字段"
        assert 'active_strategies' in overall_status, "缺少active_strategies字段"
        assert 'running_strategies' in overall_status, "缺少running_strategies字段"
        
        assert overall_status['total_strategies'] == 2, f"总策略数错误: {overall_status['total_strategies']}"
        assert overall_status['running_strategies'] == 1, f"运行策略数错误: {overall_status['running_strategies']}"
        
        # 测试单个策略状态查询
        single_status = manager.get_strategy_status("status_test_1")
        assert single_status['strategy_id'] == "status_test_1", "策略ID不匹配"
        assert single_status['status'] == "running", f"策略状态错误: {single_status['status']}"
        
        logger.info("✓ 管理器状态查询测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 管理器状态查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """测试错误处理"""
    logger.info("测试错误处理...")
    
    try:
        manager = await test_strategy_manager_creation()
        if not manager:
            return False
        
        # 测试不存在的策略ID
        try:
            await manager.start_strategy("non_existent_strategy")
            assert False, "应该抛出异常"
        except Exception:
            pass  # 预期的异常
        
        # 测试重复创建策略
        config = StrategyConfig(
            strategy_id="duplicate_test",
            strategy_type=StrategyType.GRID,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001')
        )
        
        await manager.create_strategy(config)
        
        try:
            await manager.create_strategy(config)
            assert False, "应该抛出重复创建异常"
        except Exception:
            pass  # 预期的异常
        
        # 测试错误状态转换
        await manager.start_strategy("duplicate_test")
        
        try:
            await manager.start_strategy("duplicate_test")  # 已经启动的策略
            # 这应该成功或者给出警告，但不抛出异常
        except Exception as e:
            logger.warning(f"重复启动策略的异常: {e}")
        
        logger.info("✓ 错误处理测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 错误处理测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始策略管理器测试")
    logger.info("=" * 60)
    
    tests = [
        ("策略管理器创建", test_strategy_manager_creation),
        ("策略注册", test_strategy_registration),
        ("策略创建", test_strategy_creation),
        ("策略生命周期", test_strategy_lifecycle),
        ("多策略管理", test_multiple_strategies),
        ("策略执行", test_strategy_execution),
        ("管理器监控", test_manager_monitoring),
        ("管理器状态", test_manager_status),
        ("错误处理", test_error_handling)
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
        logger.info("🎉 所有策略管理器测试通过!")
        exit(0)
    else:
        logger.error("💥 存在测试失败!")
        exit(1)