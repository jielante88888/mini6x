"""
风险检查器服务
负责验证订单和仓位风险，检查各种风险限制，生成风险警告
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from ..storage.models import (
    User, Account, Order, AutoOrder, RiskManagement, Position,
    RiskAlert, TradingStatistics, MarketType, OrderType, OrderSide,
    OrderStatus, RiskLevel, ExecutionResultStatus
)
from ..utils.exceptions import RiskManagementException, ValidationException


logger = logging.getLogger(__name__)


class RiskCheckResult:
    """风险检查结果"""
    def __init__(
        self,
        is_approved: bool,
        risk_level: RiskLevel,
        message: str,
        alert_type: str,
        current_value: Optional[Decimal] = None,
        limit_value: Optional[Decimal] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.is_approved = is_approved
        self.risk_level = risk_level
        self.message = message
        self.alert_type = alert_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.details = details or {}


class RiskCheckerService:
    """风险管理检查器服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def check_order_risk(
        self,
        user_id: int,
        account_id: int,
        symbol: str,
        order_side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        auto_order_id: Optional[int] = None,
    ) -> RiskCheckResult:
        """检查订单风险"""
        try:
            # 获取用户和账户信息
            user, account = await self._get_user_account(user_id, account_id)
            
            # 获取风险管理配置
            risk_config = await self._get_active_risk_config(user_id, account_id)
            if not risk_config:
                return RiskCheckResult(
                    is_approved=True,
                    risk_level=RiskLevel.LOW,
                    message="未找到风险配置，默认允许执行",
                    alert_type="no_config"
                )
            
            # 获取当前仓位
            current_position = await self._get_current_position(account_id, symbol)
            
            # 执行各项风险检查
            results = await asyncio.gather(
                self._check_order_size_limit(quantity, risk_config),
                self._check_position_size_limit(order_side, quantity, current_position, risk_config),
                self._check_daily_trade_limits(user_id, account_id, risk_config),
                self._check_trading_hours(risk_config),
                return_exceptions=True
            )
            
            # 合并检查结果
            approval_results = [r for r in results if not isinstance(r, Exception)]
            critical_blocking = [r for r in approval_results if not r.is_approved and r.risk_level == RiskLevel.CRITICAL]
            
            if critical_blocking:
                # 有严重风险阻止执行
                return max(critical_blocking, key=lambda x: len(x.message))
            
            # 检查是否有警告
            warnings = [r for r in approval_results if not r.is_approved and r.risk_level != RiskLevel.CRITICAL]
            if warnings:
                # 返回最严重的警告
                return max(warnings, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x.risk_level.value])
            
            # 所有检查通过
            return RiskCheckResult(
                is_approved=True,
                risk_level=RiskLevel.LOW,
                message="订单通过所有风险检查",
                alert_type="approved"
            )
            
        except Exception as e:
            logger.error(f"风险检查出错: {e}")
            raise RiskManagementException(f"风险检查失败: {e}")
    
    async def _check_order_size_limit(
        self,
        quantity: Decimal,
        risk_config: RiskManagement
    ) -> RiskCheckResult:
        """检查订单大小限制"""
        if quantity > risk_config.max_order_size:
            return RiskCheckResult(
                is_approved=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"订单数量 {quantity} 超过最大限制 {risk_config.max_order_size}",
                alert_type="order_size_limit",
                current_value=quantity,
                limit_value=risk_config.max_order_size,
                details={
                    'current': float(quantity),
                    'limit': float(risk_config.max_order_size),
                    'excess': float(quantity - risk_config.max_order_size)
                }
            )
        
        return RiskCheckResult(
            is_approved=True,
            risk_level=RiskLevel.LOW,
            message=f"订单数量 {quantity} 在限制内",
            alert_type="order_size_ok"
        )
    
    async def _check_position_size_limit(
        self,
        order_side: OrderSide,
        quantity: Decimal,
        current_position: Optional[Position],
        risk_config: RiskManagement
    ) -> RiskCheckResult:
        """检查仓位大小限制"""
        current_quantity = current_position.quantity if current_position else Decimal('0')
        
        # 计算执行后的总仓位
        if order_side == OrderSide.BUY:
            new_quantity = current_quantity + quantity
        else:
            new_quantity = current_quantity - quantity
        
        new_position_size = abs(new_quantity)
        
        if new_position_size > risk_config.max_position_size:
            risk_level = RiskLevel.HIGH if new_position_size > risk_config.max_position_size * 1.5 else RiskLevel.MEDIUM
            
            return RiskCheckResult(
                is_approved=False,
                risk_level=risk_level,
                message=f"新仓位 {new_quantity} 会超过最大限制 {risk_config.max_position_size}",
                alert_type="position_size_limit",
                current_value=current_quantity,
                limit_value=risk_config.max_position_size,
                details={
                    'current_position': float(current_quantity),
                    'order_quantity': float(quantity),
                    'new_position': float(new_quantity),
                    'limit': float(risk_config.max_position_size),
                    'excess': float(new_position_size - risk_config.max_position_size)
                }
            )
        
        return RiskCheckResult(
            is_approved=True,
            risk_level=RiskLevel.LOW,
            message=f"新仓位 {new_quantity} 在限制内",
            alert_type="position_size_ok"
        )
    
    async def _check_daily_trade_limits(
        self,
        user_id: int,
        account_id: int,
        risk_config: RiskManagement
    ) -> RiskCheckResult:
        """检查日交易限制"""
        today = datetime.now().date()
        
        # 检查日交易次数
        trade_count_query = select(func.count(Order.id)).where(
            and_(
                Order.account_id == account_id,
                Order.order_time >= today
            )
        )
        trade_count_result = await self.db_session.execute(trade_count_query)
        trade_count = trade_count_result.scalar() or 0
        
        if trade_count >= risk_config.max_daily_trades:
            return RiskCheckResult(
                is_approved=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"今日交易次数 {trade_count} 已达到上限 {risk_config.max_daily_trades}",
                alert_type="daily_trade_count_limit",
                current_value=Decimal(str(trade_count)),
                limit_value=Decimal(str(risk_config.max_daily_trades)),
                details={
                    'current_count': trade_count,
                    'limit': risk_config.max_daily_trades,
                    'remaining': risk_config.max_daily_trades - trade_count
                }
            )
        
        # 检查日交易量
        volume_query = select(func.sum(Order.total_filled)).where(
            and_(
                Order.account_id == account_id,
                Order.order_time >= today
            )
        )
        volume_result = await self.db_session.execute(volume_query)
        daily_volume = volume_result.scalar() or Decimal('0')
        
        if daily_volume > risk_config.max_daily_volume:
            return RiskCheckResult(
                is_approved=False,
                risk_level=RiskLevel.MEDIUM,
                message=f"今日交易量 {daily_volume} 接近上限 {risk_config.max_daily_volume}",
                alert_type="daily_volume_limit",
                current_value=daily_volume,
                limit_value=risk_config.max_daily_volume,
                details={
                    'current_volume': float(daily_volume),
                    'limit': float(risk_config.max_daily_volume),
                    'utilization': float(daily_volume / risk_config.max_daily_volume * 100)
                }
            )
        
        return RiskCheckResult(
            is_approved=True,
            risk_level=RiskLevel.LOW,
            message=f"日交易限制检查通过 (交易次数: {trade_count}/{risk_config.max_daily_trades}, 交易量: {daily_volume}/{risk_config.max_daily_volume})",
            alert_type="daily_limits_ok",
            details={
                'trade_count': trade_count,
                'trade_count_limit': risk_config.max_daily_trades,
                'daily_volume': float(daily_volume),
                'daily_volume_limit': float(risk_config.max_daily_volume)
            }
        )
    
    async def _check_trading_hours(self, risk_config: RiskManagement) -> RiskCheckResult:
        """检查交易时间限制"""
        if not risk_config.trading_hours_start or not risk_config.trading_hours_end:
            return RiskCheckResult(
                is_approved=True,
                risk_level=RiskLevel.LOW,
                message="未配置交易时间限制",
                alert_type="no_trading_hours"
            )
        
        now = datetime.now().time()
        start_time = datetime.strptime(risk_config.trading_hours_start, "%H:%M").time()
        end_time = datetime.strptime(risk_config.trading_hours_end, "%H:%M").time()
        
        # 处理跨日情况
        if start_time <= end_time:
            is_trading_hours = start_time <= now <= end_time
        else:
            is_trading_hours = now >= start_time or now <= end_time
        
        if not is_trading_hours:
            return RiskCheckResult(
                is_approved=False,
                risk_level=RiskLevel.MEDIUM,
                message=f"当前时间 {now.strftime('%H:%M')} 不在允许的交易时间 {risk_config.trading_hours_start}-{risk_config.trading_hours_end} 内",
                alert_type="trading_hours_restriction",
                details={
                    'current_time': now.strftime('%H:%M'),
                    'allowed_start': risk_config.trading_hours_start,
                    'allowed_end': risk_config.trading_hours_end
                }
            )
        
        return RiskCheckResult(
            is_approved=True,
            risk_level=RiskLevel.LOW,
            message=f"交易时间检查通过 ({now.strftime('%H:%M')} 在允许范围内)",
            alert_type="trading_hours_ok",
            details={
                'current_time': now.strftime('%H:%M'),
                'allowed_hours': f"{risk_config.trading_hours_start}-{risk_config.trading_hours_end}"
            }
        )
    
    async def _get_user_account(self, user_id: int, account_id: int) -> Tuple[User, Account]:
        """获取用户和账户信息"""
        # 获取用户
        user_query = select(User).where(User.id == user_id, User.is_active == True)
        user_result = await self.db_session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValidationException(f"用户 {user_id} 不存在或已禁用")
        
        # 获取账户
        account_query = select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
            Account.is_active == True
        )
        account_result = await self.db_session.execute(account_query)
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise ValidationException(f"账户 {account_id} 不存在或已禁用")
        
        return user, account
    
    async def _get_active_risk_config(self, user_id: int, account_id: int) -> Optional[RiskManagement]:
        """获取活跃的风险管理配置"""
        query = select(RiskManagement).where(
            and_(
                RiskManagement.user_id == user_id,
                RiskManagement.account_id == account_id,
                RiskManagement.is_active == True
            )
        ).order_by(RiskManagement.updated_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_current_position(self, account_id: int, symbol: str) -> Optional[Position]:
        """获取当前仓位"""
        query = select(Position).where(
            and_(
                Position.account_id == account_id,
                Position.symbol == symbol,
                Position.is_active == True
            )
        ).order_by(Position.updated_at.desc())
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_risk_alert(
        self,
        user_id: int,
        account_id: int,
        alert_result: RiskCheckResult,
        symbol: Optional[str] = None,
        auto_order_id: Optional[int] = None,
        order_id: Optional[int] = None,
    ) -> RiskAlert:
        """创建风险警告"""
        alert = RiskAlert(
            user_id=user_id,
            account_id=account_id,
            alert_id=f"risk_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{alert_result.alert_type}",
            severity=self._map_risk_level_to_severity(alert_result.risk_level),
            message=alert_result.message,
            alert_type=alert_result.alert_type,
            symbol=symbol,
            auto_order_id=auto_order_id,
            order_id=order_id,
            details=alert_result.details or {},
            current_value=alert_result.current_value,
            limit_value=alert_result.limit_value,
            timestamp=datetime.now()
        )
        
        self.db_session.add(alert)
        await self.db_session.flush()
        
        logger.warning(f"创建风险警告: {alert.message}", extra={
            'user_id': user_id,
            'account_id': account_id,
            'alert_type': alert_result.alert_type,
            'severity': alert.severity,
            'symbol': symbol
        })
        
        return alert
    
    def _map_risk_level_to_severity(self, risk_level: RiskLevel) -> str:
        """映射风险等级到严重程度"""
        mapping = {
            RiskLevel.LOW: "INFO",
            RiskLevel.MEDIUM: "WARNING",
            RiskLevel.HIGH: "WARNING",
            RiskLevel.CRITICAL: "CRITICAL"
        }
        return mapping.get(risk_level, "INFO")
    
    async def get_user_risk_summary(self, user_id: int, account_id: Optional[int] = None) -> Dict[str, Any]:
        """获取用户风险摘要"""
        base_query = select(RiskAlert).where(
            and_(
                RiskAlert.user_id == user_id,
                RiskAlert.is_acknowledged == False
            )
        )
        
        if account_id:
            base_query = base_query.where(RiskAlert.account_id == account_id)
        
        # 获取未确认的警告
        unacknowledged_result = await self.db_session.execute(base_query)
        unacknowledged_alerts = unacknowledged_result.scalars().all()
        
        # 按严重程度统计
        severity_counts = {
            'INFO': 0,
            'WARNING': 0,
            'CRITICAL': 0,
            'BLOCKED': 0
        }
        
        alert_types = {}
        
        for alert in unacknowledged_alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            alert_types[alert.alert_type] = alert_types.get(alert.alert_type, 0) + 1
        
        # 获取最近的警告
        recent_alerts_query = base_query.order_by(RiskAlert.timestamp.desc()).limit(10)
        recent_result = await self.db_session.execute(recent_alerts_query)
        recent_alerts = recent_result.scalars().all()
        
        # 获取活跃的自动订单
        active_auto_orders_query = select(AutoOrder).where(
            and_(
                AutoOrder.user_id == user_id,
                AutoOrder.is_active == True,
                AutoOrder.is_paused == False
            )
        )
        
        if account_id:
            active_auto_orders_query = active_auto_orders_query.where(AutoOrder.account_id == account_id)
        
        auto_orders_result = await self.db_session.execute(active_auto_orders_query)
        active_auto_orders = auto_orders_result.scalars().all()
        
        return {
            'total_unacknowledged_alerts': len(unacknowledged_alerts),
            'severity_distribution': severity_counts,
            'alert_types': alert_types,
            'recent_alerts': [
                {
                    'alert_id': alert.alert_id,
                    'severity': alert.severity,
                    'message': alert.message,
                    'alert_type': alert.alert_type,
                    'symbol': alert.symbol,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in recent_alerts
            ],
            'active_auto_orders_count': len(active_auto_orders),
            'auto_orders_by_symbol': {}
        }
    
    async def acknowledge_risk_alert(self, alert_id: int, user_id: int, acknowledged_by: str) -> bool:
        """确认风险警告"""
        query = select(RiskAlert).where(
            and_(
                RiskAlert.id == alert_id,
                RiskAlert.user_id == user_id,
                RiskAlert.is_acknowledged == False
            )
        )
        
        result = await self.db_session.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            return False
        
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by
        
        await self.db_session.flush()
        
        logger.info(f"风险警告已确认: {alert.alert_id}", extra={
            'alert_id': alert_id,
            'user_id': user_id,
            'acknowledged_by': acknowledged_by
        })
        
        return True
    
    async def update_position_after_order_execution(
        self,
        account_id: int,
        symbol: str,
        order_side: OrderSide,
        executed_quantity: Decimal,
        execution_price: Decimal
    ) -> Position:
        """订单执行后更新仓位"""
        # 获取当前仓位
        current_position = await self._get_current_position(account_id, symbol)
        
        if not current_position:
            # 创建新仓位
            current_position = Position(
                account_id=account_id,
                symbol=symbol,
                quantity=Decimal('0'),
                quantity_available=Decimal('0'),
                quantity_frozen=Decimal('0'),
                avg_price=Decimal('0'),
                entry_price=Decimal('0'),
                unrealized_pnl=Decimal('0'),
                realized_pnl=Decimal('0'),
                is_active=True
            )
            self.db_session.add(current_position)
        
        # 计算新仓位
        if order_side == OrderSide.BUY:
            # 买入，增加仓位
            total_cost = current_position.quantity * current_position.avg_price + executed_quantity * execution_price
            new_quantity = current_position.quantity + executed_quantity
            
            if new_quantity > 0:
                new_avg_price = total_cost / new_quantity
            else:
                new_avg_price = Decimal('0')
        else:
            # 卖出，减少仓位
            new_quantity = current_position.quantity - executed_quantity
            
            # 计算已实现盈亏
            if executed_quantity <= current_position.quantity:
                pnl = (execution_price - current_position.avg_price) * executed_quantity
                if order_side == OrderSide.SELL:
                    pnl = -pnl  # 卖出时盈亏方向相反
                current_position.realized_pnl += pnl
        
        # 更新仓位信息
        current_position.quantity = new_quantity
        current_position.quantity_available = max(Decimal('0'), new_quantity)
        current_position.avg_price = current_position.avg_price if new_quantity > 0 else Decimal('0')
        
        # 标记无仓位时为非活跃
        if new_quantity == 0:
            current_position.is_active = False
            current_position.status = "closed"
        
        current_position.updated_at = datetime.now()
        
        await self.db_session.flush()
        
        logger.info(f"仓位更新完成: {symbol} 新仓位 {new_quantity}", extra={
            'account_id': account_id,
            'symbol': symbol,
            'order_side': order_side.value,
            'executed_quantity': float(executed_quantity),
            'execution_price': float(execution_price),
            'new_position': float(new_quantity)
        })
        
        return current_position
    
    async def cleanup_expired_alerts(self, days_old: int = 30) -> int:
        """清理过期的风险警告"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        query = select(RiskAlert).where(
            and_(
                RiskAlert.timestamp < cutoff_date,
                RiskAlert.is_acknowledged == True,
                RiskAlert.is_resolved == True
            )
        )
        
        result = await self.db_session.execute(query)
        expired_alerts = result.scalars().all()
        
        count = len(expired_alerts)
        for alert in expired_alerts:
            await self.db_session.delete(alert)
        
        if count > 0:
            await self.db_session.flush()
            logger.info(f"清理了 {count} 个过期的风险警告")
        
        return count