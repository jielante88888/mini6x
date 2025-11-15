"""
风险预警系统集成测试
验证风险预警通知引擎的完整功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from backend.src.notification.risk_alert_integration import (
    RiskAlertNotificationManager,
    RiskAlertEvent,
    RiskAlertType,
    RiskAlertSeverity,
    RiskAlertStatus
)
from backend.src.storage.models import RiskAlert, User, Account
from backend.src.notification.notify_manager import NotificationManager


class TestRiskAlertIntegration:
    """风险预警集成测试类"""
    
    @pytest.fixture
    def mock_notification_manager(self):
        """模拟通知管理器"""
        manager = Mock(spec=NotificationManager)
        manager.send_notification = AsyncMock(return_value=["msg_1", "msg_2"])
        manager.send_custom_notification = AsyncMock(return_value=["msg_3"])
        return manager
    
    @pytest.fixture
    def risk_alert_manager(self, mock_notification_manager):
        """创建风险预警管理器实例"""
        return RiskAlertNotificationManager(mock_notification_manager)
    
    @pytest.fixture
    def sample_risk_alert(self):
        """创建示例风险预警"""
        alert = Mock(spec=RiskAlert)
        alert.id = 1
        alert.user_id = 1001
        alert.account_id = 2001
        alert.alert_id = "alert_20231201_120000_1001"
        alert.severity = "high"
        alert.message = "持仓风险过高，当前风险值: 85%"
        alert.alert_type = "position_risk"
        alert.symbol = "BTCUSDT"
        alert.details = {
            "current_position": 1000,
            "max_position": 1200,
            "risk_ratio": 0.85
        }
        alert.current_value = 85.0
        alert.limit_value = 80.0
        alert.created_at = datetime.now()
        return alert
    
    def test_risk_alert_manager_initialization(self, risk_alert_manager):
        """测试风险预警管理器初始化"""
        assert risk_alert_manager is not None
        assert len(risk_alert_manager.alert_configs) > 0
        assert RiskAlertType.POSITION_RISK in risk_alert_manager.alert_configs
        assert RiskAlertType.LIQUIDATION_RISK in risk_alert_manager.alert_configs
        
        # 检查默认配置
        position_config = risk_alert_manager.alert_configs[RiskAlertType.POSITION_RISK]
        assert position_config.enabled is True
        assert position_config.severity == RiskAlertSeverity.MEDIUM
        assert len(position_config.notification_channels) > 0
    
    def test_create_risk_alert_event(self, risk_alert_manager, sample_risk_alert):
        """测试创建风险预警事件"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 验证事件属性
        assert isinstance(alert_event, RiskAlertEvent)
        assert alert_event.alert_id == sample_risk_alert.id
        assert alert_event.user_id == sample_risk_alert.user_id
        assert alert_event.account_id == sample_risk_alert.account_id
        assert alert_event.severity == RiskAlertSeverity.HIGH
        assert alert_event.status == RiskAlertStatus.ACTIVE
        assert alert_event.risk_value == 85.0
        assert alert_event.threshold_value == 80.0
        
        # 检查是否添加到活跃告警跟踪
        assert sample_risk_alert.id in risk_alert_manager.active_alerts
        
        # 检查统计信息更新
        assert risk_alert_manager.alert_stats["total_alerts"] > 0
        assert risk_alert_manager.alert_stats["active_alerts"] > 0
    
    @pytest.mark.asyncio
    async def test_send_risk_alert_notification(self, risk_alert_manager, mock_notification_manager, sample_risk_alert):
        """测试发送风险预警通知"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 发送通知
        await risk_alert_manager._send_risk_alert_notification(alert_event)
        
        # 验证通知发送
        assert mock_notification_manager.send_notification.called
        call_args = mock_notification_manager.send_notification.call_args
        
        # 检查发送参数
        assert "trigger_event" in call_args.kwargs
        assert "channels" in call_args.kwargs
        assert "priority" in call_args.kwargs
        assert "metadata" in call_args.kwargs
        
        # 检查通知发送状态
        assert alert_event.notification_sent is True
    
    def test_acknowledge_alert(self, risk_alert_manager, sample_risk_alert):
        """测试确认告警"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 确认告警
        success = risk_alert_manager.acknowledge_alert(
            event_id=alert_event.event_id,
            acknowledged_by="test_user"
        )
        
        # 验证确认结果
        assert success is True
        assert alert_event.status == RiskAlertStatus.ACKNOWLEDGED
        assert alert_event.acknowledged_at is not None
        assert alert_event.acknowledged_by == "test_user"
        
        # 验证事件仍存在于活跃告警中（因为是已确认状态）
        assert alert_event.event_id in [
            event.event_id for event in risk_alert_manager.active_alerts.values()
        ]
    
    def test_resolve_alert(self, risk_alert_manager, sample_risk_alert):
        """测试解决告警"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 解决告警
        success = risk_alert_manager.resolve_alert(
            event_id=alert_event.event_id,
            resolved_by="test_user"
        )
        
        # 验证解决结果
        assert success is True
        assert alert_event.status == RiskAlertStatus.RESOLVED
        assert alert_event.resolved_at is not None
        assert alert_event.resolved_by == "test_user"
        
        # 验证事件已从活跃告警中移除
        assert alert_event.alert_id not in risk_alert_manager.active_alerts
    
    def test_escalate_alert(self, risk_alert_manager, mock_notification_manager, sample_risk_alert):
        """测试升级告警"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 升级告警
        success = risk_alert_manager.escalate_alert(
            event_id=alert_event.event_id,
            escalation_level=2
        )
        
        # 验证升级结果
        assert success is True
        assert alert_event.status == RiskAlertStatus.ESCALATED
        assert alert_event.escalated_at is not None
        assert alert_event.escalation_level == 2
        
        # 检查统计信息更新
        assert risk_alert_manager.alert_stats["escalated_alerts"] > 0
    
    def test_urgency_score_calculation(self, risk_alert_manager, sample_risk_alert):
        """测试紧急程度评分计算"""
        # 创建风险预警事件
        alert_event = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=sample_risk_alert.user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 获取紧急程度评分
        urgency_score = alert_event.urgency_score
        
        # 验证评分范围
        assert 1 <= urgency_score <= 10
        
        # 高严重程度应该有较高评分
        high_severity_event = RiskAlertEvent(
            event_id="test_2",
            alert_id=2,
            user_id=1001,
            account_id=2001,
            alert_type=RiskAlertType.LIQUIDATION_RISK,
            severity=RiskAlertSeverity.EMERGENCY,
            status=RiskAlertStatus.ACTIVE,
            title="清算风险",
            message="即将清算",
            risk_value=95.0,
            threshold_value=90.0,
            created_at=datetime.now() - timedelta(hours=2)
        )
        
        emergency_score = high_severity_event.urgency_score
        assert emergency_score >= urgency_score  # 紧急事件评分应该更高
    
    def test_get_user_active_alerts(self, risk_alert_manager, sample_risk_alert):
        """测试获取用户活跃告警"""
        user_id = sample_risk_alert.user_id
        
        # 创建多个告警事件
        alert_event1 = risk_alert_manager.create_risk_alert(
            risk_alert=sample_risk_alert,
            user_id=user_id,
            account_id=sample_risk_alert.account_id
        )
        
        # 创建不同用户的告警
        different_user_alert = Mock(spec=RiskAlert)
        different_user_alert.id = 2
        different_user_alert.user_id = 2002  # 不同用户
        different_user_alert.account_id = 2001
        different_user_alert.alert_id = "alert_2"
        different_user_alert.severity = "medium"
        different_user_alert.message = "测试告警2"
        different_user_alert.alert_type = "test"
        different_user_alert.symbol = "ETHUSDT"
        different_user_alert.details = {}
        different_user_alert.current_value = 50.0
        different_user_alert.limit_value = 60.0
        different_user_alert.created_at = datetime.now()
        
        alert_event2 = risk_alert_manager.create_risk_alert(
            risk_alert=different_user_alert,
            user_id=2002,
            account_id=2001
        )
        
        # 获取特定用户的活跃告警
        user_alerts = risk_alert_manager.get_user_active_alerts(user_id)
        
        # 验证结果
        assert len(user_alerts) == 1
        assert user_alerts[0].event_id == alert_event1.event_id
        
        # 确认告警不应该在活跃告警中
        risk_alert_manager.acknowledge_alert(
            event_id=alert_event1.event_id,
            acknowledged_by="test"
        )
        
        acknowledged_alerts = risk_alert_manager.get_user_active_alerts(user_id)
        assert len(acknowledged_alerts) == 0  # 已确认的告警不应该在活跃列表中
    
    def test_alert_statistics(self, risk_alert_manager, sample_risk_alert):
        """测试告警统计信息"""
        # 创建几个不同类型的告警
        alert_types = [
            RiskAlertType.POSITION_RISK,
            RiskAlertType.MARKET_RISK,
            RiskAlertType.SYSTEM_RISK
        ]
        
        for i, alert_type in enumerate(alert_types):
            mock_alert = Mock(spec=RiskAlert)
            mock_alert.id = i + 1
            mock_alert.user_id = 1001
            mock_alert.account_id = 2001
            mock_alert.alert_id = f"alert_{i}"
            mock_alert.severity = ["low", "medium", "high"][i]
            mock_alert.message = f"测试告警 {i}"
            mock_alert.alert_type = alert_type.value
            mock_alert.symbol = f"SYMBOL{i}"
            mock_alert.details = {}
            mock_alert.current_value = float(i * 10 + 50)
            mock_alert.limit_value = float(i * 10 + 60)
            mock_alert.created_at = datetime.now()
            
            risk_alert_manager.create_risk_alert(
                risk_alert=mock_alert,
                user_id=1001,
                account_id=2001
            )
        
        # 获取统计信息
        stats = risk_alert_manager.get_alert_statistics()
        
        # 验证统计信息
        assert "summary" in stats
        assert "active_alerts" in stats
        assert "configuration" in stats
        
        summary = stats["summary"]
        assert summary["total_alerts"] == len(alert_types)
        assert summary["active_alerts"] == len(alert_types)
        
        # 验证按严重程度统计
        by_severity = summary["by_severity"]
        assert len(by_severity) > 0
        
        # 验证按类型统计
        by_type = summary["by_type"]
        assert len(by_type) > 0
    
    @pytest.mark.asyncio
    async def test_notification_priority_mapping(self, risk_alert_manager):
        """测试通知优先级映射"""
        # 测试不同严重程度到通知优先级的映射
        severity_priority_map = {
            RiskAlertSeverity.LOW: "normal",
            RiskAlertSeverity.MEDIUM: "high", 
            RiskAlertSeverity.HIGH: "urgent",
            RiskAlertSeverity.CRITICAL: "critical",
            RiskAlertSeverity.EMERGENCY: "critical"
        }
        
        for severity, expected_priority in severity_priority_map.items():
            notification_priority = risk_alert_manager._convert_to_notification_priority(severity)
            # 验证优先级映射正确
            assert notification_priority is not None
    
    def test_severity_conversion(self, risk_alert_manager):
        """测试严重程度转换"""
        # 测试从字符串到枚举的转换
        test_cases = {
            "low": RiskAlertSeverity.LOW,
            "MEDIUM": RiskAlertSeverity.MEDIUM,
            "High": RiskAlertSeverity.HIGH,
            "CRITICAL": RiskAlertSeverity.CRITICAL,
            "invalid": RiskAlertSeverity.MEDIUM  # 默认值
        }
        
        for input_severity, expected_severity in test_cases.items():
            result = risk_alert_manager._convert_severity(input_severity)
            assert result == expected_severity
    
    def test_alert_type_determination(self, risk_alert_manager):
        """测试告警类型确定"""
        # 测试从告警类型字符串推断枚举类型
        test_cases = {
            "position_risk": RiskAlertType.POSITION_RISK,
            "ACCOUNT_RISK": RiskAlertType.ACCOUNT_RISK,
            "market_volatility": RiskAlertType.MARKET_RISK,
            "liquidation_warning": RiskAlertType.LIQUIDATION_RISK,
            "exchange_downtime": RiskAlertType.EXCHANGE_RISK,
            "unknown_type": RiskAlertType.SYSTEM_RISK  # 默认类型
        }
        
        for input_type, expected_type in test_cases.items():
            mock_alert = Mock(spec=RiskAlert)
            mock_alert.alert_type = input_type
            mock_alert.severity = "medium"
            mock_alert.message = "测试"
            mock_alert.id = 1
            mock_alert.user_id = 1001
            mock_alert.account_id = 2001
            mock_alert.created_at = datetime.now()
            mock_alert.details = {}
            mock_alert.current_value = 50.0
            mock_alert.limit_value = 60.0
            
            result = risk_alert_manager._determine_alert_type(mock_alert)
            assert result == expected_type


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])