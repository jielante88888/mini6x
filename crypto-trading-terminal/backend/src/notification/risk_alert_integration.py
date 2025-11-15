"""
风险告警与通知系统集成
实现风险告警的多渠道通知、优先级管理和升级机制
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from ..storage.models import RiskAlert
from .notify_manager import (
    NotificationManager, NotificationChannel, NotificationPriority, 
    NotificationMessage, NotificationTemplate, TriggerEvent
)
from ..conditions.base_conditions import ConditionResult


class RiskAlertSeverity(Enum):
    """风险告警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class RiskAlertStatus(Enum):
    """风险告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class RiskAlertType(Enum):
    """风险告警类型"""
    POSITION_RISK = "position_risk"
    ACCOUNT_RISK = "account_risk"
    MARKET_RISK = "market_risk"
    LIQUIDATION_RISK = "liquidation_risk"
    EXCHANGE_RISK = "exchange_risk"
    STRATEGY_RISK = "strategy_risk"
    SYSTEM_RISK = "system_risk"
    COMPLIANCE_RISK = "compliance_risk"


@dataclass
class RiskAlertConfiguration:
    """风险告警配置"""
    alert_type: RiskAlertType
    severity: RiskAlertSeverity
    enabled: bool = True
    auto_acknowledge: bool = False
    auto_escalate: bool = True
    escalation_delay_minutes: int = 30
    notification_channels: List[NotificationChannel] = None
    escalation_channels: List[NotificationChannel] = None
    acknowledgment_required: bool = True
    max_attempts: int = 3
    retry_delay_minutes: int = 5
    
    # 告警参数
    threshold_values: Dict[str, Any] = None
    custom_template: Optional[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []
        if self.escalation_channels is None:
            self.escalation_channels = []
        if self.threshold_values is None:
            self.threshold_values = {}


@dataclass
class RiskAlertEvent:
    """风险告警事件"""
    event_id: str
    alert_id: int
    user_id: int
    account_id: int
    alert_type: RiskAlertType
    severity: RiskAlertSeverity
    status: RiskAlertStatus
    title: str
    message: str
    risk_value: float
    threshold_value: float
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    escalation_level: int = 0
    retry_count: int = 0
    notification_sent: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_active(self) -> bool:
        return self.status in [RiskAlertStatus.ACTIVE, RiskAlertStatus.ESCALATED]
    
    @property
    def needs_acknowledgment(self) -> bool:
        return self.status == RiskAlertStatus.ACTIVE
    
    @property
    def can_escalate(self) -> bool:
        return self.status == RiskAlertStatus.ACTIVE and self.retry_count < 3
    
    @property
    def time_since_creation(self) -> timedelta:
        return datetime.now() - self.created_at
    
    @property
    def urgency_score(self) -> int:
        """计算紧急程度评分 (1-10)"""
        base_score = {
            RiskAlertSeverity.LOW: 1,
            RiskAlertSeverity.MEDIUM: 3,
            RiskAlertSeverity.HIGH: 5,
            RiskAlertSeverity.CRITICAL: 8,
            RiskAlertSeverity.EMERGENCY: 10
        }[self.severity]
        
        # 时间因素调整
        if self.time_since_creation > timedelta(hours=1):
            base_score += 1
        if self.time_since_creation > timedelta(hours=6):
            base_score += 2
        if self.time_since_creation > timedelta(hours=24):
            base_score += 3
        
        return min(base_score, 10)


class RiskAlertNotificationManager:
    """风险告警通知管理器"""
    
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager
        
        # 告警配置
        self.alert_configs: Dict[RiskAlertType, RiskAlertConfiguration] = {}
        self.user_alert_configs: Dict[int, Dict[RiskAlertType, RiskAlertConfiguration]] = {}
        
        # 活跃告警跟踪
        self.active_alerts: Dict[int, RiskAlertEvent] = {}
        self.pending_notifications: Dict[str, RiskAlertEvent] = {}
        
        # 升级规则
        self.escalation_rules = {
            RiskAlertSeverity.LOW: 120,  # 2小时
            RiskAlertSeverity.MEDIUM: 60,  # 1小时
            RiskAlertSeverity.HIGH: 30,  # 30分钟
            RiskAlertSeverity.CRITICAL: 15,  # 15分钟
            RiskAlertSeverity.EMERGENCY: 5,  # 5分钟
        }
        
        # 告警统计
        self.alert_stats = {
            "total_alerts": 0,
            "active_alerts": 0,
            "resolved_alerts": 0,
            "escalated_alerts": 0,
            "by_severity": {},
            "by_type": {},
            "notification_success_rate": 0.0,
            "average_response_time": 0.0
        }
        
        # 初始化默认配置
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """初始化默认配置"""
        # 仓位风险告警
        self.alert_configs[RiskAlertType.POSITION_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.POSITION_RISK,
            severity=RiskAlertSeverity.MEDIUM,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP
            ],
            escalation_channels=[
                NotificationChannel.TELEGRAM,
                NotificationChannel.EMAIL
            ],
            acknowledgment_required=True,
            max_attempts=3,
            escalation_delay_minutes=30
        )
        
        # 账户风险告警
        self.alert_configs[RiskAlertType.ACCOUNT_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.ACCOUNT_RISK,
            severity=RiskAlertSeverity.HIGH,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.TELEGRAM
            ],
            escalation_channels=[
                NotificationChannel.EMAIL
            ],
            acknowledgment_required=True,
            max_attempts=2,
            escalation_delay_minutes=15
        )
        
        # 市场风险告警
        self.alert_configs[RiskAlertType.MARKET_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.MARKET_RISK,
            severity=RiskAlertSeverity.MEDIUM,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP
            ],
            escalation_channels=[
                NotificationChannel.WEBHOOK
            ],
            acknowledgment_required=False,
            max_attempts=2,
            escalation_delay_minutes=60
        )
        
        # 清算风险告警
        self.alert_configs[RiskAlertType.LIQUIDATION_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.LIQUIDATION_RISK,
            severity=RiskAlertSeverity.EMERGENCY,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.TELEGRAM,
                NotificationChannel.EMAIL
            ],
            escalation_channels=[
                NotificationChannel.PHONE_CALL
            ],
            acknowledgment_required=True,
            max_attempts=1,
            escalation_delay_minutes=5
        )
        
        # 交易所风险告警
        self.alert_configs[RiskAlertType.EXCHANGE_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.EXCHANGE_RISK,
            severity=RiskAlertSeverity.HIGH,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.TELEGRAM
            ],
            escalation_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.WEBHOOK
            ],
            acknowledgment_required=True,
            max_attempts=2,
            escalation_delay_minutes=20
        )
        
        # 策略风险告警
        self.alert_configs[RiskAlertType.STRATEGY_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.STRATEGY_RISK,
            severity=RiskAlertSeverity.MEDIUM,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP
            ],
            escalation_channels=[
                NotificationChannel.TELEGRAM
            ],
            acknowledgment_required=False,
            max_attempts=3,
            escalation_delay_minutes=45
        )
        
        # 系统风险告警
        self.alert_configs[RiskAlertType.SYSTEM_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.SYSTEM_RISK,
            severity=RiskAlertSeverity.CRITICAL,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.TELEGRAM,
                NotificationChannel.EMAIL
            ],
            escalation_channels=[
                NotificationChannel.WEBHOOK
            ],
            acknowledgment_required=True,
            max_attempts=1,
            escalation_delay_minutes=10
        )
        
        # 合规风险告警
        self.alert_configs[RiskAlertType.COMPLIANCE_RISK] = RiskAlertConfiguration(
            alert_type=RiskAlertType.COMPLIANCE_RISK,
            severity=RiskAlertSeverity.CRITICAL,
            enabled=True,
            auto_escalate=True,
            notification_channels=[
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.EMAIL
            ],
            escalation_channels=[
                NotificationChannel.WEBHOOK
            ],
            acknowledgment_required=True,
            max_attempts=1,
            escalation_delay_minutes=30
        )
    
    def configure_user_alert(
        self,
        user_id: int,
        alert_type: RiskAlertType,
        config: RiskAlertConfiguration
    ):
        """配置用户特定的风险告警"""
        if user_id not in self.user_alert_configs:
            self.user_alert_configs[user_id] = {}
        
        self.user_alert_configs[user_id][alert_type] = config
        print(f"已配置用户 {user_id} 的 {alert_type.value} 告警")
    
    def get_alert_config(
        self,
        user_id: int,
        alert_type: RiskAlertType
    ) -> RiskAlertConfiguration:
        """获取告警配置（优先使用用户配置，否则使用默认配置）"""
        # 优先使用用户特定配置
        user_configs = self.user_alert_configs.get(user_id, {})
        if alert_type in user_configs:
            return user_configs[alert_type]
        
        # 使用默认配置
        return self.alert_configs.get(alert_type, RiskAlertConfiguration(
            alert_type=alert_type,
            severity=RiskAlertSeverity.MEDIUM
        ))
    
    def create_risk_alert(
        self,
        risk_alert: RiskAlert,
        user_id: int,
        account_id: int
    ) -> RiskAlertEvent:
        """创建风险告警事件"""
        # 生成事件ID
        event_id = str(uuid.uuid4())
        
        # 转换严重程度
        severity = self._convert_severity(risk_alert.severity)
        
        # 创建告警事件
        alert_event = RiskAlertEvent(
            event_id=event_id,
            alert_id=risk_alert.id,
            user_id=user_id,
            account_id=account_id,
            alert_type=self._determine_alert_type(risk_alert),
            severity=severity,
            status=RiskAlertStatus.ACTIVE,
            title=self._generate_alert_title(risk_alert),
            message=risk_alert.message,
            risk_value=float(risk_alert.current_value) if risk_alert.current_value else 0.0,
            threshold_value=float(risk_alert.limit_value) if risk_alert.limit_value else 0.0,
            created_at=risk_alert.created_at,
            metadata=risk_alert.details or {}
        )
        
        # 添加到活跃告警跟踪
        self.active_alerts[risk_alert.id] = alert_event
        
        # 更新统计
        self._update_stats("created", severity, alert_event.alert_type)
        
        # 发送通知
        asyncio.create_task(self._send_risk_alert_notification(alert_event))
        
        print(f"创建风险告警事件: {event_id} - {alert_event.title}")
        
        return alert_event
    
    def acknowledge_alert(
        self,
        event_id: str,
        acknowledged_by: str
    ) -> bool:
        """确认告警"""
        alert_event = self._find_alert_event(event_id)
        if not alert_event:
            return False
        
        alert_event.status = RiskAlertStatus.ACKNOWLEDGED
        alert_event.acknowledged_at = datetime.now()
        alert_event.acknowledged_by = acknowledged_by
        
        # 取消待发送的升级通知
        self._cancel_pending_escalation(event_id)
        
        print(f"告警已确认: {event_id} by {acknowledged_by}")
        return True
    
    def resolve_alert(
        self,
        event_id: str,
        resolved_by: str
    ) -> bool:
        """解决告警"""
        alert_event = self._find_alert_event(event_id)
        if not alert_event:
            return False
        
        alert_event.status = RiskAlertStatus.RESOLVED
        alert_event.resolved_at = datetime.now()
        alert_event.resolved_by = resolved_by
        
        # 从活跃告警中移除
        self.active_alerts.pop(alert_event.alert_id, None)
        
        # 更新统计
        self._update_stats("resolved", alert_event.severity, alert_event.alert_type)
        
        print(f"告警已解决: {event_id} by {resolved_by}")
        return True
    
    def escalate_alert(self, event_id: str, escalation_level: int = 1) -> bool:
        """升级告警"""
        alert_event = self._find_alert_event(event_id)
        if not alert_event or not alert_event.can_escalate:
            return False
        
        alert_event.status = RiskAlertStatus.ESCALATED
        alert_event.escalated_at = datetime.now()
        alert_event.escalation_level += escalation_level
        
        # 更新统计
        self._update_stats("escalated", alert_event.severity, alert_event.alert_type)
        
        # 发送升级通知
        asyncio.create_task(self._send_escalation_notification(alert_event))
        
        print(f"告警已升级: {event_id} level {alert_event.escalation_level}")
        return True
    
    async def process_alert_lifecycle(self):
        """处理告警生命周期"""
        while True:
            try:
                current_time = datetime.now()
                
                # 检查需要升级的告警
                await self._check_escalation_triggers(current_time)
                
                # 检查需要重新发送的通知
                await self._check_notification_retries(current_time)
                
                # 检查过期的告警
                await self._check_expired_alerts(current_time)
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                print(f"处理告警生命周期时出错: {str(e)}")
                await asyncio.sleep(60)
    
    async def _send_risk_alert_notification(self, alert_event: RiskAlertEvent):
        """发送风险告警通知"""
        try:
            # 获取告警配置
            config = self.get_alert_config(alert_event.user_id, alert_event.alert_type)
            
            if not config.enabled:
                return
            
            # 创建触发事件
            trigger_event = self._create_trigger_event(alert_event)
            
            # 发送通知
            message_ids = self.notification_manager.send_notification(
                trigger_event=trigger_event,
                channels=config.notification_channels,
                priority=self._convert_to_notification_priority(alert_event.severity),
                metadata={
                    "alert_event_id": alert_event.event_id,
                    "alert_type": alert_event.alert_type.value,
                    "severity": alert_event.severity.value,
                    "risk_value": alert_event.risk_value,
                    "threshold_value": alert_event.threshold_value,
                    "user_id": alert_event.user_id,
                    "account_id": alert_event.account_id
                }
            )
            
            alert_event.notification_sent = len(message_ids) > 0
            
            if alert_event.notification_sent:
                print(f"风险告警通知已发送: {alert_event.event_id}")
            else:
                print(f"风险告警通知发送失败: {alert_event.event_id}")
            
        except Exception as e:
            print(f"发送风险告警通知时出错: {str(e)}")
    
    async def _send_escalation_notification(self, alert_event: RiskAlertEvent):
        """发送升级通知"""
        try:
            # 获取告警配置
            config = self.get_alert_config(alert_event.user_id, alert_event.alert_type)
            
            # 创建升级通知
            escalation_title = f"🚨 告警升级 - {alert_event.title}"
            escalation_message = f"""
告警已升级到第{alert_event.escalation_level}级

原始告警: {alert_event.title}
告警详情: {alert_event.message}
风险值: {alert_event.risk_value}
阈值: {alert_event.threshold_value}
创建时间: {alert_event.created_at.strftime('%Y-%m-%d %H:%M:%S')}
升级时间: {alert_event.escalated_at.strftime('%Y-%m-%d %H:%M:%S')}

请立即处理此高优先级告警！
"""
            
            # 发送升级通知
            message_ids = self.notification_manager.send_custom_notification(
                title=escalation_title,
                content=escalation_message,
                channels=config.escalation_channels,
                priority=NotificationPriority.URGENT,
                metadata={
                    "alert_event_id": alert_event.event_id,
                    "escalation_level": alert_event.escalation_level,
                    "original_alert": alert_event.title
                }
            )
            
            print(f"升级通知已发送: {alert_event.event_id}")
            
        except Exception as e:
            print(f"发送升级通知时出错: {str(e)}")
    
    async def _check_escalation_triggers(self, current_time: datetime):
        """检查升级触发条件"""
        for alert_event in self.active_alerts.values():
            if not alert_event.is_active:
                continue
            
            config = self.get_alert_config(alert_event.user_id, alert_event.alert_type)
            
            if not config.auto_escalate:
                continue
            
            # 检查升级延迟
            time_since_creation = current_time - alert_event.created_at
            escalation_delay = timedelta(minutes=config.escalation_delay_minutes)
            
            if time_since_creation > escalation_delay and alert_event.retry_count < config.max_attempts:
                # 升级告警
                self.escalate_alert(alert_event.event_id)
                alert_event.retry_count += 1
                
                # 设置下次升级检查
                next_escalation_time = current_time + timedelta(minutes=config.retry_delay_minutes)
                self.pending_notifications[alert_event.event_id] = alert_event
    
    async def _check_notification_retries(self, current_time: datetime):
        """检查通知重试"""
        for event_id, alert_event in list(self.pending_notifications.items()):
            config = self.get_alert_config(alert_event.user_id, alert_event.alert_type)
            
            # 检查是否需要重试
            if alert_event.retry_count < config.max_attempts:
                time_since_last_attempt = current_time - alert_event.created_at
                retry_delay = timedelta(minutes=config.retry_delay_minutes)
                
                if time_since_last_attempt > retry_delay:
                    # 重试发送通知
                    await self._send_risk_alert_notification(alert_event)
                    alert_event.retry_count += 1
                    
                    # 如果达到最大重试次数，移除待处理
                    if alert_event.retry_count >= config.max_attempts:
                        self.pending_notifications.pop(event_id, None)
            else:
                # 达到最大重试次数，移除待处理
                self.pending_notifications.pop(event_id, None)
    
    async def _check_expired_alerts(self, current_time: datetime):
        """检查过期的告警"""
        expired_alerts = []
        
        for alert_event in self.active_alerts.values():
            # 告警过期时间：24小时
            if current_time - alert_event.created_at > timedelta(hours=24):
                alert_event.status = RiskAlertStatus.EXPIRED
                expired_alerts.append(alert_event.event_id)
        
        # 移除过期告警
        for event_id in expired_alerts:
            alert_event = self.active_alerts.pop(alert_event.event_id, None)
            if alert_event:
                self._update_stats("expired", alert_event.severity, alert_event.alert_type)
                print(f"告警已过期: {event_id}")
    
    def _cancel_pending_escalation(self, event_id: str):
        """取消待发送的升级通知"""
        self.pending_notifications.pop(event_id, None)
    
    def _find_alert_event(self, event_id: str) -> Optional[RiskAlertEvent]:
        """查找告警事件"""
        for alert_event in self.active_alerts.values():
            if alert_event.event_id == event_id:
                return alert_event
        return None
    
    def _convert_severity(self, severity: str) -> RiskAlertSeverity:
        """转换严重程度"""
        severity_map = {
            "low": RiskAlertSeverity.LOW,
            "medium": RiskAlertSeverity.MEDIUM,
            "high": RiskAlertSeverity.HIGH,
            "critical": RiskAlertSeverity.CRITICAL
        }
        return severity_map.get(severity.lower(), RiskAlertSeverity.MEDIUM)
    
    def _determine_alert_type(self, risk_alert: RiskAlert) -> RiskAlertType:
        """确定告警类型"""
        alert_type_map = {
            "position": RiskAlertType.POSITION_RISK,
            "account": RiskAlertType.ACCOUNT_RISK,
            "market": RiskAlertType.MARKET_RISK,
            "liquidation": RiskAlertType.LIQUIDATION_RISK,
            "exchange": RiskAlertType.EXCHANGE_RISK,
            "strategy": RiskAlertType.STRATEGY_RISK,
            "system": RiskAlertType.SYSTEM_RISK,
            "compliance": RiskAlertType.COMPLIANCE_RISK
        }
        
        # 从告警类型字段推断
        alert_type_str = risk_alert.alert_type.lower()
        for key, value in alert_type_map.items():
            if key in alert_type_str:
                return value
        
        return RiskAlertType.SYSTEM_RISK  # 默认类型
    
    def _generate_alert_title(self, risk_alert: RiskAlert) -> str:
        """生成告警标题"""
        type_titles = {
            RiskAlertType.POSITION_RISK: "仓位风险",
            RiskAlertType.ACCOUNT_RISK: "账户风险",
            RiskAlertType.MARKET_RISK: "市场风险",
            RiskAlertType.LIQUIDATION_RISK: "清算风险",
            RiskAlertType.EXCHANGE_RISK: "交易所风险",
            RiskAlertType.STRATEGY_RISK: "策略风险",
            RiskAlertType.SYSTEM_RISK: "系统风险",
            RiskAlertType.COMPLIANCE_RISK: "合规风险"
        }
        
        alert_type = self._determine_alert_type(risk_alert)
        title_prefix = type_titles.get(alert_type, "风险告警")
        
        return f"🚨 {title_prefix} - 风险值: {risk_alert.risk_value:.2f}"
    
    def _create_trigger_event(self, alert_event: RiskAlertEvent) -> TriggerEvent:
        """创建触发事件"""
        # 创建模拟的触发结果
        class MockResult:
            def __init__(self, value, details):
                self.value = value
                self.details = details
        
        result = MockResult(
            value={
                "alert_event_id": alert_event.event_id,
                "risk_value": alert_event.risk_value,
                "threshold_value": alert_event.threshold_value,
                "severity": alert_event.severity.value
            },
            details=alert_event.message
        )
        
        return TriggerEvent(
            condition_id=f"risk_alert_{alert_event.alert_id}",
            condition_name=alert_event.title,
            timestamp=alert_event.created_at,
            result=result,
            priority=alert_event.urgency_score
        )
    
    def _convert_to_notification_priority(self, severity: RiskAlertSeverity) -> NotificationPriority:
        """转换为通知优先级"""
        priority_map = {
            RiskAlertSeverity.LOW: NotificationPriority.NORMAL,
            RiskAlertSeverity.MEDIUM: NotificationPriority.HIGH,
            RiskAlertSeverity.HIGH: NotificationPriority.URGENT,
            RiskAlertSeverity.CRITICAL: NotificationPriority.CRITICAL,
            RiskAlertSeverity.EMERGENCY: NotificationPriority.CRITICAL
        }
        return priority_map.get(severity, NotificationPriority.NORMAL)
    
    def _update_stats(self, action: str, severity: RiskAlertSeverity, alert_type: RiskAlertType):
        """更新统计信息"""
        self.alert_stats["total_alerts"] += 1
        
        if action == "resolved":
            self.alert_stats["resolved_alerts"] += 1
        elif action == "escalated":
            self.alert_stats["escalated_alerts"] += 1
        elif action == "expired":
            # 过期告警不增加总数，但标记为非活跃
            pass
        
        # 按严重程度统计
        severity_key = severity.value
        self.alert_stats["by_severity"][severity_key] = (
            self.alert_stats["by_severity"].get(severity_key, 0) + 1
        )
        
        # 按类型统计
        type_key = alert_type.value
        self.alert_stats["by_type"][type_key] = (
            self.alert_stats["by_type"].get(type_key, 0) + 1
        )
        
        # 更新活跃告警数
        self.alert_stats["active_alerts"] = len(self.active_alerts)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        return {
            "summary": self.alert_stats.copy(),
            "active_alerts": [
                asdict(alert) for alert in self.active_alerts.values()
            ],
            "pending_notifications": len(self.pending_notifications),
            "configuration": {
                alert_type.value: {
                    "enabled": config.enabled,
                    "severity": config.severity.value,
                    "auto_escalate": config.auto_escalate,
                    "channels": [ch.value for ch in config.notification_channels]
                }
                for alert_type, config in self.alert_configs.items()
            }
        }
    
    def get_user_active_alerts(self, user_id: int) -> List[RiskAlertEvent]:
        """获取用户活跃告警"""
        return [
            alert for alert in self.active_alerts.values()
            if alert.user_id == user_id and alert.is_active
        ]
    
    def cleanup_old_alerts(self, days_old: int = 30):
        """清理旧的告警记录"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # 这里应该实现与数据库的交互，删除旧的告警记录
        # 目前只是打印清理信息
        print(f"清理 {days_old} 天前的告警记录 (截止日期: {cutoff_date})")


# 全局风险告警通知管理器实例
_global_risk_alert_manager: Optional[RiskAlertNotificationManager] = None


def get_risk_alert_notification_manager() -> RiskAlertNotificationManager:
    """获取全局风险告警通知管理器实例"""
    global _global_risk_alert_manager
    if _global_risk_alert_manager is None:
        notification_manager = get_notification_manager()
        _global_risk_alert_manager = RiskAlertNotificationManager(notification_manager)
    return _global_risk_alert_manager


def init_risk_alert_notification_manager(notification_manager: NotificationManager) -> RiskAlertNotificationManager:
    """初始化全局风险告警通知管理器"""
    global _global_risk_alert_manager
    _global_risk_alert_manager = RiskAlertNotificationManager(notification_manager)
    return _global_risk_alert_manager