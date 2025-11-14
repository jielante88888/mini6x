"""
通知管理器
处理多渠道通知发送、队列管理、重试机制和状态跟踪
"""

import asyncio
import json
import smtplib
import ssl
import tempfile
import threading
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import aiohttp
import websockets
from concurrent.futures import ThreadPoolExecutor
import ssl as ssl_module

from ..conditions.condition_engine import TriggerEvent


class NotificationChannel(Enum):
    """通知渠道枚举"""
    POPUP = "popup"
    DESKTOP = "desktop"
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"
    DISCORD = "discord"
    PUSH_NOTIFICATION = "push_notification"
    FILE_LOG = "file_log"


class NotificationPriority(Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class DeliveryStatus(Enum):
    """投递状态枚举"""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class NotificationTemplate(Enum):
    """通知模板枚举"""
    PRICE_ALERT = "price_alert"
    VOLUME_SPIKE = "volume_spike"
    TECHNICAL_SIGNAL = "technical_signal"
    SYSTEM_ALERT = "system_alert"
    TRADING_SIGNAL = "trading_signal"
    ERROR_ALERT = "error_alert"
    CUSTOM = "custom"


@dataclass
class NotificationConfig:
    """通知配置"""
    channel: NotificationChannel
    enabled: bool = True
    priority: NotificationPriority = NotificationPriority.NORMAL
    retry_attempts: int = 3
    retry_delay: float = 5.0
    timeout: float = 30.0
    batch_size: int = 10
    batch_delay: float = 2.0
    rate_limit: int = 60  # 每分钟最大通知数
    
    # 渠道特定配置
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


@dataclass
class NotificationMessage:
    """通知消息"""
    message_id: str
    channel: NotificationChannel
    title: str
    content: str
    priority: NotificationPriority
    timestamp: datetime
    trigger_event: Optional[TriggerEvent] = None
    template: Optional[NotificationTemplate] = None
    metadata: Dict[str, Any] = None
    attachments: Optional[List[str]] = None
    recipient: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.attachments is None:
            self.attachments = []


@dataclass
class DeliveryAttempt:
    """投递尝试记录"""
    attempt_id: str
    timestamp: datetime
    status: DeliveryStatus
    response: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class DeliveryRecord:
    """投递记录"""
    message_id: str
    channel: NotificationChannel
    status: DeliveryStatus
    created_at: datetime
    delivered_at: Optional[datetime] = None
    attempts: List[DeliveryAttempt] = None
    total_attempts: int = 0
    final_error: Optional[str] = None
    
    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []


class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 通知配置
        self.channel_configs: Dict[NotificationChannel, NotificationConfig] = {}
        self.default_config = NotificationConfig(NotificationChannel.POPUP)
        
        # 消息队列
        self.pending_queue: List[NotificationMessage] = []
        self.sending_queue: Dict[str, NotificationMessage] = {}
        self.delivery_records: Dict[str, DeliveryRecord] = {}
        
        # 线程和并发控制
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 通知渠道处理器
        self.channel_handlers = {
            NotificationChannel.POPUP: self._handle_popup_notification,
            NotificationChannel.DESKTOP: self._handle_desktop_notification,
            NotificationChannel.TELEGRAM: self._handle_telegram_notification,
            NotificationChannel.EMAIL: self._handle_email_notification,
            NotificationChannel.WEBHOOK: self._handle_webhook_notification,
            NotificationChannel.FILE_LOG: self._handle_file_log_notification,
            NotificationChannel.SMS: self._handle_sms_notification,
            NotificationChannel.SLACK: self._handle_slack_notification,
            NotificationChannel.DISCORD: self._handle_discord_notification,
        }
        
        # 模板引擎
        self.template_engine = NotificationTemplateEngine()
        
        # 统计信息
        self.stats = {
            "total_sent": 0,
            "total_failed": 0,
            "by_channel": {},
            "by_priority": {},
            "average_delivery_time": 0.0,
            "last_sent_time": None
        }
        
        # 速率限制
        self.rate_limiters: Dict[NotificationChannel, List[datetime]] = {}
        
        # 初始化默认配置
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """初始化默认配置"""
        # 弹窗通知
        self.channel_configs[NotificationChannel.POPUP] = NotificationConfig(
            channel=NotificationChannel.POPUP,
            enabled=True,
            priority=NotificationPriority.NORMAL,
            retry_attempts=2,
            retry_delay=1.0,
            timeout=5.0,
            rate_limit=10
        )
        
        # 桌面通知
        self.channel_configs[NotificationChannel.DESKTOP] = NotificationConfig(
            channel=NotificationChannel.DESKTOP,
            enabled=True,
            priority=NotificationPriority.NORMAL,
            retry_attempts=3,
            retry_delay=2.0,
            timeout=10.0,
            rate_limit=30
        )
        
        # Telegram通知
        self.channel_configs[NotificationChannel.TELEGRAM] = NotificationConfig(
            channel=NotificationChannel.TELEGRAM,
            enabled=False,  # 需要配置token
            priority=NotificationPriority.HIGH,
            retry_attempts=3,
            retry_delay=5.0,
            timeout=15.0,
            rate_limit=20
        )
        
        # 邮件通知
        self.channel_configs[NotificationChannel.EMAIL] = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=False,  # 需要配置SMTP
            priority=NotificationPriority.HIGH,
            retry_attempts=3,
            retry_delay=10.0,
            timeout=30.0,
            rate_limit=5
        )
        
        # Webhook通知
        self.channel_configs[NotificationChannel.WEBHOOK] = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=False,
            priority=NotificationPriority.NORMAL,
            retry_attempts=3,
            retry_delay=3.0,
            timeout=10.0,
            rate_limit=60
        )
        
        # 文件日志
        self.channel_configs[NotificationChannel.FILE_LOG] = NotificationConfig(
            channel=NotificationChannel.FILE_LOG,
            enabled=True,
            priority=NotificationPriority.LOW,
            retry_attempts=1,
            retry_delay=0.5,
            timeout=2.0,
            rate_limit=1000
        )
    
    def configure_channel(self, channel: NotificationChannel, config: NotificationConfig):
        """配置通知渠道"""
        with self.lock:
            self.channel_configs[channel] = config
            print(f"已配置通知渠道: {channel.value}")
    
    def enable_channel(self, channel: NotificationChannel, enabled: bool = True):
        """启用/禁用通知渠道"""
        with self.lock:
            if channel in self.channel_configs:
                self.channel_configs[channel].enabled = enabled
                print(f"通知渠道 {channel.value} 已{'启用' if enabled else '禁用'}")
    
    def send_notification(
        self,
        trigger_event: TriggerEvent,
        channels: Optional[List[NotificationChannel]] = None,
        template: Optional[NotificationTemplate] = None,
        custom_content: Optional[str] = None,
        priority: Optional[NotificationPriority] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """发送通知"""
        
        # 确定通知渠道
        if channels is None:
            channels = self._determine_channels_from_event(trigger_event)
        
        message_ids = []
        
        for channel in channels:
            try:
                # 检查渠道是否启用
                if not self._is_channel_enabled(channel):
                    continue
                
                # 检查速率限制
                if not self._check_rate_limit(channel):
                    print(f"通知渠道 {channel.value} 速率限制已触发，跳过发送")
                    continue
                
                # 生成通知消息
                message = self._create_notification_message(
                    trigger_event=trigger_event,
                    channel=channel,
                    template=template,
                    custom_content=custom_content,
                    priority=priority,
                    metadata=metadata or {}
                )
                
                # 添加到队列
                message_id = self._queue_message(message)
                message_ids.append(message_id)
                
                # 立即发送（如果配置为立即发送）
                config = self.channel_configs.get(channel, self.default_config)
                if config.priority in [NotificationPriority.URGENT, NotificationPriority.CRITICAL]:
                    asyncio.create_task(self._process_pending_queue())
                
            except Exception as e:
                print(f"发送通知失败 {channel.value}: {str(e)}")
                continue
        
        return message_ids
    
    def send_custom_notification(
        self,
        title: str,
        content: str,
        channels: List[NotificationChannel],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """发送自定义通知"""
        
        message_ids = []
        
        for channel in channels:
            try:
                if not self._is_channel_enabled(channel):
                    continue
                
                if not self._check_rate_limit(channel):
                    continue
                
                message = NotificationMessage(
                    message_id=str(uuid.uuid4()),
                    channel=channel,
                    title=title,
                    content=content,
                    priority=priority,
                    timestamp=datetime.now(),
                    metadata=metadata or {}
                )
                
                message_id = self._queue_message(message)
                message_ids.append(message_id)
                
            except Exception as e:
                print(f"发送自定义通知失败 {channel.value}: {str(e)}")
                continue
        
        return message_ids
    
    async def process_queue(self):
        """处理通知队列"""
        await self._process_pending_queue()
    
    def get_delivery_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取投递状态"""
        with self.lock:
            record = self.delivery_records.get(message_id)
            if not record:
                return None
            
            return asdict(record)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                "stats": self.stats.copy(),
                "queue_size": len(self.pending_queue),
                "sending_count": len(self.sending_queue),
                "channel_configs": {
                    channel.value: {
                        "enabled": config.enabled,
                        "priority": config.priority.value,
                        "rate_limit": config.rate_limit
                    }
                    for channel, config in self.channel_configs.items()
                }
            }
    
    def clear_queue(self):
        """清空队列"""
        with self.lock:
            self.pending_queue.clear()
            self.sending_queue.clear()
            print("通知队列已清空")
    
    def _determine_channels_from_event(self, trigger_event: TriggerEvent) -> List[NotificationChannel]:
        """根据触发事件确定通知渠道"""
        # 根据条件类型和优先级确定渠道
        condition_type = trigger_event.result.value.__class__.__name__ if trigger_event.result.value else "Unknown"
        
        # 优先级映射
        priority = trigger_event.priority
        if priority >= 8:  # 高优先级
            return [NotificationChannel.DESKTOP, NotificationChannel.POPUP, NotificationChannel.TELEGRAM]
        elif priority >= 5:  # 中等优先级
            return [NotificationChannel.POPUP, NotificationChannel.DESKTOP]
        else:  # 低优先级
            return [NotificationChannel.FILE_LOG]
    
    def _is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """检查渠道是否启用"""
        config = self.channel_configs.get(channel, self.default_config)
        return config.enabled
    
    def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """检查速率限制"""
        config = self.channel_configs.get(channel, self.default_config)
        
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        
        # 初始化速率限制记录
        if channel not in self.rate_limiters:
            self.rate_limiters[channel] = []
        
        # 清理过旧的记录
        cutoff_time = current_minute - timedelta(minutes=1)
        self.rate_limiters[channel] = [
            timestamp for timestamp in self.rate_limiters[channel]
            if timestamp > cutoff_time
        ]
        
        # 检查是否超过限制
        if len(self.rate_limiters[channel]) >= config.rate_limit:
            return False
        
        # 记录本次发送
        self.rate_limiters[channel].append(now)
        return True
    
    def _create_notification_message(
        self,
        trigger_event: TriggerEvent,
        channel: NotificationChannel,
        template: Optional[NotificationTemplate],
        custom_content: Optional[str],
        priority: Optional[NotificationPriority],
        metadata: Dict[str, Any]
    ) -> NotificationMessage:
        """创建通知消息"""
        
        # 生成标题和内容
        if custom_content:
            title, content = self._parse_custom_content(custom_content)
        else:
            title, content = self.template_engine.render(
                template or NotificationTemplate.CUSTOM,
                trigger_event,
                channel
            )
        
        # 确定优先级
        if priority is None:
            config = self.channel_configs.get(channel, self.default_config)
            priority = config.priority
        
        return NotificationMessage(
            message_id=str(uuid.uuid4()),
            channel=channel,
            title=title,
            content=content,
            priority=priority,
            timestamp=datetime.now(),
            trigger_event=trigger_event,
            template=template,
            metadata=metadata
        )
    
    def _parse_custom_content(self, custom_content: str) -> Tuple[str, str]:
        """解析自定义内容"""
        lines = custom_content.strip().split('\n', 1)
        if len(lines) == 1:
            return "通知", lines[0]
        else:
            return lines[0], lines[1]
    
    def _queue_message(self, message: NotificationMessage) -> str:
        """将消息加入队列"""
        with self.lock:
            self.pending_queue.append(message)
            
            # 创建投递记录
            record = DeliveryRecord(
                message_id=message.message_id,
                channel=message.channel,
                status=DeliveryStatus.PENDING,
                created_at=message.timestamp
            )
            self.delivery_records[message.message_id] = record
            
            print(f"消息已加入队列: {message.message_id} ({message.channel.value})")
            return message.message_id
    
    async def _process_pending_queue(self):
        """处理待发送队列"""
        while True:
            try:
                # 获取待发送的消息
                message = None
                with self.lock:
                    if self.pending_queue:
                        message = self.pending_queue.pop(0)
                
                if not message:
                    await asyncio.sleep(0.1)
                    continue
                
                # 检查消息是否过期
                if self._is_message_expired(message):
                    self._mark_as_expired(message.message_id)
                    continue
                
                # 发送到对应渠道
                await self._send_message(message)
                
                # 处理批量延迟
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"处理队列时出错: {str(e)}")
                await asyncio.sleep(1)
    
    def _is_message_expired(self, message: NotificationMessage) -> bool:
        """检查消息是否过期"""
        # 消息有效期：1小时
        expiry_time = message.timestamp + timedelta(hours=1)
        return datetime.now() > expiry_time
    
    def _mark_as_expired(self, message_id: str):
        """标记为过期"""
        with self.lock:
            if message_id in self.delivery_records:
                self.delivery_records[message_id].status = DeliveryStatus.EXPIRED
    
    async def _send_message(self, message: NotificationMessage):
        """发送消息"""
        channel = message.channel
        handler = self.channel_handlers.get(channel)
        
        if not handler:
            print(f"不支持的通知渠道: {channel.value}")
            return
        
        message_id = message.message_id
        
        # 更新状态
        with self.lock:
            if message_id in self.delivery_records:
                self.delivery_records[message_id].status = DeliveryStatus.SENDING
            self.sending_queue[message_id] = message
        
        try:
            # 执行发送
            success = await handler(message)
            
            # 更新状态
            with self.lock:
                if message_id in self.delivery_records:
                    record = self.delivery_records[message_id]
                    record.status = DeliveryStatus.DELIVERED if success else DeliveryStatus.FAILED
                    record.delivered_at = datetime.now()
                    record.total_attempts = len(record.attempts)
                    
                    if not success:
                        record.final_error = f"渠道 {channel.value} 发送失败"
                
                self.sending_queue.pop(message_id, None)
            
            # 更新统计
            if success:
                self._update_stats_success(channel, message.priority)
            else:
                self._update_stats_failure(channel, message.priority)
            
            print(f"消息发送{'成功' if success else '失败'}: {message_id} ({channel.value})")
            
        except Exception as e:
            # 标记失败
            with self.lock:
                if message_id in self.delivery_records:
                    self.delivery_records[message_id].status = DeliveryStatus.FAILED
                    self.delivery_records[message_id].final_error = str(e)
                self.sending_queue.pop(message_id, None)
            
            self._update_stats_failure(channel, message.priority)
            print(f"消息发送异常: {message_id} - {str(e)}")
    
    def _update_stats_success(self, channel: NotificationChannel, priority: NotificationPriority):
        """更新成功统计"""
        self.stats["total_sent"] += 1
        self.stats["last_sent_time"] = datetime.now()
        
        # 按渠道统计
        channel_key = channel.value
        self.stats["by_channel"][channel_key] = self.stats["by_channel"].get(channel_key, 0) + 1
        
        # 按优先级统计
        priority_key = priority.value
        self.stats["by_priority"][priority_key] = self.stats["by_priority"].get(priority_key, 0) + 1
    
    def _update_stats_failure(self, channel: NotificationChannel, priority: NotificationPriority):
        """更新失败统计"""
        self.stats["total_failed"] += 1
        
        # 按渠道统计失败
        channel_key = f"{channel.value}_failed"
        self.stats["by_channel"][channel_key] = self.stats["by_channel"].get(channel_key, 0) + 1
    
    # 渠道处理器实现
    
    async def _handle_popup_notification(self, message: NotificationMessage) -> bool:
        """处理弹窗通知"""
        try:
            # 这里应该实现实际的弹窗逻辑
            # 在Web环境中可以使用浏览器的通知API
            # 在桌面环境中可以使用系统通知API
            
            print(f"弹窗通知: {message.title}")
            print(f"内容: {message.content}")
            
            # 模拟异步发送
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"弹窗通知失败: {str(e)}")
            return False
    
    async def _handle_desktop_notification(self, message: NotificationMessage) -> bool:
        """处理桌面通知"""
        try:
            # 使用plyer库实现桌面通知
            # 这里使用模拟实现
            print(f"桌面通知: {message.title}")
            print(f"内容: {message.content}")
            
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"桌面通知失败: {str(e)}")
            return False
    
    async def _handle_telegram_notification(self, message: NotificationMessage) -> bool:
        """处理Telegram通知"""
        try:
            config = self.channel_configs[NotificationChannel.TELEGRAM]
            bot_token = config.settings.get("bot_token")
            chat_id = config.settings.get("chat_id")
            
            if not bot_token or not chat_id:
                print("Telegram配置不完整")
                return False
            
            # 构建消息
            telegram_message = f"*{message.title}*\n\n{message.content}"
            
            # 发送到Telegram
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": telegram_message,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Telegram API错误: {response.status}")
                        return False
            
        except Exception as e:
            print(f"Telegram通知失败: {str(e)}")
            return False
    
    async def _handle_email_notification(self, message: NotificationMessage) -> bool:
        """处理邮件通知"""
        try:
            config = self.channel_configs[NotificationChannel.EMAIL]
            
            smtp_server = config.settings.get("smtp_server")
            smtp_port = config.settings.get("smtp_port", 587)
            username = config.settings.get("username")
            password = config.settings.get("password")
            recipient = config.settings.get("recipient")
            
            if not all([smtp_server, username, password, recipient]):
                print("邮件配置不完整")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = recipient
            msg['Subject'] = message.title
            
            msg.attach(MIMEText(message.content, 'plain'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"邮件通知失败: {str(e)}")
            return False
    
    async def _handle_webhook_notification(self, message: NotificationMessage) -> bool:
        """处理Webhook通知"""
        try:
            config = self.channel_configs[NotificationChannel.WEBHOOK]
            webhook_url = config.settings.get("webhook_url")
            
            if not webhook_url:
                print("Webhook URL未配置")
                return False
            
            # 构建payload
            payload = {
                "message_id": message.message_id,
                "title": message.title,
                "content": message.content,
                "priority": message.priority.value,
                "timestamp": message.timestamp.isoformat(),
                "channel": message.channel.value
            }
            
            # 添加触发事件信息
            if message.trigger_event:
                payload["trigger"] = {
                    "condition_id": message.trigger_event.condition_id,
                    "condition_name": message.trigger_event.condition_name,
                    "details": message.trigger_event.result.details
                }
            
            # 发送Webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
            
        except Exception as e:
            print(f"Webhook通知失败: {str(e)}")
            return False
    
    async def _handle_file_log_notification(self, message: NotificationMessage) -> bool:
        """处理文件日志通知"""
        try:
            # 记录到文件
            log_entry = {
                "timestamp": message.timestamp.isoformat(),
                "channel": message.channel.value,
                "priority": message.priority.value,
                "title": message.title,
                "content": message.content,
                "message_id": message.message_id
            }
            
            # 追加到日志文件
            log_file = Path("notifications.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            print(f"文件日志通知失败: {str(e)}")
            return False
    
    async def _handle_sms_notification(self, message: NotificationMessage) -> bool:
        """处理SMS通知"""
        try:
            # 这里需要集成SMS服务（如Twilio）
            # 暂时返回模拟成功
            print(f"SMS通知: {message.title}")
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"SMS通知失败: {str(e)}")
            return False
    
    async def _handle_slack_notification(self, message: NotificationMessage) -> bool:
        """处理Slack通知"""
        try:
            # 集成Slack Webhook
            config = self.channel_configs[NotificationChannel.SLACK]
            webhook_url = config.settings.get("webhook_url")
            
            if not webhook_url:
                print("Slack Webhook URL未配置")
                return False
            
            payload = {
                "text": f"*{message.title}*\n{message.content}",
                "username": "Trading Bot",
                "icon_emoji": ":bell:"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
            
        except Exception as e:
            print(f"Slack通知失败: {str(e)}")
            return False
    
    async def _handle_discord_notification(self, message: NotificationMessage) -> bool:
        """处理Discord通知"""
        try:
            # 集成Discord Webhook
            config = self.channel_configs[NotificationChannel.DISCORD]
            webhook_url = config.settings.get("webhook_url")
            
            if not webhook_url:
                print("Discord Webhook URL未配置")
                return False
            
            payload = {
                "content": f"🔔 **{message.title}**\n{message.content}",
                "username": "Trading Bot",
                "avatar_url": "https://example.com/bot-avatar.png"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
            
        except Exception as e:
            print(f"Discord通知失败: {str(e)}")
            return False


class NotificationTemplateEngine:
    """通知模板引擎"""
    
    def __init__(self):
        self.templates = {
            NotificationTemplate.PRICE_ALERT: self._render_price_alert,
            NotificationTemplate.VOLUME_SPIKE: self._render_volume_spike,
            NotificationTemplate.TECHNICAL_SIGNAL: self._render_technical_signal,
            NotificationTemplate.SYSTEM_ALERT: self._render_system_alert,
            NotificationTemplate.TRADING_SIGNAL: self._render_trading_signal,
            NotificationTemplate.ERROR_ALERT: self._render_error_alert,
            NotificationTemplate.CUSTOM: self._render_custom
        }
    
    def render(
        self,
        template: NotificationTemplate,
        trigger_event: TriggerEvent,
        channel: NotificationChannel
    ) -> tuple[str, str]:
        """渲染模板"""
        renderer = self.templates.get(template, self._render_custom)
        return renderer(trigger_event, channel)
    
    def _render_price_alert(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染价格预警模板"""
        if not trigger_event.result.value:
            return "价格预警", "价格条件已满足"
        
        alert_data = trigger_event.result.value
        title = f"💰 价格预警 - {alert_data.symbol}"
        
        if hasattr(alert_data, 'current_value'):
            content = f"""
币种: {alert_data.symbol}
当前价格: {alert_data.current_value:.4f}
触发值: {alert_data.threshold_value}
状态: {alert_data.details}
时间: {trigger_event.timestamp.strftime('%H:%M:%S')}
"""
        else:
            content = f"币种: {alert_data.symbol}\n详情: {alert_data.details}"
        
        return title, content.strip()
    
    def _render_volume_spike(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染成交量激增模板"""
        if not trigger_event.result.value:
            return "成交量激增", "成交量条件已满足"
        
        alert_data = trigger_event.result.value
        title = f"📈 成交量激增 - {alert_data.symbol}"
        
        content = f"""
币种: {alert_data.symbol}
成交量比率: {alert_data.current_value:.2f}x
阈值: {alert_data.threshold_value}
严重程度: {alert_data.severity.value}
详情: {alert_data.details}
"""
        
        return title, content.strip()
    
    def _render_technical_signal(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染技术指标信号模板"""
        if not trigger_event.result.value:
            return "技术信号", "技术指标条件已满足"
        
        alert_data = trigger_event.result.value
        title = f"📊 技术信号 - {alert_data.symbol}"
        
        content = f"""
币种: {alert_data.symbol}
信号类型: {alert_data.alert_type.value}
当前值: {alert_data.current_value}
阈值: {alert_data.threshold_value}
方向: {alert_data.direction.value}
详情: {alert_data.details}
"""
        
        return title, content.strip()
    
    def _render_system_alert(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染系统预警模板"""
        title = f"⚠️ 系统预警"
        content = f"""
条件名称: {trigger_event.condition_name}
触发时间: {trigger_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
详情: {trigger_event.result.details}
优先级: {trigger_event.priority}
"""
        
        return title, content.strip()
    
    def _render_trading_signal(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染交易信号模板"""
        if not trigger_event.result.value:
            return "交易信号", "交易条件已满足"
        
        alert_data = trigger_event.result.value
        title = f"🚀 交易信号 - {alert_data.symbol}"
        
        content = f"""
币种: {alert_data.symbol}
信号: {alert_data.details}
方向: {alert_data.direction.value}
强度: {alert_data.severity.value}
时间: {trigger_event.timestamp.strftime('%H:%M:%S')}
"""
        
        return title, content.strip()
    
    def _render_error_alert(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染错误预警模板"""
        title = f"❌ 错误预警"
        content = f"""
错误条件: {trigger_event.condition_name}
错误详情: {trigger_event.result.details}
发生时间: {trigger_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
优先级: {trigger_event.priority}
"""
        
        return title, content.strip()
    
    def _render_custom(self, trigger_event: TriggerEvent, channel: NotificationChannel) -> tuple[str, str]:
        """渲染自定义模板"""
        title = f"📢 条件触发 - {trigger_event.condition_name}"
        content = f"""
条件名称: {trigger_event.condition_name}
触发详情: {trigger_event.result.details}
触发时间: {trigger_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
优先级: {trigger_event.priority}
"""
        
        return title, content.strip()


# 全局通知管理器实例
_global_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器实例"""
    global _global_notification_manager
    if _global_notification_manager is None:
        _global_notification_manager = NotificationManager()
    return _global_notification_manager


def init_notification_manager(config: Optional[Dict[str, Any]] = None) -> NotificationManager:
    """初始化全局通知管理器"""
    global _global_notification_manager
    _global_notification_manager = NotificationManager(config)
    return _global_notification_manager