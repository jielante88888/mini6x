"""
现货马丁格尔交易策略
基于亏损加倍理论的交易策略，每次亏损后增加仓位，盈利后回到基础仓位
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from ..base import (
    BaseSpotStrategy, MarketData, OrderRequest, OrderResult, OrderType, 
    OrderSide, StrategyType, StrategyStatus, ValidationException
)


logger = logging.getLogger(__name__)


@dataclass
class MartingaleStep:
    """马丁格尔步骤记录"""
    step_id: str
    order_side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    is_winning_step: bool = False
    profit_loss: Decimal = Decimal('0')
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    order_id: Optional[str] = None
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValidationException("仓位数量必须大于0")
        if self.entry_price <= 0:
            raise ValidationException("入场价格必须大于0")
    
    def calculate_profit_loss(self, exit_price: Decimal) -> Decimal:
        """计算盈亏"""
        if self.order_side == OrderSide.BUY:
            return (exit_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - exit_price) * self.quantity


class MartingaleStrategy(BaseSpotStrategy):
    """马丁格尔交易策略"""
    
    def __init__(self, config, order_manager=None):
        super().__init__(config, order_manager)
        
        # 马丁格尔配置
        self.current_step: int = 0
        self.consecutive_losses: int = 0
        self.steps_history: List[MartingaleStep] = []
        
        # 仓位管理
        self.current_position: Decimal = Decimal('0')
        self.average_entry_price: Decimal = Decimal('0')
        self.total_invested: Decimal = Decimal('0')
        self.total_realized_pnl: Decimal = Decimal('0')
        
        # 策略方向
        self.trend_direction: Optional[OrderSide] = None  # None表示自适应方向
        self.last_direction: Optional[OrderSide] = None
        
        # 风险控制
        self.max_consecutive_losses: int = 10
        self.max_total_invested: Optional[Decimal] = None
        self.profit_target_reached: bool = False
        
        # 运行状态
        self.is_in_position: bool = False
        self.last_trade_time: Optional[datetime] = None
        self.cooldown_period: int = 60  # 秒
        
        # 配置验证
        if self.config.strategy_type != StrategyType.MARTINGALE:
            raise ValidationException("MartingaleStrategy需要MARTINGALE策略类型")
        
        if self.config.max_martingale_steps <= 0:
            raise ValidationException("最大马丁格尔步数必须大于0")
    
    async def _initialize_specific(self):
        """初始化马丁格尔策略特定功能"""
        try:
            # 验证马丁格尔配置
            if not self.config.martingale_multiplier or self.config.martingale_multiplier <= Decimal('1.0'):
                raise ValidationException("马丁格尔倍数必须大于1")
            
            if self.config.max_martingale_steps > 20:  # 限制最大步数
                raise ValidationException("最大马丁格尔步数不能超过20")
            
            # 计算最大总投资
            if not self.max_total_invested:
                self.max_total_invested = self.config.base_quantity * \
                    sum(Decimal(str(self.config.martingale_multiplier ** i)) 
                        for i in range(self.config.max_martingale_steps + 1))
            
            self.logger.info(f"初始化马丁格尔策略: 倍数{self.config.martingale_multiplier}, "
                           f"最大步数{self.config.max_martingale_steps}, "
                           f"最大投资{self.max_total_invested}")
            
        except Exception as e:
            self.logger.error(f"马丁格尔策略初始化失败: {e}")
            raise
    
    async def _start_specific(self):
        """启动马丁格尔策略特定功能"""
        # 启动时重置状态
        self.current_step = 0
        self.consecutive_losses = 0
        self.is_in_position = False
        self.profit_target_reached = False
        
        self.logger.info("马丁格尔策略启动")
    
    async def _pause_specific(self):
        """暂停马丁格尔策略特定功能"""
        # 暂停时取消当前挂单
        if self.is_in_position:
            # 这里应该取消挂单
            pass
    
    async def _resume_specific(self):
        """恢复马丁格尔策略特定功能"""
        # 恢复时检查是否需要重新进入市场
        if not self.is_in_position and self._should_enter_market():
            await self._start_new_martingale_cycle()
    
    async def _stop_specific(self):
        """停止马丁格尔策略特定功能"""
        # 停止时平仓
        if self.is_in_position:
            # 这里应该执行平仓操作
            pass
        
        # 重置状态
        self.reset_strategy()
    
    def reset_strategy(self):
        """重置策略状态"""
        self.current_step = 0
        self.consecutive_losses = 0
        self.steps_history.clear()
        self.current_position = Decimal('0')
        self.average_entry_price = Decimal('0')
        self.total_invested = Decimal('0')
        self.is_in_position = False
        self.profit_target_reached = False
        
        self.logger.info("马丁格尔策略状态已重置")
    
    async def get_next_orders(self, market_data: MarketData) -> List[OrderRequest]:
        """获取马丁格尔订单"""
        if not self.is_in_position:
            return []
        
        try:
            orders = []
            
            # 检查是否需要平仓
            if self._should_close_position(market_data):
                close_order = self._create_close_order(market_data)
                if close_order:
                    orders.append(close_order)
            
            # 检查是否需要启动新的马丁格尔周期
            elif self._should_start_new_cycle(market_data):
                new_cycle_orders = await self._start_new_martingale_cycle(market_data)
                orders.extend(new_cycle_orders)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取马丁格尔订单失败: {e}")
            return []
    
    async def process_order_result(self, order_result: OrderResult) -> bool:
        """处理马丁格尔订单执行结果"""
        try:
            self.update_state_after_order(order_result)
            
            if not order_result.success:
                self.logger.warning(f"马丁格尔订单执行失败: {order_result.error_message}")
                return False
            
            # 查找对应的马丁格尔步骤
            martingale_step = self._find_martingale_step_by_order_id(order_result.order_id)
            if not martingale_step:
                self.logger.warning(f"找不到对应的马丁格尔步骤: {order_result.order_id}")
                return False
            
            # 更新马丁格尔步骤
            martingale_step.closed_at = datetime.now()
            
            # 计算盈亏
            current_price = self.last_market_data.current_price if self.last_market_data else order_result.average_price
            profit_loss = martingale_step.calculate_profit_loss(current_price)
            martingale_step.profit_loss = profit_loss
            martingale_step.is_winning_step = profit_loss > 0
            
            # 更新策略状态
            await self._update_martingale_state(martingale_step, order_result, profit_loss)
            
            # 检查是否达到盈利目标
            if self.state.total_profit >= self.config.profit_target:
                self.profit_target_reached = True
                self.logger.info(f"达到盈利目标: {self.state.total_profit}")
            
            self.logger.info(f"马丁格尔步骤执行完成: {martingale_step.step_id}, "
                           f"盈亏: {profit_loss}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理马丁格尔订单结果失败: {e}")
            return False
    
    def _should_close_position(self, market_data: MarketData) -> bool:
        """检查是否应该平仓"""
        if not self.is_in_position or not self.current_position:
            return False
        
        # 检查止损条件
        if self.state.should_stop_loss():
            return True
        
        # 检查盈利条件
        if self.current_position > 0:  # 多头仓位
            current_pnl = (market_data.current_price - self.average_entry_price) * self.current_position
            if current_pnl >= self.config.profit_target:
                return True
        else:  # 空头仓位
            current_pnl = (self.average_entry_price - market_data.current_price) * abs(self.current_position)
            if current_pnl >= self.config.profit_target:
                return True
        
        return False
    
    def _should_start_new_cycle(self, market_data: MarketData) -> bool:
        """检查是否应该启动新的马丁格尔周期"""
        # 检查冷却期
        if self.last_trade_time:
            time_since_last = (datetime.now() - self.last_trade_time).total_seconds()
            if time_since_last < self.cooldown_period:
                return False
        
        # 检查是否已达到最大连续亏损
        if self.consecutive_losses >= self.config.max_martingale_steps:
            return False
        
        # 检查总投资限制
        if self.total_invested >= self.max_total_invested:
            return False
        
        # 检查是否盈利目标已达成
        if self.profit_target_reached:
            return False
        
        return True
    
    def _should_enter_market(self) -> bool:
        """检查是否应该进入市场"""
        return not self.is_in_position and len([step for step in self.steps_history 
                                              if not step.closed_at]) == 0
    
    def _create_close_order(self, market_data: MarketData) -> Optional[OrderRequest]:
        """创建平仓订单"""
        if abs(self.current_position) < Decimal('0.0001'):  # 仓位太小，不需要平仓
            return None
        
        # 确定平仓方向
        if self.current_position > 0:
            close_side = OrderSide.SELL
        else:
            close_side = OrderSide.BUY
        
        close_order = OrderRequest(
            order_id=f"martingale_close_{int(datetime.now().timestamp())}",
            symbol=self.config.symbol,
            order_type=OrderType.MARKET,  # 平仓使用市价单
            order_side=close_side,
            quantity=abs(self.current_position),
            metadata={
                'strategy_type': 'martingale',
                'action': 'close_position',
                'average_price': str(self.average_entry_price),
                'current_step': self.current_step
            }
        )
        
        return close_order
    
    async def _start_new_martingale_cycle(self, market_data: Optional[MarketData] = None) -> List[OrderRequest]:
        """启动新的马丁格尔周期"""
        try:
            if not market_data:
                return []
            
            # 计算本次仓位大小
            quantity = self._calculate_martingale_quantity()
            
            # 确定交易方向
            if self.trend_direction:
                # 固定方向
                order_side = self.trend_direction
            else:
                # 自适应方向
                order_side = self._determine_trade_direction(market_data)
            
            # 计算订单价格
            if order_side == OrderSide.BUY:
                price = market_data.bid_price
            else:
                price = market_data.ask_price
            
            # 创建马丁格尔步骤
            step = MartingaleStep(
                step_id=f"step_{self.current_step}_{int(datetime.now().timestamp())}",
                order_side=order_side,
                quantity=quantity,
                entry_price=price
            )
            
            # 创建订单
            order_request = OrderRequest(
                order_id=f"martingale_entry_{int(datetime.now().timestamp())}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=order_side,
                quantity=quantity,
                price=price,
                metadata={
                    'strategy_type': 'martingale',
                    'action': 'entry',
                    'step_id': step.step_id,
                    'current_step': self.current_step,
                    'martingale_multiplier': str(self.config.martingale_multiplier)
                }
            )
            
            step.order_id = order_request.order_id
            self.steps_history.append(step)
            self.last_direction = order_side
            self.last_trade_time = datetime.now()
            
            self.logger.info(f"启动马丁格尔步骤 {self.current_step}: {order_side.value} {quantity}@{price}")
            
            return [order_request]
            
        except Exception as e:
            self.logger.error(f"启动马丁格尔周期失败: {e}")
            return []
    
    def _calculate_martingale_quantity(self) -> Decimal:
        """计算马丁格尔仓位大小"""
        # 基础公式: base_quantity * multiplier^current_step
        multiplier_factor = Decimal(str(self.config.martingale_multiplier ** self.current_step))
        quantity = self.config.base_quantity * multiplier_factor
        
        # 确保在订单大小限制内
        quantity = max(self.config.min_order_size, 
                      min(quantity, self.config.max_order_size))
        
        return quantity
    
    def _determine_trade_direction(self, market_data: MarketData) -> OrderSide:
        """确定交易方向（自适应）"""
        # 简单的趋势判断逻辑
        # 这里可以集成更复杂的技术指标判断
        
        if not self.last_market_data:
            # 第一次交易，随机或默认买入
            return OrderSide.BUY
        
        # 基于价格变化趋势
        price_change = (market_data.current_price - self.last_market_data.current_price) / self.last_market_data.current_price
        
        if price_change > Decimal('0.001'):  # 价格上涨0.1%
            return OrderSide.BUY  # 追涨
        elif price_change < Decimal('-0.001'):  # 价格下跌0.1%
            return OrderSide.SELL  # 追跌
        else:
            # 横盘，继续当前方向或默认为买入
            return self.last_direction or OrderSide.BUY
    
    def _find_martingale_step_by_order_id(self, order_id: str) -> Optional[MartingaleStep]:
        """根据订单ID查找马丁格尔步骤"""
        for step in self.steps_history:
            if step.order_id == order_id:
                return step
        return None
    
    async def _update_martingale_state(self, step: MartingaleStep, order_result: OrderResult, profit_loss: Decimal):
        """更新马丁格尔状态"""
        try:
            # 更新累计盈亏
            self.total_realized_pnl += profit_loss
            self.state.realized_pnl = self.total_realized_pnl
            self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
            
            # 更新连续亏损计数
            if profit_loss < 0:
                self.consecutive_losses += 1
                self.state.consecutive_losses = self.consecutive_losses
            else:
                self.consecutive_losses = 0
                self.state.consecutive_losses = 0
            
            # 更新当前仓位和平均价格
            if step.order_side == OrderSide.BUY:
                if self.current_position >= 0:
                    # 增加多头仓位
                    total_cost = self.average_entry_price * self.current_position + step.entry_price * step.quantity
                    self.current_position += step.quantity
                    self.average_entry_price = total_cost / self.current_position
                else:
                    # 减空头仓位
                    if step.quantity >= abs(self.current_position):
                        # 完全平仓
                        self.current_position = Decimal('0')
                        self.average_entry_price = Decimal('0')
                    else:
                        self.current_position += step.quantity  # 空头减少
                
                self.total_invested += step.quantity
            else:  # SELL
                if self.current_position <= 0:
                    # 增加空头仓位
                    total_cost = self.average_entry_price * abs(self.current_position) + step.entry_price * step.quantity
                    self.current_position -= step.quantity  # 空头增加（负值）
                    self.average_entry_price = total_cost / abs(self.current_position)
                else:
                    # 减多头仓位
                    if step.quantity >= self.current_position:
                        # 完全平仓
                        self.current_position = Decimal('0')
                        self.average_entry_price = Decimal('0')
                    else:
                        self.current_position -= step.quantity
                
                self.total_invested += step.quantity
            
            # 更新持仓状态
            self.is_in_position = abs(self.current_position) > Decimal('0.0001')
            
            # 步骤计数
            self.current_step += 1
            
            # 检查是否需要重置
            if profit_loss > 0 or self.current_step >= self.config.max_martingale_steps:
                self.current_step = 0
                self.logger.info(f"马丁格尔步骤重置，当前盈亏: {profit_loss}")
            
        except Exception as e:
            self.logger.error(f"更新马丁格尔状态失败: {e}")
    
    def get_martingale_status(self) -> Dict[str, Any]:
        """获取马丁格尔策略状态"""
        active_steps = [step for step in self.steps_history if not step.closed_at]
        completed_steps = [step for step in self.steps_history if step.closed_at]
        winning_steps = [step for step in completed_steps if step.is_winning_step]
        
        return {
            'strategy_id': self.config.strategy_id,
            'symbol': self.config.symbol,
            'current_step': self.current_step,
            'consecutive_losses': self.consecutive_losses,
            'max_martingale_steps': self.config.max_martingale_steps,
            'martingale_multiplier': str(self.config.martingale_multiplier),
            'current_position': str(self.current_position),
            'average_entry_price': str(self.average_entry_price),
            'total_invested': str(self.total_invested),
            'total_realized_pnl': str(self.total_realized_pnl),
            'is_in_position': self.is_in_position,
            'trend_direction': self.trend_direction.value if self.trend_direction else 'adaptive',
            'last_direction': self.last_direction.value if self.last_direction else None,
            'active_steps_count': len(active_steps),
            'completed_steps_count': len(completed_steps),
            'winning_steps_count': len(winning_steps),
            'win_rate': len(winning_steps) / max(len(completed_steps), 1),
            'profit_target_reached': self.profit_target_reached,
            'max_total_invested': str(self.max_total_invested),
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取马丁格尔策略性能指标"""
        base_metrics = super().get_performance_metrics()
        
        completed_steps = [step for step in self.steps_history if step.closed_at]
        winning_steps = [step for step in completed_steps if step.is_winning_step]
        total_pnl = sum(step.profit_loss for step in completed_steps)
        
        # 添加马丁格尔特定指标
        martingale_metrics = {
            'current_martingale_step': self.current_step,
            'max_consecutive_losses': self.consecutive_losses,
            'total_martingale_cycles': len(completed_steps) // max(self.config.max_martingale_steps, 1),
            'winning_cycle_rate': len([i for i in range(0, len(completed_steps), self.config.max_martingale_steps) 
                                     if i + self.config.max_martingale_steps <= len(completed_steps) and
                                     sum(completed_steps[j].profit_loss for j in range(i, i + self.config.max_martingale_steps)) > 0]) / 
                                   max(len(completed_steps) // self.config.max_martingale_steps, 1),
            'average_cycle_profit': total_pnl / max(len(completed_steps) // self.config.max_martingale_steps, 1) if completed_steps else 0,
            'capital_efficiency': float(self.state.total_profit / max(self.total_invested, 1)),
            'martingale_risk_score': self._calculate_risk_score()
        }
        
        base_metrics.update(martingale_metrics)
        return base_metrics
    
    def _calculate_risk_score(self) -> float:
        """计算马丁格尔策略风险评分"""
        risk_factors = [
            min(self.consecutive_losses / 10.0, 1.0),  # 连续亏损因子
            min(self.total_invested / max(self.max_total_invested, Decimal('1')), 1.0),  # 资金使用率
            min(self.current_step / float(self.config.max_martingale_steps), 1.0)  # 当前步数比例
        ]
        
        return sum(risk_factors) / len(risk_factors)
    
    def set_trend_direction(self, direction: OrderSide):
        """设置趋势方向（固定方向模式）"""
        self.trend_direction = direction
        self.logger.info(f"设置马丁格尔趋势方向: {direction.value}")
    
    def set_adaptive_mode(self):
        """设置为自适应模式"""
        self.trend_direction = None
        self.logger.info("设置马丁格尔为自适应模式")


# 策略工厂函数
def create_martingale_strategy(config, order_manager=None) -> MartingaleStrategy:
    """创建马丁格尔策略实例"""
    return MartingaleStrategy(config, order_manager)


# 策略配置验证函数
def validate_martingale_config(config) -> bool:
    """验证马丁格尔策略配置"""
    try:
        if config.strategy_type != StrategyType.MARTINGALE:
            return False
        
        if not config.martingale_multiplier or config.martingale_multiplier <= Decimal('1.0'):
            return False
        
        if not config.max_martingale_steps or config.max_martingale_steps <= 0:
            return False
        
        if config.max_martingale_steps > 20:
            return False
        
        return True
        
    except Exception:
        return False