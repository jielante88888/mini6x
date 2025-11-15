#!/usr/bin/env python3
"""
期货策略执行合约测试
测试期货策略的核心执行逻辑，包括杠杆管理、资金费率处理、风险控制等期货特有功能

Test Scope:
- 期货策略生命周期管理
- 杠杆倍数动态调整
- 资金费率计算和影响
- 保证金管理和爆仓防护
- 期货特有订单类型支持
- 风险控制机制
"""

import asyncio
import logging
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# 导入期货策略模块
from backend.src.strategies.futures.base_futures_strategy import (
    BaseFuturesStrategy,
    FuturesOrder,
    FuturesPosition,
    LeverageManager,
    MarginManager,
    FundingRateCalculator
)
from backend.src.strategies.futures.trend_strategy import FuturesTrendStrategy
from backend.src.strategies.futures.swing_strategy import FuturesSwingStrategy
from backend.src.adapters.binance.futures import BinanceFuturesAdapter
from backend.src.adapters.okx.derivatives import OKXDerivativesAdapter

# 设置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFuturesStrategyLifecycle:
    """期货策略生命周期测试"""
    
    @pytest.fixture
    async def futures_adapter_mock(self):
        """模拟期货交易所适配器"""
        adapter = AsyncMock()
        adapter.get_account_info.return_value = {
            'balance': '10000.00',
            'positions': [],
            'leverage': 10
        }
        adapter.get_position.return_value = None
        adapter.place_order.return_value = {'order_id': '12345', 'status': 'filled'}
        adapter.cancel_order.return_value = {'order_id': '12345', 'status': 'canceled'}
        return adapter
    
    @pytest.fixture
    async def trend_strategy(self, futures_adapter_mock):
        """创建期货趋势策略实例"""
        strategy = FuturesTrendStrategy(
            strategy_id="trend_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            timeframe="1h",
            trend_period=20,
            leverage=10,
            stop_loss_pct=2.0,
            take_profit_pct=4.0,
            max_position_size=1000.0
        )
        strategy.set_exchange_adapter(futures_adapter_mock)
        return strategy
    
    async def test_strategy_initialization(self, trend_strategy):
        """测试策略初始化"""
        assert trend_strategy.strategy_id == "trend_test_001"
        assert trend_strategy.symbol == "BTCUSDT"
        assert trend_strategy.exchange == "binance"
        assert trend_strategy.leverage == 10
        assert trend_strategy.strategy_type == "trend"
        assert trend_strategy.status == "initialized"
    
    async def test_strategy_lifecycle(self, trend_strategy):
        """测试策略生命周期"""
        # 初始化到启动
        assert trend_strategy.status == "initialized"
        
        await trend_strategy.start()
        assert trend_strategy.status == "running"
        
        await trend_strategy.pause()
        assert trend_strategy.status == "paused"
        
        await trend_strategy.resume()
        assert trend_strategy.status == "running"
        
        await trend_strategy.stop()
        assert trend_strategy.status == "stopped"


class TestLeverageManagement:
    """杠杆管理测试"""
    
    @pytest.fixture
    def leverage_manager(self):
        """创建杠杆管理器"""
        return LeverageManager(
            min_leverage=1,
            max_leverage=100,
            current_leverage=10,
            exchange_risk_limits={
                'binance': {'BTC': 100, 'ETH': 100},
                'okx': {'BTC': 100, 'ETH': 100}
            }
        )
    
    def test_leverage_adjustment(self, leverage_manager):
        """测试杠杆调整"""
        # 初始杠杆
        assert leverage_manager.current_leverage == 10
        
        # 正常调整
        result = leverage_manager.set_leverage(20)
        assert result is True
        assert leverage_manager.current_leverage == 20
        
        # 超出交易所限制
        result = leverage_manager.set_leverage(150)
        assert result is False
        assert leverage_manager.current_leverage == 20  # 保持不变
        
        # 低于最小值
        result = leverage_manager.set_leverage(0.5)
        assert result is False
        assert leverage_manager.current_leverage == 20
    
    def test_leverage_optimization(self, leverage_manager):
        """测试杠杆优化"""
        # 模拟市场波动数据
        price_volatility = [0.02, 0.05, 0.08, 0.03, 0.06]
        account_balance = Decimal('10000')
        
        optimal_leverage = leverage_manager.calculate_optimal_leverage(
            price_volatility=price_volatility,
            account_balance=account_balance,
            max_risk_per_trade=0.02  # 每笔交易风险2%
        )
        
        assert optimal_leverage >= 1
        assert optimal_leverage <= 100
        assert isinstance(optimal_leverage, int)
        
        # 高波动应该降低杠杆
        high_vol = [0.15, 0.20, 0.18, 0.22, 0.16]
        optimal_high = leverage_manager.calculate_optimal_leverage(
            price_volatility=high_vol,
            account_balance=account_balance,
            max_risk_per_trade=0.02
        )
        assert optimal_high <= optimal_leverage


class TestMarginManagement:
    """保证金管理测试"""
    
    @pytest.fixture
    def margin_manager(self):
        """创建保证金管理器"""
        return MarginManager(
            exchange="binance",
            initial_margin_requirement=0.1,
            maintenance_margin_requirement=0.05,
            max_leverage=100
        )
    
    def test_margin_calculation(self, margin_manager):
        """测试保证金计算"""
        # 开仓保证金计算
        position_size = Decimal('0.1')  # 0.1 BTC
        entry_price = Decimal('50000')
        leverage = 20
        
        required_margin = margin_manager.calculate_initial_margin(
            position_size=position_size,
            entry_price=entry_price,
            leverage=leverage
        )
        
        expected_margin = (position_size * entry_price) / Decimal(str(leverage))
        assert required_margin == expected_margin
        
        # 维护保证金计算
        maintenance_margin = margin_manager.calculate_maintenance_margin(
            position_size=position_size,
            entry_price=entry_price,
            leverage=leverage
        )
        
        expected_maintenance = (position_size * entry_price) / Decimal(str(leverage)) * Decimal('0.5')  # 维护保证金是初始保证金的一半
        assert maintenance_margin == expected_maintenance
    
    def test_liquidation_risk_check(self, margin_manager):
        """测试爆仓风险检查"""
        position = FuturesPosition(
            symbol="BTCUSDT",
            side="long",
            size=Decimal('0.1'),
            entry_price=Decimal('50000'),
            mark_price=Decimal('48000'),
            leverage=20,
            unrealized_pnl=Decimal('-200')
        )
        
        account_info = {
            'balance': Decimal('1000'),
            'available_balance': Decimal('800'),
            'unrealized_pnl': Decimal('-200')
        }
        
        risk_check = margin_manager.check_liquidation_risk(
            position=position,
            account_info=account_info
        )
        
        assert 'liquidation_price' in risk_check
        assert 'risk_level' in risk_check
        assert 'recommended_action' in risk_check
        
        assert risk_check['risk_level'] in ['low', 'medium', 'high', 'critical']
        assert isinstance(risk_check['recommended_action'], str)


class TestFundingRateHandling:
    """资金费率处理测试"""
    
    @pytest.fixture
    def funding_calculator(self):
        """创建资金费率计算器"""
        return FundingRateCalculator()
    
    @pytest.mark.asyncio
    async def test_funding_rate_calculation(self, funding_calculator):
        """测试资金费率计算"""
        # 模拟资金费率数据
        funding_data = {
            'last_funding_rate': Decimal('0.0001'),  # 0.01%
            'next_funding_time': datetime.now() + timedelta(hours=8),
            'predictions': [Decimal('0.0002'), Decimal('-0.0001'), Decimal('0.0003')]
        }
        
        # 计算预期资金费率收益/成本
        position_size = Decimal('1.0')  # 1 BTC
        leverage = 20
        
        funding_impact = funding_calculator.calculate_funding_impact(
            funding_data=funding_data,
            position_size=position_size,
            leverage=leverage,
            position_side='long'
        )
        
        assert 'current_funding_rate' in funding_impact
        assert 'annualized_rate' in funding_impact
        assert 'estimated_cost' in funding_impact
        assert 'next_funding_payment' in funding_impact
        
        # 长期持仓的资金费率影响
        long_term_impact = funding_calculator.calculate_long_term_funding_impact(
            funding_data=funding_data,
            position_size=position_size,
            leverage=leverage,
            holding_days=30
        )
        
        assert 'total_cost_30d' in long_term_impact
        assert 'break_even_rate' in long_term_impact
        assert 'recommendation' in long_term_impact
    
    @pytest.mark.asyncio
    async def test_funding_rate_strategy(self, funding_calculator):
        """测试基于资金费率的策略决策"""
        # 负资金费率（做空者支付）情况
        negative_funding = {
            'current_rate': Decimal('-0.001'),
            'predictions': [Decimal('-0.001'), Decimal('-0.0015'), Decimal('-0.0005')],
            'trend': 'negative'
        }
        
        strategy_decision = funding_calculator.should_long_position(
            funding_data=negative_funding,
            market_conditions='bullish'
        )
        
        assert 'decision' in strategy_decision
        assert 'confidence' in strategy_decision
        assert 'reasoning' in strategy_decision
        
        # 正资金费率（做多者支付）情况
        positive_funding = {
            'current_rate': Decimal('0.001'),
            'predictions': [Decimal('0.001'), Decimal('0.0015'), Decimal('0.0005')],
            'trend': 'positive'
        }
        
        strategy_decision_short = funding_calculator.should_short_position(
            funding_data=positive_funding,
            market_conditions='bearish'
        )
        
        assert strategy_decision['decision'] != strategy_decision_short['decision']


class TestFuturesOrderTypes:
    """期货订单类型测试"""
    
    def test_futures_order_creation(self):
        """测试期货订单创建"""
        # 市价单
        market_order = FuturesOrder(
            symbol="BTCUSDT",
            side="buy",
            order_type="market",
            quantity=Decimal('0.1'),
            price=None,
            leverage=10,
            reduce_only=False,
            time_in_force="GTC"
        )
        
        assert market_order.order_type == "market"
        assert market_order.price is None
        
        # 限价单
        limit_order = FuturesOrder(
            symbol="BTCUSDT",
            side="sell",
            order_type="limit",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            leverage=10,
            reduce_only=True,
            time_in_force="GTC"
        )
        
        assert limit_order.order_type == "limit"
        assert limit_order.price == Decimal('50000')
        assert limit_order.reduce_only is True
        
        # 止损单
        stop_order = FuturesOrder(
            symbol="BTCUSDT",
            side="sell",
            order_type="stop_market",
            quantity=Decimal('0.1'),
            price=Decimal('48000'),
            leverage=10,
            reduce_only=True,
            time_in_force="GTC"
        )
        
        assert stop_order.order_type == "stop_market"
        assert stop_order.price == Decimal('48000')
    
    def test_order_validation(self):
        """测试订单验证"""
        # 有效订单
        valid_order = FuturesOrder(
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            leverage=10,
            reduce_only=False,
            time_in_force="GTC"
        )
        
        validation_result = valid_order.validate()
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        
        # 无效订单 - 数量为0
        invalid_order = FuturesOrder(
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal('0'),
            price=Decimal('50000'),
            leverage=10,
            reduce_only=False,
            time_in_force="GTC"
        )
        
        validation_result = invalid_order.validate()
        assert validation_result.is_valid is False
        assert "quantity must be positive" in str(validation_result.errors)
        
        # 无效订单 - 限价单未指定价格
        invalid_limit_order = FuturesOrder(
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal('0.1'),
            price=None,
            leverage=10,
            reduce_only=False,
            time_in_force="GTC"
        )
        
        validation_result = invalid_limit_order.validate()
        assert validation_result.is_valid is False
        assert "limit order requires price" in str(validation_result.errors)


class TestFuturesRiskControls:
    """期货风险控制测试"""
    
    @pytest.mark.asyncio
    async def test_position_sizing_risk(self):
        """测试仓位规模风险控制"""
        # 创建测试策略
        strategy = FuturesTrendStrategy(
            strategy_id="risk_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            max_position_size=1000.0,
            max_portfolio_risk=0.1,  # 最大投资组合风险10%
            leverage=20
        )
        
        # 模拟当前账户状态
        account_info = {
            'balance': Decimal('10000'),
            'available_balance': Decimal('8000'),
            'unrealized_pnl': Decimal('0')
        }
        
        # 测试正常仓位规模
        recommended_size = strategy.calculate_safe_position_size(
            account_balance=account_info['balance'],
            current_price=Decimal('50000'),
            volatility=0.02,
            risk_tolerance=0.02
        )
        
        assert recommended_size > 0
        assert recommended_size <= Decimal('1000')  # 不超过最大仓位
        assert recommended_size <= account_info['balance'] * Decimal('0.1')  # 不超过风险限制
    
    @pytest.mark.asyncio
    async def test_maximum_drawdown_protection(self):
        """测试最大回撤保护"""
        # 创建带回撤保护的策略
        strategy = FuturesTrendStrategy(
            strategy_id="drawdown_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            max_drawdown_limit=0.15,  # 最大回撤15%
            leverage=10
        )
        
        # 模拟策略表现数据
        performance_history = [
            Decimal('10000'), Decimal('9500'), Decimal('10200'),
            Decimal('9800'), Decimal('11000'), Decimal('9500'),
            Decimal('9200')  # 累计回撤超过15%
        ]
        
        # 测试回撤检测
        current_drawdown = strategy.calculate_current_drawdown(performance_history)
        should_stop = strategy.should_emergency_stop(current_drawdown)
        
        assert current_drawdown > 0
        if current_drawdown > 0.15:
            assert should_stop is True
    
    @pytest.mark.asyncio
    async def test_correlation_risk_management(self):
        """测试相关性风险管理"""
        # 创建多品种策略
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        strategy = FuturesTrendStrategy(
            strategy_id="correlation_test_001",
            symbols=symbols,
            exchange="binance",
            max_correlation_exposure=0.3  # 最大相关性风险30%
        )
        
        # 模拟相关性数据
        correlation_matrix = {
            ('BTCUSDT', 'ETHUSDT'): 0.8,
            ('BTCUSDT', 'ADAUSDT'): 0.6,
            ('ETHUSDT', 'ADAUSDT'): 0.7
        }
        
        # 测试相关性风险评估
        risk_assessment = strategy.assess_correlation_risk(
            proposed_positions={
                'BTCUSDT': Decimal('1000'),
                'ETHUSDT': Decimal('800'),
                'ADAUSDT': Decimal('500')
            },
            correlation_matrix=correlation_matrix
        )
        
        assert 'overall_risk' in risk_assessment
        assert 'correlation_adjusted_exposure' in risk_assessment
        assert 'recommendations' in risk_assessment
        
        assert risk_assessment['overall_risk'] >= 0
        assert risk_assessment['overall_risk'] <= 1


class TestFuturesStrategyExecution:
    """期货策略执行测试"""
    
    @pytest.fixture
    async def mock_exchange_adapter(self):
        """模拟交易所适配器"""
        adapter = AsyncMock()
        
        # 模拟账户信息
        adapter.get_account_info.return_value = {
            'balance': '10000.00',
            'positions': [],
            'leverage': 10,
            'max_withdraw_amount': '10000.00'
        }
        
        # 模拟当前价格
        adapter.get_ticker.return_value = {
            'last_price': '50000.00',
            'high_24h': '51000.00',
            'low_24h': '49000.00',
            'volume': '1000.00'
        }
        
        # 模拟下单结果
        adapter.place_order.return_value = {
            'order_id': '12345',
            'symbol': 'BTCUSDT',
            'status': 'filled',
            'executed_qty': '0.1',
            'executed_price': '50000.00'
        }
        
        return adapter
    
    @pytest.mark.asyncio
    async def test_strategy_signal_generation(self, mock_exchange_adapter):
        """测试策略信号生成"""
        strategy = FuturesTrendStrategy(
            strategy_id="signal_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            trend_period=20,
            confirmation_period=5
        )
        
        strategy.set_exchange_adapter(mock_exchange_adapter)
        
        # 模拟历史价格数据
        price_data = [
            {'timestamp': datetime.now() - timedelta(hours=i), 'open': 49000 + i*100, 'high': 49100 + i*100, 'low': 48900 + i*100, 'close': 49050 + i*100, 'volume': 100}
            for i in range(25, 0, -1)
        ]
        
        # 生成交易信号
        signal = await strategy.generate_trading_signal(price_data)
        
        assert 'signal' in signal
        assert 'confidence' in signal
        assert 'reasoning' in signal
        assert 'entry_price' in signal
        assert 'stop_loss' in signal
        assert 'take_profit' in signal
        
        assert signal['signal'] in ['buy', 'sell', 'hold']
        assert 0 <= signal['confidence'] <= 1
        assert isinstance(signal['entry_price'], Decimal)
        assert isinstance(signal['stop_loss'], Decimal)
        assert isinstance(signal['take_profit'], Decimal)
    
    @pytest.mark.asyncio
    async def test_strategy_execution_flow(self, mock_exchange_adapter):
        """测试策略执行流程"""
        strategy = FuturesSwingStrategy(
            strategy_id="execution_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            leverage=10,
            stop_loss_pct=2.0,
            take_profit_pct=4.0
        )
        
        strategy.set_exchange_adapter(mock_exchange_adapter)
        
        # 启动策略
        await strategy.start()
        assert strategy.status == "running"
        
        # 模拟执行一笔交易
        execution_result = await strategy.execute_trade(
            signal={
                'signal': 'buy',
                'confidence': 0.8,
                'entry_price': Decimal('50000'),
                'stop_loss': Decimal('49000'),
                'take_profit': Decimal('52000'),
                'position_size': Decimal('0.1')
            }
        )
        
        assert 'success' in execution_result
        assert 'order_id' in execution_result
        assert 'execution_price' in execution_result
        assert 'execution_time' in execution_result
        
        # 停止策略
        await strategy.stop()
        assert strategy.status == "stopped"


class TestFuturesPositionManagement:
    """期货持仓管理测试"""
    
    @pytest.fixture
    def futures_position(self):
        """创建期货持仓"""
        return FuturesPosition(
            symbol="BTCUSDT",
            side="long",
            size=Decimal('0.1'),
            entry_price=Decimal('50000'),
            mark_price=Decimal('51000'),
            leverage=20,
            unrealized_pnl=Decimal('200'),
            margin=Decimal('250'),
            liquidation_price=Decimal('47500')
        )
    
    def test_position_update(self, futures_position):
        """测试持仓更新"""
        original_pnl = futures_position.unrealized_pnl
        
        # 更新标记价格
        futures_position.update_mark_price(Decimal('51500'))
        new_pnl = futures_position.unrealized_pnl
        
        assert new_pnl != original_pnl  # 盈亏应该变化
        assert futures_position.mark_price == Decimal('51500')
    
    def test_position_realization(self, futures_position):
        """测试持仓实现"""
        # 平仓一半仓位
        partial_close_result = futures_position.close_position(
            size=Decimal('0.05'),
            exit_price=Decimal('51000'),
            timestamp=datetime.now()
        )
        
        assert partial_close_result['closed_size'] == Decimal('0.05')
        assert futures_position.size == Decimal('0.05')  # 剩余仓位
        assert partial_close_result['realized_pnl'] != 0
        
        # 全平仓
        full_close_result = futures_position.close_position(
            size=Decimal('0.05'),
            exit_price=Decimal('51200'),
            timestamp=datetime.now()
        )
        
        assert full_close_result['closed_size'] == Decimal('0.05')
        assert futures_position.size == Decimal('0')  # 无剩余仓位
        assert full_close_result['position_closed'] is True
    
    def test_position_risk_metrics(self, futures_position):
        """测试持仓风险指标"""
        risk_metrics = futures_position.calculate_risk_metrics(
            account_balance=Decimal('5000'),
            portfolio_value=Decimal('10000')
        )
        
        assert 'margin_ratio' in risk_metrics
        assert 'exposure_value' in risk_metrics
        assert 'unrealized_pnl_pct' in risk_metrics
        assert 'liquidation_distance' in risk_metrics
        
        assert risk_metrics['margin_ratio'] > 0
        assert risk_metrics['exposure_value'] > 0
        assert abs(risk_metrics['unrealized_pnl_pct']) >= 0


# 集成测试
class TestFuturesStrategyIntegration:
    """期货策略集成测试"""
    
    @pytest.mark.asyncio
    @patch('backend.src.adapters.binance.futures.BinanceFuturesAdapter')
    async def test_end_to_end_strategy_execution(self, mock_adapter_class):
        """端到端策略执行测试"""
        # 设置模拟适配器
        mock_adapter = AsyncMock()
        mock_adapter_class.return_value = mock_adapter
        
        # 配置适配器返回值
        mock_adapter.get_account_info.return_value = {
            'balance': '10000.00',
            'positions': [],
            'leverage': 10
        }
        
        mock_adapter.get_ticker.return_value = {
            'last_price': '50000.00',
            'high_24h': '51000.00',
            'low_24h': '49000.00',
            'volume': '1000.00'
        }
        
        mock_adapter.place_order.return_value = {
            'order_id': '12345',
            'status': 'filled',
            'executed_qty': '0.1',
            'executed_price': '50000.00'
        }
        
        # 创建并执行策略
        strategy = FuturesTrendStrategy(
            strategy_id="integration_test_001",
            symbol="BTCUSDT",
            exchange="binance",
            leverage=10,
            stop_loss_pct=2.0,
            take_profit_pct=4.0
        )
        
        # 启动策略
        await strategy.start()
        assert strategy.status == "running"
        
        # 执行交易流程
        execution_result = await strategy.execute_full_cycle(
            price_data=self._generate_test_price_data(),
            account_info={
                'balance': Decimal('10000'),
                'available_balance': Decimal('8000')
            }
        )
        
        assert 'signal_generated' in execution_result
        assert 'orders_placed' in execution_result
        assert 'positions_updated' in execution_result
        assert 'risk_metrics' in execution_result
        
        # 停止策略
        await strategy.stop()
        assert strategy.status == "stopped"
    
    def _generate_test_price_data(self):
        """生成测试价格数据"""
        base_price = 50000
        return [
            {
                'timestamp': datetime.now() - timedelta(hours=i),
                'open': base_price - 100 + i*10,
                'high': base_price - 50 + i*10,
                'low': base_price - 150 + i*10,
                'close': base_price - 100 + i*10,
                'volume': 1000 + i*100
            }
            for i in range(25, 0, -1)
        ]


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])