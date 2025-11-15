"""
策略性能追踪集成测试
验证现货策略系统的性能追踪、分析和报告功能的完整集成
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json
from decimal import Decimal
from typing import List, Dict, Any

from backend.src.auto_trading.order_manager import OrderManager
from backend.src.auto_trading.execution_engine import ExecutionEngine, ExecutionConfig
from backend.src.auto_trading.risk_checker import RiskCheckerService
from backend.src.strategies.base import SpotStrategy, StrategyType, StrategyStatus, StrategyState
from backend.src.strategies.spot.grid_strategy import GridStrategy
from backend.src.strategies.spot.martingale_strategy import MartingaleStrategy
from backend.src.strategies.spot.arbitrage_strategy import ArbitrageStrategy
from backend.src.core.performance_tracker import PerformanceTracker, PerformanceMetrics
from backend.src.storage.models import (
    User, Account, TradingPair, MarketData, Order, AutoOrder,
    OrderExecution, Position, TradingStatistics, RiskAlert
)
from backend.src.notification.risk_alert_integration import RiskAlertNotificationManager


class TestStrategyPerformanceIntegration:
    """策略性能追踪集成测试类"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = Mock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.scalars.return_value.first.return_value = None
        return session
    
    @pytest.fixture
    def mock_order_manager(self):
        """模拟订单管理器"""
        manager = Mock(spec=OrderManager)
        manager.create_order = AsyncMock()
        manager.execute_order = AsyncMock(return_value=True)
        manager.get_user_orders = AsyncMock(return_value=[])
        return manager
    
    @pytest.fixture
    def mock_execution_engine(self):
        """模拟执行引擎"""
        engine = Mock(spec=ExecutionEngine)
        engine.execute_order = AsyncMock()
        engine.get_execution_stats = AsyncMock(return_value={
            'total_executions': 100,
            'successful_executions': 95,
            'failed_executions': 5,
            'success_rate': 95.0
        })
        return engine
    
    @pytest.fixture
    def mock_risk_checker(self):
        """模拟风险检查器"""
        checker = Mock(spec=RiskCheckerService)
        checker.check_order_risk = AsyncMock(return_value=Mock(is_approved=True))
        checker.create_risk_alert = AsyncMock()
        return checker
    
    @pytest.fixture
    def performance_tracker(self, mock_db_session):
        """创建性能追踪器实例"""
        return PerformanceTracker(mock_db_session)
    
    @pytest.fixture
    def sample_user(self):
        """创建示例用户"""
        user = Mock(spec=User)
        user.id = 1001
        user.username = "strategy_trader"
        user.email = "trader@example.com"
        user.is_active = True
        return user
    
    @pytest.fixture
    def sample_account(self):
        """创建示例账户"""
        account = Mock(spec=Account)
        account.id = 2001
        account.user_id = 1001
        account.exchange = "binance"
        account.account_type = "spot"
        account.api_key = "test_api_key"
        account.is_active = True
        return account
    
    @pytest.fixture
    def sample_trading_pair(self):
        """创建示例交易对"""
        pair = Mock(spec=TradingPair)
        pair.id = 3001
        pair.symbol = "BTCUSDT"
        pair.base_asset = "BTC"
        pair.quote_asset = "USDT"
        pair.market_type = "spot"
        pair.min_qty = Decimal('0.001')
        pair.max_qty = Decimal('10.0')
        pair.step_size = Decimal('0.001')
        return pair
    
    @pytest.fixture
    def sample_market_data(self):
        """创建示例市场数据"""
        data = Mock(spec=MarketData)
        data.symbol = "BTCUSDT"
        data.current_price = Decimal('50000')
        data.previous_close = Decimal('49500')
        data.high_24h = Decimal('50500')
        data.low_24h = Decimal('49200')
        data.price_change = Decimal('500')
        data.price_change_percent = Decimal('1.01')
        data.volume_24h = Decimal('1000.5')
        data.timestamp = datetime.now()
        return data
    
    @pytest.fixture
    def sample_orders(self):
        """创建示例订单历史"""
        orders = []
        for i in range(20):
            order = Mock(spec=Order)
            order.id = i + 1
            order.user_id = 1001
            order.account_id = 2001
            order.symbol = "BTCUSDT"
            order.order_type = "limit"
            order.order_side = "buy" if i % 2 == 0 else "sell"
            order.quantity = Decimal('0.001')
            order.price = Decimal(str(50000 + i * 100))
            order.quantity_filled = Decimal('0.001') if i < 15 else Decimal('0')  # 75%成交率
            order.status = "filled" if i < 15 else "cancelled"
            order.order_time = datetime.now() - timedelta(hours=i)
            orders.append(order)
        return orders
    
    @pytest.fixture
    def sample_executions(self):
        """创建示例执行记录"""
        executions = []
        for i in range(20):
            execution = Mock(spec=OrderExecution)
            execution.id = i + 1
            execution.order_id = i + 1
            execution.execution_id = f"exec_{i + 1}"
            execution.status = "success" if i < 15 else "failed"
            execution.success = i < 15
            execution.filled_quantity = Decimal('0.001') if i < 15 else Decimal('0')
            execution.average_price = Decimal(str(50000 + i * 100))
            execution.commission = Decimal('0.5')
            execution.execution_time = datetime.now() - timedelta(hours=i)
            execution.latency_ms = 150.0 + (i * 10)  # 平均150ms延迟
            executions.append(execution)
        return executions
    
    @pytest.fixture
    def sample_positions(self):
        """创建示例仓位信息"""
        positions = []
        for i in range(3):
            position = Mock(spec=Position)
            position.id = i + 1
            position.account_id = 2001
            position.user_id = 1001
            position.symbol = ["BTCUSDT", "ETHUSDT", "ADAUSDT"][i]
            position.quantity = Decimal(str(0.5 + i * 0.1))
            position.avg_price = Decimal(str(45000 + i * 1000))
            position.unrealized_pnl = Decimal(str(100 + i * 50))  # 小幅盈利
            position.is_active = True
            positions.append(position)
        return positions
    
    @pytest.fixture
    def sample_grid_strategy(self, sample_account, sample_trading_pair):
        """创建网格策略实例"""
        strategy = GridStrategy(
            strategy_id="grid_test_001",
            user_id=1001,
            account_id=2001,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            grid_levels=5,
            grid_spacing=Decimal('0.01')
        )
        return strategy
    
    @pytest.fixture
    def sample_martingale_strategy(self, sample_account, sample_trading_pair):
        """创建马丁格尔策略实例"""
        strategy = MartingaleStrategy(
            strategy_id="martingale_test_001",
            user_id=1001,
            account_id=2001,
            symbol="ETHUSDT",
            base_quantity=Decimal('0.1'),
            max_steps=3,
            multiplier=Decimal('2.0')
        )
        return strategy
    
    @pytest.fixture
    def sample_arbitrage_strategy(self, sample_account):
        """创建套利策略实例"""
        strategy = ArbitrageStrategy(
            strategy_id="arbitrage_test_001",
            user_id=1001,
            account_id=2001,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            exchanges=['binance', 'okx', 'huobi'],
            threshold=Decimal('0.005')
        )
        return strategy

    # ===== 基础功能测试 =====
    
    def test_performance_tracker_initialization(self, performance_tracker):
        """测试性能追踪器初始化"""
        assert performance_tracker is not None
        assert hasattr(performance_tracker, 'db_session')
        assert hasattr(performance_tracker, 'metrics_cache')
        assert hasattr(performance_tracker, 'real_time_monitor')
    
    @pytest.mark.asyncio
    async def test_strategy_state_tracking(self, performance_tracker, sample_grid_strategy):
        """测试策略状态追踪"""
        # 模拟策略状态变化
        initial_state = StrategyState(
            strategy_id="grid_test_001",
            status=StrategyStatus.CREATED,
            created_at=datetime.now()
        )
        
        # 记录状态变化
        await performance_tracker.record_strategy_state(
            strategy_id="grid_test_001",
            state=initial_state
        )
        
        # 验证状态记录
        cached_state = await performance_tracker.get_strategy_state("grid_test_001")
        assert cached_state is not None
        assert cached_state.strategy_id == "grid_test_001"
        assert cached_state.status == StrategyStatus.CREATED
    
    @pytest.mark.asyncio
    async def test_order_execution_tracking(self, performance_tracker, sample_orders, sample_executions):
        """测试订单执行追踪"""
        # 模拟订单执行数据
        for order, execution in zip(sample_orders, sample_executions):
            await performance_tracker.record_order_execution(
                order_id=order.id,
                execution=execution,
                strategy_id="grid_test_001"
            )
        
        # 验证执行统计
        stats = await performance_tracker.get_strategy_performance("grid_test_001")
        assert stats is not None
        assert stats.total_orders == 20
        assert stats.successful_orders == 15
        assert stats.success_rate == 75.0  # 15/20 = 75%
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, performance_tracker, sample_positions):
        """测试仓位追踪"""
        for position in sample_positions:
            await performance_tracker.record_position_update(
                position=position,
                strategy_id="grid_test_001"
            )
        
        # 验证仓位统计
        position_stats = await performance_tracker.get_position_statistics("grid_test_001")
        assert position_stats is not None
        assert position_stats.total_positions == 3
        assert position_stats.active_positions == 3
        assert position_stats.total_unrealized_pnl > 0
    
    # ===== 实时性能监控测试 =====
    
    @pytest.mark.asyncio
    async def test_real_time_performance_monitoring(self, performance_tracker, sample_grid_strategy):
        """测试实时性能监控"""
        # 启动实时监控
        monitor_task = asyncio.create_task(
            performance_tracker.start_real_time_monitoring(
                strategy_id="grid_test_001",
                interval_seconds=1
            )
        )
        
        try:
            # 等待监控启动
            await asyncio.sleep(0.1)
            
            # 模拟性能数据更新
            await performance_tracker.update_real_time_metrics(
                strategy_id="grid_test_001",
                current_pnl=Decimal('50'),
                active_orders=5,
                memory_usage=85.5
            )
            
            # 验证实时数据
            real_time_data = performance_tracker.get_real_time_metrics("grid_test_001")
            assert real_time_data is not None
            assert real_time_data.current_pnl == Decimal('50')
            assert real_time_data.active_orders == 5
            
        finally:
            # 停止监控
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_performance_alerts(self, performance_tracker):
        """测试性能告警机制"""
        # 模拟低性能情况
        await performance_tracker.check_performance_alerts(
            strategy_id="grid_test_001",
            current_metrics={
                'success_rate': 45.0,  # 低于50%阈值
                'max_drawdown': 15.0,  # 超过10%阈值
                'memory_usage': 95.0    # 超过90%阈值
            }
        )
        
        # 验证告警记录（模拟检查）
        alerts = performance_tracker.get_performance_alerts("grid_test_001")
        assert alerts is not None
        # 应该有性能告警（具体数量取决于实现）
    
    # ===== 策略对比分析测试 =====
    
    @pytest.mark.asyncio
    async def test_strategy_comparison_analysis(self, performance_tracker, sample_grid_strategy, sample_martingale_strategy):
        """测试策略对比分析"""
        # 记录两个策略的性能数据
        await performance_tracker.record_strategy_performance(
            strategy_id="grid_test_001",
            metrics={
                'total_return': 12.5,
                'sharpe_ratio': 1.8,
                'max_drawdown': 8.5,
                'win_rate': 65.0,
                'profit_factor': 1.6
            }
        )
        
        await performance_tracker.record_strategy_performance(
            strategy_id="martingale_test_001",
            metrics={
                'total_return': 8.2,
                'sharpe_ratio': 1.2,
                'max_drawdown': 12.3,
                'win_rate': 55.0,
                'profit_factor': 1.3
            }
        )
        
        # 执行对比分析
        comparison = await performance_tracker.compare_strategies([
            "grid_test_001",
            "martingale_test_001"
        ])
        
        assert comparison is not None
        assert "grid_test_001" in comparison
        assert "martingale_test_001" in comparison
        assert "grid_test_001" in comparison["best_performer"]
    
    @pytest.mark.asyncio
    async def test_strategy_ranking(self, performance_tracker):
        """测试策略排名功能"""
        # 记录多个策略性能
        strategies = [
            ("strategy_a", {'total_return': 15.0, 'sharpe_ratio': 2.0, 'max_drawdown': 5.0}),
            ("strategy_b", {'total_return': 12.0, 'sharpe_ratio': 1.8, 'max_drawdown': 7.0}),
            ("strategy_c", {'total_return': 18.0, 'sharpe_ratio': 1.5, 'max_drawdown': 12.0})
        ]
        
        for strategy_id, metrics in strategies:
            await performance_tracker.record_strategy_performance(
                strategy_id=strategy_id,
                metrics=metrics
            )
        
        # 获取排名
        ranking = await performance_tracker.get_strategy_ranking(
            sort_by="total_return",
            limit=3
        )
        
        assert ranking is not None
        assert len(ranking) == 3
        assert ranking[0]['strategy_id'] == "strategy_c"  # 最高收益率
        assert ranking[0]['total_return'] == 18.0
    
    # ===== 历史数据分析测试 =====
    
    @pytest.mark.asyncio
    async def test_historical_performance_analysis(self, performance_tracker):
        """测试历史性能分析"""
        # 模拟历史数据
        base_date = datetime.now() - timedelta(days=30)
        for day in range(30):
            date = base_date + timedelta(days=day)
            await performance_tracker.record_daily_performance(
                strategy_id="grid_test_001",
                date=date,
                daily_return=Decimal(str(0.5 + (day % 7) * 0.2)),
                daily_volume=Decimal(str(1000 + day * 50)),
                daily_trades=10 + (day % 5)
            )
        
        # 分析历史数据
        analysis = await performance_tracker.analyze_historical_performance(
            strategy_id="grid_test_001",
            period_days=30
        )
        
        assert analysis is not None
        assert analysis.average_daily_return > 0
        assert analysis.total_return > 0
        assert analysis.volatility > 0
        assert analysis.best_day_return > 0
        assert analysis.worst_day_return < 0
    
    @pytest.mark.asyncio
    async def test_performance_trend_analysis(self, performance_tracker):
        """测试性能趋势分析"""
        # 创建趋势数据
        for i in range(20):
            await performance_tracker.record_weekly_performance(
                strategy_id="grid_test_001",
                week_number=i,
                weekly_return=Decimal(str(2.0 + i * 0.5))  # 递增趋势
            )
        
        # 分析趋势
        trend = await performance_tracker.analyze_performance_trend(
            strategy_id="grid_test_001",
            metric="weekly_return"
        )
        
        assert trend is not None
        assert trend.trend_direction == "increasing"
        assert trend.trend_strength > 0
        assert trend.confidence_level > 0.5
    
    # ===== 风险指标测试 =====
    
    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, performance_tracker, sample_orders, sample_executions):
        """测试风险指标计算"""
        # 记录性能数据
        await performance_tracker.record_performance_data(
            strategy_id="grid_test_001",
            orders=sample_orders,
            executions=sample_executions
        )
        
        # 计算风险指标
        risk_metrics = await performance_tracker.calculate_risk_metrics("grid_test_001")
        
        assert risk_metrics is not None
        assert risk_metrics.max_drawdown >= 0
        assert risk_metrics.sharpe_ratio is not None
        assert risk_metrics.sortino_ratio is not None
        assert risk_metrics.calmar_ratio is not None
        assert 0 <= risk_metrics.var_95 <= 1  # 95% VaR应该在0-1之间
        assert 0 <= risk_metrics.win_rate <= 1
    
    @pytest.mark.asyncio
    async def test_portfolio_risk_assessment(self, performance_tracker):
        """测试投资组合风险评估"""
        # 模拟多个策略的投资组合
        strategies = ["grid_test_001", "martingale_test_001", "arbitrage_test_001"]
        
        portfolio_risk = await performance_tracker.assess_portfolio_risk(
            strategy_ids=strategies,
            weights={'grid_test_001': 0.4, 'martingale_test_001': 0.4, 'arbitrage_test_001': 0.2}
        )
        
        assert portfolio_risk is not None
        assert portfolio_risk.portfolio_volatility > 0
        assert portfolio_risk.correlation_matrix is not None
        assert portfolio_risk.diversification_ratio > 0
        assert portfolio_risk.risk_contribution is not None
    
    # ===== 报告生成测试 =====
    
    @pytest.mark.asyncio
    async def test_performance_report_generation(self, performance_tracker):
        """测试性能报告生成"""
        # 准备测试数据
        await performance_tracker.record_strategy_performance(
            strategy_id="grid_test_001",
            metrics={
                'total_return': 15.5,
                'sharpe_ratio': 1.9,
                'max_drawdown': 6.5,
                'win_rate': 68.0,
                'profit_factor': 1.7,
                'total_trades': 150
            }
        )
        
        # 生成报告
        report = await performance_tracker.generate_performance_report(
            strategy_id="grid_test_001",
            period="30d",
            format="json"
        )
        
        assert report is not None
        assert "summary" in report
        assert "metrics" in report
        assert "analysis" in report
        assert report["summary"]["strategy_id"] == "grid_test_001"
        assert report["metrics"]["total_return"] == 15.5
    
    @pytest.mark.asyncio
    async def test_custom_performance_report(self, performance_tracker):
        """测试自定义性能报告"""
        # 生成自定义报告
        report = await performance_tracker.generate_custom_report(
            strategy_ids=["grid_test_001", "martingale_test_001"],
            metrics=['total_return', 'sharpe_ratio', 'max_drawdown'],
            comparison=True,
            include_charts=False
        )
        
        assert report is not None
        assert "strategies" in report
        assert "grid_test_001" in report["strategies"]
        assert "martingale_test_001" in report["strategies"]
        assert "comparison" in report
        assert report["metrics"] == ['total_return', 'sharpe_ratio', 'max_drawdown']
    
    # ===== 数据存储测试 =====
    
    @pytest.mark.asyncio
    async def test_database_storage_integration(self, performance_tracker, sample_orders):
        """测试数据库存储集成"""
        # 模拟数据库操作
        performance_tracker.db_session.add = Mock()
        performance_tracker.db_session.flush = AsyncMock()
        performance_tracker.db_session.commit = AsyncMock()
        
        # 存储性能数据
        await performance_tracker.store_performance_data(
            strategy_id="grid_test_001",
            performance_data={
                'orders': sample_orders[:5],
                'metrics': {
                    'total_return': 12.5,
                    'sharpe_ratio': 1.8,
                    'max_drawdown': 8.5
                }
            }
        )
        
        # 验证数据库操作
        assert performance_tracker.db_session.add.called
        assert performance_tracker.db_session.flush.called
        assert performance_tracker.db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_data_persistence_and_retrieval(self, performance_tracker):
        """测试数据持久化和检索"""
        # 存储测试数据
        test_data = {
            'strategy_id': 'grid_test_001',
            'performance_metrics': {
                'total_return': 15.0,
                'sharpe_ratio': 2.0,
                'max_drawdown': 5.0
            },
            'timestamp': datetime.now()
        }
        
        await performance_tracker.save_performance_record(test_data)
        
        # 检索数据
        retrieved_data = await performance_tracker.load_performance_record('grid_test_001')
        
        assert retrieved_data is not None
        assert retrieved_data['strategy_id'] == 'grid_test_001'
        assert retrieved_data['performance_metrics']['total_return'] == 15.0
    
    # ===== 性能优化测试 =====
    
    @pytest.mark.asyncio
    async def test_caching_performance(self, performance_tracker):
        """测试缓存性能"""
        # 模拟缓存操作
        await performance_tracker.cache_strategy_metrics(
            strategy_id="grid_test_001",
            metrics={'total_return': 15.0, 'sharpe_ratio': 1.8}
        )
        
        # 从缓存获取（应该很快）
        start_time = asyncio.get_event_loop().time()
        cached_metrics = performance_tracker.get_cached_metrics("grid_test_001")
        end_time = asyncio.get_event_loop().time()
        
        cache_time = end_time - start_time
        assert cache_time < 0.01  # 缓存访问应该小于10ms
        assert cached_metrics is not None
        assert cached_metrics['total_return'] == 15.0
    
    @pytest.mark.asyncio
    async def test_concurrent_performance_tracking(self, performance_tracker):
        """测试并发性能追踪"""
        # 并发记录多个策略的性能数据
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                performance_tracker.record_strategy_performance(
                    strategy_id=f"strategy_{i}",
                    metrics={
                        'total_return': 10.0 + i,
                        'sharpe_ratio': 1.0 + i * 0.1,
                        'max_drawdown': 5.0 + i * 0.5
                    }
                )
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count == 10  # 所有任务都应该成功
    
    # ===== 集成场景测试 =====
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_tracking(self, performance_tracker, sample_grid_strategy):
        """测试端到端性能追踪"""
        # 模拟完整的策略生命周期
        strategy_id = "grid_test_001"
        
        # 1. 策略创建
        initial_state = StrategyState(
            strategy_id=strategy_id,
            status=StrategyStatus.CREATED,
            created_at=datetime.now()
        )
        await performance_tracker.record_strategy_state(strategy_id, initial_state)
        
        # 2. 策略启动
        running_state = StrategyState(
            strategy_id=strategy_id,
            status=StrategyStatus.RUNNING,
            started_at=datetime.now()
        )
        await performance_tracker.record_strategy_state(strategy_id, running_state)
        
        # 3. 模拟交易活动
        for i in range(10):
            await performance_tracker.record_trade_execution(
                strategy_id=strategy_id,
                trade_data={
                    'timestamp': datetime.now() - timedelta(minutes=i),
                    'symbol': 'BTCUSDT',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': Decimal('0.001'),
                    'price': Decimal(str(50000 + i * 100)),
                    'pnl': Decimal(str((-1) ** i * (50 + i * 10)))  # 交替盈亏
                }
            )
        
        # 4. 获取完整性能报告
        report = await performance_tracker.generate_comprehensive_report(
            strategy_id=strategy_id,
            include_trades=True,
            include_risk_metrics=True,
            include_comparisons=False
        )
        
        # 验证完整报告
        assert report is not None
        assert "strategy_info" in report
        assert "performance_summary" in report
        assert "trade_analysis" in report
        assert "risk_metrics" in report
        assert report["strategy_info"]["strategy_id"] == strategy_id
        assert len(report["trade_analysis"]["trades"]) == 10
    
    @pytest.mark.asyncio
    async def test_multi_strategy_portfolio_tracking(self, performance_tracker):
        """测试多策略投资组合追踪"""
        # 创建多个策略
        strategies = [
            ("grid_portfolio_001", "grid"),
            ("martingale_portfolio_001", "martingale"),
            ("arbitrage_portfolio_001", "arbitrage")
        ]
        
        # 记录每个策略的性能数据
        for strategy_id, strategy_type in strategies:
            # 模拟不同类型的性能数据
            metrics = {
                'total_return': 15.0 if strategy_type == "grid" else (8.0 if strategy_type == "martingale" else 12.0),
                'sharpe_ratio': 2.0 if strategy_type == "grid" else (1.2 if strategy_type == "martingale" else 1.5),
                'max_drawdown': 6.0 if strategy_type == "grid" else (12.0 if strategy_type == "martingale" else 8.0),
                'win_rate': 70.0 if strategy_type == "grid" else (60.0 if strategy_type == "martingale" else 65.0)
            }
            
            await performance_tracker.record_strategy_performance(
                strategy_id=strategy_id,
                metrics=metrics
            )
        
        # 生成投资组合报告
        portfolio_report = await performance_tracker.generate_portfolio_report(
            strategy_ids=[s[0] for s in strategies],
            weights={
                "grid_portfolio_001": 0.4,
                "martingale_portfolio_001": 0.35,
                "arbitrage_portfolio_001": 0.25
            }
        )
        
        # 验证投资组合报告
        assert portfolio_report is not None
        assert "portfolio_summary" in portfolio_report
        assert "individual_strategies" in portfolio_report
        assert "risk_analysis" in portfolio_report
        assert "correlation_analysis" in portfolio_report
        
        # 验证权重总和为1
        total_weight = sum(portfolio_report["portfolio_summary"]["strategy_weights"].values())
        assert abs(total_weight - 1.0) < 0.001
    
    # ===== 错误处理测试 =====
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, performance_tracker):
        """测试错误处理和恢复"""
        # 测试无效策略ID
        invalid_result = await performance_tracker.record_strategy_performance(
            strategy_id="",  # 空ID
            metrics={'total_return': 10.0}
        )
        assert invalid_result is False
        
        # 测试无效指标数据
        invalid_metrics_result = await performance_tracker.record_strategy_performance(
            strategy_id="grid_test_001",
            metrics={'invalid_metric': 'invalid_value'}
        )
        # 应该能够处理无效指标而不崩溃
        
        # 测试数据库错误处理
        performance_tracker.db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        error_result = await performance_tracker.record_strategy_performance(
            strategy_id="grid_test_001",
            metrics={'total_return': 10.0}
        )
        
        # 应该能够处理数据库错误
        assert error_result is False
    
    @pytest.mark.asyncio
    async def test_data_validation(self, performance_tracker):
        """测试数据验证"""
        # 测试无效的性能指标
        with pytest.raises(ValueError):
            await performance_tracker.validate_performance_metrics({
                'total_return': -150.0,  # 负收益率超过100%
                'sharpe_ratio': -5.0,    # 负夏普比率
                'max_drawdown': 200.0    # 超过100%的回撤
            })
        
        # 测试有效的性能指标
        valid_metrics = {
            'total_return': 25.0,
            'sharpe_ratio': 1.5,
            'max_drawdown': 8.5,
            'win_rate': 0.65
        }
        
        validation_result = await performance_tracker.validate_performance_metrics(valid_metrics)
        assert validation_result is True


# 测试运行器
if __name__ == "__main__":
    # 运行集成测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])