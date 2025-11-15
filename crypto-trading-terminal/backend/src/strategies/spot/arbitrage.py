"""
现货套利交易策略
基于不同交易所价格差异的套利交易策略，同时在多个交易所进行买卖操作
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..base import (
    BaseSpotStrategy, MarketData, OrderRequest, OrderResult, OrderType, 
    OrderSide, StrategyType, StrategyStatus, ValidationException
)


logger = logging.getLogger(__name__)


class ExchangeName(Enum):
    """交易所名称"""
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"
    HUOBI = "huobi"


@dataclass
class ExchangePrice:
    """交易所价格信息"""
    exchange: ExchangeName
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_quantity: Decimal
    ask_quantity: Decimal
    timestamp: datetime
    fee_rate: Decimal = Decimal('0.001')  # 默认手续费率0.1%
    
    def __post_init__(self):
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise ValidationException("价格必须大于0")
        if self.bid_price > self.ask_price:
            raise ValidationException("买价不能高于卖价")
    
    @property
    def spread(self) -> Decimal:
        """价差"""
        return self.ask_price - self.bid_price
    
    @property
    def spread_percentage(self) -> Decimal:
        """价差百分比"""
        return self.spread / self.bid_price if self.bid_price > 0 else Decimal('0')


@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    opportunity_id: str
    symbol: str
    buy_exchange: ExchangeName
    sell_exchange: ExchangeName
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    potential_profit: Decimal
    profit_percentage: Decimal
    net_profit_after_fees: Decimal
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.buy_price >= self.sell_price:
            raise ValidationException("买入价格必须低于卖出价格")
        if self.quantity <= 0:
            raise ValidationException("套利数量必须大于0")
        if self.potential_profit <= 0:
            raise ValidationException("潜在盈利必须大于0")
    
    @property
    def price_difference(self) -> Decimal:
        """价格差异"""
        return self.sell_price - self.buy_price


@dataclass
class ArbitrageOrder:
    """套利订单对"""
    arbitrage_opportunity_id: str
    buy_order: OrderRequest
    sell_order: OrderRequest
    buy_exchange: ExchangeName
    sell_exchange: ExchangeName
    quantity: Decimal
    expected_profit: Decimal
    created_at: datetime = field(default_factory=datetime.now)
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_result: Optional[OrderResult] = None
    sell_result: Optional[OrderResult] = None
    status: str = "pending"  # pending, executing, completed, failed, cancelled
    completed_at: Optional[datetime] = None
    actual_profit: Decimal = Decimal('0')
    execution_time: Optional[float] = None
    
    def is_completed(self) -> bool:
        """检查是否完成"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """检查是否失败"""
        return self.status == "failed"


class ArbitrageStrategy(BaseSpotStrategy):
    """套利交易策略"""
    
    def __init__(self, config, order_manager=None):
        super().__init__(config, order_manager)
        
        # 套利配置
        self.monitored_exchanges: List[ExchangeName] = []
        self.price_data: Dict[ExchangeName, ExchangePrice] = {}
        self.arbitrage_opportunities: List[ArbitrageOpportunity] = []
        self.active_arbitrage_orders: List[ArbitrageOrder] = []
        
        # 策略参数
        self.min_profit_threshold: Decimal = Decimal('0.005')  # 最小盈利阈值0.5%
        self.max_position_size: Decimal = Decimal('1.0')      # 最大仓位大小
        self.execution_timeout: int = 30                      # 执行超时30秒
        self.opportunity_lifetime: int = 60                   # 机会有效期60秒
        
        # 手续费和成本
        self.withdrawal_fees: Dict[str, Decimal] = {}         # 提现手续费
        self.transfer_times: Dict[str, int] = {}              # 转账时间（秒）
        
        # 统计信息
        self.total_arbitrage_cycles: int = 0
        self.successful_arbitrage_cycles: int = 0
        self.total_arbitrage_profit: Decimal = Decimal('0')
        self.average_execution_time: Decimal = Decimal('0')
        
        # 运行状态
        self.is_monitoring: bool = False
        self.last_market_scan: Optional[datetime] = None
        
        # 配置验证
        if self.config.strategy_type != StrategyType.ARBITRAGE:
            raise ValidationException("ArbitrageStrategy需要ARBITRAGE策略类型")
        
        if self.config.arbitrage_threshold <= 0:
            raise ValidationException("套利阈值必须大于0")
        
        # 设置默认监控的交易所
        self.monitored_exchanges = [ExchangeName.BINANCE, ExchangeName.OKX]
    
    async def _initialize_specific(self):
        """初始化套利策略特定功能"""
        try:
            # 验证套利配置
            if not self.monitored_exchanges or len(self.monitored_exchanges) < 2:
                raise ValidationException("至少需要监控2个交易所")
            
            if self.config.arbitrage_threshold > Decimal('0.1'):  # 10%
                raise ValidationException("套利阈值不能超过10%")
            
            # 初始化手续费和转账时间
            self._initialize_fees_and_times()
            
            self.logger.info(f"初始化套利策略: 监控交易所{len(self.monitored_exchanges)}个, "
                           f"最小盈利阈值{self.min_profit_threshold}")
            
        except Exception as e:
            self.logger.error(f"套利策略初始化失败: {e}")
            raise
    
    async def _start_specific(self):
        """启动套利策略特定功能"""
        self.is_monitoring = True
        self.logger.info("套利策略监控启动")
    
    async def _pause_specific(self):
        """暂停套利策略特定功能"""
        self.is_monitoring = False
        # 取消所有活跃的套利订单
        for arbitrage_order in self.active_arbitrage_orders:
            if arbitrage_order.status == "executing":
                arbitrage_order.status = "cancelled"
    
    async def _resume_specific(self):
        """恢复套利策略特定功能"""
        self.is_monitoring = True
        self.logger.info("套利策略监控恢复")
    
    async def _stop_specific(self):
        """停止套利策略特定功能"""
        self.is_monitoring = False
        # 清理所有订单
        self.active_arbitrage_orders.clear()
        self.arbitrage_opportunities.clear()
    
    def _initialize_fees_and_times(self):
        """初始化手续费和转账时间"""
        # 这里可以配置实际的手续费和转账时间
        # 示例配置
        self.withdrawal_fees = {
            "BTCUSDT": Decimal('0.0005'),
            "ETHUSDT": Decimal('0.01'),
            "BNBUSDT": Decimal('0.01')
        }
        
        self.transfer_times = {
            "BTCUSDT": 60,   # 1分钟
            "ETHUSDT": 30,   # 30秒
            "BNBUSDT": 15    # 15秒
        }
    
    async def get_next_orders(self, market_data: MarketData) -> List[OrderRequest]:
        """获取套利订单"""
        if not self.is_monitoring:
            return []
        
        try:
            orders = []
            
            # 扫描套利机会
            opportunities = await self._scan_arbitrage_opportunities(market_data.symbol)
            
            # 处理有效机会
            for opportunity in opportunities:
                if self._is_profitable_opportunity(opportunity):
                    arbitrage_orders = await self._create_arbitrage_orders(opportunity)
                    orders.extend([arbitrage_orders.buy_order, arbitrage_orders.sell_order])
                    self.active_arbitrage_orders.append(arbitrage_orders)
            
            # 清理过期机会
            await self._cleanup_expired_opportunities()
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取套利订单失败: {e}")
            return []
    
    async def process_order_result(self, order_result: OrderResult) -> bool:
        """处理套利订单执行结果"""
        try:
            self.update_state_after_order(order_result)
            
            # 查找对应的套利订单
            arbitrage_order = self._find_arbitrage_order_by_order_id(order_result.order_id)
            if not arbitrage_order:
                self.logger.warning(f"找不到对应的套利订单: {order_result.order_id}")
                return False
            
            # 更新订单结果
            if order_result.order_id == arbitrage_order.buy_order.order_id:
                arbitrage_order.buy_result = order_result
                arbitrage_order.buy_order_id = order_result.order_id
            else:
                arbitrage_order.sell_result = order_result
                arbitrage_order.sell_order_id = order_result.order_id
            
            # 检查订单是否都完成
            if arbitrage_order.buy_result and arbitrage_order.sell_result:
                await self._complete_arbitrage_cycle(arbitrage_order)
            elif not order_result.success:
                # 订单失败
                arbitrage_order.status = "failed"
                self.logger.warning(f"套利订单执行失败: {order_result.error_message}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"处理套利订单结果失败: {e}")
            return False
    
    async def _scan_arbitrage_opportunities(self, symbol: str) -> List[ArbitrageOpportunity]:
        """扫描套利机会"""
        try:
            opportunities = []
            
            if len(self.price_data) < 2:
                return opportunities
            
            # 获取所有价格数据
            exchange_prices = [price_data for price_data in self.price_data.values() 
                             if price_data.symbol == symbol]
            
            # 比较不同交易所之间的价格
            for i, price1 in enumerate(exchange_prices):
                for price2 in exchange_prices[i+1:]:
                    opportunity = self._calculate_arbitrage_opportunity(price1, price2)
                    if opportunity:
                        opportunities.append(opportunity)
            
            self.arbitrage_opportunities.extend(opportunities)
            self.last_market_scan = datetime.now()
            
            if opportunities:
                self.logger.info(f"发现{len(opportunities)}个套利机会: {symbol}")
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"扫描套利机会失败: {e}")
            return []
    
    def _calculate_arbitrage_opportunity(self, price1: ExchangePrice, price2: ExchangePrice) -> Optional[ArbitrageOpportunity]:
        """计算套利机会"""
        try:
            # 确保是不同的交易所
            if price1.exchange == price2.exchange:
                return None
            
            # 计算套利机会
            # 机会1: price1买入, price2卖出
            if price1.bid_price < price2.ask_price:
                profit = price2.ask_price - price1.bid_price
                profit_percentage = profit / price1.bid_price
                
                opportunity = ArbitrageOpportunity(
                    opportunity_id=f"arb_{int(datetime.now().timestamp())}_{price1.exchange.value}_{price2.exchange.value}",
                    symbol=price1.symbol,
                    buy_exchange=price1.exchange,
                    sell_exchange=price2.exchange,
                    buy_price=price1.bid_price,
                    sell_price=price2.ask_price,
                    quantity=self._calculate_optimal_quantity(price1, price2),
                    potential_profit=profit,
                    profit_percentage=profit_percentage,
                    net_profit_after_fees=self._calculate_net_profit(price1, price2),
                    expires_at=datetime.now() + timedelta(seconds=self.opportunity_lifetime)
                )
                
                return opportunity
            
            # 机会2: price2买入, price1卖出
            if price2.bid_price < price1.ask_price:
                profit = price1.ask_price - price2.bid_price
                profit_percentage = profit / price2.bid_price
                
                opportunity = ArbitrageOpportunity(
                    opportunity_id=f"arb_{int(datetime.now().timestamp())}_{price2.exchange.value}_{price1.exchange.value}",
                    symbol=price1.symbol,
                    buy_exchange=price2.exchange,
                    sell_exchange=price1.exchange,
                    buy_price=price2.bid_price,
                    sell_price=price1.ask_price,
                    quantity=self._calculate_optimal_quantity(price2, price1),
                    potential_profit=profit,
                    profit_percentage=profit_percentage,
                    net_profit_after_fees=self._calculate_net_profit(price2, price1),
                    expires_at=datetime.now() + timedelta(seconds=self.opportunity_lifetime)
                )
                
                return opportunity
            
            return None
            
        except Exception as e:
            self.logger.error(f"计算套利机会失败: {e}")
            return None
    
    def _calculate_optimal_quantity(self, buy_price: ExchangePrice, sell_price: ExchangePrice) -> Decimal:
        """计算最优套利数量"""
        # 基于最小盈利阈值和账户余额计算最优数量
        # 这里简化处理，使用固定比例
        
        min_profit_amount = self.min_profit_threshold * buy_price.bid_price * self.config.base_quantity
        price_diff = sell_price.ask_price - buy_price.bid_price
        
        if price_diff > 0:
            optimal_quantity = min_profit_amount / price_diff
        else:
            optimal_quantity = self.config.base_quantity
        
        # 确保在限制范围内
        quantity = max(self.config.min_order_size, 
                      min(optimal_quantity, self.config.max_order_size))
        
        return quantity
    
    def _calculate_net_profit(self, buy_price: ExchangePrice, sell_price: ExchangePrice) -> Decimal:
        """计算扣除手续费后的净盈利"""
        # 计算毛盈利
        gross_profit = (sell_price.ask_price - buy_price.bid_price) * self.config.base_quantity
        
        # 计算手续费
        buy_fee = buy_price.bid_price * self.config.base_quantity * buy_price.fee_rate
        sell_fee = sell_price.ask_price * self.config.base_quantity * sell_price.fee_rate
        total_fees = buy_fee + sell_fee
        
        # 扣除转账费用（如果需要）
        transfer_fee = self.withdrawal_fees.get(buy_price.symbol, Decimal('0'))
        
        # 净盈利
        net_profit = gross_profit - total_fees - transfer_fee
        
        return max(net_profit, Decimal('0'))
    
    def _is_profitable_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """检查是否是有利可图的套利机会"""
        # 检查净盈利是否超过阈值
        if opportunity.net_profit_after_fees < self.min_profit_threshold:
            return False
        
        # 检查是否超过最大仓位
        if opportunity.quantity > self.max_position_size:
            return False
        
        # 检查是否已过期
        if opportunity.expires_at and datetime.now() > opportunity.expires_at:
            return False
        
        # 检查是否已经执行过相同的机会
        existing_order = self._find_existing_arbitrage_order(opportunity)
        if existing_order:
            return False
        
        return True
    
    def _find_existing_arbitrage_order(self, opportunity: ArbitrageOpportunity) -> Optional[ArbitrageOrder]:
        """查找已存在的套利订单"""
        for order in self.active_arbitrage_orders:
            if (order.buy_exchange == opportunity.buy_exchange and 
                order.sell_exchange == opportunity.sell_exchange and
                order.quantity == opportunity.quantity):
                return order
        return None
    
    async def _create_arbitrage_orders(self, opportunity: ArbitrageOpportunity) -> ArbitrageOrder:
        """创建套利订单对"""
        # 创建买入订单
        buy_order = OrderRequest(
            order_id=f"arb_buy_{int(datetime.now().timestamp())}",
            symbol=opportunity.symbol,
            order_type=OrderType.LIMIT,
            order_side=OrderSide.BUY,
            quantity=opportunity.quantity,
            price=opportunity.buy_price,
            metadata={
                'strategy_type': 'arbitrage',
                'exchange': opportunity.buy_exchange.value,
                'opportunity_id': opportunity.opportunity_id,
                'sell_exchange': opportunity.sell_exchange.value
            }
        )
        
        # 创建卖出订单
        sell_order = OrderRequest(
            order_id=f"arb_sell_{int(datetime.now().timestamp())}",
            symbol=opportunity.symbol,
            order_type=OrderType.LIMIT,
            order_side=OrderSide.SELL,
            quantity=opportunity.quantity,
            price=opportunity.sell_price,
            metadata={
                'strategy_type': 'arbitrage',
                'exchange': opportunity.sell_exchange.value,
                'opportunity_id': opportunity.opportunity_id,
                'buy_exchange': opportunity.buy_exchange.value
            }
        )
        
        arbitrage_order = ArbitrageOrder(
            arbitrage_opportunity_id=opportunity.opportunity_id,
            buy_order=buy_order,
            sell_order=sell_order,
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange,
            quantity=opportunity.quantity,
            expected_profit=opportunity.net_profit_after_fees
        )
        
        return arbitrage_order
    
    def _find_arbitrage_order_by_order_id(self, order_id: str) -> Optional[ArbitrageOrder]:
        """根据订单ID查找套利订单"""
        for order in self.active_arbitrage_orders:
            if (order.buy_order.order_id == order_id or 
                order.sell_order.order_id == order_id):
                return order
        return None
    
    async def _complete_arbitrage_cycle(self, arbitrage_order: ArbitrageOrder):
        """完成套利周期"""
        try:
            arbitrage_order.status = "completed"
            arbitrage_order.completed_at = datetime.now()
            
            # 计算实际盈利
            if arbitrage_order.buy_result and arbitrage_order.sell_result:
                buy_cost = arbitrage_order.buy_result.average_price * arbitrage_order.quantity
                sell_revenue = arbitrage_order.sell_result.average_price * arbitrage_order.quantity
                total_fees = (arbitrage_order.buy_result.commission + 
                            arbitrage_order.sell_result.commission)
                
                arbitrage_order.actual_profit = sell_revenue - buy_cost - total_fees
                
                # 更新统计
                self.total_arbitrage_cycles += 1
                if arbitrage_order.actual_profit > 0:
                    self.successful_arbitrage_cycles += 1
                
                self.total_arbitrage_profit += arbitrage_order.actual_profit
                
                # 计算执行时间
                if arbitrage_order.completed_at and arbitrage_order.created_at:
                    execution_time = (arbitrage_order.completed_at - arbitrage_order.created_at).total_seconds()
                    arbitrage_order.execution_time = execution_time
                    
                    # 更新平均执行时间
                    if self.total_arbitrage_cycles > 0:
                        self.average_execution_time = (
                            (self.average_execution_time * (self.total_arbitrage_cycles - 1) + 
                             Decimal(str(execution_time))) / self.total_arbitrage_cycles
                        )
            
            self.logger.info(f"套利周期完成: {arbitrage_order.arbitrage_opportunity_id}, "
                           f"实际盈利: {arbitrage_order.actual_profit}")
            
        except Exception as e:
            self.logger.error(f"完成套利周期失败: {e}")
            arbitrage_order.status = "failed"
    
    async def _cleanup_expired_opportunities(self):
        """清理过期的套利机会"""
        now = datetime.now()
        
        # 清理过期的机会
        self.arbitrage_opportunities = [
            opp for opp in self.arbitrage_opportunities 
            if not opp.expires_at or opp.expires_at > now
        ]
        
        # 清理失败的订单
        self.active_arbitrage_orders = [
            order for order in self.active_arbitrage_orders 
            if order.status not in ["failed", "cancelled"]
        ]
    
    def update_exchange_price(self, exchange: ExchangeName, price_data: Dict[str, Any]):
        """更新交易所价格数据"""
        try:
            exchange_price = ExchangePrice(
                exchange=exchange,
                symbol=price_data['symbol'],
                bid_price=Decimal(str(price_data['bid_price'])),
                ask_price=Decimal(str(price_data['ask_price'])),
                bid_quantity=Decimal(str(price_data.get('bid_quantity', '0'))),
                ask_quantity=Decimal(str(price_data.get('ask_quantity', '0'))),
                timestamp=datetime.now(),
                fee_rate=Decimal(str(price_data.get('fee_rate', '0.001')))
            )
            
            self.price_data[exchange] = exchange_price
            
        except Exception as e:
            self.logger.error(f"更新交易所价格失败 {exchange.value}: {e}")
    
    def get_arbitrage_status(self) -> Dict[str, Any]:
        """获取套利策略状态"""
        active_opportunities = len(self.arbitrage_opportunities)
        active_orders = len(self.active_arbitrage_orders)
        success_rate = (self.successful_arbitrage_cycles / max(self.total_arbitrage_cycles, 1))
        
        return {
            'strategy_id': self.config.strategy_id,
            'monitored_exchanges': [ex.value for ex in self.monitored_exchanges],
            'total_exchanges_monitored': len(self.monitored_exchanges),
            'price_data_count': len(self.price_data),
            'active_opportunities': active_opportunities,
            'active_orders': active_orders,
            'total_arbitrage_cycles': self.total_arbitrage_cycles,
            'successful_arbitrage_cycles': self.successful_arbitrage_cycles,
            'success_rate': float(success_rate),
            'total_arbitrage_profit': str(self.total_arbitrage_profit),
            'average_execution_time': float(self.average_execution_time),
            'min_profit_threshold': str(self.min_profit_threshold),
            'is_monitoring': self.is_monitoring,
            'last_market_scan': self.last_market_scan.isoformat() if self.last_market_scan else None
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取套利策略性能指标"""
        base_metrics = super().get_performance_metrics()
        
        # 添加套利特定指标
        arbitrage_metrics = {
            'arbitrage_cycles_completed': self.total_arbitrage_cycles,
            'arbitrage_success_rate': self.successful_arbitrage_cycles / max(self.total_arbitrage_cycles, 1),
            'total_arbitrage_profit': float(self.total_arbitrage_profit),
            'average_profit_per_cycle': float(self.total_arbitrage_profit / max(self.total_arbitrage_cycles, 1)),
            'average_execution_time': float(self.average_execution_time),
            'active_opportunities': len(self.arbitrage_opportunities),
            'exchanges_monitored': len(self.monitored_exchanges),
            'profit_efficiency': float(self.total_arbitrage_profit / max(self.state.total_profit, 1))
        }
        
        base_metrics.update(arbitrage_metrics)
        return base_metrics
    
    def set_monitored_exchanges(self, exchanges: List[ExchangeName]):
        """设置监控的交易所"""
        if len(exchanges) < 2:
            raise ValidationException("至少需要监控2个交易所")
        
        self.monitored_exchanges = exchanges
        self.logger.info(f"设置监控交易所: {[ex.value for ex in exchanges]}")
    
    def set_profit_threshold(self, threshold: Decimal):
        """设置盈利阈值"""
        if threshold <= 0 or threshold > Decimal('0.1'):
            raise ValidationException("盈利阈值必须在(0, 10%]之间")
        
        self.min_profit_threshold = threshold
        self.logger.info(f"设置盈利阈值: {threshold}")


# 策略工厂函数
def create_arbitrage_strategy(config, order_manager=None) -> ArbitrageStrategy:
    """创建套利策略实例"""
    return ArbitrageStrategy(config, order_manager)


# 策略配置验证函数
def validate_arbitrage_config(config) -> bool:
    """验证套利策略配置"""
    try:
        if config.strategy_type != StrategyType.ARBITRAGE:
            return False
        
        if not config.arbitrage_threshold or config.arbitrage_threshold <= 0:
            return False
        
        if config.arbitrage_threshold > Decimal('0.1'):
            return False
        
        return True
        
    except Exception:
        return False