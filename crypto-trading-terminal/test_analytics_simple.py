#!/usr/bin/env python3
"""
简化的策略性能分析系统测试
测试核心功能而不依赖复杂的数据库模型
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from decimal import Decimal
from datetime import datetime, timedelta

# 简化导入，直接使用analytics模块
try:
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
    
    # 创建简化的StrategyType
    from enum import Enum
    class StrategyType(Enum):
        GRID = "grid"
        MARTINGALE = "martingale"
        ARBITRAGE = "arbitrage"
        
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)


def test_performance_analyzer():
    """测试性能分析器数学计算"""
    print("测试性能分析器...")
    
    from backend.src.strategies.analytics import PerformanceAnalyzer
    
    # 测试夏普比率计算
    returns = [Decimal('0.01'), Decimal('0.02'), Decimal('-0.01'), Decimal('0.015'), Decimal('0.005')]
    sharpe = PerformanceAnalyzer.calculate_sharpe_ratio(returns)
    print(f"夏普比率: {sharpe}")
    assert isinstance(sharpe, Decimal), "夏普比率计算结果类型错误"
    
    # 测试索提诺比率
    sortino = PerformanceAnalyzer.calculate_sortino_ratio(returns)
    print(f"索提诺比率: {sortino}")
    assert isinstance(sortino, Decimal), "索提诺比率计算结果类型错误"
    
    # 测试最大回撤
    values = [Decimal('10000'), Decimal('9500'), Decimal('9800'), Decimal('10500'), Decimal('10200')]
    max_dd, start_idx, end_idx = PerformanceAnalyzer.calculate_max_drawdown(values)
    print(f"最大回撤: {max_dd}")
    assert isinstance(max_dd, Decimal), "最大回撤计算结果类型错误"
    
    print("✓ 性能分析器测试通过")


def test_strategy_performance_tracker():
    """测试策略性能跟踪器"""
    print("\n测试策略性能跟踪器...")
    
    # 创建跟踪器
    tracker = StrategyPerformanceTracker(
        strategy_id="test_strategy_1",
        strategy_type=StrategyType.GRID,
        symbol="BTC/USDT"
    )
    
    # 添加交易记录
    trades = [
        create_trade_record(
            trade_id="trade_1",
            strategy_id="test_strategy_1",
            symbol="BTC/USDT",
            trade_type="buy",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            profit_loss=Decimal('100'),
            commission=Decimal('5')
        ),
        create_trade_record(
            trade_id="trade_2",
            strategy_id="test_strategy_1",
            symbol="BTC/USDT",
            trade_type="sell",
            quantity=Decimal('0.1'),
            price=Decimal('51000'),
            profit_loss=Decimal('150'),
            commission=Decimal('5')
        )
    ]
    
    for trade in trades:
        tracker.add_trade(trade)
    
    # 测试性能摘要
    summary = tracker.get_performance_summary()
    print(f"性能摘要: {summary}")
    assert 'strategy_id' in summary, "性能摘要缺少strategy_id"
    assert summary['strategy_id'] == "test_strategy_1", "策略ID不匹配"
    assert summary['total_trades'] == 2, "交易次数不匹配"
    
    # 测试胜率计算
    win_rate = tracker.calculate_win_rate()
    print(f"胜率: {win_rate}")
    assert isinstance(win_rate, Decimal), "胜率类型错误"
    
    print("✓ 策略性能跟踪器测试通过")


def test_performance_analytics_engine():
    """测试性能分析引擎"""
    print("\n测试性能分析引擎...")
    
    # 创建引擎
    engine = create_performance_analytics_engine()
    assert isinstance(engine, PerformanceAnalyticsEngine), "引擎类型错误"
    
    # 注册策略
    tracker = engine.register_strategy(
        strategy_id="test_strategy_2",
        strategy_type=StrategyType.MARTINGALE,
        symbol="ETH/USDT"
    )
    
    # 添加交易记录
    trade = create_trade_record(
        trade_id="trade_3",
        strategy_id="test_strategy_2",
        symbol="ETH/USDT",
        trade_type="buy",
        quantity=Decimal('1.0'),
        price=Decimal('3000'),
        profit_loss=Decimal('50'),
        commission=Decimal('3')
    )
    
    engine.add_trade_record(trade)
    
    # 测试获取策略性能
    performance = engine.get_strategy_performance("test_strategy_2")
    print(f"策略性能: {performance}")
    assert performance is not None, "策略性能为空"
    assert performance['strategy_id'] == "test_strategy_2", "策略ID不匹配"
    
    # 测试策略比较
    comparison = engine.compare_strategies(["test_strategy_1", "test_strategy_2"])
    print(f"策略比较结果: {comparison}")
    assert 'comparison_results' in comparison, "比较结果缺少comparison_results"
    
    print("✓ 性能分析引擎测试通过")


def test_benchmark_data():
    """测试基准数据"""
    print("\n测试基准数据...")
    
    engine = create_performance_analytics_engine()
    
    # 添加基准数据
    benchmark = create_benchmark_data(
        timestamp=datetime.now(),
        value=Decimal('50000'),
        benchmark_type=BenchmarkType.BUY_AND_HOLD,
        symbol="BTC/USDT"
    )
    
    engine.add_benchmark_data(benchmark)
    
    # 测试获取所有策略性能
    all_performance = engine.get_all_strategies_performance()
    print(f"所有策略性能: {all_performance}")
    assert isinstance(all_performance, dict), "所有策略性能返回类型错误"
    
    print("✓ 基准数据测试通过")


def test_performance_report():
    """测试性能报告生成"""
    print("\n测试性能报告生成...")
    
    engine = create_performance_analytics_engine()
    
    # 注册策略
    tracker = engine.register_strategy(
        strategy_id="test_strategy_3",
        strategy_type=StrategyType.ARBITRAGE,
        symbol="BTC/USDT"
    )
    
    # 添加更多交易记录用于报告测试
    for i in range(10):
        trade = create_trade_record(
            trade_id=f"report_trade_{i}",
            strategy_id="test_strategy_3",
            symbol="BTC/USDT",
            trade_type="buy" if i % 2 == 0 else "sell",
            quantity=Decimal('0.1'),
            price=Decimal('50000') + Decimal(str(i * 100)),
            profit_loss=Decimal(str(50 + i * 10)),
            commission=Decimal('5')
        )
        engine.add_trade_record(trade)
    
    # 生成性能报告
    report = engine.generate_performance_report("test_strategy_3")
    print(f"性能报告生成: {report}")
    
    assert 'strategy_id' in report, "报告缺少strategy_id"
    assert 'performance_summary' in report, "报告缺少performance_summary"
    assert 'trade_analysis' in report, "报告缺少trade_analysis"
    assert 'recommendations' in report, "报告缺少recommendations"
    
    print("✓ 性能报告生成测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始运行策略性能分析系统测试\n")
    
    try:
        test_performance_analyzer()
        test_strategy_performance_tracker()
        test_performance_analytics_engine()
        test_benchmark_data()
        test_performance_report()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过！策略性能分析系统工作正常")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)