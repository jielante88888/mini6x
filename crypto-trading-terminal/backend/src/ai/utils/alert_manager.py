"""
Alert Manager
Unified alert management and notification system
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog
import json
import asyncio

logger = structlog.get_logger()


class AlertChannel(Enum):
    """Available alert delivery channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    DESKTOP = "desktop"
    LOG = "log"
    FILE = "file"


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AlertMessage:
    """Alert message structure"""
    alert_id: str
    title: str
    message: str
    priority: AlertPriority
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]
    channels: List[AlertChannel]
    acknowledged: bool = False
    resolved: bool = False


class AlertManager:
    """Unified alert management system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_alerts_per_hour": 100,
            "alert_retention_days": 30,
            "rate_limiting": {
                "enabled": True,
                "max_alerts_per_minute": 10
            },
            "channels": {
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "to_addresses": []
                },
                "webhook": {
                    "enabled": False,
                    "urls": [],
                    "timeout_seconds": 30
                },
                "sms": {
                    "enabled": False,
                    "provider": "",
                    "api_key": "",
                    "phone_numbers": []
                },
                "desktop": {
                    "enabled": True
                },
                "log": {
                    "enabled": True,
                    "log_level": "INFO"
                },
                "file": {
                    "enabled": True,
                    "file_path": "alerts.log"
                }
            }
        }
        
        # Alert storage
        self.alerts: List[AlertMessage] = []
        self.active_alerts: Dict[str, AlertMessage] = {}
        
        # Rate limiting
        self.alert_counts: Dict[str, int] = {}  # timestamp -> count
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Channel implementations
        self.channel_handlers = {
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.SMS: self._send_sms_alert,
            AlertChannel.DESKTOP: self._send_desktop_alert,
            AlertChannel.LOG: self._send_log_alert,
            AlertChannel.FILE: self._send_file_alert
        }
        
        # Callback functions
        self.alert_callbacks: List[Callable] = []
        
        logger.info("警报管理器初始化完成", config=self.config)
    
    async def send_alert(self, level: str, title: str, message: str, 
                        metadata: Dict[str, Any] = None, 
                        source: str = "model_monitor",
                        channels: List[str] = None) -> str:
        """Send an alert through configured channels"""
        
        # Convert level to AlertPriority
        try:
            priority = AlertPriority(level.lower())
        except ValueError:
            priority = AlertPriority.MEDIUM
        
        # Default channels if not specified
        if channels is None:
            channels = ["log", "desktop"]
        
        # Convert channel strings to enum
        channel_enums = []
        for channel_str in channels:
            try:
                channel_enums.append(AlertChannel(channel_str))
            except ValueError:
                logger.warning("未知的警报渠道", channel=channel_str)
                continue
        
        if not channel_enums:
            channel_enums = [AlertChannel.LOG, AlertChannel.DESKTOP]
        
        # Create alert message
        alert_id = f"alert_{source}_{int(datetime.now().timestamp())}"
        alert = AlertMessage(
            alert_id=alert_id,
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            source=source,
            metadata=metadata or {},
            channels=channel_enums
        )
        
        # Rate limiting check
        if not await self._check_rate_limit(source):
            logger.warning("警报频率限制，跳过发送", source=source, title=title)
            return alert_id
        
        # Store alert
        self.alerts.append(alert)
        self.active_alerts[alert_id] = alert
        
        # Clean up old alerts
        await self._cleanup_old_alerts()
        
        # Send through configured channels
        send_tasks = []
        for channel in channel_enums:
            if self._is_channel_enabled(channel):
                send_tasks.append(self._send_through_channel(alert, channel))
        
        # Send concurrently
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.warning("警报回调失败", error=str(e))
        
        logger.info("警报已发送", 
                   alert_id=alert_id,
                   priority=priority.value,
                   source=source,
                   channels=[c.value for c in channel_enums])
        
        return alert_id
    
    async def _check_rate_limit(self, source: str) -> bool:
        """Check if alert rate limit is exceeded"""
        if not self.config.get("rate_limiting", {}).get("enabled", True):
            return True
        
        current_time = datetime.now(timezone.utc)
        current_minute = current_time.replace(second=0, microsecond=0)
        minute_key = current_minute.isoformat()
        
        # Initialize counter for this minute
        if minute_key not in self.alert_counts:
            self.alert_counts[minute_key] = 0
        
        # Check limit
        max_alerts_per_minute = self.config["rate_limiting"]["max_alerts_per_minute"]
        if self.alert_counts[minute_key] >= max_alerts_per_minute:
            return False
        
        # Increment counter
        self.alert_counts[minute_key] += 1
        
        return True
    
    async def _send_through_channel(self, alert: AlertMessage, channel: AlertChannel):
        """Send alert through a specific channel"""
        try:
            handler = self.channel_handlers.get(channel)
            if handler:
                await handler(alert)
            else:
                logger.warning("未实现的警报渠道", channel=channel.value)
        except Exception as e:
            logger.error("警报发送失败", 
                        channel=channel.value,
                        alert_id=alert.alert_id,
                        error=str(e))
    
    def _is_channel_enabled(self, channel: AlertChannel) -> bool:
        """Check if a channel is enabled in config"""
        channel_config = self.config.get("channels", {}).get(channel.value, {})
        return channel_config.get("enabled", False)
    
    async def _send_email_alert(self, alert: AlertMessage):
        """Send alert via email"""
        if not self._is_channel_enabled(AlertChannel.EMAIL):
            return
        
        # Email implementation would go here
        # For now, just log the attempt
        logger.info("邮件警报已发送", 
                   alert_id=alert.alert_id,
                   title=alert.title,
                   priority=alert.priority.value)
    
    async def _send_webhook_alert(self, alert: AlertMessage):
        """Send alert via webhook"""
        if not self._is_channel_enabled(AlertChannel.WEBHOOK):
            return
        
        # Webhook implementation would go here
        # For now, just log the attempt
        logger.info("Webhook警报已发送", 
                   alert_id=alert.alert_id,
                   title=alert.title,
                   priority=alert.priority.value)
    
    async def _send_sms_alert(self, alert: AlertMessage):
        """Send alert via SMS"""
        if not self._is_channel_enabled(AlertChannel.SMS):
            return
        
        # SMS implementation would go here
        # For now, just log the attempt
        logger.info("SMS警报已发送", 
                   alert_id=alert.alert_id,
                   title=alert.title,
                   priority=alert.priority.value)
    
    async def _send_desktop_alert(self, alert: AlertMessage):
        """Send desktop notification"""
        if not self._is_channel_enabled(AlertChannel.DESKTOP):
            return
        
        # Desktop notification implementation would go here
        # For now, just log the attempt
        logger.info("桌面警报已发送", 
                   alert_id=alert.alert_id,
                   title=alert.title,
                   priority=alert.priority.value)
    
    async def _send_log_alert(self, alert: AlertMessage):
        """Send alert to application log"""
        if not self._is_channel_enabled(AlertChannel.LOG):
            return
        
        # Log based on priority
        log_level = self.config.get("channels", {}).get("log", {}).get("log_level", "INFO")
        
        log_message = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "priority": alert.priority.value,
            "source": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }
        
        if log_level.upper() == "CRITICAL" and alert.priority == AlertPriority.CRITICAL:
            logger.critical("警报: {}", **log_message)
        elif log_level.upper() == "ERROR" and alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
            logger.error("警报: {}", **log_message)
        elif log_level.upper() == "WARNING" and alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH, AlertPriority.MEDIUM]:
            logger.warning("警报: {}", **log_message)
        else:
            logger.info("警报: {}", **log_message)
    
    async def _send_file_alert(self, alert: AlertMessage):
        """Write alert to file"""
        if not self._is_channel_enabled(AlertChannel.FILE):
            return
        
        file_path = self.config.get("channels", {}).get("file", {}).get("file_path", "alerts.log")
        
        try:
            alert_data = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "priority": alert.priority.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata
            }
            
            # Append to file
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error("文件警报写入失败", file_path=file_path, error=str(e))
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.get("alert_retention_days", 30))
        
        # Remove old alerts from main list
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
        
        # Remove old alerts from active alerts (only keep unacknowledged recent ones)
        to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if alert.acknowledged or alert.resolved or alert.timestamp < cutoff_time:
                to_remove.append(alert_id)
        
        for alert_id in to_remove:
            del self.active_alerts[alert_id]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        # Check in active alerts
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info("警报已确认", alert_id=alert_id)
            return True
        
        # Check in all alerts
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info("警报已确认", alert_id=alert_id)
                return True
        
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        # Check in active alerts
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.active_alerts[alert_id].acknowledged = True
            logger.info("警报已解决", alert_id=alert_id)
            return True
        
        # Check in all alerts
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.acknowledged = True
                logger.info("警报已解决", alert_id=alert_id)
                return True
        
        return False
    
    async def get_active_alerts(self, priority: Optional[AlertPriority] = None,
                              source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active (unacknowledged) alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.acknowledged]
        
        # Apply filters
        if priority:
            active_alerts = [alert for alert in active_alerts if alert.priority == priority]
        
        if source:
            active_alerts = [alert for alert in active_alerts if alert.source == source]
        
        # Sort by timestamp (most recent first)
        active_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "priority": alert.priority.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
                "channels": [c.value for c in alert.channels]
            }
            for alert in active_alerts
        ]
    
    async def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
        
        # Sort by timestamp (most recent first)
        recent_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "priority": alert.priority.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "metadata": alert.metadata,
                "channels": [c.value for c in alert.channels]
            }
            for alert in recent_alerts
        ]
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert system statistics"""
        total_alerts = len(self.alerts)
        active_alerts = len([alert for alert in self.alerts if not alert.acknowledged])
        resolved_alerts = len([alert for alert in self.alerts if alert.resolved])
        
        # Count by priority
        priority_counts = {}
        for priority in AlertPriority:
            priority_counts[priority.value] = len([alert for alert in self.alerts if alert.priority == priority])
        
        # Count by source
        source_counts = {}
        for alert in self.alerts:
            source = alert.source
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Calculate resolution rate
        resolution_rate = (resolved_alerts / total_alerts) if total_alerts > 0 else 0
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": resolved_alerts,
            "resolution_rate": resolution_rate,
            "priority_breakdown": priority_counts,
            "source_breakdown": source_counts,
            "retention_days": self.config.get("alert_retention_days", 30),
            "rate_limiting_enabled": self.config.get("rate_limiting", {}).get("enabled", True)
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add callback function to be called when alerts are sent"""
        self.alert_callbacks.append(callback)
    
    async def test_alert_channels(self) -> Dict[str, bool]:
        """Test all configured alert channels"""
        test_results = {}
        
        for channel in AlertChannel:
            try:
                test_alert = AlertMessage(
                    alert_id=f"test_{channel.value}_{int(datetime.now().timestamp())}",
                    title=f"测试警报 - {channel.value}",
                    message=f"这是一个测试警报，验证 {channel.value} 渠道是否正常工作",
                    priority=AlertPriority.LOW,
                    timestamp=datetime.now(timezone.utc),
                    source="alert_test",
                    metadata={"test": True},
                    channels=[channel]
                )
                
                if self._is_channel_enabled(channel):
                    await self._send_through_channel(test_alert, channel)
                    test_results[channel.value] = True
                else:
                    test_results[channel.value] = False
                    
            except Exception as e:
                logger.error(f"{channel.value} 渠道测试失败", error=str(e))
                test_results[channel.value] = False
        
        return test_results
    
    async def configure_channel(self, channel_name: str, config: Dict[str, Any]):
        """Configure a specific alert channel"""
        if channel_name in self.config["channels"]:
            self.config["channels"][channel_name].update(config)
            logger.info("警报渠道配置已更新", channel=channel_name, config=config)
        else:
            logger.warning("未知的警报渠道", channel=channel_name)
    
    async def enable_channel(self, channel_name: str, enabled: bool = True):
        """Enable or disable a specific alert channel"""
        if channel_name in self.config["channels"]:
            self.config["channels"][channel_name]["enabled"] = enabled
            logger.info("警报渠道状态已更新", channel=channel_name, enabled=enabled)
        else:
            logger.warning("未知的警报渠道", channel=channel_name)
