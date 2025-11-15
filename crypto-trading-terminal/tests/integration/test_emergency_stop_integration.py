"""
紧急停止功能集成测试
验证紧急停止系统的完整功能和安全性
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from backend.src.auto_trading.emergency_stop import (
    EmergencyStopService,
    EmergencyStopConfig,
    StopLevel,
    StopReason,
    StopStatus,
    StopRecord
)
from backend.src.storage.models import User, Account, AutoOrder, Order, RiskAlert
from backend.src.notification.risk_alert_integration import RiskAlertNotificationManager


class TestEmergencyStopService:
    """紧急停止服务测试类"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = Mock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        return session
    
    @pytest.fixture
    def emergency_service(self, mock_db_session):
        """创建紧急停止服务实例"""
        return EmergencyStopService(mock_db_session)
    
    @pytest.fixture
    def sample_user(self):
        """创建示例用户"""
        user = Mock(spec=User)
        user.id = 1001
        user.username = "test_user"
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
        account.is_active = True
        return account
    
    @pytest.fixture
    def sample_auto_orders(self):
        """创建示例自动订单"""
        orders = []
        for i in range(5):
            order = Mock(spec=AutoOrder)
            order.id = i + 1
            order.user_id = 1001
            order.account_id = 2001
            order.symbol = "BTCUSDT"
            order.status = "new"
            order.is_paused = False
            order.strategy_name = "test_strategy"
            orders.append(order)
        return orders
    
    def test_emergency_stop_service_initialization(self, emergency_service):
        """测试紧急停止服务初始化"""
        assert emergency_service is not None
        assert len(emergency_service.active_stops) == 0
        assert emergency_service.is_monitoring is False
        assert "total_stops" in emergency_service.stats
        assert "orders_cancelled" in emergency_service.stats
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, emergency_service):
        """测试启动和停止监控"""
        # 启动监控
        await emergency_service.start_monitoring()
        assert emergency_service.is_monitoring is True
        assert emergency_service.monitoring_task is not None
        
        # 停止监控
        await emergency_service.stop_monitoring()
        assert emergency_service.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_execute_global_emergency_stop(self, emergency_service):
        """测试执行全局紧急停止"""
        # 创建配置
        config = EmergencyStopConfig(
            stop_level=StopLevel.GLOBAL,
            target_id="global",
            reason=StopReason.MANUAL,
            max_stop_duration=300
        )
        
        # 执行紧急停止
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        # 验证结果
        assert stop_id is not None
        assert stop_id in emergency_service.active_stops
        
        stop_record = emergency_service.active_stops[stop_id]
        assert stop_record.stop_level == StopLevel.GLOBAL
        assert stop_record.status == StopStatus.ACTIVE
        assert stop_record.triggered_by == "test_user"
        assert stop_record.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_execute_user_emergency_stop(self, emergency_service):
        """测试执行用户紧急停止"""
        config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.RISK_THRESHOLD,
            max_stop_duration=600
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="admin_user"
        )
        
        assert stop_id in emergency_service.active_stops
        stop_record = emergency_service.active_stops[stop_id]
        assert stop_record.stop_level == StopLevel.USER
        assert stop_record.target_id == 1001
        assert stop_record.reason == StopReason.RISK_THRESHOLD
    
    def test_is_trading_stopped_global(self, emergency_service):
        """测试全局停止状态检查"""
        # 默认应该没有停止
        assert not emergency_service.is_trading_stopped()
        
        # 模拟全局停止记录
        stop_record = StopRecord(
            stop_id="test_global",
            stop_level=StopLevel.GLOBAL,
            target_id="global",
            reason=StopReason.MANUAL,
            status=StopStatus.ACTIVE,
            triggered_at=datetime.now(),
            triggered_by="test",
            expires_at=None,
            cancelled_at=None,
            cancelled_by=None,
            orders_affected=0,
            total_amount=0.0,
            metadata={}
        )
        
        emergency_service.active_stops["test_global"] = stop_record
        
        # 现在应该检测到停止
        assert emergency_service.is_trading_stopped()
        assert emergency_service.is_trading_stopped(user_id=1001)
        assert emergency_service.is_trading_stopped(account_id=2001)
        assert emergency_service.is_trading_stopped(symbol="BTCUSDT")
    
    def test_is_trading_stopped_user_level(self, emergency_service):
        """测试用户级别停止状态检查"""
        # 创建用户级别停止记录
        stop_record = StopRecord(
            stop_id="test_user",
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.MANUAL,
            status=StopStatus.ACTIVE,
            triggered_at=datetime.now(),
            triggered_by="test",
            expires_at=None,
            cancelled_at=None,
            cancelled_by=None,
            orders_affected=0,
            total_amount=0.0,
            metadata={}
        )
        
        emergency_service.active_stops["test_user"] = stop_record
        
        # 测试停止状态
        assert emergency_service.is_trading_stopped(user_id=1001)
        assert not emergency_service.is_trading_stopped(user_id=1002)
        
        # 其他级别的检查应该返回False
        assert not emergency_service.is_trading_stopped(account_id=2001)
        assert not emergency_service.is_trading_stopped(symbol="BTCUSDT")
    
    @pytest.mark.asyncio
    async def test_cancel_emergency_stop(self, emergency_service):
        """测试取消紧急停止"""
        # 先创建一个停止记录
        config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.MANUAL
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        assert stop_id in emergency_service.active_stops
        
        # 取消停止
        success = await emergency_service.cancel_emergency_stop(
            stop_id=stop_id,
            cancelled_by="admin_user",
            reason="测试取消"
        )
        
        assert success is True
        assert stop_id not in emergency_service.active_stops
    
    @pytest.mark.asyncio
    async def test_resume_trading(self, emergency_service):
        """测试恢复交易"""
        # 先创建一个停止记录
        config = EmergencyStopConfig(
            stop_level=StopLevel.ACCOUNT,
            target_id=2001,
            reason=StopReason.SYSTEM_ERROR
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        assert stop_id in emergency_service.active_stops
        
        # 恢复交易
        success = await emergency_service.resume_trading(
            stop_id=stop_id,
            resumed_by="admin_user"
        )
        
        assert success is True
        assert stop_id not in emergency_service.active_stops
    
    @pytest.mark.asyncio
    async def test_get_active_stops(self, emergency_service):
        """测试获取活跃停止记录"""
        # 创建几个停止记录
        configs = [
            EmergencyStopConfig(StopLevel.GLOBAL, "global", StopReason.MANUAL),
            EmergencyStopConfig(StopLevel.USER, 1001, StopReason.RISK_THRESHOLD),
            EmergencyStopConfig(StopLevel.SYMBOL, "BTCUSDT", StopReason.EXCHANGE_ISSUE)
        ]
        
        stop_ids = []
        for config in configs:
            stop_id = await emergency_service.execute_emergency_stop(
                config=config,
                triggered_by="test_user"
            )
            stop_ids.append(stop_id)
        
        # 获取活跃停止
        active_stops = await emergency_service.get_active_stops()
        
        assert len(active_stops) == 3
        stop_ids_in_result = [stop.stop_id for stop in active_stops]
        
        for stop_id in stop_ids:
            assert stop_id in stop_ids_in_result
    
    def test_stop_statistics(self, emergency_service):
        """测试停止统计信息"""
        # 初始化统计信息
        emergency_service._update_stats("stop", StopLevel.USER, StopReason.MANUAL, 5, 1000.0)
        
        stats = asyncio.run(emergency_service.get_statistics())
        
        assert "stats" in stats
        assert "active_stops_count" in stats
        assert "active_stops" in stats
        
        assert stats["stats"]["total_stops"] == 1
        assert stats["stats"]["orders_cancelled"] == 5
        assert stats["stats"]["amount_preserved"] == 1000.0
        assert stats["active_stops_count"] == 0  # 没有活跃停止
    
    @pytest.mark.asyncio
    async def test_duplicate_stop_prevention(self, emergency_service):
        """测试重复停止预防"""
        config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.MANUAL
        )
        
        # 第一次停止
        stop_id1 = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        # 第二次相同目标的停止应该返回已存在的停止ID
        stop_id2 = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        assert stop_id1 == stop_id2
        assert len(emergency_service.active_stops) == 1
    
    @pytest.mark.asyncio
    async def test_expiry_mechanism(self, emergency_service):
        """测试过期机制"""
        # 创建短期停止
        config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.MANUAL,
            max_stop_duration=1  # 1秒
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        assert stop_id in emergency_service.active_stops
        
        # 等待过期
        await asyncio.sleep(1.5)
        
        # 手动触发过期检查
        await emergency_service._monitoring_loop()
        
        # 检查是否已过期
        assert stop_id not in emergency_service.active_stops
    
    @pytest.mark.asyncio
    async def test_stop_level_hierarchy(self, emergency_service):
        """测试停止级别优先级"""
        # 创建全局停止
        global_config = EmergencyStopConfig(
            stop_level=StopLevel.GLOBAL,
            target_id="global",
            reason=StopReason.MANUAL
        )
        
        global_stop_id = await emergency_service.execute_emergency_stop(
            config=global_config,
            triggered_by="test_user"
        )
        
        # 创建用户停止
        user_config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.RISK_THRESHOLD
        )
        
        user_stop_id = await emergency_service.execute_emergency_stop(
            config=user_config,
            triggered_by="test_user"
        )
        
        # 检查优先级：全局停止应该生效
        assert emergency_service.is_trading_stopped(user_id=1001)
        assert emergency_service.is_trading_stopped(account_id=2001)
        assert emergency_service.is_trading_stopped(symbol="BTCUSDT")
        
        # 取消全局停止
        await emergency_service.cancel_emergency_stop(
            stop_id=global_stop_id,
            cancelled_by="test_user"
        )
        
        # 现在用户停止应该生效
        assert emergency_service.is_trading_stopped(user_id=1001)
        assert not emergency_service.is_trading_stopped(account_id=2002)  # 另一个用户
        assert not emergency_service.is_trading_stopped(symbol="ETHUSDT")  # 另一个交易对
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, emergency_service):
        """测试监控循环"""
        # 启动监控
        await emergency_service.start_monitoring()
        
        # 创建一个会过期的停止
        config = EmergencyStopConfig(
            stop_level=StopLevel.SYMBOL,
            target_id="BTCUSDT",
            reason=StopReason.MANUAL,
            max_stop_duration=2
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=config,
            triggered_by="test_user"
        )
        
        # 等待监控循环处理过期
        await asyncio.sleep(3)
        
        # 检查是否已自动过期
        assert stop_id not in emergency_service.active_stops
        
        # 停止监控
        await emergency_service.stop_monitoring()
    
    def test_stop_record_serialization(self, emergency_service):
        """测试停止记录序列化"""
        stop_record = StopRecord(
            stop_id="test_123",
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.RISK_THRESHOLD,
            status=StopStatus.ACTIVE,
            triggered_at=datetime.now(),
            triggered_by="test_user",
            expires_at=None,
            cancelled_at=None,
            cancelled_by=None,
            orders_affected=5,
            total_amount=1000.0,
            metadata={"test": True}
        )
        
        # 转换为字典
        stop_dict = {
            "stop_id": stop_record.stop_id,
            "stop_level": stop_record.stop_level.value,
            "target_id": stop_record.target_id,
            "reason": stop_record.reason.value,
            "status": stop_record.status.value,
            "triggered_at": stop_record.triggered_at.isoformat(),
            "orders_affected": stop_record.orders_affected,
            "total_amount": stop_record.total_amount
        }
        
        # 验证序列化结果
        assert stop_dict["stop_id"] == "test_123"
        assert stop_dict["stop_level"] == "user"
        assert stop_dict["target_id"] == 1001
        assert stop_dict["reason"] == "risk_threshold"
        assert stop_dict["status"] == "active"
        assert stop_dict["orders_affected"] == 5
        assert stop_dict["total_amount"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_emergency_stop_configuration_validation(self, emergency_service):
        """测试紧急停止配置验证"""
        # 测试有效配置
        valid_config = EmergencyStopConfig(
            stop_level=StopLevel.GLOBAL,
            target_id="global",
            reason=StopReason.MANUAL,
            max_stop_duration=3600,
            require_confirmation=True
        )
        
        stop_id = await emergency_service.execute_emergency_stop(
            config=valid_config,
            triggered_by="test_user",
            confirmation_token="valid_token"
        )
        
        assert stop_id is not None
        
        # 测试需要确认的配置（无确认令牌）
        strict_config = EmergencyStopConfig(
            stop_level=StopLevel.USER,
            target_id=1001,
            reason=StopReason.MANUAL,
            require_confirmation=True
        )
        
        with pytest.raises(ValueError, match="紧急停止需要确认令牌"):
            await emergency_service.execute_emergency_stop(
                config=strict_config,
                triggered_by="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_order_cancellation_integration(self, emergency_service):
        """测试订单取消集成"""
        # 模拟数据库查询返回的订单
        mock_orders = []
        for i in range(3):
            order = Mock(spec=Order)
            order.id = i + 1
            order.status = "new"
            order.price = 50000.0
            order.quantity = 0.1
            mock_orders.append(order)
        
        emergency_service.db_session.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=mock_orders)))
        
        # 执行全局停止
        config = EmergencyStopConfig(
            stop_level=StopLevel.GLOBAL,
            target_id="global",
            reason=StopReason.MANUAL,
            cancel_pending_orders=True
        )
        
        orders_affected, total_amount = await emergency_service._stop_all_trading(config, "test_user")
        
        # 验证结果
        assert orders_affected == 3  # 3个订单被取消
        assert total_amount == 15000.0  # 3 * 0.1 * 50000 = 15000
        
        # 验证所有订单状态被更新
        for order in mock_orders:
            assert order.status == "cancelled"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])