"""
仓位管理器
负责实时跟踪和管理仓位，计算风险指标，提供风险预警和仓位调整建议
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ..storage.models import (
    User, Account, Position, Order, RiskAlert, MarketData,
    OrderSide, MarketType, RiskLevel
)
from ..utils.exceptions import PositionManagementException, ValidationException


logger = logging.getLogger(__name__)


class PositionRiskLevel(Enum):
    """仓位风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PositionRiskMetrics:
    """仓位风险指标"""
    position_id: int
    symbol: str
    current_position: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    risk_level: PositionRiskLevel
    max_drawdown: Decimal
    sharpe_ratio: Optional[float] = None
    var_95: Optional[Decimal] = None  # 95% VaR
    expected_shortfall: Optional[Decimal] = None  # CVaR
    liquidity_score: float = 0.0
    concentration_risk: float = 0.0
    margin_usage: Optional[Decimal] = None
    maintenance_margin: Optional[Decimal] = None


@dataclass
class StopLossConfig:
    """止损配置"""
    enabled: bool
    stop_loss_percent: Decimal = Decimal('5.0')  # 默认5%
    trailing_stop: bool = False
    trailing_distance: Decimal = Decimal('2.0')  # 跟踪止损距离
    emergency_stop: bool = False  # 紧急止损
    max_loss_amount: Optional[Decimal] = None  # 最大亏损金额


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    enabled: bool
    take_profit_percent: Decimal = Decimal('10.0')  # 默认10%
    partial_close: bool = False  # 部分平仓
    partial_percent: Decimal = Decimal('50.0')  # 部分平仓比例
    ladder_take_profit: bool = False  # 阶梯止盈
    ladder_profits: List[Decimal] = None  # 阶梯收益列表

    def __post_init__(self):
        if self.ladder_profits is None:
            self.ladder_profits = [Decimal('5.0'), Decimal('10.0'), Decimal('20.0')]


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.risk_thresholds = {
            PositionRiskLevel.LOW: {
                'max_pnl_percent': Decimal('10.0'),
                'max_concentration': Decimal('20.0'),  # 单个仓位占总投资的比例
                'max_var_percent': Decimal('5.0'),
            },
            PositionRiskLevel.MEDIUM: {
                'max_pnl_percent': Decimal('20.0'),
                'max_concentration': Decimal('30.0'),
                'max_var_percent': Decimal('10.0'),
            },
            PositionRiskLevel.HIGH: {
                'max_pnl_percent': Decimal('30.0'),
                'max_concentration': Decimal('50.0'),
                'max_var_percent': Decimal('15.0'),
            },
            PositionRiskLevel.CRITICAL: {
                'max_pnl_percent': Decimal('50.0'),
                'max_concentration': Decimal('80.0'),
                'max_var_percent': Decimal('25.0'),
            }
        }
    
    async def get_user_positions(
        self,
        user_id: int,
        account_id: Optional[int] = None,
        symbol: Optional[str] = None,
        include_closed: bool = False
    ) -> List[Position]:
        """获取用户仓位列表"""
        try:
            # 构建基础查询
            query = select(Position).join(Account).where(Account.user_id == user_id)
            
            # 添加过滤条件
            if account_id:
                query = query.where(Position.account_id == account_id)
            
            if symbol:
                query = query.where(Position.symbol == symbol)
            
            if not include_closed:
                query = query.where(Position.is_active == True)
            
            # 按更新时间排序
            query = query.order_by(desc(Position.updated_at))
            
            result = await self.db_session.execute(query)
            positions = result.scalars().all()
            
            return list(positions)
            
        except Exception as e:
            logger.error(f"获取用户仓位失败: {e}", extra={'user_id': user_id})
            raise PositionManagementException(f"获取仓位列表失败: {e}")
    
    async def get_position_risk_metrics(
        self,
        position_id: int,
        user_id: int
    ) -> PositionRiskMetrics:
        """获取仓位风险指标"""
        try:
            # 获取仓位信息
            position = await self._get_position_by_id(position_id, user_id)
            if not position:
                raise ValidationException(f"仓位 {position_id} 不存在")
            
            # 获取当前价格
            current_price = await self._get_current_price(position.symbol, position.account_id)
            if not current_price:
                raise ValidationException(f"无法获取 {position.symbol} 的当前价格")
            
            # 计算未实现盈亏
            unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
            unrealized_pnl_percent = self._calculate_unrealized_pnl_percent(position, current_price)
            
            # 获取历史价格数据计算风险指标
            price_history = await self._get_price_history(position.symbol, 30)  # 30天历史数据
            
            # 计算风险指标
            max_drawdown = self._calculate_max_drawdown(price_history, position.entry_price)
            var_95 = self._calculate_var_95(price_history) if price_history else None
            expected_shortfall = self._calculate_expected_shortfall(price_history) if price_history else None
            sharpe_ratio = self._calculate_sharpe_ratio(price_history) if price_history else None
            
            # 计算集中度风险
            concentration_risk = await self._calculate_concentration_risk(user_id, position.account_id, position.symbol)
            
            # 计算流动性分数
            liquidity_score = await self._calculate_liquidity_score(position.symbol)
            
            # 计算保证金使用率（期货）
            margin_usage = None
            maintenance_margin = None
            if position.market_type == MarketType.FUTURES:
                margin_usage = await self._calculate_margin_usage(position)
                maintenance_margin = await self._calculate_maintenance_margin(position)
            
            # 确定风险等级
            risk_level = self._determine_risk_level(position, unrealized_pnl_percent, concentration_risk, var_95)
            
            return PositionRiskMetrics(
                position_id=position.id,
                symbol=position.symbol,
                current_position=position.quantity,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                risk_level=risk_level,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                liquidity_score=liquidity_score,
                concentration_risk=concentration_risk,
                margin_usage=margin_usage,
                maintenance_margin=maintenance_margin
            )
            
        except Exception as e:
            logger.error(f"计算仓位风险指标失败: {e}", extra={'position_id': position_id})
            raise PositionManagementException(f"计算风险指标失败: {e}")
    
    async def calculate_portfolio_risk(self, user_id: int, account_id: int) -> Dict[str, Any]:
        """计算投资组合风险"""
        try:
            # 获取所有活跃仓位
            positions = await self.get_user_positions(user_id, account_id)
            
            if not positions:
                return {
                    'total_positions': 0,
                    'total_value': Decimal('0'),
                    'total_pnl': Decimal('0'),
                    'portfolio_risk_level': PositionRiskLevel.LOW,
                    'risk_metrics': {}
                }
            
            # 获取所有仓位的市场数据
            market_data = {}
            total_value = Decimal('0')
            total_pnl = Decimal('0')
            total_exposure = Decimal('0')
            
            for position in positions:
                current_price = await self._get_current_price(position.symbol, account_id)
                if current_price:
                    position_value = abs(position.quantity) * current_price
                    position_pnl = self._calculate_unrealized_pnl(position, current_price)
                    
                    market_data[position.symbol] = {
                        'current_price': current_price,
                        'position_value': position_value,
                        'position_pnl': position_pnl,
                        'quantity': position.quantity
                    }
                    
                    total_value += position_value
                    total_pnl += position_pnl
                    total_exposure += position_value
            
            # 计算投资组合风险指标
            portfolio_risk_level = await self._calculate_portfolio_risk_level(user_id, account_id, market_data)
            
            # 计算相关性风险
            correlation_risk = await self._calculate_correlation_risk(positions)
            
            # 计算VaR
            portfolio_var = await self._calculate_portfolio_var(market_data)
            
            # 计算最大回撤
            max_drawdown = await self._calculate_portfolio_max_drawdown(user_id, account_id)
            
            # 计算夏普比率
            sharpe_ratio = await self._calculate_portfolio_sharpe_ratio(market_data)
            
            return {
                'total_positions': len(positions),
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_exposure': total_exposure,
                'portfolio_risk_level': portfolio_risk_level,
                'positions_detail': market_data,
                'risk_metrics': {
                    'portfolio_var': portfolio_var,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'correlation_risk': correlation_risk,
                    'concentration_risk': await self._calculate_total_concentration_risk(market_data, total_value)
                },
                'risk_breakdown': await self._calculate_risk_breakdown(positions)
            }
            
        except Exception as e:
            logger.error(f"计算投资组合风险失败: {e}", extra={'user_id': user_id, 'account_id': account_id})
            raise PositionManagementException(f"计算投资组合风险失败: {e}")
    
    async def check_stop_loss_triggers(self, position_id: int, user_id: int) -> List[Dict[str, Any]]:
        """检查止损触发条件"""
        try:
            position = await self._get_position_by_id(position_id, user_id)
            if not position:
                return []
            
            triggers = []
            
            # 获取止损配置
            stop_loss_config = await self._get_stop_loss_config(position_id)
            if not stop_loss_config.enabled:
                return triggers
            
            # 获取当前价格
            current_price = await self._get_current_price(position.symbol, position.account_id)
            if not current_price:
                return triggers
            
            # 检查固定止损
            if stop_loss_config.stop_loss_percent > 0:
                stop_price = self._calculate_stop_price(position, stop_loss_config.stop_loss_percent)
                if self._should_trigger_stop_loss(position, current_price, stop_price):
                    triggers.append({
                        'type': 'fixed_stop_loss',
                        'trigger_price': stop_price,
                        'current_price': current_price,
                        'stop_percent': stop_loss_config.stop_loss_percent,
                        'suggested_action': 'close_position'
                    })
            
            # 检查跟踪止损
            if stop_loss_config.trailing_stop and stop_loss_config.trailing_distance > 0:
                trailing_stop_price = await self._calculate_trailing_stop_price(position, stop_loss_config.trailing_distance)
                if self._should_trigger_trailing_stop(position, current_price, trailing_stop_price):
                    triggers.append({
                        'type': 'trailing_stop',
                        'trigger_price': trailing_stop_price,
                        'current_price': current_price,
                        'trailing_distance': stop_loss_config.trailing_distance,
                        'suggested_action': 'close_position'
                    })
            
            # 检查最大亏损金额
            if stop_loss_config.max_loss_amount:
                unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
                if unrealized_pnl < -abs(stop_loss_config.max_loss_amount):
                    triggers.append({
                        'type': 'max_loss_amount',
                        'current_loss': abs(unrealized_pnl),
                        'max_loss': stop_loss_config.max_loss_amount,
                        'suggested_action': 'close_position'
                    })
            
            return triggers
            
        except Exception as e:
            logger.error(f"检查止损触发失败: {e}", extra={'position_id': position_id})
            raise PositionManagementException(f"检查止损触发失败: {e}")
    
    async def check_take_profit_triggers(self, position_id: int, user_id: int) -> List[Dict[str, Any]]:
        """检查止盈触发条件"""
        try:
            position = await self._get_position_by_id(position_id, user_id)
            if not position:
                return []
            
            triggers = []
            
            # 获取止盈配置
            take_profit_config = await self._get_take_profit_config(position_id)
            if not take_profit_config.enabled:
                return triggers
            
            # 获取当前价格
            current_price = await self._get_current_price(position.symbol, position.account_id)
            if not current_price:
                return triggers
            
            # 检查固定止盈
            if take_profit_config.take_profit_percent > 0:
                target_price = self._calculate_take_profit_price(position, take_profit_config.take_profit_percent)
                if self._should_trigger_take_profit(position, current_price, target_price):
                    triggers.append({
                        'type': 'fixed_take_profit',
                        'trigger_price': target_price,
                        'current_price': current_price,
                        'profit_percent': take_profit_config.take_profit_percent,
                        'suggested_action': 'close_position' if not take_profit_config.partial_close else 'partial_close'
                    })
            
            # 检查阶梯止盈
            if take_profit_config.ladder_take_profit:
                for profit_level in take_profit_config.ladder_profits:
                    target_price = self._calculate_take_profit_price(position, profit_level)
                    if self._should_trigger_take_profit(position, current_price, target_price):
                        triggers.append({
                            'type': 'ladder_take_profit',
                            'trigger_price': target_price,
                            'current_price': current_price,
                            'profit_level': profit_level,
                            'suggested_action': 'partial_close'
                        })
            
            return triggers
            
        except Exception as e:
            logger.error(f"检查止盈触发失败: {e}", extra={'position_id': position_id})
            raise PositionManagementException(f"检查止盈触发失败: {e}")
    
    async def suggest_position_adjustments(
        self,
        user_id: int,
        account_id: int,
        risk_tolerance: str = "medium"  # low, medium, high
    ) -> List[Dict[str, Any]]:
        """建议仓位调整"""
        try:
            suggestions = []
            
            # 获取投资组合风险
            portfolio_risk = await self.calculate_portfolio_risk(user_id, account_id)
            
            # 获取所有仓位风险指标
            positions = await self.get_user_positions(user_id, account_id)
            
            for position in positions:
                risk_metrics = await self.get_position_risk_metrics(position.id, user_id)
                
                # 高风险仓位建议
                if risk_metrics.risk_level in [PositionRiskLevel.HIGH, PositionRiskLevel.CRITICAL]:
                    suggestions.append({
                        'position_id': position.id,
                        'symbol': position.symbol,
                        'current_risk_level': risk_metrics.risk_level.value,
                        'suggested_action': 'reduce_position',
                        'reason': f'风险等级为{risk_metrics.risk_level.value}',
                        'details': {
                            'unrealized_pnl_percent': float(risk_metrics.unrealized_pnl_percent),
                            'concentration_risk': float(risk_metrics.concentration_risk),
                            'var_95': float(risk_metrics.var_95) if risk_metrics.var_95 else None
                        },
                        'priority': 'high'
                    })
                
                # 集中度风险建议
                if risk_metrics.concentration_risk > 0.3:  # 超过30%
                    suggestions.append({
                        'position_id': position.id,
                        'symbol': position.symbol,
                        'current_risk_level': risk_metrics.risk_level.value,
                        'suggested_action': 'diversify',
                        'reason': '仓位集中度过高',
                        'details': {
                            'concentration_risk': float(risk_metrics.concentration_risk),
                            'recommended_percent': 20.0
                        },
                        'priority': 'medium'
                    })
                
                # 低流动性建议
                if risk_metrics.liquidity_score < 0.5:
                    suggestions.append({
                        'position_id': position.id,
                        'symbol': position.symbol,
                        'current_risk_level': risk_metrics.risk_level.value,
                        'suggested_action': 'monitor_closely',
                        'reason': '流动性较差',
                        'details': {
                            'liquidity_score': risk_metrics.liquidity_score
                        },
                        'priority': 'medium'
                    })
            
            # 投资组合整体建议
            if portfolio_risk['portfolio_risk_level'] == PositionRiskLevel.HIGH:
                suggestions.append({
                    'position_id': None,
                    'symbol': 'PORTFOLIO',
                    'current_risk_level': portfolio_risk['portfolio_risk_level'].value,
                    'suggested_action': 'portfolio_rebalance',
                    'reason': '投资组合整体风险偏高',
                    'details': portfolio_risk['risk_metrics'],
                    'priority': 'high'
                })
            
            # 按优先级排序
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            suggestions.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"生成仓位调整建议失败: {e}", extra={'user_id': user_id})
            raise PositionManagementException(f"生成调整建议失败: {e}")
    
    async def create_risk_alerts(self, user_id: int, account_id: int) -> List[Dict[str, Any]]:
        """创建风险警告"""
        try:
            alerts_created = []
            
            # 获取所有仓位
            positions = await self.get_user_positions(user_id, account_id)
            
            for position in positions:
                risk_metrics = await self.get_position_risk_metrics(position.id, user_id)
                
                # 检查各种风险条件
                if risk_metrics.risk_level == PositionRiskLevel.CRITICAL:
                    alert = await self._create_risk_alert(
                        user_id=user_id,
                        account_id=account_id,
                        position_id=position.id,
                        symbol=position.symbol,
                        severity="CRITICAL",
                        message=f"仓位 {position.symbol} 风险等级为严重",
                        alert_type="position_risk_critical",
                        details={
                            'risk_level': risk_metrics.risk_level.value,
                            'unrealized_pnl': float(risk_metrics.unrealized_pnl),
                            'unrealized_pnl_percent': float(risk_metrics.unrealized_pnl_percent),
                            'concentration_risk': float(risk_metrics.concentration_risk)
                        }
                    )
                    alerts_created.append(alert)
                
                elif risk_metrics.risk_level == PositionRiskLevel.HIGH:
                    alert = await self._create_risk_alert(
                        user_id=user_id,
                        account_id=account_id,
                        position_id=position.id,
                        symbol=position.symbol,
                        severity="WARNING",
                        message=f"仓位 {position.symbol} 风险等级为高",
                        alert_type="position_risk_high",
                        details={
                            'risk_level': risk_metrics.risk_level.value,
                            'unrealized_pnl_percent': float(risk_metrics.unrealized_pnl_percent),
                            'concentration_risk': float(risk_metrics.concentration_risk)
                        }
                    )
                    alerts_created.append(alert)
                
                # 检查集中度风险
                if risk_metrics.concentration_risk > 0.5:  # 超过50%
                    alert = await self._create_risk_alert(
                        user_id=user_id,
                        account_id=account_id,
                        position_id=position.id,
                        symbol=position.symbol,
                        severity="WARNING",
                        message=f"仓位 {position.symbol} 集中度风险过高",
                        alert_type="concentration_risk_high",
                        details={
                            'concentration_risk': float(risk_metrics.concentration_risk),
                            'recommended_limit': 0.3
                        }
                    )
                    alerts_created.append(alert)
            
            return alerts_created
            
        except Exception as e:
            logger.error(f"创建风险警告失败: {e}", extra={'user_id': user_id})
            raise PositionManagementException(f"创建风险警告失败: {e}")
    
    def _calculate_unrealized_pnl(self, position: Position, current_price: Decimal) -> Decimal:
        """计算未实现盈亏"""
        if position.quantity == 0:
            return Decimal('0')
        
        if position.quantity > 0:  # 多仓
            return (current_price - position.avg_price) * position.quantity
        else:  # 空仓
            return (position.avg_price - current_price) * abs(position.quantity)
    
    def _calculate_unrealized_pnl_percent(self, position: Position, current_price: Decimal) -> Decimal:
        """计算未实现盈亏百分比"""
        if position.avg_price == 0:
            return Decimal('0')
        
        unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
        cost_basis = abs(position.quantity) * position.avg_price
        
        if cost_basis == 0:
            return Decimal('0')
        
        return (unrealized_pnl / cost_basis) * 100
    
    async def _get_position_by_id(self, position_id: int, user_id: int) -> Optional[Position]:
        """根据ID获取仓位"""
        query = select(Position).join(Account).where(
            and_(
                Position.id == position_id,
                Account.user_id == user_id,
                Position.is_active == True
            )
        )
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_current_price(self, symbol: str, account_id: int) -> Optional[Decimal]:
        """获取当前价格"""
        query = select(MarketData).where(
            and_(
                MarketData.symbol == symbol,
                MarketData.account_id == account_id
            )
        ).order_by(desc(MarketData.timestamp)).limit(1)
        
        result = await self.db_session.execute(query)
        market_data = result.scalar_one_or_none()
        
        return Decimal(str(market_data.current_price)) if market_data else None
    
    async def _get_price_history(self, symbol: str, days: int) -> List[Decimal]:
        """获取历史价格数据"""
        since = datetime.now() - timedelta(days=days)
        
        query = select(MarketData.current_price).where(
            and_(
                MarketData.symbol == symbol,
                MarketData.timestamp >= since
            )
        ).order_by(MarketData.timestamp)
        
        result = await self.db_session.execute(query)
        prices = result.scalars().all()
        
        return [Decimal(str(price)) for price in prices]
    
    def _calculate_max_drawdown(self, price_history: List[Decimal], entry_price: Decimal) -> Decimal:
        """计算最大回撤"""
        if not price_history:
            return Decimal('0')
        
        max_drawdown = Decimal('0')
        peak = entry_price
        
        for price in price_history:
            if price > peak:
                peak = price
            
            drawdown = (peak - price) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown * 100
    
    def _calculate_var_95(self, price_history: List[Decimal]) -> Optional[Decimal]:
        """计算95% VaR"""
        if len(price_history) < 2:
            return None
        
        # 计算收益率
        returns = []
        for i in range(1, len(price_history)):
            daily_return = (price_history[i] - price_history[i-1]) / price_history[i-1]
            returns.append(daily_return)
        
        if not returns:
            return None
        
        # 排序并取5%分位数
        returns.sort()
        var_index = int(len(returns) * 0.05)
        var_95 = returns[var_index] if var_index < len(returns) else returns[0]
        
        return abs(var_95) * 100
    
    def _calculate_expected_shortfall(self, price_history: List[Decimal]) -> Optional[Decimal]:
        """计算期望损失(CVaR)"""
        if len(price_history) < 2:
            return None
        
        # 计算收益率
        returns = []
        for i in range(1, len(price_history)):
            daily_return = (price_history[i] - price_history[i-1]) / price_history[i-1]
            returns.append(daily_return)
        
        if not returns:
            return None
        
        # 排序并计算5%尾部平均损失
        returns.sort()
        tail_size = int(len(returns) * 0.05)
        if tail_size == 0:
            return Decimal('0')
        
        tail_losses = returns[:tail_size]
        expected_shortfall = sum(abs(loss) for loss in tail_losses) / tail_size
        
        return expected_shortfall * 100
    
    def _calculate_sharpe_ratio(self, price_history: List[Decimal]) -> Optional[float]:
        """计算夏普比率"""
        if len(price_history) < 2:
            return None
        
        # 计算收益率
        returns = []
        for i in range(1, len(price_history)):
            daily_return = (price_history[i] - price_history[i-1]) / price_history[i-1]
            returns.append(daily_return)
        
        if not returns:
            return None
        
        if len(returns) < 2:
            return 0.0
        
        # 计算平均收益率和标准差
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # 年化夏普比率（假设252个交易日）
        sharpe_ratio = (mean_return / std_return) * (252 ** 0.5)
        
        return round(sharpe_ratio, 4)
    
    async def _calculate_concentration_risk(self, user_id: int, account_id: int, symbol: str) -> float:
        """计算单个仓位的集中度风险"""
        try:
            # 获取所有仓位
            positions = await self.get_user_positions(user_id, account_id)
            
            if not positions:
                return 0.0
            
            # 计算总持仓价值
            total_value = Decimal('0')
            symbol_value = Decimal('0')
            
            for position in positions:
                current_price = await self._get_current_price(position.symbol, account_id)
                if current_price:
                    position_value = abs(position.quantity) * current_price
                    total_value += position_value
                    
                    if position.symbol == symbol:
                        symbol_value = position_value
            
            if total_value == 0:
                return 0.0
            
            concentration = float(symbol_value / total_value)
            return min(concentration, 1.0)
            
        except Exception as e:
            logger.error(f"计算集中度风险失败: {e}")
            return 0.0
    
    async def _calculate_liquidity_score(self, symbol: str) -> float:
        """计算流动性分数"""
        try:
            # 获取最近的市场数据
            since = datetime.now() - timedelta(days=1)
            
            query = select(MarketData.volume_24h).where(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.timestamp >= since
                )
            ).order_by(desc(MarketData.timestamp)).limit(1)
            
            result = await self.db_session.execute(query)
            volume = result.scalar()
            
            if not volume:
                return 0.5  # 默认中等流动性
            
            # 基于交易量计算流动性分数（归一化）
            volume_score = min(float(volume) / 1000000, 1.0)  # 假设100万为满分
            
            return volume_score
            
        except Exception as e:
            logger.error(f"计算流动性分数失败: {e}")
            return 0.5
    
    def _determine_risk_level(
        self,
        position: Position,
        unrealized_pnl_percent: Decimal,
        concentration_risk: float,
        var_95: Optional[Decimal]
    ) -> PositionRiskLevel:
        """确定风险等级"""
        risk_score = 0
        
        # 基于盈亏百分比评分
        pnl_percent = abs(unrealized_pnl_percent)
        if pnl_percent > 30:
            risk_score += 3
        elif pnl_percent > 20:
            risk_score += 2
        elif pnl_percent > 10:
            risk_score += 1
        
        # 基于集中度评分
        if concentration_risk > 0.5:
            risk_score += 3
        elif concentration_risk > 0.3:
            risk_score += 2
        elif concentration_risk > 0.2:
            risk_score += 1
        
        # 基于VaR评分
        if var_95 and var_95 > 15:
            risk_score += 3
        elif var_95 and var_95 > 10:
            risk_score += 2
        elif var_95 and var_95 > 5:
            risk_score += 1
        
        # 确定风险等级
        if risk_score >= 6:
            return PositionRiskLevel.CRITICAL
        elif risk_score >= 4:
            return PositionRiskLevel.HIGH
        elif risk_score >= 2:
            return PositionRiskLevel.MEDIUM
        else:
            return PositionRiskLevel.LOW
    
    async def _calculate_portfolio_risk_level(
        self,
        user_id: int,
        account_id: int,
        market_data: Dict[str, Any]
    ) -> PositionRiskLevel:
        """计算投资组合风险等级"""
        if not market_data:
            return PositionRiskLevel.LOW
        
        total_positions = len(market_data)
        risk_scores = []
        
        for symbol, data in market_data.items():
            # 获取仓位风险指标
            positions = await self.get_user_positions(user_id, account_id, symbol)
            if positions:
                position = positions[0]
                risk_metrics = await self.get_position_risk_metrics(position.id, user_id)
                
                # 转换风险等级为数值
                level_scores = {
                    PositionRiskLevel.LOW: 1,
                    PositionRiskLevel.MEDIUM: 2,
                    PositionRiskLevel.HIGH: 3,
                    PositionRiskLevel.CRITICAL: 4
                }
                risk_scores.append(level_scores.get(risk_metrics.risk_level, 2))
        
        if not risk_scores:
            return PositionRiskLevel.LOW
        
        # 计算加权平均风险分数
        avg_risk_score = statistics.mean(risk_scores)
        
        if avg_risk_score >= 3.5:
            return PositionRiskLevel.CRITICAL
        elif avg_risk_score >= 2.5:
            return PositionRiskLevel.HIGH
        elif avg_risk_score >= 1.5:
            return PositionRiskLevel.MEDIUM
        else:
            return PositionRiskLevel.LOW
    
    async def _calculate_correlation_risk(self, positions: List[Position]) -> float:
        """计算相关性风险"""
        # 简化实现：假设相同市场的币种有较高相关性
        if len(positions) < 2:
            return 0.0
        
        # 按市场类型分组
        market_groups = {}
        for position in positions:
            market_type = position.market_type.value
            if market_type not in market_groups:
                market_groups[market_type] = 0
            market_groups[market_type] += 1
        
        # 计算市场集中度
        total_positions = len(positions)
        max_group_size = max(market_groups.values()) if market_groups else 0
        
        concentration = max_group_size / total_positions if total_positions > 0 else 0
        
        return concentration
    
    async def _calculate_portfolio_var(self, market_data: Dict[str, Any]) -> Optional[Decimal]:
        """计算投资组合VaR"""
        if not market_data:
            return None
        
        # 简化实现：假设所有资产的相关性为中等水平
        # 实际应该计算实际相关性
        total_var = Decimal('0')
        total_value = Decimal('0')
        
        for symbol, data in market_data.items():
            position_value = data['position_value']
            total_value += position_value
            
            # 简化的VaR计算（假设每个资产Var为10%）
            var_contribution = position_value * Decimal('0.10')
            total_var += var_contribution ** 2  # 方差加法
        
        # 取平方根得到标准差，然后乘以1.65得到95%VaR
        portfolio_std = total_var ** Decimal('0.5')
        portfolio_var = portfolio_std * Decimal('1.65')
        
        return portfolio_var
    
    async def _calculate_portfolio_max_drawdown(self, user_id: int, account_id: int) -> Decimal:
        """计算投资组合最大回撤"""
        # 简化实现：基于最近的市场数据
        try:
            # 获取最近30天的数据
            since = datetime.now() - timedelta(days=30)
            
            # 获取所有币种的价格数据
            symbols = await self._get_user_symbols(user_id, account_id)
            
            if not symbols:
                return Decimal('0')
            
            # 计算每个币种的回撤
            max_drawdowns = []
            for symbol in symbols:
                query = select(MarketData.current_price).where(
                    and_(
                        MarketData.symbol == symbol,
                        MarketData.account_id == account_id,
                        MarketData.timestamp >= since
                    )
                ).order_by(MarketData.timestamp)
                
                result = await self.db_session.execute(query)
                prices = result.scalars().all()
                
                if len(prices) > 1:
                    price_list = [Decimal(str(price)) for price in prices]
                    max_drawdown = self._calculate_max_drawdown(price_list, price_list[0])
                    max_drawdowns.append(max_drawdown)
            
            if not max_drawdowns:
                return Decimal('0')
            
            # 返回平均最大回撤
            return Decimal(str(statistics.mean(max_drawdowns)))
            
        except Exception as e:
            logger.error(f"计算投资组合最大回撤失败: {e}")
            return Decimal('0')
    
    async def _calculate_portfolio_sharpe_ratio(self, market_data: Dict[str, Any]) -> Optional[float]:
        """计算投资组合夏普比率"""
        # 简化实现：基于各资产夏普比率的加权平均
        if not market_data:
            return None
        
        # 这里应该获取实际的夏普比率数据
        # 简化返回中等夏普比率
        return 1.2
    
    async def _calculate_total_concentration_risk(self, market_data: Dict[str, Any], total_value: Decimal) -> float:
        """计算总集中度风险"""
        if total_value == 0:
            return 0.0
        
        # 计算HHI（赫芬达尔-赫尔曼指数）
        hhi = Decimal('0')
        
        for symbol, data in market_data.items():
            weight = data['position_value'] / total_value
            hhi += weight ** 2
        
        # HHI越高，集中度风险越大
        concentration = float(hhi)
        return min(concentration, 1.0)
    
    async def _calculate_risk_breakdown(self, positions: List[Position]) -> Dict[str, Any]:
        """计算风险分解"""
        breakdown = {
            'by_market_type': {},
            'by_risk_level': {},
            'by_symbol': {}
        }
        
        # 按市场类型分组
        for position in positions:
            market_type = position.market_type.value
            if market_type not in breakdown['by_market_type']:
                breakdown['by_market_type'][market_type] = 0
            breakdown['by_market_type'][market_type] += 1
        
        return breakdown
    
    async def _calculate_margin_usage(self, position: Position) -> Optional[Decimal]:
        """计算保证金使用率"""
        if position.market_type != MarketType.FUTURES:
            return None
        
        # 简化实现：假设保证金率为10%
        position_value = abs(position.quantity) * position.avg_price
        required_margin = position_value * Decimal('0.1')  # 10%保证金
        
        # 这里应该获取实际可用保证金
        available_margin = Decimal('10000')  # 假设可用保证金
        
        if available_margin > 0:
            return (required_margin / available_margin) * 100
        
        return None
    
    async def _calculate_maintenance_margin(self, position: Position) -> Optional[Decimal]:
        """计算维持保证金"""
        if position.market_type != MarketType.FUTURES:
            return None
        
        # 简化实现：假设维持保证金率为5%
        position_value = abs(position.quantity) * position.avg_price
        maintenance_margin = position_value * Decimal('0.05')  # 5%维持保证金
        
        return maintenance_margin
    
    def _calculate_stop_price(self, position: Position, stop_percent: Decimal) -> Decimal:
        """计算止损价格"""
        if position.quantity > 0:  # 多仓
            return position.avg_price * (1 - stop_percent / 100)
        else:  # 空仓
            return position.avg_price * (1 + stop_percent / 100)
    
    def _should_trigger_stop_loss(
        self,
        position: Position,
        current_price: Decimal,
        stop_price: Decimal
    ) -> bool:
        """判断是否触发止损"""
        if position.quantity > 0:  # 多仓
            return current_price <= stop_price
        else:  # 空仓
            return current_price >= stop_price
    
    async def _calculate_trailing_stop_price(self, position: Position, trailing_distance: Decimal) -> Decimal:
        """计算跟踪止损价格"""
        # 这里需要获取历史最高价/最低价
        # 简化实现：使用入场价格
        return self._calculate_stop_price(position, trailing_distance)
    
    def _should_trigger_trailing_stop(
        self,
        position: Position,
        current_price: Decimal,
        trailing_stop_price: Decimal
    ) -> bool:
        """判断是否触发跟踪止损"""
        return self._should_trigger_stop_loss(position, current_price, trailing_stop_price)
    
    def _calculate_take_profit_price(self, position: Position, profit_percent: Decimal) -> Decimal:
        """计算止盈价格"""
        if position.quantity > 0:  # 多仓
            return position.avg_price * (1 + profit_percent / 100)
        else:  # 空仓
            return position.avg_price * (1 - profit_percent / 100)
    
    def _should_trigger_take_profit(
        self,
        position: Position,
        current_price: Decimal,
        target_price: Decimal
    ) -> bool:
        """判断是否触发止盈"""
        if position.quantity > 0:  # 多仓
            return current_price >= target_price
        else:  # 空仓
            return current_price <= target_price
    
    async def _get_stop_loss_config(self, position_id: int) -> StopLossConfig:
        """获取止损配置"""
        # 这里应该从数据库或配置中获取
        # 简化返回默认配置
        return StopLossConfig(
            enabled=True,
            stop_loss_percent=Decimal('5.0'),
            trailing_stop=False,
            emergency_stop=False
        )
    
    async def _get_take_profit_config(self, position_id: int) -> TakeProfitConfig:
        """获取止盈配置"""
        # 这里应该从数据库或配置中获取
        # 简化返回默认配置
        return TakeProfitConfig(
            enabled=True,
            take_profit_percent=Decimal('10.0'),
            partial_close=False
        )
    
    async def _create_risk_alert(
        self,
        user_id: int,
        account_id: int,
        position_id: Optional[int],
        symbol: str,
        severity: str,
        message: str,
        alert_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建风险警告"""
        # 这里应该调用风险检查器创建警告
        alert_data = {
            'user_id': user_id,
            'account_id': account_id,
            'position_id': position_id,
            'symbol': symbol,
            'severity': severity,
            'message': message,
            'alert_type': alert_type,
            'details': details,
            'timestamp': datetime.now()
        }
        
        logger.warning(f"创建风险警告: {message}", extra=alert_data)
        
        return alert_data
    
    async def _get_user_symbols(self, user_id: int, account_id: int) -> List[str]:
        """获取用户交易的所有币种"""
        query = select(Position.symbol).join(Account).where(
            and_(
                Account.user_id == user_id,
                Position.account_id == account_id,
                Position.is_active == True
            )
        ).distinct()
        
        result = await self.db_session.execute(query)
        return result.scalars().all()