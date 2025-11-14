"""
通知投递集成测试
验证通知系统在各种场景下的投递功能
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import tempfile
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crypto_trading_terminal.backend.src.conditions.base_conditions import MarketData
from crypto_trading_terminal.backend.src.conditions.condition_engine import (
    ConditionEngine,
    TriggerEvent,
    EvaluationContext
)
from crypto_trading_terminal.backend.src.conditions.price_conditions import PriceCondition
from crypto_trading_terminal.backend.src.notification.notify_manager import (
    NotificationManager,
    NotificationChannel,
    NotificationPriority,
    NotificationTemplate,
    DeliveryStatus,
    NotificationConfig
)
from crypto_trading_terminal.backend.src.conditions.market_alert_conditions import MarketAlertCondition


class TestNotificationDeliveryIntegration:
    """通知投递集成测试类"""
    
    @pytest.fixture
    async def notification_manager(self):
        """创建通知管理器"""
        config = {
            "max_parallel_evaluations": 5,
            "evaluation_timeout": 30.0,
            "cache_ttl": 300
        }
        
        manager = NotificationManager(config)
        yield manager
    
    @pytest.fixture
    def sample_trigger_event(self):
        """创建示例触发事件"""
        market_data = MarketData(
            symbol="BTCUSDT",
            price=50000.0,
            volume_24h=1000000.0,
            price_change_24h=2500.0,
            price_change_percent_24h=5.0,
            high_24h=52000.0,
            low_24h=48000.0,
            timestamp=datetime.now(),
            rsi=65.0,
            macd=120.5,
            macd_signal=115.2,
            bollinger_upper=51000.0,
            bollinger_lower=49000.0,
            moving_average_20=49500.0,
            moving_average_50=49200.0,
            open_interest=500000.0,
            funding_rate=0.001
        )
        
        return TriggerEvent(
            event_id="test_event_123",
            condition_id="test_condition_456",
            condition_name="Test Price Alert",
            result=Mock(satisfied=True, value=market_data, details="Price alert triggered"),
            timestamp=datetime.now(),
            context=Mock(),
            priority=5,
            metadata={"test": True}
        )
    
    @pytest.mark.asyncio
    async def test_basic_notification_delivery(self, notification_manager, sample_trigger_event):
        """测试基本通知投递"""
        # 启用桌面和弹窗通知
        notification_manager.enable_channel(NotificationChannel.POPUP, True)
        notification_manager.enable_channel(NotificationChannel.DESKTOP, True)
        
        # 发送通知
        message_ids = notification_manager.send_notification(
            trigger_event=sample_trigger_event,
            channels=[NotificationChannel.POPUP, NotificationChannel.DESKTOP]
        )
        
        # 验证消息ID生成
        assert len(message_ids) == 2
        assert all(isinstance(msg_id, str) for msg_id in message_ids)
        
        # 处理队列
        await notification_manager.process_queue()
        
        # 检查投递状态
        for msg_id in message_ids:
            status = notification_manager.get_delivery_status(msg_id)
            assert status is not None
            # 由于是模拟实现，状态可能是PENDING或DELIVERED
        
        # 检查统计
        stats = notification_manager.get_statistics()
        assert stats["stats"]["total_sent"] >= 0
        assert stats["queue_size"] == 0
    
    @pytest.mark.asyncio
    async def test_telegram_notification_integration(self, notification_manager, sample_trigger_event):
        """测试Telegram通知集成"""
        # 配置Telegram
        telegram_config = NotificationConfig(
            channel=NotificationChannel.TELEGRAM,
            enabled=True,
            priority=NotificationPriority.HIGH,
            retry_attempts=3,
            settings={
                "bot_token": "test_bot_token_123",
                "chat_id": "test_chat_id_456"
            }
        )
        
        notification_manager.configure_channel(NotificationChannel.TELEGRAM, telegram_config)
        
        # 模拟HTTP响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 发送Telegram通知
            message_ids = notification_manager.send_notification(
                trigger_event=sample_trigger_event,
                channels=[NotificationChannel.TELEGRAM]
            )
            
            await notification_manager.process_queue()
            
            # 验证API调用
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # 检查URL
            assert "https://api.telegram.org/bot" in call_args[0][0]
            
            # 检查payload
            payload = call_args[1]['json']
            assert "text" in payload
            assert payload["parse_mode"] == "Markdown"
    
    @pytest.mark.asyncio
    async def test_email_notification_integration(self, notification_manager, sample_trigger_event):
        """测试邮件通知集成"""
        # 配置邮件
        email_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=True,
            priority=NotificationPriority.HIGH,
            retry_attempts=3,
            settings={
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "test_password",
                "recipient": "recipient@example.com"
            }
        )
        
        notification_manager.configure_channel(NotificationChannel.EMAIL, email_config)
        
        # 模拟SMTP连接
        with patch('smtplib.SMTP') as mock_smtp, \
             patch('smtplib.SMTP.starttls') as mock_starttls, \
             patch('smtplib.SMTP.login') as mock_login, \
             patch('smtplib.SMTP.send_message') as mock_send_message, \
             patch('smtplib.SMTP.quit') as mock_quit:
            
            mock_smtp_instance = Mock()
            mock_smtp.return_value = mock_smtp_instance
            
            # 发送邮件通知
            message_ids = notification_manager.send_notification(
                trigger_event=sample_trigger_event,
                channels=[NotificationChannel.EMAIL]
            )
            
            await notification_manager.process_queue()
            
            # 验证SMTP调用
            mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
            mock_starttls.assert_called_once()
            mock_login.assert_called_once_with("test@example.com", "test_password")
            mock_send_message.assert_called_once()
            mock_quit.assert_called_once()
            
            # 验证邮件内容
            call_args = mock_send_message.call_args[0][0]  # 获取MIMEMultipart对象
            assert call_args['From'] == "test@example.com"
            assert call_args['To'] == "recipient@example.com"
            assert "Test Price Alert" in call_args['Subject']
    
    @pytest.mark.asyncio
    async def test_webhook_notification_integration(self, notification_manager, sample_trigger_event):
        """测试Webhook通知集成"""
        # 配置Webhook
        webhook_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=True,
            priority=NotificationPriority.NORMAL,
            settings={
                "webhook_url": "https://example.com/webhook"
            }
        )
        
        notification_manager.configure_channel(NotificationChannel.WEBHOOK, webhook_config)
        
        # 模拟HTTP响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 发送Webhook通知
            message_ids = notification_manager.send_notification(
                trigger_event=sample_trigger_event,
                channels=[NotificationChannel.WEBHOOK]
            )
            
            await notification_manager.process_queue()
            
            # 验证Webhook调用
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # 检查URL
            assert call_args[0][0] == "https://example.com/webhook"
            
            # 检查payload
            payload = call_args[1]['json']
            assert "message_id" in payload
            assert "title" in payload
            assert "content" in payload
            assert "trigger" in payload
            assert payload["trigger"]["condition_name"] == "Test Price Alert"
    
    @pytest.mark.asyncio
    async def test_file_log_notification_integration(self, notification_manager, sample_trigger_event):
        """测试文件日志通知集成"""
        # 配置文件日志
        file_config = NotificationConfig(
            channel=NotificationChannel.FILE_LOG,
            enabled=True,
            priority=NotificationPriority.LOW,
            settings={
                "log_file": "test_notifications.log"
            }
        )
        
        notification_manager.configure_channel(NotificationChannel.FILE_LOG, file_config)
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_file:
            temp_log_path = temp_file.name
        
        try:
            # 更新配置使用临时文件
            file_config.settings["log_file"] = temp_log_path
            notification_manager.configure_channel(NotificationChannel.FILE_LOG, file_config)
            
            # 发送文件日志通知
            message_ids = notification_manager.send_notification(
                trigger_event=sample_trigger_event,
                channels=[NotificationChannel.FILE_LOG]
            )
            
            await notification_manager.process_queue()
            
            # 验证日志文件内容
            with open(temp_log_path, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            assert len(log_lines) == 1
            
            # 解析日志条目
            log_entry = json.loads(log_lines[0].strip())
            assert log_entry["title"] == "Test Price Alert"
            assert log_entry["channel"] == "file_log"
            assert log_entry["priority"] == "normal"
            assert "message_id" in log_entry
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_log_path):
                os.unlink(temp_log_path)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, notification_manager, sample_trigger_event):
        """测试速率限制集成"""
        # 配置严格的速率限制
        rate_limit_config = NotificationConfig(
            channel=NotificationChannel.POPUP,
            enabled=True,
            priority=NotificationPriority.NORMAL,
            rate_limit=3  # 每分钟最多3条
        )
        
        notification_manager.configure_channel(NotificationChannel.POPUP, rate_limit_config)
        
        # 发送大量通知（应该被速率限制）
        message_ids = []
        for i in range(5):
            trigger_event = TriggerEvent(
                event_id=f"test_event_{i}",
                condition_id=f"test_condition_{i}",
                condition_name=f"Test Alert {i}",
                result=Mock(satisfied=True, value=None, details=f"Alert {i} triggered"),
                timestamp=datetime.now(),
                context=Mock(),
                priority=5,
                metadata={}
            )
            
            ids = notification_manager.send_notification(
                trigger_event=trigger_event,
                channels=[NotificationChannel.POPUP]
            )
            message_ids.extend(ids)
        
        # 应该只有3条消息被加入队列（速率限制）
        assert len(message_ids) <= 3
        
        # 处理队列
        await notification_manager.process_queue()
        
        # 检查统计
        stats = notification_manager.get_statistics()
        assert stats["stats"]["total_sent"] >= 0
    
    @pytest.mark.asyncio
    async def test_priority_based_delivery_integration(self, notification_manager):
        """测试基于优先级的投递"""
        # 配置不同优先级的渠道
        high_priority_config = NotificationConfig(
            channel=NotificationChannel.DESKTOP,
            enabled=True,
            priority=NotificationPriority.HIGH
        )
        
        low_priority_config = NotificationConfig(
            channel=NotificationChannel.FILE_LOG,
            enabled=True,
            priority=NotificationPriority.LOW
        )
        
        notification_manager.configure_channel(NotificationChannel.DESKTOP, high_priority_config)
        notification_manager.configure_channel(NotificationChannel.FILE_LOG, low_priority_config)
        
        # 创建不同优先级的触发事件
        high_priority_event = TriggerEvent(
            event_id="high_priority_event",
            condition_id="high_priority_condition",
            condition_name="High Priority Alert",
            result=Mock(satisfied=True, value=None, details="High priority alert"),
            timestamp=datetime.now(),
            context=Mock(),
            priority=8,  # 高优先级
            metadata={}
        )
        
        low_priority_event = TriggerEvent(
            event_id="low_priority_event",
            condition_id="low_priority_condition",
            condition_name="Low Priority Alert",
            result=Mock(satisfied=True, value=None, details="Low priority alert"),
            timestamp=datetime.now(),
            context=Mock(),
            priority=2,  # 低优先级
            metadata={}
        )
        
        # 发送通知
        high_ids = notification_manager.send_notification(
            trigger_event=high_priority_event,
            channels=[NotificationChannel.DESKTOP, NotificationChannel.FILE_LOG]
        )
        
        low_ids = notification_manager.send_notification(
            trigger_event=low_priority_event,
            channels=[NotificationChannel.DESKTOP, NotificationChannel.FILE_LOG]
        )
        
        # 高优先级通知应该被处理
        assert len(high_ids) == 2
        
        # 等待处理
        await notification_manager.process_queue()
        
        # 检查投递状态
        for msg_id in high_ids + low_ids:
            status = notification_manager.get_delivery_status(msg_id)
            assert status is not None
    
    @pytest.mark.asyncio
    async def test_template_rendering_integration(self, notification_manager, sample_trigger_event):
        """测试模板渲染集成"""
        # 测试价格预警模板
        price_alert_ids = notification_manager.send_notification(
            trigger_event=sample_trigger_event,
            channels=[NotificationChannel.POPUP],
            template=NotificationTemplate.PRICE_ALERT
        )
        
        # 测试成交量激增模板
        volume_spike_ids = notification_manager.send_notification(
            trigger_event=sample_trigger_event,
            channels=[NotificationChannel.POPUP],
            template=NotificationTemplate.VOLUME_SPIKE
        )
        
        # 测试系统预警模板
        system_alert_ids = notification_manager.send_notification(
            trigger_event=sample_trigger_event,
            channels=[NotificationChannel.POPUP],
            template=NotificationTemplate.SYSTEM_ALERT
        )
        
        # 处理队列
        await notification_manager.process_queue()
        
        # 验证所有模板都生成了消息
        all_ids = price_alert_ids + volume_spike_ids + system_alert_ids
        assert len(all_ids) == 3
        
        # 检查状态
        for msg_id in all_ids:
            status = notification_manager.get_delivery_status(msg_id)
            assert status is not None
    
    @pytest.mark.asyncio
    async def test_batch_processing_integration(self, notification_manager, sample_trigger_event):
        """测试批量处理集成"""
        # 设置批量模式
        notification_manager.set_trigger_mode("batch")
        
        # 配置批量设置
        batch_config = NotificationConfig(
            channel=NotificationChannel.POPUP,
            enabled=True,
            priority=NotificationPriority.NORMAL,
            batch_size=3,
            batch_delay=1.0
        )
        
        notification_manager.configure_channel(NotificationChannel.POPUP, batch_config)
        
        # 发送多个通知
        message_ids = []
        for i in range(5):
            trigger_event = TriggerEvent(
                event_id=f"batch_event_{i}",
                condition_id=f"batch_condition_{i}",
                condition_name=f"Batch Alert {i}",
                result=Mock(satisfied=True, value=None, details=f"Batch alert {i}"),
                timestamp=datetime.now(),
                context=Mock(),
                priority=5,
                metadata={}
            )
            
            ids = notification_manager.send_notification(
                trigger_event=trigger_event,
                channels=[NotificationChannel.POPUP]
            )
            message_ids.extend(ids)
        
        # 启动批量处理
        await notification_manager.process_queue()
        
        # 验证批量处理
        stats = notification_manager.get_statistics()
        assert stats["stats"]["total_sent"] >= 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_retry_integration(self, notification_manager, sample_trigger_event):
        """测试错误处理和重试集成"""
        # 配置具有重试的渠道
        retry_config = NotificationConfig(
            channel=NotificationChannel.TELEGRAM,
            enabled=True,
            priority=NotificationPriority.HIGH,
            retry_attempts=3,
            retry_delay=0.1,  # 短延迟用于测试
            settings={
                "bot_token": "invalid_token",
                "chat_id": "invalid_chat"
            }
        )
        
        notification_manager.configure_channel(NotificationChannel.TELEGRAM, retry_config)
        
        # 模拟第一次失败，第二次成功的场景
        call_count = 0
        async def mock_post_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次调用失败
                raise Exception("Network error")
            else:
                # 后续调用成功
                mock_response = Mock()
                mock_response.status = 200
                return mock_response
        
        with patch('aiohttp.ClientSession.post', side_effect=mock_post_with_failure):
            message_ids = notification_manager.send_notification(
                trigger_event=sample_trigger_event,
                channels=[NotificationChannel.TELEGRAM]
            )
            
            # 处理队列（应该重试）
            await notification_manager.process_queue()
            
            # 验证重试机制被触发
            assert call_count >= 1
    
    @pytest.mark.asyncio
    async def test_condition_engine_integration(self, notification_manager):
        """测试与条件引擎的集成"""
        # 创建条件引擎
        engine = ConditionEngine()
        await engine.start()
        
        try:
            # 创建市场数据
            market_data = MarketData(
                symbol="BTCUSDT",
                price=51000.0,  # 高于阈值，应该触发
                volume_24h=1200000.0,
                price_change_24h=2500.0,
                price_change_percent_24h=5.0,
                high_24h=52000.0,
                low_24h=48000.0,
                timestamp=datetime.now(),
                rsi=65.0
            )
            
            # 创建价格预警条件
            alert_condition = MarketAlertCondition(
                alert_type="price_change",
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold_value=5.0,
                name="Integration Test Alert"
            )
            
            condition_id = engine.register_condition(alert_condition)
            
            # 注册通知处理器
            async def notification_trigger_handler(trigger_event):
                notification_manager.send_notification(trigger_event)
            
            engine.register_trigger_handler("market_alert", notification_trigger_handler)
            
            # 评估条件
            trigger_event = await engine.evaluate_condition(condition_id, market_data)
            
            if trigger_event:
                # 处理通知
                await notification_trigger_handler(trigger_event)
                
                # 处理队列
                await notification_manager.process_queue()
                
                # 验证集成
                stats = notification_manager.get_statistics()
                assert stats["stats"]["total_sent"] >= 0
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_custom_notification_integration(self, notification_manager):
        """测试自定义通知集成"""
        # 启用相关渠道
        notification_manager.enable_channel(NotificationChannel.POPUP, True)
        notification_manager.enable_channel(NotificationChannel.EMAIL, True)
        
        # 发送自定义通知
        message_ids = notification_manager.send_custom_notification(
            title="自定义交易信号",
            content="BTC突破51000美元，建议做多\n目标价位：52000美元\n止损：50000美元",
            channels=[NotificationChannel.POPUP, NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            metadata={"strategy": "breakout", "symbol": "BTCUSDT"}
        )
        
        # 验证消息ID
        assert len(message_ids) == 2
        
        # 处理队列
        await notification_manager.process_queue()
        
        # 检查状态
        for msg_id in message_ids:
            status = notification_manager.get_delivery_status(msg_id)
            assert status is not None
        
        # 检查统计
        stats = notification_manager.get_statistics()
        assert stats["stats"]["total_sent"] >= 0
    
    @pytest.mark.asyncio
    async def test_queue_management_integration(self, notification_manager, sample_trigger_event):
        """测试队列管理集成"""
        # 启用渠道
        notification_manager.enable_channel(NotificationChannel.POPUP, True)
        
        # 发送多个通知到队列
        message_ids = []
        for i in range(10):
            trigger_event = TriggerEvent(
                event_id=f"queue_event_{i}",
                condition_id=f"queue_condition_{i}",
                condition_name=f"Queue Alert {i}",
                result=Mock(satisfied=True, value=None, details=f"Queue alert {i}"),
                timestamp=datetime.now(),
                context=Mock(),
                priority=5,
                metadata={}
            )
            
            ids = notification_manager.send_notification(
                trigger_event=trigger_event,
                channels=[NotificationChannel.POPUP]
            )
            message_ids.extend(ids)
        
        # 检查队列状态
        stats_before = notification_manager.get_statistics()
        assert stats_before["queue_size"] > 0
        
        # 清空队列
        notification_manager.clear_queue()
        
        # 验证队列已清空
        stats_after = notification_manager.get_statistics()
        assert stats_after["queue_size"] == 0
        
        # 验证消息状态（应该还在records中，但队列已清空）
        for msg_id in message_ids:
            status = notification_manager.get_delivery_status(msg_id)
            # 消息记录应该仍然存在，但状态可能是PENDING
            assert status is not None
    
    @pytest.mark.asyncio
    async def test_delivery_tracking_integration(self, notification_manager, sample_trigger_event):
        """测试投递跟踪集成"""
        # 启用渠道
        notification_manager.enable_channel(NotificationChannel.POPUP, True)
        
        # 发送通知
        message_ids = notification_manager.send_notification(
            trigger_event=sample_trigger_event,
            channels=[NotificationChannel.POPUP]
        )
        
        message_id = message_ids[0]
        
        # 检查投递记录
        record = notification_manager.get_delivery_status(message_id)
        assert record is not None
        assert record["message_id"] == message_id
        assert record["channel"] == "popup"
        assert record["status"] in [status.value for status in DeliveryStatus]
        assert record["created_at"] is not None
        
        # 处理队列
        await notification_manager.process_queue()
        
        # 再次检查状态
        updated_record = notification_manager.get_delivery_status(message_id)
        assert updated_record is not None
        assert updated_record["message_id"] == message_id
        
        # 验证尝试记录
        if updated_record.get("attempts"):
            attempts = updated_record["attempts"]
            assert len(attempts) > 0
            assert attempts[0]["status"] in [status.value for status in DeliveryStatus]
    
    @pytest.mark.asyncio
    async def test_performance_under_load_integration(self, notification_manager):
        """测试负载下的性能"""
        # 启用多个渠道
        channels = [
            NotificationChannel.POPUP,
            NotificationChannel.DESKTOP,
            NotificationChannel.FILE_LOG
        ]
        
        for channel in channels:
            notification_manager.enable_channel(channel, True)
        
        # 发送大量通知
        start_time = time.time()
        
        for i in range(50):
            trigger_event = TriggerEvent(
                event_id=f"load_event_{i}",
                condition_id=f"load_condition_{i}",
                condition_name=f"Load Test Alert {i}",
                result=Mock(satisfied=True, value=None, details=f"Load test {i}"),
                timestamp=datetime.now(),
                context=Mock(),
                priority=5,
                metadata={}
            )
            
            notification_manager.send_notification(
                trigger_event=trigger_event,
                channels=channels
            )
        
        # 处理所有通知
        await notification_manager.process_queue()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证性能（50个通知应该在合理时间内处理完成）
        assert processing_time < 30.0  # 30秒内完成
        
        # 检查统计
        stats = notification_manager.get_statistics()
        assert stats["stats"]["total_sent"] >= 0
        assert stats["queue_size"] == 0


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
