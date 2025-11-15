#!/usr/bin/env python3
"""
策略性能跟踪和分析系统测试脚本
测试性能数据收集、分析和报告生成功能
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta

# 导入模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

from backend.src.strategies.analytics import (
    PerformanceAnalyticsEngine,
    StrategyPerformanceTracker,
    create_performance_analytics_engine,
    create_trade_record,
    create_benchmark_data,
    MetricType,
    TimeFrame,
    BenchmarkType
)
from backend.src.strategies.base import StrategyType

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_performance_tracker_creation():
    """测试性能跟踪器创建"""
    logger.info("测试性能跟踪器创建...")
    
    try:
        tracker = StrategyPerformanceTracker(
            strategy_id="test_tracker",
            strategy_type=StrategyType.GRID,
            symbol="BTCUSDT"
        )
        
        assert tracker.strategy_id == "test_tracker", "策略ID不匹配"
        assert tracker.strategy_type == StrategyType.GRID, "策略类型不匹配"
        assert tracker.symbol == "BTCUSDT", "交易对不匹配"
        assert len(tracker.trade_records) == 0, "初始交易记录应该为空"
        assert len(tracker.performance_metrics) == 0, "初始性能指标应该为空"
        
        logger.info("✓ 性能跟踪器创建成功")
        return tracker
        
    except Exception as e:
        logger.error(f"✗ 性能跟踪器创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_trade_record_management():
    """测试交易记录管理"""
    logger.info("测试交易记录管理...")
    
    try:
        tracker = await test_performance_tracker_creation()
        if not tracker:
            return False
        
        # 创建交易记录
        trades = [
            create_trade_record(
                trade_id="trade_001",
                strategy_id="test_tracker",
                symbol="BTCUSDT",
                trade_type="buy",
                quantity=Decimal('0.001'),
                price=Decimal('50000'),
                profit_loss=Decimal('50'),
                commission=Decimal('1')
            ),
            create_trade_record(
                trade_id="trade_002",
                strategy_id="test_tracker",
                symbol="BTCUSDT",
                trade_type="sell",
                quantity=Decimal('0.001'),
                price=Decimal('50100'),
                profit_loss=Decimal('60'),
                commission=Decimal('1')
            ),
            create_trade_record(
                trade_id="trade_003",
                strategy_id="test_tracker",
                symbol="BTCUSDT",
                trade_type="buy",
                quantity=Decimal('0.001'),
                price=Decimal('50200'),
                profit_loss=Decimal('-30'),
                commission=Decimal('1')
            )
        ]
        
        # 添加交易记录
        for trade in trades:
            tracker.add_trade(trade)
        
        assert len(tracker.trade_records) == 3, f"交易记录数量错误: {len(tracker.trade_records)}"
        assert tracker.total_trades == 3, f"总交易次数错误: {tracker.total_trades}"
        assert tracker.total_pnl == Decimal('108'), f"总盈亏错误: {tracker.total_pnl}"  # 49 + 59 - 29
        assert tracker.total_commission == Decimal('3'), f"总手续费错误: {tracker.total_commission}"
        
        # 检查组合价值更新
        expected_value = Decimal('10000') + Decimal('108')  # 初始10000 + 净盈亏108
        assert tracker.current_portfolio_value == expected_value, f"组合价值错误: {tracker.current_portfolio_value}"
        
        # 检查性能指标生成
        assert len(tracker.performance_metrics[MetricType.PROFIT_LOSS.value]) > 0, "应该生成盈亏指标"
        assert len(tracker.performance_metrics[MetricType.WIN_RATE.value]) > 0, "应该生成胜率指标"
        
        logger.info("✓ 交易记录管理测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 交易记录管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_metrics():
    """测试性能指标计算"""
    logger.info("测试性能指标计算...")
    
    try:
        tracker = await test_performance_tracker_creation()
        if not tracker:
            return False
        
        # 添加更多交易记录用于测试
        for i in range(20):
            profit_loss = Decimal(str(100 - i * 5))  # 逐渐减少的盈利
            commission = Decimal('1')
            
            trade = create_trade_record(
                trade_id=f"trade_{i:03d}",
                strategy_id="test_tracker",
                symbol="BTCUSDT",
                trade_type="buy" if i % 2 == 0 else "sell",
                quantity=Decimal('0.001'),
                price=Decimal('50000') + Decimal(str(i)),
                profit_loss=profit_loss,
                commission=commission
            )
            tracker.add_trade(trade)
        
        # 计算指标
        win_rate = tracker.calculate_win_rate()
        profit_factor = tracker.calculate_profit_factor()
        summary = tracker.get_performance_summary()
        
        assert win_rate >= 0, f"胜率应该非负: {win_rate}"
        assert win_rate <= 1, f"胜率应该小于等于1: {win_rate}"
        assert profit_factor > 0, f"盈利因子应该大于0: {profit_factor}"
        assert 'strategy_id' in summary, "性能摘要应该包含策略ID"
        assert 'total_pnl' in summary, "性能摘要应该包含总盈亏"
        assert 'win_rate' in summary, "性能摘要应该包含胜率"
        
        logger.info(f"✓ 性能指标计算测试通过")
        logger.info(f"  胜率: {win_rate:.2%}")
        logger.info(f"  盈利因子: {profit_factor:.2f}")
        logger.info(f"  总交易次数: {tracker.total_trades}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 性能指标计算测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analytics_engine():
    """测试分析引擎"""
    logger.info("测试分析引擎...")
    
    try:
        engine = create_performance_analytics_engine()
        
        # 注册策略
        tracker1 = engine.register_strategy("strategy_grid", StrategyType.GRID, "BTCUSDT")
        tracker2 = engine.register_strategy("strategy_martingale", StrategyType.MARTINGALE, "ETHUSDT")
        
        assert len(engine.trackers) == 2, f"策略数量错误: {len(engine.trackers)}"
        assert "strategy_grid" in engine.trackers, "网格策略未注册"
        assert "strategy_martingale" in engine.trackers, "马丁格尔策略未注册"
        
        # 添加交易数据
        trades_data = [
            # 网格策略交易
            ("trade_001", "strategy_grid", "BTCUSDT", "buy", Decimal('0.001'), Decimal('50000'), Decimal('100'), Decimal('1')),
            ("trade_002", "strategy_grid", "BTCUSDT", "sell", Decimal('0.001'), Decimal('50100'), Decimal('80'), Decimal('1')),
            ("trade_003", "strategy_grid", "BTCUSDT", "buy", Decimal('0.001'), Decimal('50200'), Decimal('60'), Decimal('1')),
            
            # 马丁格尔策略交易
            ("trade_004", "strategy_martingale", "ETHUSDT", "buy", Decimal('0.1'), Decimal('3000'), Decimal('150'), Decimal('0.5')),
            ("trade_005", "strategy_martingale", "ETHUSDT", "sell", Decimal('0.1'), Decimal('3010'), Decimal('120'), Decimal('0.5')),
            ("trade_006", "strategy_martingale", "ETHUSDT", "buy", Decimal('0.2'), Decimal('3020'), Decimal('-50'), Decimal('1')),
        ]
        
        for trade_id, strategy_id, symbol, trade_type, quantity, price, profit_loss, commission in trades_data:
            trade = create_trade_record(
                trade_id=trade_id,
                strategy_id=strategy_id,
                symbol=symbol,
                trade_type=trade_type,
                quantity=quantity,
                price=price,
                profit_loss=profit_loss,
                commission=commission
            )
            engine.add_trade_record(trade)
        
        # 测试单个策略性能查询
        grid_performance = engine.get_strategy_performance("strategy_grid")
        assert grid_performance is not None, "应该返回网格策略性能"
        assert grid_performance['strategy_id'] == "strategy_grid", "策略ID不匹配"
        
        # 测试策略比较
        comparison = engine.compare_strategies(["strategy_grid", "strategy_martingale"])
        assert 'comparison_results' in comparison, "比较结果应该包含详细信息"
        assert 'ranking' in comparison, "比较结果应该包含排名"
        
        # 测试性能报告生成
        report = engine.generate_performance_report("strategy_grid")
        assert 'strategy_id' in report, "报告应该包含策略ID"
        assert 'performance_summary' in report, "报告应该包含性能摘要"
        assert 'recommendations' in report, "报告应该包含建议"
        
        logger.info("✓ 分析引擎测试通过")
        return engine
        
    except Exception as e:
        logger.error(f"✗ 分析引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_benchmark_comparison():
    """测试基准比较功能"""
    logger.info("测试基准比较功能...")
    
    try:
        engine = await test_analytics_engine()
        if not engine:
            return False
        
        # 添加基准数据
        base_price = Decimal('50000')
        for i in range(30):  # 30天的基准数据
            price_variation = Decimal(str(i * 10))  # 每天上涨10美元
            benchmark_price = base_price + price_variation
            
            benchmark_data = create_benchmark_data(
                timestamp=datetime.now() - timedelta(days=30-i),
                value=benchmark_price,
                benchmark_type=BenchmarkType.BUY_AND_HOLD,
                symbol="BTCUSDT"
            )
            engine.add_benchmark_data(benchmark_data)
        
        # 生成包含基准比较的报告
        report = engine.generate_performance_report("strategy_grid")
        
        assert 'benchmark_comparison' in report, "报告应该包含基准比较"
        benchmark_comparison = report['benchmark_comparison']
        assert 'benchmark_return' in benchmark_comparison, "应该包含基准收益率"
        assert 'strategy_return' in benchmark_comparison, "应该包含策略收益率"
        
        logger.info("✓ 基准比较功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 基准比较功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_data_export():
    """测试数据导出功能"""
    logger.info("测试数据导出功能...")
    
    try:
        tracker = await test_performance_tracker_creation()
        if not tracker:
            return False
        
        # 添加一些交易记录
        for i in range(10):
            trade = create_trade_record(
                trade_id=f"export_test_{i:03d}",
                strategy_id="export_test",
                symbol="BTCUSDT",
                trade_type="buy",
                quantity=Decimal('0.001'),
                price=Decimal('50000') + Decimal(str(i * 100)),
                profit_loss=Decimal(str(50 - i * 5)),
                commission=Decimal('1')
            )
            tracker.add_trade(trade)
        
        # 导出数据
        exported_data = tracker.export_performance_data()
        
        assert 'strategy_summary' in exported_data, "导出数据应该包含策略摘要"
        assert 'trades' in exported_data, "导出数据应该包含交易记录"
        assert 'metrics' in exported_data, "导出数据应该包含性能指标"
        assert 'snapshots' in exported_data, "导出数据应该包含性能快照"
        
        assert len(exported_data['trades']) == 10, f"导出的交易记录数量错误: {len(exported_data['trades'])}"
        assert len(exported_data['metrics']) > 0, "导出的性能指标应该不为空"
        
        logger.info("✓ 数据导出功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 数据导出功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_recommendations():
    """测试智能建议功能"""
    logger.info("测试智能建议功能...")
    
    try:
        engine = await test_analytics_engine()
        if not engine:
            return False
        
        # 生成报告并检查建议
        report = engine.generate_performance_report("strategy_grid")
        
        assert 'recommendations' in report, "报告应该包含建议"
        recommendations = report['recommendations']
        assert isinstance(recommendations, list), "建议应该是列表格式"
        assert len(recommendations) > 0, "应该至少有一个建议"
        
        # 检查建议内容是否合理
        for recommendation in recommendations:
            assert isinstance(recommendation, str), "建议应该是字符串格式"
            assert len(recommendation) > 0, "建议内容不应为空"
        
        logger.info(f"✓ 智能建议功能测试通过")
        logger.info(f"  建议数量: {len(recommendations)}")
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"  建议{i}: {rec}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 智能建议功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_analysis():
    """测试深度性能分析"""
    logger.info("测试深度性能分析...")
    
    try:
        engine = await test_analytics_engine()
        if not engine:
            return False
        
        # 生成详细报告
        report = engine.generate_performance_report("strategy_grid", timedelta(days=7))
        
        # 检查报告结构
        assert 'trade_analysis' in report, "报告应该包含交易分析"
        assert 'risk_analysis' in report, "报告应该包含风险分析"
        assert 'return_analysis' in report, "报告应该包含收益率分析"
        
        # 检查交易分析
        trade_analysis = report['trade_analysis']
        assert 'total_trades' in trade_analysis, "交易分析应该包含总交易数"
        assert 'profitable_trades' in trade_analysis, "交易分析应该包含盈利交易数"
        assert 'avg_profit_per_winning_trade' in trade_analysis, "交易分析应该包含平均盈利"
        
        # 检查风险分析
        risk_analysis = report['risk_analysis']
        assert 'volatility' in risk_analysis, "风险分析应该包含波动率"
        assert 'sharpe_ratio' in risk_analysis, "风险分析应该包含夏普比率"
        assert 'risk_level' in risk_analysis, "风险分析应该包含风险等级"
        
        # 检查收益率分析
        return_analysis = report['return_analysis']
        assert 'total_return_30d' in return_analysis, "收益率分析应该包含总收益率"
        assert 'annualized_return' in return_analysis, "收益率分析应该包含年化收益率"
        
        logger.info("✓ 深度性能分析测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 深度性能分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_strategies_comparison():
    """测试多策略对比分析"""
    logger.info("测试多策略对比分析...")
    
    try:
        engine = create_performance_analytics_engine()
        
        # 注册多个策略
        strategies = [
            ("strategy_grid", StrategyType.GRID, "BTCUSDT"),
            ("strategy_martingale", StrategyType.MARTINGALE, "ETHUSDT"),
            ("strategy_arbitrage", StrategyType.ARBITRAGE, "BTCUSDT")
        ]
        
        for strategy_id, strategy_type, symbol in strategies:
            engine.register_strategy(strategy_id, strategy_type, symbol)
        
        # 为每个策略添加交易数据
        for strategy_id, strategy_type, symbol in strategies:
            # 每个策略20笔交易
            for i in range(20):
                # 不同策略的表现差异
                if strategy_type == StrategyType.GRID:
                    profit_loss = Decimal(str(100 - i * 3))  # 稳定盈利
                elif strategy_type == StrategyType.MARTINGALE:
                    profit_loss = Decimal(str(200 - i * 8))  # 高波动
                else:  # ARBITRAGE
                    profit_loss = Decimal(str(80 - i * 2))  # 稳定小幅盈利
                
                trade = create_trade_record(
                    trade_id=f"{strategy_id}_trade_{i:03d}",
                    strategy_id=strategy_id,
                    symbol=symbol,
                    trade_type="buy",
                    quantity=Decimal('0.001'),
                    price=Decimal('50000'),
                    profit_loss=profit_loss,
                    commission=Decimal('1')
                )
                engine.add_trade_record(trade)
        
        # 测试不同指标的对比
        metrics_to_test = [
            MetricType.PROFIT_LOSS,
            MetricType.WIN_RATE,
            MetricType.SHARPE_RATIO
        ]
        
        for metric in metrics_to_test:
            comparison = engine.compare_strategies(
                ["strategy_grid", "strategy_martingale", "strategy_arbitrage"],
                metric
            )
            
            assert 'comparison_results' in comparison, f"指标{metric.value}比较应该包含结果"
            assert 'ranking' in comparison, f"指标{metric.value}比较应该包含排名"
            assert len(comparison['ranking']) == 3, f"应该有三个策略排名: {comparison['ranking']}"
        
        # 获取所有策略性能概览
        all_performance = engine.get_all_strategies_performance()
        assert len(all_performance) == 3, f"应该有3个策略性能数据: {len(all_performance)}"
        
        logger.info("✓ 多策略对比分析测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 多策略对比分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始策略性能跟踪和分析系统测试")
    logger.info("=" * 60)
    
    tests = [
        ("性能跟踪器创建", test_performance_tracker_creation),
        ("交易记录管理", test_trade_record_management),
        ("性能指标计算", test_performance_metrics),
        ("分析引擎功能", test_analytics_engine),
        ("基准比较功能", test_benchmark_comparison),
        ("数据导出功能", test_data_export),
        ("智能建议功能", test_recommendations),
        ("深度性能分析", test_performance_analysis),
        ("多策略对比分析", test_multiple_strategies_comparison)
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
        logger.info("🎉 所有策略性能跟踪和分析系统测试通过!")
        exit(0)
    else:
        logger.error("💥 存在测试失败!")
        exit(1)
