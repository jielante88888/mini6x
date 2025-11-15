#!/usr/bin/env python3
"""
期货风险控制集成测试
测试杠杆和资金费率的综合处理，确保期货策略在各种市场条件下的风险控制有效性

Test Scope:
- 杠杆动态调整机制
- 资金费率对策略收益的影响
- 保证金充足性检查
- 爆仓风险评估
- 多策略杠杆分配
- 资金费率套利机会识别
"""

import asyncio
import logging
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# 导入相关模块
from backend.src.core.risk_manager import RiskManager
from backend.src.strategies.futures.base_futures_strategy import LeverageManager, MarginManager
from backend.src.strategies.futures.trend_strategy import FuturesTrendStrategy
from backend.src.strategies.futures.swing_strategy import FuturesSwingStrategy
from backend.src.adapters.binance.futures import BinanceFuturesAdapter
from backend.src.core.funding_rate_analyzer import FundingRateAnalyzer

# 设置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLeverageDynamicAdjustment:
    """杠杆动态调整测试"""
    
    @pytest.fixture
    async def leverage_manager(self):
        """创建杠杆管理器"""
        return LeverageManager(
            exchange="binance",
            account_balance=Decimal('10000'),
            max_total_exposure=Decimal('50000'),  # 最大总风险暴露
            risk_per_trade=0.02,  # 每笔交易风险2%
            volatility_adjustment_factor=0.5
        )
    
    @pytest.mark.asyncio
    async def test_volatility_based_leverage_adjustment(self, leverage_manager):
        """测试基于波动率的杠杆调整"""
        # 测试低波动率市场
        low_volatility_prices = [50000 + i*10 for i in range(100)]  # 相对稳定的價格
        
        optimal_leverage_low = await leverage_manager.calculate_optimal_leverage(
            price_series=low_volatility_prices,
            account_risk_level='moderate'
        )
        
        assert 5 <= optimal_leverage_low <= 20  # 低波动率应该允许较高杠杆
        
        # 测试高波动率市场
        high_volatility_prices = [
            50000 + (i % 20 - 10) * 500  # 高波动的價格
            for i in range(100)
        ]
        
        optimal_leverage_high = await leverage_manager.calculate_optimal_leverage(
            price_series=high_volatility_prices,
            account_risk_level='moderate'
        )
        
        assert optimal_leverage_high <= optimal_leverage_low  # 高波动率应该降低杠杆
        assert 1 <= optimal_leverage_high <= 10
    
    @pytest.mark.asyncio
    async def test_account_health_based_adjustment(self, leverage_manager):
        """测试基于账户健康的杠杆调整"""
        # 健康账户
        healthy_account = {
            'balance': Decimal('10000'),
            'unrealized_pnl': Decimal('500'),
            'drawdown': 0.02,
            'win_rate': 0.65,
            'sharpe_ratio': 1.5
        }
        
        leverage_adjustment = await leverage_manager.adjust_leverage_for_account_health(
            current_leverage=10,
            account_info=healthy_account
        )
        
        assert leverage_adjustment >= 10  # 健康账户可以增加杠杆
        
        # 不健康账户
        unhealthy_account = {
            'balance': Decimal('8000'),
            'unrealized_pnl': Decimal('-2000'),
            'drawdown': 0.15,
            'win_rate': 0.35,
            'sharpe_ratio': 0.3
        }
        
        leverage_adjustment_risk = await leverage_manager.adjust_leverage_for_account_health(
            current_leverage=10,
            account_info=unhealthy_account
        )
        
        assert leverage_adjustment_risk <= 10  # 不健康账户应该降低杠杆
        assert leverage_adjustment_risk >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_strategies_leverage_allocation(self, leverage_manager):
        """测试多策略杠杆分配"""
        strategies = [
            {'id': 'trend_btc', 'symbol': 'BTCUSDT', 'risk_score': 0.8},
            {'id': 'swing_eth', 'symbol': 'ETHUSDT', 'risk_score': 0.6},
            {'id': 'scalping_ada', 'symbol': 'ADAUSDT', 'risk_score': 0.9}
        ]
        
        total_leverage_budget = 30  # 总杠杆预算
        allocation = await leverage_manager.allocate_leverage_budget(
            strategies=strategies,
            total_budget=total_leverage_budget
        )
        
        assert len(allocation) == 3
        total_allocated = sum(strategy['allocated_leverage'] for strategy in allocation)
        assert total_allocated <= total_leverage_budget
        
        # 风险高的策略应该分配较少杠杆
        high_risk_strategy = next(s for s in allocation if s['symbol'] == 'ADAUSDT')
        low_risk_strategy = next(s for s in allocation if s['symbol'] == 'ETHUSDT')
        
        assert high_risk_strategy['allocated_leverage'] <= low_risk_strategy['allocated_leverage']


class TestFundingRateImpactAnalysis:
    """资金费率影响分析测试"""
    
    @pytest.fixture
    async def funding_analyzer(self):
        """创建资金费率分析器"""
        return FundingRateAnalyzer()
    
    @pytest.mark.asyncio
    async def test_funding_rate_impact_on_strategy_returns(self, funding_analyzer):
        """测试资金费率对策略收益的影响"""
        # 模拟期货趋势策略数据
        strategy_data = {
            'symbol': 'BTCUSDT',
            'position_side': 'long',
            'leverage': 20,
            'position_size': Decimal('0.1'),
            'holding_days': 30,
            'expected_returns': Decimal('0.05')  # 5%收益
        }
        
        # 模拟资金费率历史数据
        funding_rates = [
            {'timestamp': datetime.now() - timedelta(days=i), 'rate': Decimal('0.0001') * (i % 3 - 1)}
            for i in range(30, 0, -1)
        ]
        
        impact_analysis = await funding_analyzer.calculate_funding_impact(
            strategy_info=strategy_data,
            funding_history=funding_rates
        )
        
        assert 'net_return_after_funding' in impact_analysis
        assert 'funding_cost_30d' in impact_analysis
        assert 'break_even_timeframe' in impact_analysis
        assert 'recommendation' in impact_analysis
        
        # 验证资金费率成本的合理性
        expected_funding_cost = sum(fr['rate'] for fr in funding_rates) * strategy_data['position_size'] * 20
        assert abs(impact_analysis['funding_cost_30d'] - expected_funding_cost) < Decimal('0.01')
    
    @pytest.mark.asyncio
    async def test_funding_rate_arbitrage_opportunities(self, funding_analyzer):
        """测试资金费率套利机会识别"""
        # 模拟多个交易所的资金费率差异
        cross_exchange_data = {
            'binance': {
                'BTCUSDT': {'funding_rate': Decimal('0.0001'), 'next_funding_time': datetime.now() + timedelta(hours=8)},
                'ETHUSDT': {'funding_rate': Decimal('-0.0002'), 'next_funding_time': datetime.now() + timedelta(hours=8)}
            },
            'okx': {
                'BTCUSDT': {'funding_rate': Decimal('-0.0001'), 'next_funding_time': datetime.now() + timedelta(hours=8)},
                'ETHUSDT': {'funding_rate': Decimal('0.0002'), 'next_funding_time': datetime.now() + timedelta(hours=8)}
            }
        }
        
        arbitrage_opportunities = await funding_analyzer.identify_arbitrage_opportunities(
            cross_exchange_data=cross_exchange_data,
            minimum_profit_threshold=Decimal('0.001')
        )
        
        assert 'opportunities' in arbitrage_opportunities
        assert len(arbitrage_opportunities['opportunities']) >= 0
        
        # 验证套利机会的合理性
        for opportunity in arbitrage_opportunities['opportunities']:
            assert 'symbol' in opportunity
            assert 'long_exchange' in opportunity
            assert 'short_exchange' in opportunity
            assert 'expected_profit' in opportunity
            assert opportunity['expected_profit'] > 0
    
    @pytest.mark.asyncio
    async def test_funding_rate_optimization_strategy(self, funding_analyzer):
        """测试基于资金费率的策略优化"""
        # 模拟策略配置和资金费率预测
        strategy_config = {
            'symbol': 'BTCUSDT',
            'base_strategy': 'trend',
            'leverage': 15,
            'target_holding_period': 'medium',  # 中期持仓
            'risk_tolerance': 'moderate'
        }
        
        funding_predictions = {
            'next_8h': Decimal('0.0002'),
            'next_24h': Decimal('0.0001'),
            'next_48h': Decimal('-0.0001'),
            'trend': 'increasing'
        }
        
        optimization_result = await funding_analyzer.optimize_strategy_for_funding(
            strategy_config=strategy_config,
            funding_predictions=funding_predictions
        )
        
        assert 'adjusted_leverage' in optimization_result
        assert 'position_timing' in optimization_result
        assert 'expected_funding_benefit' in optimization_result
        assert 'implementation_steps' in optimization_result
        
        # 验证调整的合理性
        assert optimization_result['adjusted_leverage'] != strategy_config['leverage']
        assert isinstance(optimization_result['position_timing'], dict)


class TestMarginAndLiquidationRisk:
    """保证金和爆仓风险测试"""
    
    @pytest.fixture
    async def margin_manager(self):
        """创建保证金管理器"""
        return MarginManager(
            exchange="binance",
            initial_margin_rate=0.1,
            maintenance_margin_rate=0.05,
            liquidation_buffer=0.005  # 0.5%缓冲
        )
    
    @pytest.mark.asyncio
    async def test_margin_adequacy_check(self, margin_manager):
        """测试保证金充足性检查"""
        # 测试场景：正常交易
        trade_scenario = {
            'symbol': 'BTCUSDT',
            'side': 'long',
            'quantity': Decimal('0.1'),
            'entry_price': Decimal('50000'),
            'leverage': 20,
            'current_price': Decimal('50500'),
            'account_balance': Decimal('1000'),
            'unrealized_pnl': Decimal('50')
        }
        
        margin_check = await margin_manager.check_margin_adequacy(
            trade_info=trade_scenario,
            safety_buffer=Decimal('0.02')  # 2%安全缓冲
        )
        
        assert 'margin_ratio' in margin_check
        assert 'available_margin' in margin_check
        assert 'required_margin' in margin_check
        assert 'is_adequate' in margin_check
        assert 'recommendations' in margin_check
        
        assert margin_check['required_margin'] > 0
        assert margin_check['is_adequate'] is True
        
        # 测试高风险场景
        high_risk_scenario = {
            'symbol': 'BTCUSDT',
            'side': 'long',
            'quantity': Decimal('1.0'),  # 大仓位
            'entry_price': Decimal('50000'),
            'leverage': 100,
            'current_price': Decimal('48000'),  # 大幅亏损
            'account_balance': Decimal('500'),
            'unrealized_pnl': Decimal('-2000')
        }
        
        high_risk_check = await margin_manager.check_margin_adequacy(
            trade_info=high_risk_scenario,
            safety_buffer=Decimal('0.05')  # 5%安全缓冲
        )
        
        assert high_risk_check['is_adequate'] is False
        assert 'reduce_position' in str(high_risk_check['recommendations']).lower()
    
    @pytest.mark.asyncio
    async def test_liquidation_price_calculation(self, margin_manager):
        """测试爆仓价格计算"""
        position_scenarios = [
            {
                'name': 'long_position',
                'side': 'long',
                'entry_price': Decimal('50000'),
                'quantity': Decimal('0.1'),
                'leverage': 20,
                'expected_liquidation': 47500  # 长仓爆仓价应低于入场价
            },
            {
                'name': 'short_position',
                'side': 'short',
                'entry_price': Decimal('50000'),
                'quantity': Decimal('0.1'),
                'leverage': 20,
                'expected_liquidation': 52500  # 短仓爆仓价应高于入场价
            }
        ]
        
        for scenario in position_scenarios:
            liquidation_info = margin_manager.calculate_liquidation_price(
                side=scenario['side'],
                entry_price=scenario['entry_price'],
                quantity=scenario['quantity'],
                leverage=scenario['leverage']
            )
            
            assert 'liquidation_price' in liquidation_info
            assert 'margin_required' in liquidation_info
            assert 'distance_to_liquidation' in liquidation_info
            
            liquidation_price = liquidation_info['liquidation_price']
            
            if scenario['side'] == 'long':
                assert liquidation_price < scenario['entry_price']
            else:
                assert liquidation_price > scenario['entry_price']
            
            # 验证计算逻辑的合理性
            expected_distance = (scenario['entry_price'] / Decimal(str(scenario['leverage']))) / scenario['entry_price']
            actual_distance = liquidation_info['distance_to_liquidation']
            assert abs(actual_distance - expected_distance) < Decimal('0.001')


class TestPortfolioRiskManagement:
    """投资组合风险管理测试"""
    
    @pytest.fixture
    async def risk_manager(self):
        """创建风险管理器"""
        return RiskManager(
            max_portfolio_risk=0.1,  # 最大投资组合风险10%
            max_correlation_exposure=0.3,  # 最大相关性风险30%
            max_single_position_risk=0.05,  # 最大单一仓位风险5%
            rebalance_threshold=0.15  # 再平衡阈值15%
        )
    
    @pytest.mark.asyncio
    async def test_portfolio_risk_assessment(self, risk_manager):
        """测试投资组合风险评估"""
        # 模拟多策略投资组合
        portfolio_positions = [
            {
                'strategy_id': 'trend_btc',
                'symbol': 'BTCUSDT',
                'position_value': Decimal('20000'),
                'unrealized_pnl': Decimal('500'),
                'leverage': 15,
                'correlation_btc': 1.0,
                'correlation_eth': 0.8,
                'risk_score': 0.7
            },
            {
                'strategy_id': 'swing_eth',
                'symbol': 'ETHUSDT',
                'position_value': Decimal('15000'),
                'unrealized_pnl': Decimal('-200'),
                'leverage': 12,
                'correlation_btc': 0.8,
                'correlation_eth': 1.0,
                'risk_score': 0.6
            },
            {
                'strategy_id': 'scalping_ada',
                'symbol': 'ADAUSDT',
                'position_value': Decimal('10000'),
                'unrealized_pnl': Decimal('300'),
                'leverage': 10,
                'correlation_btc': 0.6,
                'correlation_eth': 0.7,
                'risk_score': 0.9
            }
        ]
        
        portfolio_value = Decimal('50000')  # 投资组合总价值
        account_balance = Decimal('45000')  # 账户余额
        
        risk_assessment = await risk_manager.assess_portfolio_risk(
            positions=portfolio_positions,
            portfolio_value=portfolio_value,
            account_balance=account_balance
        )
        
        assert 'overall_risk_score' in risk_assessment
        assert 'correlation_risk' in risk_assessment
        assert 'position_concentration' in risk_assessment
        assert 'margin_utilization' in risk_assessment
        assert 'risk_recommendations' in risk_assessment
        
        assert 0 <= risk_assessment['overall_risk_score'] <= 1
        assert risk_assessment['correlation_risk'] >= 0
        assert risk_assessment['margin_utilization'] >= 0
    
    @pytest.mark.asyncio
    async def test_risk_based_position_sizing(self, risk_manager):
        """测试基于风险的仓位规模计算"""
        trading_scenarios = [
            {
                'name': 'conservative_trader',
                'risk_tolerance': 'low',
                'account_balance': Decimal('10000'),
                'existing_exposure': Decimal('3000'),
                'expected_volatility': 0.02,
                'max_risk_per_trade': 0.01
            },
            {
                'name': 'aggressive_trader',
                'risk_tolerance': 'high',
                'account_balance': Decimal('10000'),
                'existing_exposure': Decimal('7000'),
                'expected_volatility': 0.08,
                'max_risk_per_trade': 0.03
            }
        ]
        
        for scenario in trading_scenarios:
            position_sizing = await risk_manager.calculate_max_position_size(
                symbol='BTCUSDT',
                current_price=Decimal('50000'),
                account_balance=scenario['account_balance'],
                existing_exposure=scenario['existing_exposure'],
                risk_tolerance=scenario['risk_tolerance'],
                expected_volatility=scenario['expected_volatility'],
                max_risk_per_trade=scenario['max_risk_per_trade']
            )
            
            assert 'max_position_value' in position_sizing
            assert 'max_quantity' in position_sizing
            assert 'leverage_recommendation' in position_sizing
            assert 'risk_score' in position_sizing
            
            assert position_sizing['max_position_value'] > 0
            assert position_sizing['max_quantity'] > 0
            assert position_sizing['leverage_recommendation'] >= 1
    
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing(self, risk_manager):
        """测试投资组合再平衡"""
        current_allocation = {
            'BTCUSDT': Decimal('0.4'),    # 40% - 超配
            'ETHUSDT': Decimal('0.35'),   # 35% - 接近目标
            'ADAUSDT': Decimal('0.15'),   # 15% - 低配
            'SOLUSDT': Decimal('0.1')     # 10% - 低配
        }
        
        target_allocation = {
            'BTCUSDT': Decimal('0.3'),    # 目标30%
            'ETHUSDT': Decimal('0.4'),    # 目标40%
            'ADAUSDT': Decimal('0.2'),    # 目标20%
            'SOLUSDT': Decimal('0.1')     # 目标10%
        }
        
        portfolio_value = Decimal('50000')
        
        rebalancing_plan = await risk_manager.create_rebalancing_plan(
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            portfolio_value=portfolio_value,
            trading_costs=Decimal('0.001')  # 0.1%交易成本
        )
        
        assert 'rebalancing_actions' in rebalancing_plan
        assert 'total_cost' in rebalancing_plan
        assert 'expected_improvement' in rebalancing_plan
        assert 'execution_timeline' in rebalancing_plan
        
        # 验证再平衡行动的合理性
        actions = rebalancing_plan['rebalancing_actions']
        for action in actions:
            assert 'symbol' in action
            assert 'action' in action  # 'buy' or 'sell'
            assert 'amount' in action
            assert action['amount'] > 0


class TestIntegratedRiskWorkflow:
    """集成风险工作流测试"""
    
    @pytest.mark.asyncio
    async def test_complete_risk_workflow(self):
        """测试完整的风险管理工作流"""
        # 模拟真实交易环境
        account_info = {
            'balance': Decimal('10000'),
            'equity': Decimal('10200'),
            'available_balance': Decimal('8000')
        }
        
        market_conditions = {
            'BTCUSDT': {
                'price': Decimal('50000'),
                'volatility_24h': 0.05,
                'funding_rate': Decimal('0.0001'),
                'trend': 'bullish'
            },
            'ETHUSDT': {
                'price': Decimal('3000'),
                'volatility_24h': 0.08,
                'funding_rate': Decimal('-0.0002'),
                'trend': 'bearish'
            }
        }
        
        proposed_trades = [
            {
                'symbol': 'BTCUSDT',
                'side': 'long',
                'quantity': Decimal('0.1'),
                'leverage': 15,
                'strategy_type': 'trend'
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'short',
                'quantity': Decimal('0.5'),
                'leverage': 10,
                'strategy_type': 'swing'
            }
        ]
        
        # 执行完整的风险评估流程
        risk_analysis = await self._execute_risk_analysis_workflow(
            account_info=account_info,
            market_conditions=market_conditions,
            proposed_trades=proposed_trades
        )
        
        # 验证分析结果的完整性
        assert 'pre_trade_risk_assessment' in risk_analysis
        assert 'margin_calculations' in risk_analysis
        assert 'funding_impact_analysis' in risk_analysis
        assert 'portfolio_adjustments' in risk_analysis
        assert 'final_recommendations' in risk_analysis
        
        # 验证建议的合理性
        recommendations = risk_analysis['final_recommendations']
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert 'action' in rec
            assert 'priority' in rec
            assert 'reasoning' in rec
            assert rec['priority'] in ['low', 'medium', 'high', 'critical']
    
    async def _execute_risk_analysis_workflow(self, account_info, market_conditions, proposed_trades):
        """执行风险分析工作流"""
        # 初始化风险管理器
        risk_manager = RiskManager()
        
        # 1. 预交易风险评估
        pre_trade_assessment = await risk_manager.pre_trade_risk_check(
            proposed_trades=proposed_trades,
            account_info=account_info,
            market_conditions=market_conditions
        )
        
        # 2. 保证金计算
        margin_calculations = {}
        for trade in proposed_trades:
            symbol = trade['symbol']
            market_data = market_conditions[symbol]
            
            margin_req = await risk_manager.calculate_required_margin(
                trade_info=trade,
                market_price=market_data['price']
            )
            margin_calculations[symbol] = margin_req
        
        # 3. 资金费率影响分析
        funding_impact = {}
        for trade in proposed_trades:
            symbol = trade['symbol']
            market_data = market_conditions[symbol]
            
            funding_analysis = await risk_manager.analyze_funding_rate_impact(
                trade_info=trade,
                funding_rate=market_data['funding_rate'],
                expected_holding_period=24  # 24小时
            )
            funding_impact[symbol] = funding_analysis
        
        # 4. 投资组合调整建议
        portfolio_adjustments = await risk_manager.optimize_portfolio_allocation(
            proposed_trades=proposed_trades,
            current_exposure={},
            risk_tolerance='moderate'
        )
        
        # 5. 生成最终建议
        final_recommendations = await risk_manager.generate_risk_recommendations(
            pre_trade_assessment=pre_trade_assessment,
            margin_calculations=margin_calculations,
            funding_impact=funding_impact,
            portfolio_adjustments=portfolio_adjustments
        )
        
        return {
            'pre_trade_risk_assessment': pre_trade_assessment,
            'margin_calculations': margin_calculations,
            'funding_impact_analysis': funding_impact,
            'portfolio_adjustments': portfolio_adjustments,
            'final_recommendations': final_recommendations
        }


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])