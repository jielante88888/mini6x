"""
风险管理集成测试
验证风险管理系统的各组件协同工作，包括风险检查、限制验证、通知集成等
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Optional

# Import from the contract test
from tests.contract.test_auto_orders import (
    OrderType, OrderSide, OrderStatus, Order, Position, 
    ExecutionResult, RiskLevel
)

class RiskLimit:
    """风险限制配置"""
    def __init__(
        self,
        max_order_size: Decimal,
        max_position_size: Decimal,
        max_daily_trades: int,
        max_daily_volume: Decimal,
        max_loss_per_trade: Decimal,
        max_total_exposure: Decimal,
    ):
        self.max_order_size = max_order_size
        self.max_position_size = max_position_size
        self.max_daily_trades = max_daily_trades
        self.max_daily_volume = max_daily_volume
        self.max_loss_per_trade = max_loss_per_trade
        self.max_total_exposure = max_total_exposure

class RiskAlert:
    """风险警告"""
    def __init__(
        self,
        alert_id: str,
        severity: str,
        message: str,
        details: Dict,
        timestamp: datetime,
        symbol: str = None,
        strategy_name: str = None,
    ):
        self.alert_id = alert_id
        self.severity = severity  # INFO, WARNING, CRITICAL, BLOCKED
        self.message = message
        self.details = details
        self.timestamp = timestamp
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.acknowledged = False

class RiskChecker:
    """风险管理器模拟"""
    def __init__(self, limits: RiskLimit):
        self.limits = limits
        self.alerts: List[RiskAlert] = []
        self.daily_stats = {
            'trade_count': 0,
            'trade_volume': Decimal('0'),
            'total_loss': Decimal('0'),
            'active_positions': {},
        }
    
    async def check_order_risk(
        self, 
        order: Order, 
        current_position: Optional[Position] = None
    ) -> RiskAlert:
        """检查订单风险"""
        alerts = []
        
        # 检查订单大小限制
        if order.quantity > self.limits.max_order_size:
            alerts.append(RiskAlert(
                alert_id=f"order_size_{order.order_id}",
                severity="BLOCKED",
                message=f"订单数量 {order.quantity} 超过最大限制 {self.limits.max_order_size}",
                details={
                    'current': order.quantity,
                    'limit': self.limits.max_order_size,
                    'order_id': order.order_id,
                },
                timestamp=datetime.now(),
                symbol=order.symbol,
                strategy_name=getattr(order, 'strategy_name', None)
            ))
        
        # 计算新的总仓位
        new_position_size = current_position.quantity if current_position else Decimal('0')
        if order.side == OrderSide.BUY:
            new_position_size += order.quantity
        else:
            new_position_size -= order.quantity
        
        # 检查仓位大小限制
        if abs(new_position_size) > self.limits.max_position_size:
            alerts.append(RiskAlert(
                alert_id=f"position_size_{order.order_id}",
                severity="WARNING",
                message=f"新仓位 {new_position_size} 超过最大限制 {self.limits.max_position_size}",
                details={
                    'current': new_position_size,
                    'new_size': new_position_size,
                    'limit': self.limits.max_position_size,
                    'order_id': order.order_id,
                },
                timestamp=datetime.now(),
                symbol=order.symbol,
                strategy_name=getattr(order, 'strategy_name', None)
            ))
        
        # 检查日交易次数限制
        if self.daily_stats['trade_count'] >= self.limits.max_daily_trades:
            alerts.append(RiskAlert(
                alert_id=f"daily_trade_limit_{order.order_id}",
                severity="BLOCKED",
                message=f"今日交易次数 {self.daily_stats['trade_count']} 已达到上限 {self.limits.max_daily_trades}",
                details={
                    'current': self.daily_stats['trade_count'],
                    'limit': self.limits.max_daily_trades,
                    'order_id': order.order_id,
                },
                timestamp=datetime.now(),
                symbol=order.symbol,
                strategy_name=getattr(order, 'strategy_name', None)
            ))
        
        # 检查日交易量限制
        trade_volume = order.quantity * (order.price or Decimal('50000'))
        new_daily_volume = self.daily_stats['trade_volume'] + trade_volume
        if new_daily_volume > self.limits.max_daily_volume:
            alerts.append(RiskAlert(
                alert_id=f"daily_volume_limit_{order.order_id}",
                severity="WARNING",
                message=f"新增交易后日交易量 {new_daily_volume} 超过限制 {self.limits.max_daily_volume}",
                details={
                    'current': self.daily_stats['trade_volume'],
                    'new_volume': new_daily_volume,
                    'limit': self.limits.max_daily_volume,
                    'order_id': order.order_id,
                },
                timestamp=datetime.now(),
                symbol=order.symbol,
                strategy_name=getattr(order, 'strategy_name', None)
            ))
        
        # 记录风险警告
        for alert in alerts:
            self.alerts.append(alert)
        
        # 返回最严重的警告
        if alerts:
            severity_order = ['BLOCKED', 'CRITICAL', 'WARNING', 'INFO']
            alerts.sort(key=lambda x: severity_order.index(x.severity))
            return alerts[0]
        
        return None
    
    def update_daily_stats(self, order: Order, executed: bool = True):
        """更新日统计"""
        if executed:
            self.daily_stats['trade_count'] += 1
            trade_volume = order.quantity * (order.price or Decimal('50000'))
            self.daily_stats['trade_volume'] += trade_volume
    
    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        return {
            'daily_stats': self.daily_stats.copy(),
            'total_alerts': len(self.alerts),
            'critical_alerts': len([a for a in self.alerts if a.severity == 'CRITICAL']),
            'blocked_orders': len([a for a in self.alerts if a.severity == 'BLOCKED']),
            'warnings': len([a for a in self.alerts if a.severity == 'WARNING']),
        }

class RiskManagementIntegrator:
    """风险管理集成器"""
    def __init__(
        self,
        risk_checker: RiskChecker,
        notification_sender: AsyncMock = None,
    ):
        self.risk_checker = risk_checker
        self.notification_sender = notification_sender or AsyncMock()
        self.blocked_orders = []
    
    async def process_order_with_risk_management(
        self,
        order: Order,
        current_position: Optional[Position] = None,
    ) -> tuple[bool, str, Optional[RiskAlert]]:
        """处理订单的风险管理流程"""
        
        # 1. 风险检查
        risk_alert = await self.risk_checker.check_order_risk(order, current_position)
        
        if risk_alert:
            # 2. 发送风险通知
            await self.send_risk_notification(risk_alert)
            
            # 3. 处理风险等级
            if risk_alert.severity == "BLOCKED":
                self.blocked_orders.append(order.order_id)
                return False, f"订单被风险管理系统阻止: {risk_alert.message}", risk_alert
            
            # WARNING及以上级别允许执行但需记录
            return True, f"风险警告: {risk_alert.message}", risk_alert
        
        # 4. 通过风险检查
        return True, "订单通过风险检查", None
    
    async def send_risk_notification(self, alert: RiskAlert):
        """发送风险通知"""
        notification_data = {
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'message': alert.message,
            'details': alert.details,
            'timestamp': alert.timestamp.isoformat(),
            'symbol': alert.symbol,
            'strategy_name': alert.strategy_name,
        }
        
        await self.notification_sender.send_risk_alert(notification_data)
    
    async def acknowledge_alert(self, alert_id: str):
        """确认风险警告"""
        for alert in self.risk_checker.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break

class TestRiskManagementIntegration:
    """风险管理集成测试套件"""
    
    @pytest.fixture
    def risk_limits(self):
        """风险限制配置"""
        return RiskLimit(
            max_order_size=Decimal('10'),
            max_position_size=Decimal('100'),
            max_daily_trades=50,
            max_daily_volume=Decimal('1000000'),
            max_loss_per_trade=Decimal('50000'),
            max_total_exposure=Decimal('5000000'),
        )
    
    @pytest.fixture
    def risk_checker(self, risk_limits):
        """风险检查器"""
        return RiskChecker(risk_limits)
    
    @pytest.fixture
    def notification_sender(self):
        """通知发送器模拟"""
        return AsyncMock()
    
    @pytest.fixture
    def risk_integrator(self, risk_checker, notification_sender):
        """风险管理集成器"""
        return RiskManagementIntegrator(risk_checker, notification_sender)
    
    @pytest.fixture
    def sample_orders(self):
        """示例订单"""
        return [
            Order(
                order_id="test_001",
                symbol="BTCUSDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=Decimal('1'),
                price=Decimal('50000'),
                status=OrderStatus.PENDING,
            ),
            Order(
                order_id="test_002", 
                symbol="ETHUSDT",
                order_type=OrderType.LIMIT,
                side=OrderSide.SELL,
                quantity=Decimal('5'),
                price=Decimal('3000'),
                status=OrderStatus.PENDING,
            ),
        ]

    async def test_basic_risk_checking(self, risk_checker, sample_orders):
        """测试基本风险检查功能"""
        # 测试正常订单（应该通过检查）
        normal_order = sample_orders[0]
        alert = await risk_checker.check_order_risk(normal_order)
        assert alert is None, "正常订单应该通过风险检查"
        
        # 测试超大订单（应该被阻止）
        large_order = Order(
            order_id="large_001",
            symbol="BTCUSDT", 
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('50'),  # 超过限制
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        alert = await risk_checker.check_order_risk(large_order)
        assert alert is not None, "超大订单应该触发风险警告"
        assert alert.severity == "BLOCKED", "超大订单应该被阻止"
        assert "max_order_size" in alert.details
    
    async def test_order_size_limit(self, risk_checker, sample_orders):
        """测试订单大小限制"""
        limit_order = sample_orders[0]
        
        # 测试刚好在限制内的订单
        limit_order.quantity = Decimal('10')  # 刚好等于限制
        alert = await risk_checker.check_order_risk(limit_order)
        assert alert is None, "在限制内的订单应该通过检查"
        
        # 测试超过限制的订单
        limit_order.quantity = Decimal('10.1')  # 稍微超过限制
        alert = await risk_checker.check_order_risk(limit_order)
        assert alert is not None, "超过限制的订单应该被阻止"
        assert alert.severity == "BLOCKED"
    
    async def test_position_size_limit(self, risk_checker):
        """测试仓位大小限制"""
        current_position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('90'),  # 已接近限制
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('0'),
        )
        
        # 尝试创建新订单会超限
        new_order = Order(
            order_id="position_test",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('15'),  # 会导致总仓位105，超限
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        alert = await risk_checker.check_order_risk(new_order, current_position)
        assert alert is not None, "会超限的订单应该触发警告"
        assert alert.severity == "WARNING"
        assert "max_position_size" in alert.details
    
    async def test_daily_trade_limit(self, risk_checker, sample_orders):
        """测试日交易次数限制"""
        # 模拟已经达到日交易次数限制
        risk_checker.daily_stats['trade_count'] = 50
        
        order = sample_orders[0]
        alert = await risk_checker.check_order_risk(order)
        
        assert alert is not None, "超过日交易次数的订单应该被阻止"
        assert alert.severity == "BLOCKED"
        assert "max_daily_trades" in alert.details
    
    async def test_daily_volume_limit(self, risk_checker, sample_orders):
        """测试日交易量限制"""
        # 模拟已经接近日交易量限制
        risk_checker.daily_stats['trade_volume'] = Decimal('990000')
        
        order = sample_orders[0]
        order.quantity = Decimal('2')
        order.price = Decimal('10000')  # 2万交易量，总计101万，略超限制
        
        alert = await risk_checker.check_order_risk(order)
        assert alert is not None, "会超日交易量的订单应该触发警告"
        assert alert.severity == "WARNING"
        assert "max_daily_volume" in alert.details
    
    async def test_risk_management_integration(self, risk_integrator, sample_orders):
        """测试风险管理集成器完整流程"""
        normal_order = sample_orders[0]
        
        # 执行风险管理流程
        approved, message, alert = await risk_integrator.process_order_with_risk_management(normal_order)
        
        assert approved is True, "正常订单应该被批准"
        assert alert is None, "正常订单不应该有风险警告"
        assert "通过风险检查" in message
    
    async def test_blocked_order_handling(self, risk_integrator, risk_checker, sample_orders):
        """测试被阻止订单的处理"""
        # 设置限制很低的配置
        risk_checker.limits.max_order_size = Decimal('0.1')
        
        large_order = sample_orders[0]
        large_order.quantity = Decimal('1')  # 会超限
        
        approved, message, alert = await risk_integrator.process_order_with_risk_management(large_order)
        
        assert approved is False, "超限订单应该被拒绝"
        assert alert is not None, "应该返回风险警告"
        assert alert.severity == "BLOCKED", "应该被完全阻止"
        assert large_order.order_id in risk_integrator.blocked_orders
    
    async def test_risk_notification_integration(self, risk_integrator, notification_sender, sample_orders):
        """测试风险通知集成"""
        # 设置低限制以触发警告
        risk_integrator.risk_checker.limits.max_order_size = Decimal('0.1')
        
        large_order = sample_orders[0]
        large_order.quantity = Decimal('1')
        
        approved, message, alert = await risk_integrator.process_order_with_risk_management(large_order)
        
        # 验证通知发送
        notification_sender.send_risk_alert.assert_called_once()
        call_args = notification_sender.send_risk_alert.call_args[0][0]
        assert call_args['severity'] == 'BLOCKED'
        assert call_args['symbol'] == 'BTCUSDT'
    
    async def test_multiple_risk_alerts(self, risk_integrator, risk_checker):
        """测试多重风险警告"""
        # 设置多重限制来触发多个警告
        risk_checker.limits.max_order_size = Decimal('0.5')
        risk_checker.limits.max_position_size = Decimal('1')
        
        current_position = Position(
            symbol="BTCUSDT",
            quantity=Decimal('0.8'),
            avg_price=Decimal('50000'),
            unrealized_pnl=Decimal('0'),
        )
        
        test_order = Order(
            order_id="multi_alert",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('1'),  # 订单过大
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        alert = await risk_checker.check_order_risk(test_order, current_position)
        assert alert is not None, "应该触发至少一个警告"
        
        # 检查所有警告
        all_alerts = risk_checker.alerts
        assert len(all_alerts) >= 1, "应该记录所有风险警告"
    
    async def test_risk_summary_reporting(self, risk_checker, sample_orders):
        """测试风险摘要报告"""
        # 触发一些警告
        risk_checker.daily_stats['trade_count'] = 5
        risk_checker.daily_stats['trade_volume'] = Decimal('250000')
        
        # 添加一些模拟警告
        for i in range(3):
            alert = RiskAlert(
                alert_id=f"test_alert_{i}",
                severity="WARNING",
                message=f"Test warning {i}",
                details={},
                timestamp=datetime.now(),
            )
            risk_checker.alerts.append(alert)
        
        summary = risk_checker.get_risk_summary()
        
        assert summary['daily_stats']['trade_count'] == 5
        assert summary['total_alerts'] == 3
        assert summary['warnings'] == 3
        assert summary['critical_alerts'] == 0
        assert summary['blocked_orders'] == 0
    
    async def test_alert_acknowledgment(self, risk_integrator, risk_checker):
        """测试风险警告确认"""
        # 创建一个警告
        test_alert = RiskAlert(
            alert_id="ack_test",
            severity="WARNING",
            message="Test for acknowledgment",
            details={},
            timestamp=datetime.now(),
        )
        risk_checker.alerts.append(test_alert)
        
        assert not test_alert.acknowledged, "警告初始状态应该是未确认"
        
        await risk_integrator.acknowledge_alert("ack_test")
        
        assert test_alert.acknowledged, "警告应该被确认"
    
    async def test_daily_stats_updates(self, risk_checker, sample_orders):
        """测试日统计更新"""
        order = sample_orders[0]
        
        initial_count = risk_checker.daily_stats['trade_count']
        initial_volume = risk_checker.daily_stats['trade_volume']
        
        risk_checker.update_daily_stats(order, executed=True)
        
        assert risk_checker.daily_stats['trade_count'] == initial_count + 1
        assert risk_checker.daily_stats['trade_volume'] > initial_volume
        
        # 测试未执行订单不更新统计
        risk_checker.update_daily_stats(order, executed=False)
        assert risk_checker.daily_stats['trade_count'] == initial_count + 1
    
    async def test_comprehensive_risk_workflow(self, risk_integrator, risk_checker):
        """测试完整的风险管理流程"""
        # 模拟一天的交易流程
        
        # 1. 正常订单
        normal_order = Order(
            order_id="normal_001",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('1'),
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        approved, msg, alert = await risk_integrator.process_order_with_risk_management(normal_order)
        assert approved is True
        
        # 更新统计
        risk_checker.update_daily_stats(normal_order, executed=True)
        
        # 2. 模拟几次交易后接近限制
        risk_checker.daily_stats['trade_count'] = 45
        risk_checker.daily_stats['trade_volume'] = Decimal('950000')
        
        # 3. 接近限制的订单
        limit_order = Order(
            order_id="limit_001",
            symbol="ETHUSDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('10'),  # 小订单
            price=Decimal('3000'),
            status=OrderStatus.PENDING,
        )
        
        approved, msg, alert = await risk_integrator.process_order_with_risk_management(limit_order)
        # 可能触发交易量警告
        
        # 4. 超出限制的订单
        large_order = Order(
            order_id="blocked_001",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('20'),  # 超出订单大小限制
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        approved, msg, alert = await risk_integrator.process_order_with_risk_management(large_order)
        assert approved is False, "超限订单应该被阻止"
        assert alert.severity == "BLOCKED"
        
        # 5. 获取最终风险摘要
        summary = risk_checker.get_risk_summary()
        assert summary['daily_stats']['trade_count'] >= 2
        assert summary['blocked_orders'] >= 1
    
    async def test_risk_level_escalation(self, risk_integrator, risk_checker):
        """测试风险等级升级"""
        # 从WARNING开始，逐步升级到CRITICAL和BLOCKED
        
        # 设置风险限制较低的配置
        risk_checker.limits.max_order_size = Decimal('5')
        
        # 第一个警告订单
        warning_order = Order(
            order_id="warning_001",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('6'),  # 轻微超限
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        alert = await risk_checker.check_order_risk(warning_order)
        assert alert.severity == "WARNING"
        
        # 第二个更严重的订单（BLOCKED）
        blocked_order = Order(
            order_id="blocked_002",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('20'),  # 严重超限
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        alert = await risk_checker.check_order_risk(blocked_order)
        assert alert.severity == "BLOCKED"
    
    async def test_cross_symbol_risk_management(self, risk_checker):
        """测试跨符号风险管理"""
        # 测试不同符号的风险管理独立工作
        
        btc_order = Order(
            order_id="btc_001",
            symbol="BTCUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('1'),
            price=Decimal('50000'),
            status=OrderStatus.PENDING,
        )
        
        eth_order = Order(
            order_id="eth_001",
            symbol="ETHUSDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('10'),
            price=Decimal('3000'),
            status=OrderStatus.PENDING,
        )
        
        # 分别检查两个订单
        btc_alert = await risk_checker.check_order_risk(btc_order)
        eth_alert = await risk_checker.check_order_risk(eth_order)
        
        # 两个订单都应该通过基本的订单大小检查
        assert btc_alert is None or btc_alert.severity != "BLOCKED"
        assert eth_alert is None or eth_alert.severity != "BLOCKED"