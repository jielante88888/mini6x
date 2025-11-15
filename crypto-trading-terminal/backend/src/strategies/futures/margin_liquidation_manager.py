"""
保证金和清算管理系统
专门处理期货交易的保证金监控、计算和清算风险管理
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .base_futures_strategy import (
    FuturesMarketData, FuturesPosition, FuturesAccountBalance,
    ValidationException, RiskManagementException
)
from .leverage_manager import PositionMetrics


@dataclass
class MarginAlert:
    """保证金预警信息"""
    alert_id: str
    user_id: int
    account_id: int
    symbol: str
    alert_type: str  # 'warning', 'danger', 'critical', 'margin_call'
    margin_ratio: Decimal
    threshold: Decimal
    message: str
    timestamp: datetime
    is_acknowledged: bool = False
    auto_action_taken: bool = False


@dataclass
class LiquidationRisk:
    """清算风险信息"""
    position: FuturesPosition
    liquidation_price: Decimal
    distance_to_liquidation: Decimal
    distance_percentage: Decimal
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    time_to_liquidation: Optional[int] = None  # 预计多少时间步会清算


class MarginCalculator:
    """保证金计算器"""
    
    def __init__(self):
        self.default_settings = {
            'initial_margin_rate': Decimal('0.01'),    # 1%
            'maintenance_margin_rate': Decimal('0.005'), # 0.5%
            'maker_fee_rate': Decimal('0.0002'),      # 0.02%
            'taker_fee_rate': Decimal('0.0004'),      # 0.04%
            'liquidation_fee_rate': Decimal('0.005'), # 0.5%
        }
    
    def calculate_initial_margin(
        self,
        position_value: Decimal,
        leverage: Decimal,
        contract_type: str = 'perpetual'
    ) -> Decimal:
        """计算初始保证金"""
        try:
            if leverage <= 0:
                raise ValidationException("杠杆必须大于0")
            
            margin_rate = self.default_settings['initial_margin_rate']
            
            if contract_type.lower() == 'perpetual':
                # 永续合约：按杠杆计算
                initial_margin = position_value / leverage
            else:
                # 交割合约：按百分比计算
                initial_margin = position_value * margin_rate
            
            return initial_margin
            
        except Exception as e:
            raise ValidationException(f"初始保证金计算失败: {e}")
    
    def calculate_maintenance_margin(
        self,
        position_value: Decimal,
        leverage: Decimal,
        contract_type: str = 'perpetual'
    ) -> Decimal:
        """计算维持保证金"""
        try:
            margin_rate = self.default_settings['maintenance_margin_rate']
            
            if contract_type.lower() == 'perpetual':
                # 永续合约：按杠杆计算
                maintenance_margin = position_value / leverage * margin_rate / self.default_settings['initial_margin_rate']
            else:
                # 交割合约：按百分比计算
                maintenance_margin = position_value * margin_rate
            
            return maintenance_margin
            
        except Exception as e:
            raise ValidationException(f"维持保证金计算失败: {e}")
    
    def calculate_liquidation_price(
        self,
        entry_price: Decimal,
        quantity: Decimal,
        margin_balance: Decimal,
        leverage: Decimal,
        maintenance_margin_rate: Decimal = Decimal('0.005'),
        fee_rate: Decimal = Decimal('0.0004')
    ) -> Optional[Decimal]:
        """计算清算价格"""
        try:
            if quantity == 0 or entry_price <= 0 or leverage <= 0:
                return None
            
            position_value = abs(quantity) * entry_price
            fee = position_value * fee_rate
            
            # 考虑手续费影响的实际保证金
            effective_margin = margin_balance - fee
            
            if effective_margin <= 0:
                return None
            
            # 根据仓位方向计算清算价格
            if quantity > 0:  # 多头仓位
                liquidation_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
            else:  # 空头仓位
                liquidation_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)
            
            # 确保清算价格合理
            if liquidation_price <= 0:
                return None
            
            return liquidation_price
            
        except Exception as e:
            logging.error(f"清算价格计算失败: {e}")
            return None
    
    def calculate_margin_ratio(
        self,
        margin_balance: Decimal,
        position_value: Decimal,
        unrealized_pnl: Decimal = Decimal('0')
    ) -> Decimal:
        """计算保证金比例"""
        try:
            if position_value <= 0:
                return Decimal('0')
            
            # 可用保证金 = 账户余额 + 未实现盈亏
            available_margin = margin_balance + unrealized_pnl
            
            if available_margin <= 0:
                return Decimal('0')
            
            margin_ratio = (available_margin / position_value) * Decimal('100')
            return margin_ratio
            
        except Exception as e:
            logging.error(f"保证金比例计算失败: {e}")
            return Decimal('0')


class LiquidationManager:
    """清算管理器"""
    
    def __init__(self, margin_calculator: Optional[MarginCalculator] = None):
        self.margin_calculator = margin_calculator or MarginCalculator()
        self.liquidation_thresholds = {
            'high_risk': Decimal('15'),    # 距离清算价格15%
            'medium_risk': Decimal('25'),  # 距离清算价格25%
            'low_risk': Decimal('50'),     # 距离清算价格50%
        }
        self.logger = logging.getLogger(__name__)
    
    def assess_liquidation_risk(
        self,
        position: FuturesPosition,
        current_price: Decimal,
        margin_balance: Decimal
    ) -> LiquidationRisk:
        """评估清算风险"""
        try:
            if not position.liquidation_price or current_price <= 0:
                return LiquidationRisk(
                    position=position,
                    liquidation_price=Decimal('0'),
                    distance_to_liquidation=Decimal('0'),
                    distance_percentage=Decimal('0'),
                    risk_level='unknown'
                )
            
            # 计算距离清算价格的距离
            if position.quantity > 0:  # 多头
                distance = position.liquidation_price - current_price
            else:  # 空头
                distance = current_price - position.liquidation_price
            
            distance_percentage = abs(distance / position.liquidation_price * 100)
            
            # 确定风险等级
            risk_level = 'low'
            if distance_percentage <= self.liquidation_thresholds['high_risk']:
                risk_level = 'critical'
            elif distance_percentage <= self.liquidation_thresholds['medium_risk']:
                risk_level = 'high'
            elif distance_percentage <= self.liquidation_thresholds['low_risk']:
                risk_level = 'medium'
            
            # 计算预计清算时间（基于价格变化）
            time_to_liquidation = None
            if risk_level in ['high', 'critical'] and hasattr(position, 'price_change_1h'):
                price_change_rate = abs(position.price_change_1h)
                if price_change_rate > 0:
                    time_to_liquidation = int(distance_percentage / price_change_rate)
            
            return LiquidationRisk(
                position=position,
                liquidation_price=position.liquidation_price,
                distance_to_liquidation=distance,
                distance_percentage=distance_percentage,
                risk_level=risk_level,
                time_to_liquidation=time_to_liquidation
            )
            
        except Exception as e:
            self.logger.error(f"清算风险评估失败: {e}")
            return LiquidationRisk(
                position=position,
                liquidation_price=Decimal('0'),
                distance_to_liquidation=Decimal('0'),
                distance_percentage=Decimal('0'),
                risk_level='unknown'
            )
    
    def is_emergency_liquidation_needed(
        self,
        liquidation_risk: LiquidationRisk,
        margin_ratio: Decimal
    ) -> bool:
        """判断是否需要紧急清算"""
        try:
            # 紧急清算条件
            if liquidation_risk.risk_level == 'critical':
                return True
            
            if margin_ratio < Decimal('110'):  # 保证金比例低于110%
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"紧急清算判断失败: {e}")
            return False


class MarginMonitor:
    """保证金监控器"""
    
    def __init__(
        self,
        margin_calculator: Optional[MarginCalculator] = None,
        liquidation_manager: Optional[LiquidationManager] = None
    ):
        self.margin_calculator = margin_calculator or MarginCalculator()
        self.liquidation_manager = liquidation_manager or LiquidationManager(margin_calculator)
        
        self.monitoring_thresholds = {
            'warning': Decimal('120'),    # 保证金比例120%预警
            'danger': Decimal('110'),     # 保证金比例110%危险
            'critical': Decimal('105'),   # 保证金比例105%临界
            'margin_call': Decimal('100'), # 保证金比例100%追加保证金
        }
        
        self.alerts: List[MarginAlert] = []
        self.user_alert_callbacks: Dict[int, Callable] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_alert_callback(self, user_id: int, callback: Callable):
        """添加用户预警回调"""
        self.user_alert_callbacks[user_id] = callback
    
    def check_margin_conditions(
        self,
        position: FuturesPosition,
        account_balance: FuturesAccountBalance,
        market_data: FuturesMarketData
    ) -> List[MarginAlert]:
        """检查保证金条件并生成预警"""
        try:
            alerts = []
            
            # 计算相关指标
            position_value = abs(position.quantity * market_data.current_price)
            margin_ratio = self.margin_calculator.calculate_margin_ratio(
                account_balance.wallet_balance,
                position_value,
                position.unrealized_pnl
            )
            
            # 清算风险评估
            liquidation_risk = self.liquidation_manager.assess_liquidation_risk(
                position,
                market_data.current_price,
                account_balance.wallet_balance
            )
            
            # 生成保证金预警
            if margin_ratio <= self.monitoring_thresholds['margin_call']:
                alert = MarginAlert(
                    alert_id=f"margin_call_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='margin_call',
                    margin_ratio=margin_ratio,
                    threshold=self.monitoring_thresholds['margin_call'],
                    message=f"保证金不足，需要追加保证金。当前比例: {margin_ratio:.2f}%",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
                
            elif margin_ratio <= self.monitoring_thresholds['critical']:
                alert = MarginAlert(
                    alert_id=f"critical_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='critical',
                    margin_ratio=margin_ratio,
                    threshold=self.monitoring_thresholds['critical'],
                    message=f"保证金比例严重不足: {margin_ratio:.2f}%，面临强制平仓风险",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
                
            elif margin_ratio <= self.monitoring_thresholds['danger']:
                alert = MarginAlert(
                    alert_id=f"danger_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='danger',
                    margin_ratio=margin_ratio,
                    threshold=self.monitoring_thresholds['danger'],
                    message=f"保证金比例偏低: {margin_ratio:.2f}%，建议增加保证金或减少仓位",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
                
            elif margin_ratio <= self.monitoring_thresholds['warning']:
                alert = MarginAlert(
                    alert_id=f"warning_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='warning',
                    margin_ratio=margin_ratio,
                    threshold=self.monitoring_thresholds['warning'],
                    message=f"保证金比例需关注: {margin_ratio:.2f}%",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
            
            # 清算风险预警
            if liquidation_risk.risk_level == 'critical':
                alert = MarginAlert(
                    alert_id=f"liquidation_critical_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='critical',
                    margin_ratio=margin_ratio,
                    threshold=Decimal('0'),
                    message=f"清算风险极高！距离清算价格仅 {liquidation_risk.distance_percentage:.2f}%",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
            
            elif liquidation_risk.risk_level == 'high':
                alert = MarginAlert(
                    alert_id=f"liquidation_high_{position.user_id}_{position.symbol}_{datetime.now().timestamp()}",
                    user_id=position.user_id,
                    account_id=position.account_id,
                    symbol=position.symbol,
                    alert_type='danger',
                    margin_ratio=margin_ratio,
                    threshold=Decimal('0'),
                    message=f"清算风险较高，距离清算价格 {liquidation_risk.distance_percentage:.2f}%",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
            
            # 存储预警并发送回调
            for alert in alerts:
                self.alerts.append(alert)
                
                # 发送用户回调
                if alert.user_id in self.user_alert_callbacks:
                    try:
                        asyncio.create_task(
                            self.user_alert_callbacks[alert.user_id](alert)
                        )
                    except Exception as e:
                        self.logger.error(f"发送预警回调失败: {e}")
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查保证金条件失败: {e}")
            return []
    
    def get_active_alerts(self, user_id: Optional[int] = None) -> List[MarginAlert]:
        """获取活跃预警"""
        try:
            alerts = [alert for alert in self.alerts if not alert.is_acknowledged]
            
            if user_id:
                alerts = [alert for alert in alerts if alert.user_id == user_id]
            
            return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
            
        except Exception as e:
            self.logger.error(f"获取活跃预警失败: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认预警"""
        try:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.is_acknowledged = True
                    return True
            return False
            
        except Exception as e:
            self.logger.error(f"确认预警失败: {e}")
            return False
    
    def clear_resolved_alerts(self, older_than_hours: int = 24):
        """清除已解决的预警"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            # 清除已确认且过时的预警
            self.alerts = [
                alert for alert in self.alerts
                if not (alert.is_acknowledged and alert.timestamp < cutoff_time)
            ]
            
        except Exception as e:
            self.logger.error(f"清除已解决预警失败: {e}")


class MarginLiquidationManager:
    """保证金和清算统一管理器"""
    
    def __init__(self):
        self.margin_calculator = MarginCalculator()
        self.liquidation_manager = LiquidationManager(self.margin_calculator)
        self.margin_monitor = MarginMonitor(self.margin_calculator, self.liquidation_manager)
        
        self.active_positions: Dict[str, FuturesPosition] = {}
        self.user_accounts: Dict[int, FuturesAccountBalance] = {}
        
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_position(self, position: FuturesPosition):
        """注册仓位"""
        try:
            position_key = f"{position.user_id}_{position.account_id}_{position.symbol}"
            self.active_positions[position_key] = position
            self.logger.info(f"注册仓位: {position_key}")
            
        except Exception as e:
            self.logger.error(f"注册仓位失败: {e}")
    
    def unregister_position(self, user_id: int, account_id: int, symbol: str):
        """注销仓位"""
        try:
            position_key = f"{user_id}_{account_id}_{symbol}"
            if position_key in self.active_positions:
                del self.active_positions[position_key]
                self.logger.info(f"注销仓位: {position_key}")
            
        except Exception as e:
            self.logger.error(f"注销仓位失败: {e}")
    
    def update_account_balance(self, account: FuturesAccountBalance):
        """更新账户余额"""
        try:
            account_key = f"{account.user_id}_{account.account_id}"
            self.user_accounts[account_key] = account
            self.logger.info(f"更新账户余额: {account_key}")
            
        except Exception as e:
            self.logger.error(f"更新账户余额失败: {e}")
    
    async def monitor_position(
        self,
        user_id: int,
        account_id: int,
        symbol: str,
        position: FuturesPosition,
        account: FuturesAccountBalance,
        market_data: FuturesMarketData
    ):
        """监控单个仓位"""
        try:
            position_key = f"{user_id}_{account_id}_{symbol}"
            
            # 计算清算价格
            liquidation_price = self.margin_calculator.calculate_liquidation_price(
                entry_price=position.entry_price,
                quantity=position.quantity,
                margin_balance=account.wallet_balance,
                leverage=position.leverage
            )
            
            if liquidation_price:
                position.liquidation_price = liquidation_price
            
            # 检查保证金条件
            alerts = self.margin_monitor.check_margin_conditions(
                position,
                account,
                market_data
            )
            
            # 评估清算风险
            liquidation_risk = self.liquidation_manager.assess_liquidation_risk(
                position,
                market_data.current_price,
                account.wallet_balance
            )
            
            # 如果需要紧急清算
            position_value = abs(position.quantity * market_data.current_price)
            margin_ratio = self.margin_calculator.calculate_margin_ratio(
                account.wallet_balance,
                position_value,
                position.unrealized_pnl
            )
            
            if self.liquidation_manager.is_emergency_liquidation_needed(liquidation_risk, margin_ratio):
                self.logger.warning(f"检测到紧急清算风险: {position_key}, 风险等级: {liquidation_risk.risk_level}")
                # 这里可以触发自动清算逻辑
                await self._handle_emergency_liquidation(position_key, liquidation_risk, margin_ratio)
            
            return {
                'position_key': position_key,
                'alerts': len(alerts),
                'liquidation_risk': liquidation_risk.risk_level,
                'margin_ratio': margin_ratio,
                'liquidation_price': liquidation_price
            }
            
        except Exception as e:
            self.logger.error(f"监控仓位失败: {e}")
            return {'error': str(e)}
    
    async def _handle_emergency_liquidation(
        self,
        position_key: str,
        liquidation_risk: LiquidationRisk,
        margin_ratio: Decimal
    ):
        """处理紧急清算"""
        try:
            self.logger.critical(f"执行紧急清算: {position_key}")
            
            # 这里应该集成自动清算逻辑
            # 例如：发送清算订单、通知用户等
            alert_message = f"紧急清算执行: {position_key}, 清算风险: {liquidation_risk.risk_level}, 保证金比例: {margin_ratio}%"
            
            # 可以集成通知系统
            self.logger.critical(alert_message)
            
        except Exception as e:
            self.logger.error(f"紧急清算处理失败: {e}")
    
    async def start_global_monitoring(self):
        """启动全局监控"""
        try:
            self.logger.info("启动全局保证金监控")
            
            while True:
                # 清理已解决的预警
                self.margin_monitor.clear_resolved_alerts()
                
                # 监控所有注册仓位
                monitoring_tasks = []
                for position_key, position in self.active_positions.items():
                    user_id = position.user_id
                    account_id = position.account_id
                    symbol = position.symbol
                    
                    # 获取账户和市场数据（这里应该从实际数据源获取）
                    # 简化处理：使用模拟数据
                    
                    account_key = f"{user_id}_{account_id}"
                    if account_key in self.user_accounts:
                        account = self.user_accounts[account_key]
                        
                        # 模拟市场数据
                        market_data = FuturesMarketData(
                            symbol=symbol,
                            current_price=Decimal('50000'),  # 模拟价格
                            bid_price=Decimal('49999'),
                            ask_price=Decimal('50001'),
                            volume_24h=Decimal('1000000'),
                            price_change_24h=Decimal('0.02'),
                            timestamp=datetime.now()
                        )
                        
                        task = asyncio.create_task(
                            self.monitor_position(user_id, account_id, symbol, position, account, market_data)
                        )
                        monitoring_tasks.append(task)
                
                # 并发执行监控任务
                if monitoring_tasks:
                    results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            self.logger.error(f"监控任务异常: {result}")
                
                # 监控间隔
                await asyncio.sleep(60)  # 60秒检查一次
                
        except asyncio.CancelledError:
            self.logger.info("全局监控任务取消")
        except Exception as e:
            self.logger.error(f"全局监控异常: {e}")
    
    def stop_global_monitoring(self):
        """停止全局监控"""
        try:
            for task in self.monitoring_tasks.values():
                if not task.done():
                    task.cancel()
            self.monitoring_tasks.clear()
            self.logger.info("停止全局监控")
            
        except Exception as e:
            self.logger.error(f"停止全局监控失败: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        try:
            total_positions = len(self.active_positions)
            high_risk_positions = 0
            critical_risk_positions = 0
            
            for position in self.active_positions.values():
                # 简化风险评估
                if hasattr(position, 'liquidation_distance'):
                    if position.liquidation_distance < Decimal('10'):
                        critical_risk_positions += 1
                    elif position.liquidation_distance < Decimal('25'):
                        high_risk_positions += 1
            
            active_alerts = self.margin_monitor.get_active_alerts()
            
            return {
                'timestamp': datetime.now(),
                'total_positions': total_positions,
                'high_risk_positions': high_risk_positions,
                'critical_risk_positions': critical_risk_positions,
                'active_alerts': len(active_alerts),
                'monitoring_active': len(self.monitoring_tasks) > 0
            }
            
        except Exception as e:
            self.logger.error(f"获取风险摘要失败: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'total_positions': 0
            }