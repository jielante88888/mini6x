"""
紧急停止服务
提供全局和粒度控制的安全停止机制，用于紧急情况下的风险控制
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..storage.models import (
    User, Account, AutoOrder, Order, OrderExecution, RiskAlert,
    OrderStatus, ExecutionResultStatus, MarketType
)
from ..storage.database import get_db_session
from ..notification.risk_alert_integration import (
    RiskAlertNotificationManager,
    get_risk_alert_notification_manager,
    RiskAlertType,
    RiskAlertSeverity,
    RiskAlertEvent
)
from ..notification.notify_manager import (
    NotificationManager,
    NotificationChannel,
    NotificationPriority,
    get_notification_manager
)


logger = logging.getLogger(__name__)


class StopLevel(Enum):
    """紧急停止级别"""
    GLOBAL = "global"        # 全局停止
    USER = "user"           # 用户级别停止
    ACCOUNT = "account"     # 账户级别停止
    SYMBOL = "symbol"       # 交易对级别停止
    STRATEGY = "strategy"   # 策略级别停止


class StopReason(Enum):
    """紧急停止原因"""
    MANUAL = "manual"                    # 手动触发
    RISK_THRESHOLD = "risk_threshold"    # 风险阈值触发
    EXCHANGE_ISSUE = "exchange_issue"    # 交易所问题
    SYSTEM_ERROR = "system_error"        # 系统错误
    LIQUIDATION_RISK = "liquidation_risk"  # 清算风险
    CONNECTION_LOSS = "connection_loss"  # 连接丢失
    SUSPICIOUS_ACTIVITY = "suspicious_activity"  # 可疑活动
    COMPLIANCE_ISSUE = "compliance_issue"  # 合规问题


class StopStatus(Enum):
    """停止状态"""
    ACTIVE = "active"           # 停止生效中
    CANCELLED = "cancelled"     # 已取消
    EXPIRED = "expired"         # 已过期
    MANUAL_RESUME = "manual_resume"  # 手动恢复


@dataclass
class EmergencyStopConfig:
    """紧急停止配置"""
    stop_level: StopLevel
    target_id: Union[int, str]  # 用户ID、账户ID、交易对等
    reason: StopReason
    stop_all_orders: bool = True
    cancel_pending_orders: bool = True
    pause_new_orders: bool = True
    max_stop_duration: int = 3600  # 最大停止时长（秒），默认1小时
    require_confirmation: bool = True
    notification_channels: List[NotificationChannel] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = [
                NotificationChannel.POPUP,
                NotificationChannel.DESKTOP,
                NotificationChannel.EMAIL
            ]
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StopRecord:
    """紧急停止记录"""
    stop_id: str
    stop_level: StopLevel
    target_id: Union[int, str]
    reason: StopReason
    status: StopStatus
    triggered_at: datetime
    triggered_by: str
    expires_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_by: Optional[str]
    orders_affected: int
    total_amount: float
    metadata: Dict[str, Any]
    notification_sent: bool = False


class EmergencyStopService:
    """紧急停止服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.notification_manager = get_notification_manager()
        self.risk_alert_manager = get_risk_alert_notification_manager()
        
        # 活跃停止记录
        self.active_stops: Dict[str, StopRecord] = {}
        
        # 停止规则缓存
        self.stop_rules: Dict[str, EmergencyStopConfig] = {}
        
        # 监控任务
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        # 统计信息
        self.stats = {
            "total_stops": 0,
            "active_stops": 0,
            "orders_cancelled": 0,
            "amount_preserved": 0.0,
            "by_level": {},
            "by_reason": {}
        }
        
        logger.info("紧急停止服务初始化完成")
    
    async def start_monitoring(self):
        """启动监控任务"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("紧急停止监控任务已启动")
    
    async def stop_monitoring(self):
        """停止监控任务"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("紧急停止监控任务已停止")
    
    async def execute_emergency_stop(
        self,
        config: EmergencyStopConfig,
        triggered_by: str,
        confirmation_token: Optional[str] = None
    ) -> str:
        """执行紧急停止"""
        try:
            # 验证确认令牌
            if config.require_confirmation and not confirmation_token:
                raise ValueError("紧急停止需要确认令牌")
            
            # 生成停止ID
            stop_id = f"stop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # 检查是否已存在相同目标的活跃停止
            existing_stop = await self._get_active_stop_for_target(config.target_id, config.stop_level)
            if existing_stop:
                logger.warning(f"目标 {config.target_id} 已存在活跃停止 {existing_stop.stop_id}")
                return existing_stop.stop_id
            
            # 执行停止操作
            start_time = datetime.now()
            orders_affected = 0
            total_amount = 0.0
            
            if config.stop_level == StopLevel.GLOBAL:
                orders_affected, total_amount = await self._stop_all_trading(config, triggered_by)
            elif config.stop_level == StopLevel.USER:
                orders_affected, total_amount = await self._stop_user_trading(config, triggered_by)
            elif config.stop_level == StopLevel.ACCOUNT:
                orders_affected, total_amount = await self._stop_account_trading(config, triggered_by)
            elif config.stop_level == StopLevel.SYMBOL:
                orders_affected, total_amount = await self._stop_symbol_trading(config, triggered_by)
            elif config.stop_level == StopLevel.STRATEGY:
                orders_affected, total_amount = await self._stop_strategy_trading(config, triggered_by)
            
            # 计算过期时间
            expires_at = None
            if config.max_stop_duration > 0:
                expires_at = start_time + timedelta(seconds=config.max_stop_duration)
            
            # 创建停止记录
            stop_record = StopRecord(
                stop_id=stop_id,
                stop_level=config.stop_level,
                target_id=config.target_id,
                reason=config.reason,
                status=StopStatus.ACTIVE,
                triggered_at=start_time,
                triggered_by=triggered_by,
                expires_at=expires_at,
                cancelled_at=None,
                cancelled_by=None,
                orders_affected=orders_affected,
                total_amount=total_amount,
                metadata=config.metadata or {}
            )
            
            # 保存到内存和数据库
            self.active_stops[stop_id] = stop_record
            await self._save_stop_record(stop_record)
            
            # 发送通知
            await self._send_emergency_stop_notification(stop_record, config)
            
            # 更新统计信息
            self._update_stats("stop", config.stop_level, config.reason, orders_affected, total_amount)
            
            # 创建风险预警记录
            await self._create_risk_alert(stop_record, config)
            
            logger.info(f"紧急停止执行成功: {stop_id}, 影响订单: {orders_affected}, 金额: {total_amount}")
            
            return stop_id
            
        except Exception as e:
            logger.error(f"紧急停止执行失败: {str(e)}")
            raise
    
    async def cancel_emergency_stop(
        self,
        stop_id: str,
        cancelled_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """取消紧急停止"""
        try:
            if stop_id not in self.active_stops:
                logger.warning(f"未找到活跃停止记录: {stop_id}")
                return False
            
            stop_record = self.active_stops[stop_id]
            
            # 更新状态
            stop_record.status = StopStatus.CANCELLED
            stop_record.cancelled_at = datetime.now()
            stop_record.cancelled_by = cancelled_by
            
            # 保存到数据库
            await self._update_stop_record_status(stop_id, StopStatus.CANCELLED)
            
            # 从内存移除
            del self.active_stops[stop_id]
            
            # 发送取消通知
            await self._send_cancellation_notification(stop_record, cancelled_by, reason)
            
            logger.info(f"紧急停止已取消: {stop_id} by {cancelled_by}")
            return True
            
        except Exception as e:
            logger.error(f"取消紧急停止失败: {str(e)}")
            return False
    
    async def resume_trading(
        self,
        stop_id: str,
        resumed_by: str
    ) -> bool:
        """恢复交易"""
        try:
            if stop_id not in self.active_stops:
                logger.warning(f"未找到活跃停止记录: {stop_id}")
                return False
            
            stop_record = self.active_stops[stop_id]
            
            # 更新状态
            stop_record.status = StopStatus.MANUAL_RESUME
            stop_record.cancelled_at = datetime.now()
            stop_record.cancelled_by = resumed_by
            
            # 保存到数据库
            await self._update_stop_record_status(stop_id, StopStatus.MANUAL_RESUME)
            
            # 从内存移除
            del self.active_stops[stop_id]
            
            # 发送恢复通知
            await self._send_resume_notification(stop_record, resumed_by)
            
            logger.info(f"交易已恢复: {stop_id} by {resumed_by}")
            return True
            
        except Exception as e:
            logger.error(f"恢复交易失败: {str(e)}")
            return False
    
    def is_trading_stopped(
        self,
        user_id: Optional[int] = None,
        account_id: Optional[int] = None,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> bool:
        """检查交易是否已停止"""
        # 检查全局停止
        if self._has_global_stop():
            return True
        
        # 检查用户级别停止
        if user_id and self._has_stop_for_target(user_id, StopLevel.USER):
            return True
        
        # 检查账户级别停止
        if account_id and self._has_stop_for_target(account_id, StopLevel.ACCOUNT):
            return True
        
        # 检查交易对级别停止
        if symbol and self._has_stop_for_target(symbol, StopLevel.SYMBOL):
            return True
        
        # 检查策略级别停止
        if strategy and self._has_stop_for_target(strategy, StopLevel.STRATEGY):
            return True
        
        return False
    
    async def get_active_stops(self) -> List[StopRecord]:
        """获取所有活跃停止"""
        return list(self.active_stops.values())
    
    async def get_stop_history(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取停止历史"""
        try:
            # 这里应该查询数据库获取历史记录
            # 简化实现，返回内存中的记录
            history = []
            
            for stop_record in self.active_stops.values():
                history.append(asdict(stop_record))
            
            # 按触发时间排序
            history.sort(key=lambda x: x['triggered_at'], reverse=True)
            
            # 分页
            return history[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"获取停止历史失败: {str(e)}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "stats": self.stats.copy(),
            "active_stops_count": len(self.active_stops),
            "active_stops": [asdict(stop) for stop in self.active_stops.values()],
            "monitoring_active": self.is_monitoring
        }
    
    # 私有方法实现
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                current_time = datetime.now()
                
                # 检查过期的停止
                expired_stops = []
                for stop_id, stop_record in self.active_stops.items():
                    if (stop_record.expires_at and 
                        current_time > stop_record.expires_at and
                        stop_record.status == StopStatus.ACTIVE):
                        expired_stops.append(stop_id)
                
                # 自动过期过期停止
                for stop_id in expired_stops:
                    stop_record = self.active_stops[stop_id]
                    stop_record.status = StopStatus.EXPIRED
                    
                    # 更新数据库
                    await self._update_stop_record_status(stop_id, StopStatus.EXPIRED)
                    
                    # 从内存移除
                    del self.active_stops[stop_id]
                    
                    # 发送过期通知
                    await self._send_expiry_notification(stop_record)
                    
                    logger.info(f"紧急停止已自动过期: {stop_id}")
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {str(e)}")
                await asyncio.sleep(60)
    
    async def _stop_all_trading(self, config: EmergencyStopConfig, triggered_by: str) -> tuple[int, float]:
        """停止所有交易"""
        orders_affected = 0
        total_amount = 0.0
        
        # 取消所有活跃订单
        active_orders = await self.db_session.execute(
            select(Order).where(Order.status.in_([
                OrderStatus.NEW,
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED
            ]))
        )
        
        for order in active_orders.scalars().all():
            if await self._cancel_order(order, config):
                orders_affected += 1
                total_amount += float(order.price * order.quantity) if order.price else 0.0
        
        # 暂停所有自动订单
        auto_orders = await self.db_session.execute(
            select(AutoOrder).where(AutoOrder.status == OrderStatus.NEW)
        )
        
        for auto_order in auto_orders.scalars().all():
            auto_order.is_paused = True
            orders_affected += 1
        
        await self.db_session.commit()
        
        logger.info(f"全局停止完成，影响订单: {orders_affected}")
        return orders_affected, total_amount
    
    async def _stop_user_trading(self, config: EmergencyStopConfig, triggered_by: str) -> tuple[int, float]:
        """停止用户交易"""
        user_id = config.target_id
        orders_affected = 0
        total_amount = 0.0
        
        # 取消用户的所有活跃订单
        active_orders = await self.db_session.execute(
            select(Order).join(Account).where(
                Account.user_id == user_id,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PENDING, OrderStatus.SUBMITTED])
            )
        )
        
        for order in active_orders.scalars().all():
            if await self._cancel_order(order, config):
                orders_affected += 1
                total_amount += float(order.price * order.quantity) if order.price else 0.0
        
        # 暂停用户的自动订单
        auto_orders = await self.db_session.execute(
            select(AutoOrder).where(AutoOrder.user_id == user_id)
        )
        
        for auto_order in auto_orders.scalars().all():
            auto_order.is_paused = True
            orders_affected += 1
        
        await self.db_session.commit()
        
        logger.info(f"用户 {user_id} 停止完成，影响订单: {orders_affected}")
        return orders_affected, total_amount
    
    async def _stop_account_trading(self, config: EmergencyStopConfig, triggered_by: str) -> tuple[int, float]:
        """停止账户交易"""
        account_id = config.target_id
        orders_affected = 0
        total_amount = 0.0
        
        # 取消账户的所有活跃订单
        active_orders = await self.db_session.execute(
            select(Order).where(
                Order.account_id == account_id,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PENDING, OrderStatus.SUBMITTED])
            )
        )
        
        for order in active_orders.scalars().all():
            if await self._cancel_order(order, config):
                orders_affected += 1
                total_amount += float(order.price * order.quantity) if order.price else 0.0
        
        # 暂停账户的自动订单
        auto_orders = await self.db_session.execute(
            select(AutoOrder).where(AutoOrder.account_id == account_id)
        )
        
        for auto_order in auto_orders.scalars().all():
            auto_order.is_paused = True
            orders_affected += 1
        
        await self.db_session.commit()
        
        logger.info(f"账户 {account_id} 停止完成，影响订单: {orders_affected}")
        return orders_affected, total_amount
    
    async def _stop_symbol_trading(self, config: EmergencyStopConfig, triggered_by: str) -> tuple[int, float]:
        """停止交易对交易"""
        symbol = config.target_id
        orders_affected = 0
        total_amount = 0.0
        
        # 取消交易对的所有活跃订单
        active_orders = await self.db_session.execute(
            select(Order).where(
                Order.symbol == symbol,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PENDING, OrderStatus.SUBMITTED])
            )
        )
        
        for order in active_orders.scalars().all():
            if await self._cancel_order(order, config):
                orders_affected += 1
                total_amount += float(order.price * order.quantity) if order.price else 0.0
        
        # 暂停交易对的自动订单
        auto_orders = await self.db_session.execute(
            select(AutoOrder).where(AutoOrder.symbol == symbol)
        )
        
        for auto_order in auto_orders.scalars().all():
            auto_order.is_paused = True
            orders_affected += 1
        
        await self.db_session.commit()
        
        logger.info(f"交易对 {symbol} 停止完成，影响订单: {orders_affected}")
        return orders_affected, total_amount
    
    async def _stop_strategy_trading(self, config: EmergencyStopConfig, triggered_by: str) -> tuple[int, float]:
        """停止策略交易"""
        strategy_name = config.target_id
        orders_affected = 0
        total_amount = 0.0
        
        # 取消策略的所有活跃订单
        auto_orders = await self.db_session.execute(
            select(AutoOrder).where(AutoOrder.strategy_name == strategy_name)
        )
        
        for auto_order in auto_orders.scalars().all():
            # 取消相关的普通订单
            if auto_order.order_id:
                order = await self.db_session.get(Order, auto_order.order_id)
                if order and order.status in [OrderStatus.NEW, OrderStatus.PENDING]:
                    if await self._cancel_order(order, config):
                        orders_affected += 1
                        total_amount += float(order.price * order.quantity) if order.price else 0.0
            
            # 暂停自动订单
            auto_order.is_paused = True
            orders_affected += 1
        
        await self.db_session.commit()
        
        logger.info(f"策略 {strategy_name} 停止完成，影响订单: {orders_affected}")
        return orders_affected, total_amount
    
    async def _cancel_order(self, order: Order, config: EmergencyStopConfig) -> bool:
        """取消单个订单"""
        try:
            # 更新订单状态
            order.status = OrderStatus.CANCELLED
            
            # 创建执行记录
            execution = OrderExecution(
                order_id=order.id,
                execution_id=f"cancel_{uuid.uuid4().hex[:16]}",
                status=ExecutionResultStatus.SUCCESS,
                success=False,
                message=f"订单因紧急停止而取消，原因: {config.reason.value}",
                execution_time=datetime.now()
            )
            
            self.db_session.add(execution)
            return True
            
        except Exception as e:
            logger.error(f"取消订单失败 {order.id}: {str(e)}")
            return False
    
    def _has_global_stop(self) -> bool:
        """检查是否有全局停止"""
        for stop_record in self.active_stops.values():
            if (stop_record.stop_level == StopLevel.GLOBAL and 
                stop_record.status == StopStatus.ACTIVE):
                return True
        return False
    
    def _has_stop_for_target(self, target_id: Union[int, str], level: StopLevel) -> bool:
        """检查目标是否有停止"""
        for stop_record in self.active_stops.values():
            if (stop_record.stop_level == level and 
                stop_record.target_id == target_id and
                stop_record.status == StopStatus.ACTIVE):
                return True
        return False
    
    async def _get_active_stop_for_target(self, target_id: Union[int, str], level: StopLevel) -> Optional[StopRecord]:
        """获取目标的有效停止记录"""
        for stop_record in self.active_stops.values():
            if (stop_record.stop_level == level and 
                stop_record.target_id == target_id and
                stop_record.status == StopStatus.ACTIVE):
                return stop_record
        return None
    
    async def _save_stop_record(self, stop_record: StopRecord):
        """保存停止记录到数据库"""
        # 这里应该保存到数据库表
        # 简化实现，只记录日志
        logger.info(f"保存停止记录: {stop_record.stop_id}")
    
    async def _update_stop_record_status(self, stop_id: str, status: StopStatus):
        """更新停止记录状态"""
        # 这里应该更新数据库记录
        # 简化实现
        logger.info(f"更新停止记录状态: {stop_id} -> {status.value}")
    
    def _update_stats(self, action: str, level: StopLevel, reason: StopReason, orders: int, amount: float):
        """更新统计信息"""
        self.stats["total_stops"] += 1
        self.stats["active_stops"] = len(self.active_stops)
        self.stats["orders_cancelled"] += orders
        self.stats["amount_preserved"] += amount
        
        # 按级别统计
        level_key = level.value
        self.stats["by_level"][level_key] = self.stats["by_level"].get(level_key, 0) + 1
        
        # 按原因统计
        reason_key = reason.value
        self.stats["by_reason"][reason_key] = self.stats["by_reason"].get(reason_key, 0) + 1
    
    async def _send_emergency_stop_notification(self, stop_record: StopRecord, config: EmergencyStopConfig):
        """发送紧急停止通知"""
        try:
            title = f"🚨 紧急停止触发 - {stop_record.stop_level.value.upper()}"
            message = f"""
紧急停止已触发！

停止级别: {stop_record.stop_level.value.upper()}
目标: {stop_record.target_id}
触发原因: {stop_record.reason.value}
触发时间: {stop_record.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
触发者: {stop_record.triggered_by}

影响订单: {stop_record.orders_affected} 个
影响金额: {stop_record.total_amount:.2f}

停止ID: {stop_record.stop_id}
"""
            
            # 发送通知
            message_ids = await self.notification_manager.send_custom_notification(
                title=title,
                content=message,
                channels=config.notification_channels,
                priority=NotificationPriority.CRITICAL,
                metadata={
                    "stop_id": stop_record.stop_id,
                    "stop_level": stop_record.stop_level.value,
                    "reason": stop_record.reason.value
                }
            )
            
            stop_record.notification_sent = len(message_ids) > 0
            
            logger.info(f"紧急停止通知已发送: {stop_record.stop_id}")
            
        except Exception as e:
            logger.error(f"发送紧急停止通知失败: {str(e)}")
    
    async def _send_cancellation_notification(self, stop_record: StopRecord, cancelled_by: str, reason: Optional[str]):
        """发送取消通知"""
        try:
            title = f"✅ 紧急停止已取消"
            message = f"""
紧急停止已被取消！

停止ID: {stop_record.stop_id}
取消时间: {stop_record.cancelled_at.strftime('%Y-%m-%d %H:%M:%S')}
取消者: {cancelled_by}
取消原因: {reason or '未提供'}
"""
            
            # 发送通知
            await self.notification_manager.send_custom_notification(
                title=title,
                content=message,
                channels=[NotificationChannel.POPUP, NotificationChannel.EMAIL],
                priority=NotificationPriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"发送取消通知失败: {str(e)}")
    
    async def _send_resume_notification(self, stop_record: StopRecord, resumed_by: str):
        """发送恢复通知"""
        try:
            title = f"🔄 交易已恢复"
            message = f"""
紧急停止已取消，交易恢复！

停止ID: {stop_record.stop_id}
恢复时间: {stop_record.cancelled_at.strftime('%Y-%m-%d %H:%M:%S')}
恢复者: {resumed_by}
"""
            
            # 发送通知
            await self.notification_manager.send_custom_notification(
                title=title,
                content=message,
                channels=[NotificationChannel.POPUP],
                priority=NotificationPriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"发送恢复通知失败: {str(e)}")
    
    async def _send_expiry_notification(self, stop_record: StopRecord):
        """发送过期通知"""
        try:
            title = f"⏰ 紧急停止已过期"
            message = f"""
紧急停止已自动过期！

停止ID: {stop_record.stop_id}
过期时间: {stop_record.expires_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # 发送通知
            await self.notification_manager.send_custom_notification(
                title=title,
                content=message,
                channels=[NotificationChannel.POPUP],
                priority=NotificationPriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"发送过期通知失败: {str(e)}")
    
    async def _create_risk_alert(self, stop_record: StopRecord, config: EmergencyStopConfig):
        """创建风险预警记录"""
        try:
            # 创建风险预警记录
            risk_alert = RiskAlert(
                user_id=1,  # 默认系统用户，实际应根据配置确定
                account_id=1,  # 默认账户
                alert_id=f"emergency_stop_{stop_record.stop_id}",
                severity="critical",
                message=f"紧急停止触发: {stop_record.reason.value}",
                alert_type="emergency_stop",
                symbol=None,
                details={
                    "stop_id": stop_record.stop_id,
                    "stop_level": stop_record.stop_level.value,
                    "reason": stop_record.reason.value,
                    "orders_affected": stop_record.orders_affected,
                    "amount_preserved": stop_record.total_amount,
                    "metadata": stop_record.metadata
                },
                timestamp=stop_record.triggered_at
            )
            
            self.db_session.add(risk_alert)
            await self.db_session.commit()
            
        except Exception as e:
            logger.error(f"创建风险预警失败: {str(e)}")


# 全局紧急停止服务实例
_global_emergency_stop_service: Optional[EmergencyStopService] = None


def get_emergency_stop_service(db_session: Optional[AsyncSession] = None) -> EmergencyStopService:
    """获取全局紧急停止服务实例"""
    global _global_emergency_stop_service
    
    if _global_emergency_stop_service is None:
        if db_session is None:
            # 创建临时会话
            async def get_temp_session():
                async for session in get_db_session():
                    return session
            
            # 这里应该有实际实现，简化处理
            raise ValueError("需要提供数据库会话")
        
        _global_emergency_stop_service = EmergencyStopService(db_session)
    
    return _global_emergency_stop_service


def init_emergency_stop_service(db_session: AsyncSession) -> EmergencyStopService:
    """初始化全局紧急停止服务"""
    global _global_emergency_stop_service
    _global_emergency_stop_service = EmergencyStopService(db_session)
    return _global_emergency_stop_service