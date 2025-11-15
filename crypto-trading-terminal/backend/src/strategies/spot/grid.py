"""
现货网格交易策略
基于价格区间分层的网格交易策略，在设定的价格范围内自动化买卖操作
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from ..base import (
    BaseSpotStrategy, MarketData, OrderRequest, OrderResult, OrderType, 
    OrderSide, StrategyType, StrategyStatus
)
from ..base import ValidationException


logger = logging.getLogger(__name__)


@dataclass
class GridLevel:
    """网格层级"""
    level_id: str
    price: Decimal
    order_side: OrderSide
    quantity: Decimal
    order_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    profit: Decimal = Decimal('0')
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValidationException("网格价格必须大于0")
        if self.quantity <= 0:
            raise ValidationException("网格数量必须大于0")


class GridStrategy(BaseSpotStrategy):
    """网格交易策略"""
    
    def __init__(self, config, order_manager=None):
        super().__init__(config, order_manager)
        
        # 网格配置
        self.upper_price: Optional[Decimal] = None
        self.lower_price: Optional[Decimal] = None
        self.grid_size: Decimal = Decimal('0')  # 网格大小
        self.grid_levels: List[GridLevel] = []
        
        # 策略状态
        self.center_price: Optional[Decimal] = None
        self.avg_buy_price: Decimal = Decimal('0')
        self.avg_sell_price: Decimal = Decimal('0')
        self.total_buy_quantity: Decimal = Decimal('0')
        self.total_sell_quantity: Decimal = Decimal('0')
        
        # 运行状态
        self.is_initialized: bool = False
        self.last_rebalance_time: Optional[datetime] = None
        
        # 统计信息
        self.completed_cycles: int = 0
        self.total_profit_from_cycles: Decimal = Decimal('0')
        
        # 配置验证
        if self.config.strategy_type != StrategyType.GRID:
            raise ValidationException("GridStrategy需要GRID策略类型")
    
    async def _initialize_specific(self):
        """初始化网格策略特定功能"""
        try:
            # 验证网格配置
            if not self.config.grid_levels or self.config.grid_levels <= 0:
                raise ValidationException("网格层数必须大于0")
            
            if not self.config.grid_spacing or self.config.grid_spacing <= 0:
                raise ValidationException("网格间距必须大于0")
            
            self.logger.info(f"初始化网格策略: {self.config.grid_levels}层, 间距{self.config.grid_spacing}")
            
            # 标记初始化完成
            self.is_initialized = True
            
        except Exception as e:
            self.logger.error(f"网格策略初始化失败: {e}")
            raise
    
    async def _start_specific(self):
        """启动网格策略特定功能"""
        # 网格策略不需要特殊的启动逻辑
        pass
    
    async def _pause_specific(self):
        """暂停网格策略特定功能"""
        # 取消所有挂单
        await self._cancel_all_pending_orders()
    
    async def _resume_specific(self):
        """恢复网格策略特定功能"""
        # 重新建立网格
        if self.last_market_data:
            await self._rebuild_grid(self.last_market_data)
    
    async def _stop_specific(self):
        """停止网格策略特定功能"""
        # 取消所有挂单
        await self._cancel_all_pending_orders()
        self.grid_levels.clear()
    
    async def get_next_orders(self, market_data: MarketData) -> List[OrderRequest]:
        """获取下一批网格订单"""
        if not self.is_initialized:
            return []
        
        try:
            orders = []
            
            # 检查是否需要重新构建网格
            if not self._is_grid_valid(market_data.current_price):
                await self._rebuild_grid(market_data)
            
            # 检查是否有需要补充的网格层级
            missing_levels = self._get_missing_grid_levels(market_data.current_price)
            
            for level in missing_levels:
                order_request = OrderRequest(
                    order_id=f"grid_{level.level_id}_{int(datetime.now().timestamp())}",
                    symbol=self.config.symbol,
                    order_type=OrderType.LIMIT,
                    order_side=level.order_side,
                    quantity=level.quantity,
                    price=level.price,
                    metadata={
                        'strategy_type': 'grid',
                        'grid_level': level.level_id,
                        'original_price': str(level.price)
                    }
                )
                orders.append(order_request)
                level.order_id = order_request.order_id
                self.grid_levels.append(level)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取网格订单失败: {e}")
            return []
    
    async def process_order_result(self, order_result: OrderResult) -> bool:
        """处理网格订单执行结果"""
        try:
            # 更新策略状态
            self.update_state_after_order(order_result)
            
            if not order_result.success:
                self.logger.warning(f"网格订单执行失败: {order_result.error_message}")
                return False
            
            # 查找对应的网格层级
            grid_level = self._find_grid_level_by_order_id(order_result.order_id)
            if not grid_level:
                self.logger.warning(f"找不到对应的网格层级: {order_result.order_id}")
                return False
            
            # 更新网格层级状态
            grid_level.filled_at = datetime.now()
            grid_level.is_active = False
            
            # 计算盈利
            grid_level.profit = self._calculate_grid_profit(grid_level, order_result)
            
            # 更新策略统计
            await self._update_grid_statistics(grid_level, order_result)
            
            # 检查是否完成一个网格循环
            if self._is_grid_cycle_complete():
                await self._complete_grid_cycle()
            
            # 重新构建网格（如果有新价格区间）
            if self.last_market_data:
                await self._rebuild_grid(self.last_market_data)
            
            self.logger.info(f"网格订单执行成功: {order_result.order_id}, 盈利: {grid_level.profit}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理网格订单结果失败: {e}")
            return False
    
    async def _rebuild_grid(self, market_data: MarketData):
        """重新构建网格"""
        try:
            current_price = market_data.current_price
            
            # 计算网格价格区间
            await self._calculate_grid_prices(current_price)
            
            # 清空现有网格
            await self._cancel_all_pending_orders()
            self.grid_levels.clear()
            
            # 生成新的网格层级
            self._generate_grid_levels(current_price)
            
            self.last_rebalance_time = datetime.now()
            
            self.logger.info(f"网格重新构建完成: 区间[{self.lower_price}, {self.upper_price}], "
                           f"当前价格: {current_price}")
            
        except Exception as e:
            self.logger.error(f"重新构建网格失败: {e}")
            raise
    
    async def _calculate_grid_prices(self, current_price: Decimal):
        """计算网格价格区间"""
        # 计算上下价格区间
        grid_range = current_price * self.config.grid_spacing * Decimal(self.config.grid_levels / 2)
        
        self.upper_price = current_price + grid_range
        self.lower_price = current_price - grid_range
        self.center_price = current_price
        
        # 确保价格在有效范围内
        if self.upper_price == self.lower_price:
            raise ValidationException("网格区间计算错误：上下价格相等")
        
        # 计算网格大小
        price_range = self.upper_price - self.lower_price
        self.grid_size = price_range / Decimal(self.config.grid_levels)
        
        self.logger.debug(f"网格价格计算: 中心价{current_price}, 区间[{self.lower_price}, {self.upper_price}], "
                         f"网格大小{self.grid_size}")
    
    def _generate_grid_levels(self, current_price: Decimal):
        """生成网格层级"""
        # 生成所有价格点
        prices = []
        for i in range(self.config.grid_levels + 1):
            price = self.lower_price + (self.grid_size * Decimal(i))
            prices.append(price)
        
        # 为每个价格区间创建订单
        for i in range(len(prices) - 1):
            lower_price = prices[i]
            upper_price = prices[i + 1]
            mid_price = (lower_price + upper_price) / 2
            
            # 决定订单方向（基于当前价格）
            if current_price >= mid_price:
                # 买单在下方
                order_side = OrderSide.BUY
                order_price = mid_price
            else:
                # 卖单在上方
                order_side = OrderSide.SELL
                order_price = mid_price
            
            # 计算订单数量（可以基于网格大小或固定数量）
            quantity = self._calculate_grid_quantity(order_price, order_side)
            
            # 创建网格层级
            level = GridLevel(
                level_id=f"level_{i}",
                price=order_price,
                order_side=order_side,
                quantity=quantity
            )
            
            self.grid_levels.append(level)
        
        self.logger.info(f"生成{len(self.grid_levels)}个网格层级")
    
    def _calculate_grid_quantity(self, price: Decimal, order_side: OrderSide) -> Decimal:
        """计算网格订单数量"""
        # 基于价格和账户余额计算订单数量
        # 这里简化处理，使用固定数量，实际应该考虑账户余额和风险控制
        
        # 可以基于价格范围调整数量
        if self.center_price:
            price_factor = abs(price - self.center_price) / self.center_price
            quantity = self.config.base_quantity * (Decimal('1') + price_factor)
        else:
            quantity = self.config.base_quantity
        
        # 确保在订单大小限制内
        quantity = max(self.config.min_order_size, 
                      min(quantity, self.config.max_order_size))
        
        return quantity
    
    def _is_grid_valid(self, current_price: Decimal) -> bool:
        """检查网格是否仍然有效"""
        if not self.upper_price or not self.lower_price:
            return False
        
        # 检查当前价格是否仍在网格范围内
        if current_price < self.lower_price or current_price > self.upper_price:
            return False
        
        # 检查网格是否需要重新平衡（基于时间或价格变动）
        if self.last_rebalance_time:
            rebalance_interval = timedelta(minutes=30)  # 每30分钟重新平衡
            if datetime.now() - self.last_rebalance_time > rebalance_interval:
                return False
        
        return True
    
    def _get_missing_grid_levels(self, current_price: Decimal) -> List[GridLevel]:
        """获取缺失的网格层级"""
        missing_levels = []
        
        for level in self.grid_levels:
            if level.is_active and not level.order_id:
                missing_levels.append(level)
        
        return missing_levels
    
    def _find_grid_level_by_order_id(self, order_id: str) -> Optional[GridLevel]:
        """根据订单ID查找网格层级"""
        for level in self.grid_levels:
            if level.order_id == order_id:
                return level
        return None
    
    def _calculate_grid_profit(self, grid_level: GridLevel, order_result: OrderResult) -> Decimal:
        """计算网格层级盈利"""
        try:
            if not self.center_price or grid_level.filled_at is None:
                return Decimal('0')
            
            # 简化计算：基于买卖价差和数量
            if grid_level.order_side == OrderSide.SELL:
                # 卖出订单：计算与买入价格的差价
                profit = (order_result.average_price - self.avg_buy_price) * order_result.filled_quantity
            else:
                # 买入订单：记录买入价格
                if self.avg_buy_price == 0:
                    self.avg_buy_price = order_result.average_price
                profit = Decimal('0')
            
            return max(profit, Decimal('0'))  # 确保盈利为正数
            
        except Exception as e:
            self.logger.error(f"计算网格盈利失败: {e}")
            return Decimal('0')
    
    async def _update_grid_statistics(self, grid_level: GridLevel, order_result: OrderResult):
        """更新网格统计信息"""
        try:
            # 更新买卖统计
            if grid_level.order_side == OrderSide.BUY:
                # 更新买入统计
                self.total_buy_quantity += order_result.filled_quantity
                if self.avg_buy_price == 0:
                    self.avg_buy_price = order_result.average_price
                else:
                    # 计算新的平均买入价格
                    total_cost = (self.avg_buy_price * self.total_buy_quantity) + \
                                (order_result.average_price * order_result.filled_quantity)
                    self.total_buy_quantity += order_result.filled_quantity
                    self.avg_buy_price = total_cost / self.total_buy_quantity
            else:
                # 更新卖出统计
                self.total_sell_quantity += order_result.filled_quantity
                if self.avg_sell_price == 0:
                    self.avg_sell_price = order_result.average_price
                else:
                    total_revenue = (self.avg_sell_price * self.total_sell_quantity) + \
                                  (order_result.average_price * order_result.filled_quantity)
                    self.total_sell_quantity += order_result.filled_quantity
                    self.avg_sell_price = total_revenue / self.total_sell_quantity
            
            # 更新策略盈亏
            self.state.realized_pnl += grid_level.profit
            self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
            
        except Exception as e:
            self.logger.error(f"更新网格统计失败: {e}")
    
    def _is_grid_cycle_complete(self) -> bool:
        """检查是否完成一个网格循环"""
        try:
            # 检查是否有等量的买卖订单完成
            active_buy_levels = [level for level in self.grid_levels 
                               if level.order_side == OrderSide.BUY and level.filled_at]
            active_sell_levels = [level for level in self.grid_levels 
                                if level.order_side == OrderSide.SELL and level.filled_at]
            
            # 如果买卖订单数量相等，可能完成一个循环
            if len(active_buy_levels) == len(active_sell_levels) and len(active_buy_levels) > 0:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查网格循环失败: {e}")
            return False
    
    async def _complete_grid_cycle(self):
        """完成网格循环"""
        try:
            self.completed_cycles += 1
            
            # 计算本轮循环盈利
            cycle_profit = self.avg_sell_price * self.total_sell_quantity - \
                          self.avg_buy_price * self.total_buy_quantity
            
            if cycle_profit > 0:
                self.total_profit_from_cycles += cycle_profit
                self.logger.info(f"完成网格循环 #{self.completed_cycles}, 盈利: {cycle_profit}")
            
            # 重置本轮统计
            self.total_buy_quantity = Decimal('0')
            self.total_sell_quantity = Decimal('0')
            self.avg_buy_price = Decimal('0')
            self.avg_sell_price = Decimal('0')
            
            # 清理已完成的层级
            self.grid_levels = [level for level in self.grid_levels if level.is_active]
            
        except Exception as e:
            self.logger.error(f"完成网格循环失败: {e}")
    
    async def _cancel_all_pending_orders(self):
        """取消所有挂单"""
        try:
            if not self.order_manager:
                return
            
            for level in self.grid_levels:
                if level.order_id and level.is_active:
                    # 这里应该调用订单管理器取消订单
                    # await self.order_manager.cancel_order(level.order_id)
                    level.order_id = None
                    self.logger.debug(f"取消网格订单: {level.level_id}")
            
        except Exception as e:
            self.logger.error(f"取消挂单失败: {e}")
    
    def get_grid_status(self) -> Dict[str, Any]:
        """获取网格状态信息"""
        return {
            'strategy_id': self.config.strategy_id,
            'symbol': self.config.symbol,
            'center_price': str(self.center_price) if self.center_price else None,
            'upper_price': str(self.upper_price) if self.upper_price else None,
            'lower_price': str(self.lower_price) if self.lower_price else None,
            'grid_size': str(self.grid_size),
            'total_levels': len(self.grid_levels),
            'active_levels': len([level for level in self.grid_levels if level.is_active]),
            'completed_levels': len([level for level in self.grid_levels if level.filled_at]),
            'completed_cycles': self.completed_cycles,
            'total_profit_from_cycles': str(self.total_profit_from_cycles),
            'avg_buy_price': str(self.avg_buy_price),
            'avg_sell_price': str(self.avg_sell_price),
            'total_buy_quantity': str(self.total_buy_quantity),
            'total_sell_quantity': str(self.total_sell_quantity),
            'last_rebalance': self.last_rebalance_time.isoformat() if self.last_rebalance_time else None,
            'is_initialized': self.is_initialized
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取网格策略性能指标"""
        base_metrics = super().get_performance_metrics()
        
        # 添加网格特定指标
        grid_metrics = {
            'grid_cycles_completed': self.completed_cycles,
            'total_grid_profit': float(self.total_profit_from_cycles),
            'average_cycle_profit': float(self.total_profit_from_cycles / max(self.completed_cycles, 1)),
            'grid_efficiency': len([level for level in self.grid_levels if level.filled_at]) / max(len(self.grid_levels), 1),
            'price_coverage': float((self.upper_price - self.lower_price) / self.center_price) if self.center_price and self.upper_price and self.lower_price else 0,
        }
        
        base_metrics.update(grid_metrics)
        return base_metrics


# 策略工厂函数
def create_grid_strategy(config, order_manager=None) -> GridStrategy:
    """创建网格策略实例"""
    return GridStrategy(config, order_manager)


# 策略配置验证函数
def validate_grid_config(config) -> bool:
    """验证网格策略配置"""
    try:
        if config.strategy_type != StrategyType.GRID:
            return False
        
        if not config.grid_levels or config.grid_levels <= 0:
            return False
        
        if not config.grid_spacing or config.grid_spacing <= 0:
            return False
        
        if config.grid_spacing > Decimal('0.5'):  # 网格间距不能超过50%
            return False
        
        return True
        
    except Exception:
        return False