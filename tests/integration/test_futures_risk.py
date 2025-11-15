"""
合约交易风险集成测试
验证合约交易中的杠杆管理、资金费率处理、保证金计算、强平风险管理等核心功能
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Optional, Tuple

# Import from the contract test
from tests.contract.test_futures_strategies import (
    OrderType, OrderSide, OrderStatus, Order, Position,
    LeverageMode, FundingRateMode, ContractType
)

class LeverageLevel:
    """杠杆倍数配置"""
    def __init__(
        self,
        symbol: str,
        max_leverage: Decimal,
        min_leverage: Decimal = Decimal('1'),
        maintenance_margin_rate: Decimal = Decimal('0.005'),
        initial_margin_rate: Decimal = Decimal('0.01'),
        liquidation_threshold: Decimal = Decimal('0.9'),
    ):
        self.symbol = symbol
        self.max_leverage = max_leverage
        self.min_leverage = min_leverage
        self.maintenance_margin_rate = maintenance_margin_rate  # 维持保证金率
        self.initial_margin_rate = initial_margin_rate  # 初始保证金率
        self.liquidation_threshold = liquidation_threshold  # 强平阈值

class FundingRateInfo:
    """资金费率信息"""
    def __init__(
        self,
        symbol: str,
        current_rate: Decimal,
        next_rate: Decimal,
        last_update: datetime,
        next_settlement_time: datetime,
        rate_mode: FundingRateMode = FundingRateMode.TRADING_FEE,
    ):
        self.symbol = symbol
        self.current_rate = current_rate  # 当前8小时资金费率
        self.next_rate = next_rate  # 下期预测资金费率
        self.last_update = last_update
        self.next_settlement_time = next_settlement_time
        self.rate_mode = rate_mode
        self.settlement_history = []  # 历史结算记录

class MarginAccount:
    """保证金账户"""
    def __init__(
        self,
        symbol: str,
        wallet_balance: Decimal,
        available_balance: Decimal,
        maintenance_margin: Decimal = Decimal('0'),
        initial_margin: Decimal = Decimal('0'),
        unrealized_pnl: Decimal = Decimal('0'),
        position: Optional[Position] = None,
    ):
        self.symbol = symbol
        self.wallet_balance = wallet_balance  # 钱包余额
        self.available_balance = available_balance  # 可用余额
        self.maintenance_margin = maintenance_margin  # 维持保证金
        self.initial_margin = initial_margin  # 初始保证金
        self.unrealized_pnl = unrealized_pnl  # 未实现盈亏
        self.position = position  # 当前持仓
        self.leverage = Decimal('1')  # 当前杠杆倍数
        self.entry_price = Decimal('0')  # 开仓价格
        self.liquidation_price = Decimal('0')  # 强平价格

class LiquidationRisk:
    """强平风险评估"""
    def __init__(
        self,
        symbol: str,
        liquidation_price: Decimal,
        current_price: Decimal,
        risk_level: str,  # LOW, MEDIUM, HIGH, CRITICAL
        distance_to_liquidation: Decimal,  # 到强平价的距离百分比
        estimated_loss_at_liquidation: Decimal,
        margin_requirement_change: Decimal,
    ):
        self.symbol = symbol
        self.liquidation_price = liquidation_price
        self.current_price = current_price
        self.risk_level = risk_level
        self.distance_to_liquidation = distance_to_liquidation
        self.estimated_loss_at_liquidation = estimated_loss_at_liquidation
        self.margin_requirement_change = margin_requirement_change
        self.timestamp = datetime.now()

class FuturesRiskManager:
    """合约风险管理器"""
    def __init__(self):
        self.leverage_configs = {}  # symbol -> LeverageLevel
        self.funding_rates = {}  # symbol -> FundingRateInfo
        self.margin_accounts = {}  # symbol -> MarginAccount
        self.risk_alerts = []  # 风险警告列表
    
    def register_leverage_config(self, config: LeverageLevel):
        """注册杠杆配置"""
        self.leverage_configs[config.symbol] = config
    
    def update_funding_rate(self, rate_info: FundingRateInfo):
        """更新资金费率信息"""
        self.funding_rates[rate_info.symbol] = rate_info
    
    def calculate_margin_requirement(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        leverage: Decimal,
        contract_type: ContractType = ContractType.PERPETUAL,
    ) -> Dict[str, Decimal]:
        """计算保证金要求"""
        config = self.leverage_configs.get(symbol)
        if not config:
            raise ValueError(f"No leverage config found for {symbol}")
        
        # 确保杠杆在允许范围内
        leverage = max(config.min_leverage, min(leverage, config.max_leverage))
        
        # 计算保证金
        if contract_type == ContractType.PERPETUAL:
            # 永续合约保证金计算
            position_value = quantity * price
            initial_margin = position_value / leverage * (1 + config.initial_margin_rate)
            maintenance_margin = position_value / leverage * config.maintenance_margin_rate
        else:
            # 交割合约保证金计算
            position_value = quantity * price
            initial_margin = position_value * config.initial_margin_rate
            maintenance_margin = position_value * config.maintenance_margin_rate
        
        return {
            'initial_margin': initial_margin,
            'maintenance_margin': maintenance_margin,
            'effective_leverage': position_value / initial_margin if initial_margin > 0 else Decimal('0'),
            'max_position_size': (config.wallet_balance * leverage) / price if hasattr(config, 'wallet_balance') else Decimal('0')
        }
    
    def calculate_liquidation_price(
        self,
        symbol: str,
        entry_price: Decimal,
        quantity: Decimal,
        side: OrderSide,
        leverage: Decimal,
        wallet_balance: Decimal,
        contract_type: ContractType = ContractType.PERPETUAL,
    ) -> Decimal:
        """计算强平价格"""
        config = self.leverage_configs.get(symbol)
        if not config:
            raise ValueError(f"No leverage config found for {symbol}")
        
        if contract_type == ContractType.PERPETUAL:
            # 永续合约强平价格计算
            maintenance_rate = config.maintenance_margin_rate
            
            if side == OrderSide.BUY:
                # 多头持仓强平价
                liquidation_price = entry_price * (1 - maintenance_rate / leverage) / (1 - maintenance_rate)
            else:
                # 空头持仓强平价
                liquidation_price = entry_price * (1 + maintenance_rate / leverage) / (1 + maintenance_rate)
        else:
            # 交割合约强平价格计算
            position_value = abs(quantity) * entry_price
            maintenance_value = position_value * config.maintenance_margin_rate
            
            if side == OrderSide.BUY:
                liquidation_price = entry_price - (wallet_balance - maintenance_value) / quantity
            else:
                liquidation_price = entry_price + (wallet_balance - maintenance_value) / quantity
        
        return max(liquidation_price, Decimal('0'))
    
    def assess_liquidation_risk(
        self,
        symbol: str,
        current_price: Decimal,
        position: Position,
        wallet_balance: Decimal,
    ) -> LiquidationRisk:
        """评估强平风险"""
        config = self.leverage_configs.get(symbol)
        if not config:
            raise ValueError(f"No leverage config found for {symbol}")
        
        # 计算当前强平价格
        liquidation_price = self.calculate_liquidation_price(
            symbol=symbol,
            entry_price=position.avg_price,
            quantity=position.quantity,
            side=OrderSide.SELL if position.quantity > 0 else OrderSide.BUY,
            leverage=config.max_leverage,  # 使用最大杠杆计算最坏情况
            wallet_balance=wallet_balance,
        )
        
        # 计算到强平价的距离
        if position.quantity > 0:  # 多头持仓
            if liquidation_price > 0:
                distance = (current_price - liquidation_price) / current_price * 100
            else:
                distance = Decimal('100')
        else:  # 空头持仓
            if liquidation_price > 0:
                distance = (liquidation_price - current_price) / current_price * 100
            else:
                distance = Decimal('100')
        
        # 评估风险等级
        if distance < 5:
            risk_level = "CRITICAL"
        elif distance < 10:
            risk_level = "HIGH"
        elif distance < 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # 计算预计损失
        estimated_loss = abs(position.quantity) * abs(current_price - liquidation_price)
        
        # 计算保证金变化
        margin_change = abs(position.quantity) * abs(current_price - liquidation_price)
        
        return LiquidationRisk(
            symbol=symbol,
            liquidation_price=liquidation_price,
            current_price=current_price,
            risk_level=risk_level,
            distance_to_liquidation=distance,
            estimated_loss_at_liquidation=estimated_loss,
            margin_requirement_change=margin_change,
        )
    
    def calculate_funding_rate_impact(
        self,
        symbol: str,
        position: Position,
        time_remaining: timedelta,
        current_rate: Decimal,
    ) -> Dict[str, Decimal]:
        """计算资金费率影响"""
        # 计算持仓价值
        position_value = abs(position.quantity) * position.avg_price
        
        # 计算8小时费率（转换为小时费率）
        hourly_rate = current_rate / 8
        
        # 计算剩余时间的费率影响
        time_factor = time_remaining.total_seconds() / 3600  # 转换为小时
        funding_impact = position_value * hourly_rate * time_factor
        
        # 根据持仓方向调整影响（多头付费率，空头收费率）
        if position.quantity > 0:  # 多头
            impact = -funding_impact  # 多头付费率
        else:  # 空头
            impact = funding_impact  # 空头收费率
        
        return {
            'hourly_funding_cost': hourly_rate * position_value,
            'estimated_funding_cost': funding_impact,
            'effective_cost_per_day': funding_impact * (24 / time_remaining.total_seconds() * 3600) if time_remaining.total_seconds() > 0 else Decimal('0'),
            'break_even_price_move': abs(impact) / abs(position.quantity) if position.quantity != 0 else Decimal('0'),
        }
    
    def add_risk_alert(self, alert_type: str, message: str, details: Dict):
        """添加风险警告"""
        self.risk_alerts.append({
            'type': alert_type,
            'message': message,
            'details': details,
            'timestamp': datetime.now(),
        })

class TestFuturesRiskIntegration:
    """合约风险集成测试套件"""
    
    @pytest.fixture
    def leverage_config(self):
        """杠杆配置"""
        return LeverageLevel(
            symbol="BTCUSDT",
            max_leverage=Decimal('125'),
            min_leverage=Decimal('1'),
            maintenance_margin_rate=Decimal('0.005'),
            initial_margin_rate=Decimal('0.008'),
            liquidation_threshold=Decimal('0.9'),
        )
    
    @pytest.fixture
    def funding_rate_info(self):
        """资金费率信息"""
        return FundingRateInfo(
            symbol="BTCUSDT",
            current_rate=Decimal('0.0001'),  # 0.01%
            next_rate=Decimal('0.0002'),     # 0.02%
            last_update=datetime.now(),
            next_settlement_time=datetime.now() + timedelta(hours=8),
            rate_mode=FundingRateMode.TRADING_FEE,
        )
    
    @pytest.fixture
    def futures_risk_manager(self, leverage_config, funding_rate_info):
        """合约风险管理器"""
        manager = FuturesRiskManager()
        manager.register_leverage_config(leverage_config)
        manager.update_funding_rate(funding_rate_info)
        return manager
    
    @pytest.fixture
    def sample_positions(self):
        """示例持仓"""
        return [
            Position(
                symbol="BTCUSDT",
                quantity=Decimal('1'),
                avg_price=Decimal('50000'),
                unrealized_pnl=Decimal('0'),
                contract_type=ContractType.PERPETUAL,
            ),
            Position(
                symbol="ETHUSDT",
                quantity=Decimal('-10'),
                avg_price=Decimal('3000'),
                unrealized_pnl=Decimal('500'),
                contract_type=ContractType.PERPETUAL,
            ),
        ]

    def test_leverage_configuration_validation(self, futures_risk_manager, leverage_config):
        """测试杠杆配置验证"""
        # 测试正常杠杆配置
        btc_config = futures_risk_manager.leverage_configs.get("BTCUSDT")
        assert btc_config is not None
        assert btc_config.max_leverage == Decimal('125')
        assert btc_config.maintenance_margin_rate == Decimal('0.005')
        
        # 测试杠杆范围限制
        assert btc_config.max_leverage >= btc_config.min_leverage
        assert btc_config.maintenance_margin_rate <= btc_config.initial_margin_rate
    
    def test_margin_calculation_basic(self, futures_risk_manager):
        """测试基本保证金计算"""
        result = futures_risk_manager.calculate_margin_requirement(
            symbol="BTCUSDT",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            leverage=Decimal('10'),
            contract_type=ContractType.PERPETUAL,
        )
        
        assert 'initial_margin' in result
        assert 'maintenance_margin' in result
        assert 'effective_leverage' in result
        
        # 验证保证金计算逻辑
        expected_initial = Decimal('1') * Decimal('50000') / Decimal('10') * Decimal('1.008')
        expected_maintenance = Decimal('1') * Decimal('50000') / Decimal('10') * Decimal('0.005')
        
        assert abs(result['initial_margin'] - expected_initial) < Decimal('1')
        assert abs(result['maintenance_margin'] - expected_maintenance) < Decimal('1')
    
    def test_margin_calculation_leverage_limits(self, futures_risk_manager):
        """测试杠杆限制下的保证金计算"""
        # 测试超过最大杠杆
        result = futures_risk_manager.calculate_margin_requirement(
            symbol="BTCUSDT",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            leverage=Decimal('200'),  # 超过最大125倍
            contract_type=ContractType.PERPETUAL,
        )
        
        # 应该被限制在最大杠杆内
        effective_leverage = result['effective_leverage']
        max_leverage = futures_risk_manager.leverage_configs["BTCUSDT"].max_leverage
        assert effective_leverage <= max_leverage
        
        # 测试小于最小杠杆
        result = futures_risk_manager.calculate_margin_requirement(
            symbol="BTCUSDT",
            quantity=Decimal('1'),
            price=Decimal('50000'),
            leverage=Decimal('0.5'),  # 小于最小1倍
            contract_type=ContractType.PERPETUAL,
        )
        
        effective_leverage = result['effective_leverage']
        min_leverage = futures_risk_manager.leverage_configs["BTCUSDT"].min_leverage
        assert effective_leverage >= min_leverage
    
    def test_liquidation_price_calculation_long(self, futures_risk_manager):
        """测试多头持仓强平价格计算"""
        liquidation_price = futures_risk_manager.calculate_liquidation_price(
            symbol="BTCUSDT",
            entry_price=Decimal('50000'),
            quantity=Decimal('1'),
            side=OrderSide.BUY,
            leverage=Decimal('10'),
            wallet_balance=Decimal('10000'),
            contract_type=ContractType.PERPETUAL,
        )
        
        assert liquidation_price > 0
        assert liquidation_price < Decimal('50000')  # 多头强平价应该低于开仓价
        
        # 验证计算逻辑
        expected_price = Decimal('50000') * (1 - Decimal('0.005') / Decimal('10')) / (1 - Decimal('0.005'))
        assert abs(liquidation_price - expected_price) < Decimal('1')
    
    def test_liquidation_price_calculation_short(self, futures_risk_manager):
        """测试空头持仓强平价格计算"""
        liquidation_price = futures_risk_manager.calculate_liquidation_price(
            symbol="BTCUSDT",
            entry_price=Decimal('50000'),
            quantity=Decimal('1'),
            side=OrderSide.SELL,
            leverage=Decimal('10'),
            wallet_balance=Decimal('10000'),
            contract_type=ContractType.PERPETUAL,
        )
        
        assert liquidation_price > 0
        assert liquidation_price > Decimal('50000')  # 空头强平价应该高于开仓价
        
        # 验证计算逻辑
        expected_price = Decimal('50000') * (1 + Decimal('0.005') / Decimal('10')) / (1 + Decimal('0.005'))
        assert abs(liquidation_price - expected_price) < Decimal('1')
    
    def test_liquidation_risk_assessment_low_risk(self, futures_risk_manager, sample_positions):
        """测试低风险强平风险评估"""
        position = sample_positions[0]  # BTC多头持仓
        current_price = Decimal('52000')  # 价格上涨
        
        risk = futures_risk_manager.assess_liquidation_risk(
            symbol="BTCUSDT",
            current_price=current_price,
            position=position,
            wallet_balance=Decimal('10000'),
        )
        
        assert risk.symbol == "BTCUSDT"
        assert risk.current_price == current_price
        assert risk.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert risk.distance_to_liquidation >= 0
        
        # 价格盈利时应该是低风险
        if position.avg_price < current_price:
            assert risk.risk_level in ["LOW", "MEDIUM"]
    
    def test_liquidation_risk_assessment_high_risk(self, futures_risk_manager):
        """测试高风险强平风险评估"""
        position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('10'),  # 大仓位
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('-5000'),  # 大幅亏损
            contract_type=ContractType.PERPETUAL,
        )
        current_price = Decimal('45000')  # 价格大幅下跌
        
        risk = futures_risk_manager.assess_liquidation_risk(
            symbol="BTCUSDT",
            current_price=current_price,
            position=position,
            wallet_balance=Decimal('1000'),  # 很少的保证金
        )
        
        assert risk.risk_level in ["HIGH", "CRITICAL"]  # 应该显示高风险
        assert risk.distance_to_liquidation < 20  # 距离强平很近
    
    def test_funding_rate_calculation_long_position(self, futures_risk_manager, sample_positions):
        """测试多头持仓资金费率计算"""
        position = sample_positions[0]  # BTC多头持仓
        time_remaining = timedelta(hours=6)
        
        impact = futures_risk_manager.calculate_funding_rate_impact(
            symbol="BTCUSDT",
            position=position,
            time_remaining=time_remaining,
            current_rate=Decimal('0.0001'),  # 0.01%
        )
        
        assert 'hourly_funding_cost' in impact
        assert 'estimated_funding_cost' in impact
        assert 'effective_cost_per_day' in impact
        assert 'break_even_price_move' in impact
        
        # 多头持仓应该付资金费率
        assert impact['estimated_funding_cost'] < 0
        
        # 验证计算逻辑
        position_value = Decimal('1') * Decimal('50000')
        hourly_rate = Decimal('0.0001') / 8
        time_factor = 6  # 6小时
        expected_cost = position_value * hourly_rate * time_factor
        
        assert abs(abs(impact['estimated_funding_cost']) - expected_cost) < Decimal('1')
    
    def test_funding_rate_calculation_short_position(self, futures_risk_manager, sample_positions):
        """测试空头持仓资金费率计算"""
        position = sample_positions[1]  # ETH空头持仓
        time_remaining = timedelta(hours=4)
        
        impact = futures_risk_manager.calculate_funding_rate_impact(
            symbol="ETHUSDT",
            position=position,
            time_remaining=time_remaining,
            current_rate=Decimal('0.0002'),  # 0.02%
        )
        
        # 空头持仓应该收资金费率
        assert impact['estimated_funding_cost'] > 0
        
        # 验证计算逻辑
        position_value = abs(Decimal('-10')) * Decimal('3000')
        hourly_rate = Decimal('0.0002') / 8
        time_factor = 4  # 4小时
        expected_cost = position_value * hourly_rate * time_factor
        
        assert abs(impact['estimated_funding_cost'] - expected_cost) < Decimal('1')
    
    def test_funding_rate_impact_analysis(self, futures_risk_manager, sample_positions):
        """测试资金费率影响分析"""
        position = sample_positions[0]
        time_remaining = timedelta(hours=8)  # 刚好一个资金费率周期
        
        impact = futures_risk_manager.calculate_funding_rate_impact(
            symbol="BTCUSDT",
            position=position,
            time_remaining=time_remaining,
            current_rate=Decimal('0.0001'),
        )
        
        # 8小时周期的成本应该等于当前费率
        position_value = abs(position.quantity) * position.avg_price
        expected_cost = position_value * Decimal('0.0001')  # 8小时费率
        
        if position.quantity > 0:  # 多头
            expected_cost = -expected_cost
        
        assert abs(impact['estimated_funding_cost'] - expected_cost) < Decimal('1')
    
    def test_leverage_margin_requirement_scaling(self, futures_risk_manager):
        """测试杠杆倍数对保证金要求的缩放效应"""
        base_quantity = Decimal('1')
        base_price = Decimal('50000')
        
        # 测试不同杠杆倍数
        leverage_levels = [1, 5, 10, 20, 50, 100]
        margin_ratios = []
        
        for leverage in leverage_levels:
            result = futures_risk_manager.calculate_margin_requirement(
                symbol="BTCUSDT",
                quantity=base_quantity,
                price=base_price,
                leverage=Decimal(str(leverage)),
                contract_type=ContractType.PERPETUAL,
            )
            
            initial_margin = result['initial_margin']
            position_value = base_quantity * base_price
            margin_ratio = initial_margin / position_value
            
            margin_ratios.append({
                'leverage': leverage,
                'margin_ratio': float(margin_ratio),
                'initial_margin': float(initial_margin),
            })
        
        # 验证杠杆和保证金的关系
        for i in range(1, len(margin_ratios)):
            prev_ratio = margin_ratios[i-1]
            curr_ratio = margin_ratios[i]
            
            # 杠杆增加，保证金比例应该减少
            assert curr_ratio['margin_ratio'] < prev_ratio['margin_ratio']
            
            # 但实际保证金金额应该随杠杆增加而减少
            assert curr_ratio['initial_margin'] < prev_ratio['initial_margin']
    
    def test_risk_level_classification(self, futures_risk_manager):
        """测试风险等级分类"""
        position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('5'),
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('-2000'),
            contract_type=ContractType.PERPETUAL,
        )
        
        # 测试不同的价格水平
        test_scenarios = [
            (Decimal('52000'), "LOW"),    # 大幅盈利
            (Decimal('50000'), "MEDIUM"), # 盈亏平衡
            (Decimal('48000'), "HIGH"),   # 小幅亏损
            (Decimal('46000'), "CRITICAL"), # 接近强平
        ]
        
        for current_price, expected_risk_level in test_scenarios:
            risk = futures_risk_manager.assess_liquidation_risk(
                symbol="BTCUSDT",
                current_price=current_price,
                position=position,
                wallet_balance=Decimal('5000'),
            )
            
            # 风险等级应该符合预期（或至少在合理范围内）
            if expected_risk_level == "LOW":
                assert risk.risk_level in ["LOW", "MEDIUM"]
            elif expected_risk_level == "MEDIUM":
                assert risk.risk_level in ["MEDIUM", "HIGH"]
            elif expected_risk_level == "HIGH":
                assert risk.risk_level in ["HIGH", "CRITICAL"]
            elif expected_risk_level == "CRITICAL":
                assert risk.risk_level == "CRITICAL"
    
    def test_funding_rate_settlement_impact(self, futures_risk_manager, sample_positions):
        """测试资金费率结算影响"""
        position = sample_positions[0]
        funding_rate = futures_risk_manager.funding_rates.get("BTCUSDT")
        
        # 模拟8小时后的资金费率结算
        time_to_settlement = funding_rate.next_settlement_time - funding_rate.last_update
        impact = futures_risk_manager.calculate_funding_rate_impact(
            symbol="BTCUSDT",
            position=position,
            time_remaining=time_to_settlement,
            current_rate=funding_rate.current_rate,
        )
        
        # 结算时的影响应该等于当前费率
        position_value = abs(position.quantity) * position.avg_price
        expected_impact = position_value * funding_rate.current_rate
        
        if position.quantity > 0:  # 多头
            expected_impact = -expected_impact
        
        assert abs(impact['estimated_funding_cost'] - expected_impact) < Decimal('1')
    
    def test_cross_leverage_risk_management(self, futures_risk_manager):
        """测试跨杠杆风险管理"""
        # 模拟多个不同杠杆的持仓
        positions = [
            Position("BTCUSDT", Decimal('1'), Decimal('50000'), Decimal('0'), ContractType.PERPETUAL),
            Position("ETHUSDT", Decimal('-10'), Decimal('3000'), Decimal('500'), ContractType.PERPETUAL),
            Position("ADAUSDT", Decimal('1000'), Decimal('1'), Decimal('50'), ContractType.PERPETUAL),
        ]
        
        total_risk_value = Decimal('0')
        total_margin_requirement = Decimal('0')
        
        for position in positions:
            # 计算保证金要求
            if position.symbol == "BTCUSDT":
                price = position.avg_price
                leverage = Decimal('10')
            elif position.symbol == "ETHUSDT":
                price = position.avg_price
                leverage = Decimal('20')
            else:  # ADAUSDT
                price = position.avg_price
                leverage = Decimal('5')
            
            result = futures_risk_manager.calculate_margin_requirement(
                symbol=position.symbol,
                quantity=abs(position.quantity),
                price=price,
                leverage=leverage,
                contract_type=ContractType.PERPETUAL,
            )
            
            total_margin_requirement += result['initial_margin']
            total_risk_value += abs(position.quantity) * price
        
        # 验证总体风险管理
        assert total_margin_requirement > 0
        assert total_risk_value > total_margin_requirement
        
        # 计算总体杠杆
        overall_leverage = total_risk_value / total_margin_requirement if total_margin_requirement > 0 else Decimal('0')
        assert overall_leverage > 1  # 应该使用杠杆
    
    def test_futures_risk_alerts(self, futures_risk_manager):
        """测试合约风险警告系统"""
        # 模拟高风险情况
        position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('20'),  # 大仓位
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('-15000'),  # 大幅亏损
            contract_type=ContractType.PERPETUAL,
        )
        
        current_price = Decimal('47000')
        
        # 评估风险
        risk = futures_risk_manager.assess_liquidation_risk(
            symbol="BTCUSDT",
            current_price=current_price,
            position=position,
            wallet_balance=Decimal('2000'),  # 很少保证金
        )
        
        # 根据风险等级添加警告
        if risk.risk_level == "CRITICAL":
            futures_risk_manager.add_risk_alert(
                alert_type="LIQUIDATION_RISK",
                message=f"CRITICAL: {risk.symbol} 面临强制平仓风险",
                details={
                    'risk_level': risk.risk_level,
                    'distance_to_liquidation': str(risk.distance_to_liquidation),
                    'estimated_loss': str(risk.estimated_loss_at_liquidation),
                    'current_price': str(current_price),
                    'liquidation_price': str(risk.liquidation_price),
                }
            )
        elif risk.risk_level == "HIGH":
            futures_risk_manager.add_risk_alert(
                alert_type="HIGH_RISK",
                message=f"HIGH: {risk.symbol} 风险较高，建议减仓",
                details={
                    'risk_level': risk.risk_level,
                    'distance_to_liquidation': str(risk.distance_to_liquidation),
                }
            )
        
        # 验证警告
        assert len(futures_risk_manager.risk_alerts) > 0
        
        critical_alerts = [a for a in futures_risk_manager.risk_alerts if a['type'] == "LIQUIDATION_RISK"]
        assert len(critical_alerts) > 0
        
        # 验证警告内容
        alert = critical_alerts[0]
        assert 'CRITICAL' in alert['message']
        assert 'risk_level' in alert['details']
        assert alert['details']['risk_level'] == "CRITICAL"
    
    def test_comprehensive_futures_risk_scenario(self, futures_risk_manager):
        """测试综合合约风险场景"""
        # 场景：多空对冲但风险不均衡的情况
        
        # 多头持仓
        long_position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('5'),
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('0'),
            contract_type=ContractType.PERPETUAL,
        )
        
        # 空头持仓（更大仓位）
        short_position = Position(
            symbol="ETHUSDT",
            quantity=Decimal('-20'),
            avg_price=Decimal('3000'),
            unrealized_pnl=Decimal('-1000'),
            contract_type=ContractType.PERPETUAL,
        )
        
        # 当前价格
        btc_price = Decimal('52000')
        eth_price = Decimal('2900')
        
        # 评估风险
        btc_risk = futures_risk_manager.assess_liquidation_risk(
            symbol="BTCUSDT",
            current_price=btc_price,
            position=long_position,
            wallet_balance=Decimal('10000'),
        )
        
        eth_risk = futures_risk_manager.assess_liquidation_risk(
            symbol="ETHUSDT",
            current_price=eth_price,
            position=short_position,
            wallet_balance=Decimal('5000'),
        )
        
        # 计算资金费率影响
        funding_impact_btc = futures_risk_manager.calculate_funding_rate_impact(
            symbol="BTCUSDT",
            position=long_position,
            time_remaining=timedelta(hours=6),
            current_rate=Decimal('0.0001'),
        )
        
        funding_impact_eth = futures_risk_manager.calculate_funding_rate_impact(
            symbol="ETHUSDT",
            position=short_position,
            time_remaining=timedelta(hours=6),
            current_rate=Decimal('0.0002'),
        )
        
        # 验证风险评估
        assert btc_risk.symbol == "BTCUSDT"
        assert eth_risk.symbol == "ETHUSDT"
        assert btc_risk.distance_to_liquidation > 0
        assert eth_risk.distance_to_liquidation > 0
        
        # 验证资金费率影响
        assert funding_impact_btc['estimated_funding_cost'] < 0  # 多头付费率
        assert funding_impact_eth['estimated_funding_cost'] > 0  # 空头收费率
        
        # 计算总体资金费率成本
        total_funding_cost = funding_impact_btc['estimated_funding_cost'] + funding_impact_eth['estimated_funding_cost']
        
        # 根据具体市场情况验证合理性
        # 如果ETH的资金费率更高，空头持仓可能获得净收益
        if abs(funding_impact_eth['estimated_funding_cost']) > abs(funding_impact_btc['estimated_funding_cost']):
            assert total_funding_cost > 0  # 净收益
        else:
            assert total_funding_cost < 0  # 净成本
    
    def test_leverage_adjustment_impact(self, futures_risk_manager):
        """测试杠杆调整影响"""
        position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('2'),
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('0'),
            contract_type=ContractType.PERPETUAL,
        )
        
        current_price = Decimal('48000')  # 亏损状态
        
        # 测试不同杠杆下的风险
        leverage_levels = [5, 10, 20, 50]
        risk_levels = []
        
        for leverage in leverage_levels:
            # 模拟不同杠杆下的强平价格
            liquidation_price = futures_risk_manager.calculate_liquidation_price(
                symbol="BTCUSDT",
                entry_price=position.avg_price,
                quantity=position.quantity,
                side=OrderSide.BUY,
                leverage=Decimal(str(leverage)),
                wallet_balance=Decimal('10000'),
            )
            
            risk = futures_risk_manager.assess_liquidation_risk(
                symbol="BTCUSDT",
                current_price=current_price,
                position=position,
                wallet_balance=Decimal('10000'),
            )
            
            risk_levels.append({
                'leverage': leverage,
                'liquidation_price': liquidation_price,
                'risk_level': risk.risk_level,
                'distance_to_liquidation': risk.distance_to_liquidation,
            })
        
        # 验证杠杆调整的影响
        for i in range(1, len(risk_levels)):
            prev = risk_levels[i-1]
            curr = risk_levels[i]
            
            # 杠杆增加，强平价格应该更接近当前价格
            assert curr['liquidation_price'] > prev['liquidation_price']
            assert curr['distance_to_liquidation'] < prev['distance_to_liquidation']
    
    def test_funding_rate_volatility_impact(self, futures_risk_manager, sample_positions):
        """测试资金费率波动影响"""
        position = sample_positions[0]
        
        # 测试不同资金费率水平的影响
        funding_rates = [
            Decimal('-0.0010'),  # -0.1% (非常不利)
            Decimal('-0.0001'),  # -0.01% (轻微不利)
            Decimal('0'),        # 0% (中性)
            Decimal('0.0001'),   # +0.01% (轻微有利)
            Decimal('0.0010'),   # +0.1% (非常有利)
        ]
        
        funding_impacts = []
        
        for rate in funding_rates:
            impact = futures_risk_manager.calculate_funding_rate_impact(
                symbol="BTCUSDT",
                position=position,
                time_remaining=timedelta(hours=8),
                current_rate=rate,
            )
            
            funding_impacts.append({
                'rate': rate,
                'impact': impact['estimated_funding_cost'],
                'break_even_move': impact['break_even_price_move'],
            })
        
        # 验证资金费率影响逻辑
        for i, impact_data in enumerate(funding_impacts):
            if impact_data['rate'] < 0:  # 负费率（多头付费率）
                assert impact_data['impact'] < 0
            elif impact_data['rate'] > 0:  # 正费率（多头收费率）
                assert impact_data['impact'] > 0
            else:  # 零费率
                assert abs(impact_data['impact']) < Decimal('1')
        
        # 验证盈亏平衡价格移动
        for impact_data in funding_impacts:
            assert impact_data['break_even_move'] >= 0
            
        # 费率越不利，盈亏平衡移动越大
        for i in range(1, len(funding_impacts)):
            prev_impact = funding_impacts[i-1]
            curr_impact = funding_impacts[i]
            
            if prev_impact['rate'] < curr_impact['rate']:
                # 费率改善，盈亏平衡移动应该减小
                assert curr_impact['break_even_move'] <= prev_impact['break_even_move']
    
    def test_position_size_leverage_correlation(self, futures_risk_manager):
        """测试持仓大小与杠杆相关性"""
        base_price = Decimal('50000')
        base_wallet_balance = Decimal('10000')
        
        # 测试不同持仓大小下的杠杆需求
        position_sizes = [Decimal('0.1'), Decimal('0.5'), Decimal('1'), Decimal('2'), Decimal('5')]
        required_leverages = []
        
        for size in position_sizes:
            # 计算维持所需最小杠杆
            position_value = size * base_price
            min_margin = position_value * Decimal('0.005')  # 最小维持保证金率
            max_leverage = base_wallet_balance / min_margin
            
            required_leverages.append({
                'position_size': size,
                'position_value': position_value,
                'max_safe_leverage': max_leverage,
            })
        
        # 验证相关性
        for i in range(1, len(required_leverages)):
            prev = required_leverages[i-1]
            curr = required_leverages[i]
            
            # 持仓增加，可安全使用的杠杆应该减少
            assert curr['position_size'] > prev['position_size']
            assert curr['max_safe_leverage'] < prev['max_safe_leverage']
    
    def test_market_conditions_risk_adaptation(self, futures_risk_manager, sample_positions):
        """测试市场条件下的风险适应"""
        position = sample_positions[0]
        
        # 模拟不同的市场条件
        market_scenarios = [
            {
                'name': 'bull_market',
                'current_price': Decimal('55000'),
                'volatility': Decimal('0.02'),
                'funding_rate': Decimal('0.0002'),
            },
            {
                'name': 'bear_market',
                'current_price': Decimal('45000'),
                'volatility': Decimal('0.03'),
                'funding_rate': Decimal('-0.0001'),
            },
            {
                'name': 'sideways_market',
                'current_price': Decimal('50000'),
                'volatility': Decimal('0.01'),
                'funding_rate': Decimal('0'),
            },
        ]
        
        risk_assessments = []
        
        for scenario in market_scenarios:
            # 评估风险
            risk = futures_risk_manager.assess_liquidation_risk(
                symbol="BTCUSDT",
                current_price=scenario['current_price'],
                position=position,
                wallet_balance=Decimal('10000'),
            )
            
            # 计算资金费率影响
            funding_impact = futures_risk_manager.calculate_funding_rate_impact(
                symbol="BTCUSDT",
                position=position,
                time_remaining=timedelta(hours=8),
                current_rate=scenario['funding_rate'],
            )
            
            risk_assessments.append({
                'market': scenario['name'],
                'risk_level': risk.risk_level,
                'distance_to_liquidation': risk.distance_to_liquidation,
                'funding_impact': funding_impact['estimated_funding_cost'],
                'current_price': scenario['current_price'],
            })
        
        # 验证不同市场条件下的风险差异
        for assessment in risk_assessments:
            assert assessment['risk_level'] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert assessment['distance_to_liquidation'] >= 0
            
            if assessment['market'] == 'bear_market' and position.quantity > 0:
                # 熊市下的多头持仓应该有更高风险
                assert assessment['risk_level'] in ["HIGH", "CRITICAL"]
            elif assessment['market'] == 'bull_market' and position.quantity > 0:
                # 牛市下的多头持仓应该有较低风险
                assert assessment['risk_level'] in ["LOW", "MEDIUM"]