"""
合约摆动策略
实现基于价格波动的摆动交易功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from .base_futures_strategy import (
    BaseFuturesStrategy, FuturesMarketData, FuturesOrderRequest, 
    FuturesOrderResult, FuturesPosition, OrderType, OrderSide,
    PositionSide, ValidationException, FuturesStrategyConfig,
    FuturesStrategyType
)


class PricePatternAnalyzer:
    """价格模式分析器"""
    
    def __init__(self):
        self.price_history: List[Decimal] = []
        self.volume_history: List[Decimal] = []
        self.timestamp_history: List[datetime] = []
        self.support_levels: List[Decimal] = []
        self.resistance_levels: List[Decimal] = []
    
    def add_data_point(self, price: Decimal, volume: Decimal, timestamp: datetime):
        """添加数据点"""
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)
        
        # 保持历史数据在合理范围内
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-500:]
            self.volume_history = self.volume_history[-500:]
            self.timestamp_history = self.timestamp_history[-500:]
    
    def identify_support_resistance(self, lookback_period: int = 50) -> Dict[str, List[Decimal]]:
        """识别支撑和阻力位"""
        if len(self.price_history) < lookback_period:
            return {'support': [], 'resistance': []}
        
        recent_prices = self.price_history[-lookback_period:]
        
        # 找到局部高点和低点
        highs = []
        lows = []
        
        for i in range(2, len(recent_prices) - 2):
            # 局部高点
            if (recent_prices[i] > recent_prices[i-1] and 
                recent_prices[i] > recent_prices[i+1] and
                recent_prices[i] > recent_prices[i-2] and 
                recent_prices[i] > recent_prices[i+2]):
                highs.append(recent_prices[i])
            
            # 局部低点
            if (recent_prices[i] < recent_prices[i-1] and 
                recent_prices[i] < recent_prices[i+1] and
                recent_prices[i] < recent_prices[i-2] and 
                recent_prices[i] < recent_prices[i+2]):
                lows.append(recent_prices[i])
        
        # 聚类支撑阻力位
        support_levels = self._cluster_price_levels(lows, tolerance=0.02)
        resistance_levels = self._cluster_price_levels(highs, tolerance=0.02)
        
        return {
            'support': sorted(support_levels),
            'resistance': sorted(resistance_levels, reverse=True)
        }
    
    def _cluster_price_levels(self, prices: List[Decimal], tolerance: Decimal = Decimal('0.02')) -> List[Decimal]:
        """聚类价格水平"""
        if not prices:
            return []
        
        clustered_levels = []
        used = [False] * len(prices)
        
        for i, price in enumerate(prices):
            if used[i]:
                continue
            
            # 找到所有接近这个价格的点
            cluster = [price]
            used[i] = True
            
            for j, other_price in enumerate(prices[i+1:], i+1):
                if not used[j] and abs(other_price - price) / price <= tolerance:
                    cluster.append(other_price)
                    used[j] = True
            
            # 计算聚类的平均值
            if cluster:
                avg_price = sum(cluster) / Decimal(str(len(cluster)))
                clustered_levels.append(avg_price)
        
        return sorted(clustered_levels)
    
    def analyze_swing_pattern(self, lookback_period: int = 30) -> Dict[str, Any]:
        """分析摆动模式"""
        if len(self.price_history) < lookback_period:
            return {'pattern': 'insufficient_data', 'direction': 'unknown', 'strength': Decimal('0')}
        
        recent_prices = self.price_history[-lookback_period:]
        current_price = recent_prices[-1]
        
        # 识别摆动高低点
        swing_highs = self._find_swing_points(recent_prices, 'high')
        swing_lows = self._find_swing_points(recent_prices, 'low')
        
        # 分析摆动模式
        pattern_analysis = self._analyze_swing_pattern(recent_prices, swing_highs, swing_lows)
        
        # 计算摆动强度
        strength = self._calculate_swing_strength(recent_prices, swing_highs, swing_lows)
        
        # 确定摆动方向
        direction = self._determine_swing_direction(swing_highs, swing_lows, current_price)
        
        return {
            'pattern': pattern_analysis['pattern'],
            'direction': direction,
            'strength': strength,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'current_price': current_price,
            'nearest_resistance': self._find_nearest_level(current_price, 'resistance'),
            'nearest_support': self._find_nearest_level(current_price, 'support'),
            'volatility': self._calculate_volatility(recent_prices)
        }
    
    def _find_swing_points(self, prices: List[Decimal], point_type: str) -> List[Tuple[int, Decimal]]:
        """找到摆动点"""
        if len(prices) < 5:
            return []
        
        swing_points = []
        window = 2  # 左右各2个点确认
        
        for i in range(window, len(prices) - window):
            is_swing = True
            
            if point_type == 'high':
                # 检查是否为摆动高点
                for j in range(i - window, i + window + 1):
                    if j != i and prices[j] >= prices[i]:
                        is_swing = False
                        break
            else:  # point_type == 'low'
                # 检查是否为摆动低点
                for j in range(i - window, i + window + 1):
                    if j != i and prices[j] <= prices[i]:
                        is_swing = False
                        break
            
            if is_swing:
                swing_points.append((i, prices[i]))
        
        return swing_points
    
    def _analyze_swing_pattern(self, prices: List[Decimal], swing_highs: List[Tuple[int, Decimal]], 
                             swing_lows: List[Tuple[int, Decimal]]) -> Dict[str, str]:
        """分析摆动模式"""
        if not swing_highs or not swing_lows:
            return {'pattern': 'no_swing_points'}
        
        # 分析最近几个摆动点
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
        
        # 判断模式
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # 双顶双底模式
            if (recent_highs[-1][1] > recent_highs[-2][1] and 
                recent_lows[-1][1] < recent_lows[-2][1]):
                pattern = 'ascending_triangle'
            elif (recent_highs[-1][1] < recent_highs[-2][1] and 
                  recent_lows[-1][1] > recent_lows[-2][1]):
                pattern = 'descending_triangle'
            elif (recent_highs[-1][1] > recent_highs[-2][1] and 
                  recent_lows[-1][1] > recent_lows[-2][1]):
                pattern = 'ascending_channel'
            elif (recent_highs[-1][1] < recent_highs[-2][1] and 
                  recent_lows[-1][1] < recent_lows[-2][1]):
                pattern = 'descending_channel'
            else:
                pattern = 'sideways'
        else:
            pattern = 'developing'
        
        return {'pattern': pattern}
    
    def _calculate_swing_strength(self, prices: List[Decimal], swing_highs: List[Tuple[int, Decimal]], 
                                swing_lows: List[Tuple[int, Decimal]]) -> Decimal:
        """计算摆动强度"""
        if len(prices) < 2:
            return Decimal('0')
        
        # 计算价格波动幅度
        price_range = max(prices) - min(prices)
        avg_price = sum(prices) / Decimal(str(len(prices)))
        
        if avg_price == 0:
            return Decimal('0')
        
        volatility = price_range / avg_price
        
        # 考虑摆动点的密度和幅度
        swing_density = Decimal(str(len(swing_highs) + len(swing_lows))) / Decimal(str(len(prices)))
        
        # 综合强度
        strength = min(volatility * swing_density * Decimal('10'), Decimal('1'))
        
        return strength
    
    def _determine_swing_direction(self, swing_highs: List[Tuple[int, Decimal]], 
                                 swing_lows: List[Tuple[int, Decimal]], 
                                 current_price: Decimal) -> str:
        """确定摆动方向"""
        if not swing_highs or not swing_lows:
            return 'unknown'
        
        # 找到最近的摆动高点
        latest_high = swing_highs[-1]
        latest_low = swing_lows[-1]
        
        # 判断当前位置相对于摆动点的位置
        if current_price > latest_high[1]:
            return 'bullish_breakout'
        elif current_price < latest_low[1]:
            return 'bearish_breakout'
        elif latest_high[1] > latest_low[1]:
            # 当前价格在摆动区间内
            if len(swing_highs) >= 2 and latest_high[1] > swing_highs[-2][1]:
                return 'bullish'
            elif len(swing_lows) >= 2 and latest_low[1] < swing_lows[-2][1]:
                return 'bearish'
            else:
                return 'sideways'
        else:
            return 'unknown'
    
    def _find_nearest_level(self, current_price: Decimal, level_type: str) -> Optional[Decimal]:
        """找到最近的支撑或阻力位"""
        if level_type == 'resistance' and self.resistance_levels:
            # 找到第一个大于当前价格的阻力位
            for level in sorted(self.resistance_levels):
                if level > current_price:
                    return level
            return self.resistance_levels[-1] if self.resistance_levels else None
        
        elif level_type == 'support' and self.support_levels:
            # 找到第一个小于当前价格的支撑位
            for level in sorted(self.support_levels, reverse=True):
                if level < current_price:
                    return level
            return self.support_levels[0] if self.support_levels else None
        
        return None
    
    def _calculate_volatility(self, prices: List[Decimal]) -> Decimal:
        """计算价格波动性"""
        if len(prices) < 2:
            return Decimal('0')
        
        # 计算价格变化的标准差
        changes = []
        for i in range(1, len(prices)):
            change = abs(prices[i] - prices[i-1]) / prices[i-1]
            changes.append(change)
        
        if not changes:
            return Decimal('0')
        
        mean_change = sum(changes) / Decimal(str(len(changes)))
        variance = sum((change - mean_change) ** 2 for change in changes) / Decimal(str(len(changes)))
        
        return variance.sqrt()


class SwingTradingStrategy(BaseFuturesStrategy):
    """合约摆动交易策略"""
    
    def __init__(self, config: FuturesStrategyConfig, order_manager: Optional[Any] = None):
        super().__init__(config, order_manager)
        
        # 验证策略类型
        if config.strategy_type != FuturesStrategyType.SWING:
            raise ValidationException("策略类型不匹配")
        
        self.pattern_analyzer = PricePatternAnalyzer()
        self.last_signal: Optional[str] = None
        self.signal_history: List[Dict[str, Any]] = []
        
        # 策略参数
        self.volatility_period = config.volatility_period
        self.volatility_threshold = config.volatility_threshold
        self.swing_confirmation_periods = 2
        
        # 摆动交易参数
        self.target_profit_pct = config.profit_target * Decimal('1.5')  # 目标利润1.5倍
        self.stop_loss_pct = config.stop_loss * Decimal('0.7')  # 止损0.7倍
        
        self.logger = logging.getLogger(f"futures_swing.{config.strategy_id}")
    
    async def _initialize_specific(self):
        """初始化摆动策略特定功能"""
        self.logger.info("初始化摆动交易策略")
        
        # 摆动状态追踪
        self.swing_state = {
            'in_swing': False,
            'swing_entry_price': Decimal('0'),
            'swing_target_price': Decimal('0'),
            'swing_stop_price': Decimal('0'),
            'swing_direction': 'unknown'
        }
    
    async def _start_specific(self):
        """启动摆动策略特定功能"""
        self.logger.info("启动摆动交易策略")
    
    async def _pause_specific(self):
        """暂停摆动策略特定功能"""
        self.logger.info("暂停摆动交易策略")
    
    async def _resume_specific(self):
        """恢复摆动策略特定功能"""
        self.logger.info("恢复摆动交易策略")
    
    async def _stop_specific(self):
        """停止摆动策略特定功能"""
        self.logger.info("停止摆动交易策略")
    
    async def get_next_orders(self, market_data: FuturesMarketData) -> List[FuturesOrderRequest]:
        """获取下一批订单"""
        try:
            if not self.state.is_trading_allowed():
                return []
            
            # 添加市场数据到模式分析器
            self.pattern_analyzer.add_data_point(
                market_data.current_price,
                market_data.volume_24h,
                market_data.timestamp
            )
            
            # 更新支撑阻力位
            levels = self.pattern_analyzer.identify_support_resistance()
            self.pattern_analyzer.support_levels = levels['support']
            self.pattern_analyzer.resistance_levels = levels['resistance']
            
            # 分析摆动模式
            swing_analysis = self.pattern_analyzer.analyze_swing_pattern()
            
            # 生成交易信号
            signal = self._generate_swing_signal(market_data, swing_analysis)
            
            orders = []
            
            if signal['action'] == 'enter_long':
                orders = await self._generate_enter_long_orders(market_data, signal)
            elif signal['action'] == 'enter_short':
                orders = await self._generate_enter_short_orders(market_data, signal)
            elif signal['action'] == 'add_to_long':
                orders = await self._generate_add_to_long_orders(market_data, signal)
            elif signal['action'] == 'add_to_short':
                orders = await self._generate_add_to_short_orders(market_data, signal)
            elif signal['action'] == 'exit_long':
                orders = await self._generate_exit_long_orders(market_data, signal)
            elif signal['action'] == 'exit_short':
                orders = await self._generate_exit_short_orders(market_data, signal)
            elif signal['action'] == 'take_profit':
                orders = await self._generate_take_profit_orders(market_data, signal)
            elif signal['action'] == 'stop_loss':
                orders = await self._generate_stop_loss_orders(market_data, signal)
            
            # 记录信号
            self._record_swing_signal(signal, swing_analysis)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取摆动订单失败: {e}")
            return []
    
    def _generate_swing_signal(self, market_data: FuturesMarketData, swing_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成摆动交易信号"""
        signal = {
            'action': 'hold',
            'confidence': Decimal('0'),
            'strength': Decimal('0'),
            'pattern': swing_analysis['pattern'],
            'direction': swing_analysis['direction'],
            'reasons': []
        }
        
        try:
            current_price = market_data.current_price
            nearest_support = swing_analysis.get('nearest_support')
            nearest_resistance = swing_analysis.get('nearest_resistance')
            volatility = swing_analysis.get('volatility', Decimal('0'))
            
            # 检查波动性是否足够
            if volatility < self.volatility_threshold:
                signal['reasons'].append(f"波动性不足: {volatility:.4f}")
                return signal
            
            # 检查是否在摆动交易中
            if self.swing_state['in_swing']:
                signal = self._check_existing_swing_position(market_data, swing_analysis)
                return signal
            
            # 基于模式生成信号
            pattern = swing_analysis['pattern']
            direction = swing_analysis['direction']
            strength = swing_analysis['strength']
            
            # 突破交易信号
            if direction == 'bullish_breakout' and nearest_resistance:
                signal.update({
                    'action': 'enter_long',
                    'target_price': self._calculate_target_price(current_price, 'long'),
                    'stop_price': current_price * (Decimal('1') - self.stop_loss_pct),
                    'confidence': min(strength + Decimal('0.3'), Decimal('1')),
                    'strength': strength,
                    'reasons': [f"突破阻力位: {direction}, 阻力位: {nearest_resistance}"]
                })
            
            elif direction == 'bearish_breakout' and nearest_support:
                signal.update({
                    'action': 'enter_short',
                    'target_price': self._calculate_target_price(current_price, 'short'),
                    'stop_price': current_price * (Decimal('1') + self.stop_loss_pct),
                    'confidence': min(strength + Decimal('0.3'), Decimal('1')),
                    'strength': strength,
                    'reasons': [f"突破支撑位: {direction}, 支撑位: {nearest_support}"]
                })
            
            # 反弹交易信号
            elif pattern == 'bullish' and nearest_support:
                distance_to_support = abs(current_price - nearest_support) / current_price
                if distance_to_support < Decimal('0.02'):  # 距离支撑位2%以内
                    signal.update({
                        'action': 'enter_long',
                        'target_price': nearest_resistance or self._calculate_target_price(current_price, 'long'),
                        'stop_price': nearest_support * Decimal('0.98'),
                        'confidence': Decimal('0.8'),
                        'strength': strength,
                        'reasons': [f"支撑位反弹: {direction}, 支撑位: {nearest_support}"]
                    })
            
            elif pattern == 'bearish' and nearest_resistance:
                distance_to_resistance = abs(current_price - nearest_resistance) / current_price
                if distance_to_resistance < Decimal('0.02'):  # 距离阻力位2%以内
                    signal.update({
                        'action': 'enter_short',
                        'target_price': nearest_support or self._calculate_target_price(current_price, 'short'),
                        'stop_price': nearest_resistance * Decimal('1.02'),
                        'confidence': Decimal('0.8'),
                        'strength': strength,
                        'reasons': [f"阻力位回调: {direction}, 阻力位: {nearest_resistance}"]
                    })
            
            # 三角形突破信号
            elif pattern in ['ascending_triangle', 'descending_triangle']:
                signal.update({
                    'action': self._analyze_triangle_breakout(market_data, swing_analysis, pattern),
                    'confidence': min(strength + Decimal('0.4'), Decimal('1')),
                    'strength': strength,
                    'reasons': [f"三角形模式: {pattern}"]
                })
        
        except Exception as e:
            self.logger.error(f"生成摆动信号失败: {e}")
            signal['reasons'].append(f"信号生成错误: {e}")
        
        return signal
    
    def _check_existing_swing_position(self, market_data: FuturesMarketData, swing_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """检查现有摆动仓位"""
        signal = {
            'action': 'hold',
            'confidence': Decimal('0'),
            'reasons': []
        }
        
        try:
            current_price = market_data.current_price
            swing_direction = self.swing_state['swing_direction']
            target_price = self.swing_state['swing_target_price']
            stop_price = self.swing_state['swing_stop_price']
            
            # 检查止损
            if ((swing_direction == 'long' and current_price <= stop_price) or
                (swing_direction == 'short' and current_price >= stop_price)):
                signal.update({
                    'action': 'stop_loss',
                    'confidence': Decimal('1'),
                    'reasons': [f"止损触发: {swing_direction}, 价格: {current_price}, 止损: {stop_price}"]
                })
            
            # 检查止盈
            elif ((swing_direction == 'long' and current_price >= target_price) or
                  (swing_direction == 'short' and current_price <= target_price)):
                signal.update({
                    'action': 'take_profit',
                    'confidence': Decimal('1'),
                    'reasons': [f"止盈触发: {swing_direction}, 价格: {current_price}, 目标: {target_price}"]
                })
            
            # 检查是否继续持有
            else:
                # 检查是否需要减仓（基于技术指标）
                if self._should_reduce_swing_position(market_data, swing_analysis):
                    if swing_direction == 'long':
                        signal.update({
                            'action': 'exit_long',
                            'confidence': Decimal('0.7'),
                            'reasons': ['技术指标建议减仓']
                        })
                    else:
                        signal.update({
                            'action': 'exit_short',
                            'confidence': Decimal('0.7'),
                            'reasons': ['技术指标建议减仓']
                        })
                else:
                    signal['reasons'].append('继续持有摆动仓位')
        
        except Exception as e:
            self.logger.error(f"检查摆动仓位失败: {e}")
            signal['reasons'].append(f"检查错误: {e}")
        
        return signal
    
    def _analyze_triangle_breakout(self, market_data: FuturesMarketData, swing_analysis: Dict[str, Any], pattern: str) -> str:
        """分析三角形突破"""
        # 简化的三角形突破判断
        current_price = market_data.current_price
        
        if pattern == 'ascending_triangle':
            # 上升三角形：向上突破看涨
            return 'enter_long'
        elif pattern == 'descending_triangle':
            # 下降三角形：向下突破看跌
            return 'enter_short'
        else:
            return 'hold'
    
    def _calculate_target_price(self, entry_price: Decimal, direction: str) -> Decimal:
        """计算目标价格"""
        if direction == 'long':
            return entry_price * (Decimal('1') + self.target_profit_pct)
        else:
            return entry_price * (Decimal('1') - self.target_profit_pct)
    
    def _should_reduce_swing_position(self, market_data: FuturesMarketData, swing_analysis: Dict[str, Any]) -> bool:
        """检查是否应该减少摆动仓位"""
        # 这里可以添加更复杂的逻辑，比如基于RSI、MACD等指标
        current_price = market_data.current_price
        swing_direction = self.swing_state['swing_direction']
        
        # 简化的减仓逻辑：价格偏离摆动幅度过大时减仓
        entry_price = self.swing_state['swing_entry_price']
        if entry_price > 0:
            deviation = abs(current_price - entry_price) / entry_price
            if deviation > Decimal('0.15'):  # 偏离超过15%
                return True
        
        return False
    
    async def _generate_enter_long_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成开多头订单"""
        try:
            orders = []
            
            # 设置摆动状态
            self.swing_state.update({
                'in_swing': True,
                'swing_entry_price': market_data.current_price,
                'swing_target_price': signal.get('target_price', self._calculate_target_price(market_data.current_price, 'long')),
                'swing_stop_price': signal.get('stop_price', market_data.current_price * (Decimal('1') - self.stop_loss_pct)),
                'swing_direction': 'long'
            })
            
            # 计算订单数量
            quantity = self._calculate_swing_position_size(market_data, 'long')
            
            if quantity <= 0:
                return orders
            
            # 主订单：限价单
            price_buffer = Decimal('0.001')
            limit_price = market_data.current_price * (Decimal('1') - price_buffer)
            
            entry_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.BUY,
                quantity=quantity,
                price=limit_price,
                position_side=PositionSide.LONG,
                client_order_id=f"swing_long_{int(datetime.now().timestamp())}"
            )
            orders.append(entry_order)
            
            # 止损订单
            stop_price = self.swing_state['swing_stop_price']
            stop_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_stop_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.STOP,
                order_side=OrderSide.SELL,
                quantity=quantity,
                stop_price=stop_price,
                position_side=PositionSide.LONG,
                client_order_id=f"swing_stop_long_{int(datetime.now().timestamp())}"
            )
            orders.append(stop_order)
            
            # 止盈订单
            target_price = self.swing_state['swing_target_price']
            take_profit_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_target_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.SELL,
                quantity=quantity,
                price=target_price,
                position_side=PositionSide.LONG,
                client_order_id=f"swing_target_long_{int(datetime.now().timestamp())}"
            )
            orders.append(take_profit_order)
            
            self.logger.info(f"生成摆动开多头订单: 数量={quantity}, 入场={market_data.current_price}, 目标={target_price}, 止损={stop_price}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成摆动开多头订单失败: {e}")
            return []
    
    async def _generate_enter_short_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成开空头订单"""
        try:
            orders = []
            
            # 设置摆动状态
            self.swing_state.update({
                'in_swing': True,
                'swing_entry_price': market_data.current_price,
                'swing_target_price': signal.get('target_price', self._calculate_target_price(market_data.current_price, 'short')),
                'swing_stop_price': signal.get('stop_price', market_data.current_price * (Decimal('1') + self.stop_loss_pct)),
                'swing_direction': 'short'
            })
            
            # 计算订单数量
            quantity = self._calculate_swing_position_size(market_data, 'short')
            
            if quantity <= 0:
                return orders
            
            # 主订单：限价单
            price_buffer = Decimal('0.001')
            limit_price = market_data.current_price * (Decimal('1') + price_buffer)
            
            entry_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.SELL,
                quantity=quantity,
                price=limit_price,
                position_side=PositionSide.SHORT,
                client_order_id=f"swing_short_{int(datetime.now().timestamp())}"
            )
            orders.append(entry_order)
            
            # 止损订单
            stop_price = self.swing_state['swing_stop_price']
            stop_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_stop_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.STOP,
                order_side=OrderSide.BUY,
                quantity=quantity,
                stop_price=stop_price,
                position_side=PositionSide.SHORT,
                client_order_id=f"swing_stop_short_{int(datetime.now().timestamp())}"
            )
            orders.append(stop_order)
            
            # 止盈订单
            target_price = self.swing_state['swing_target_price']
            take_profit_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_target_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.BUY,
                quantity=quantity,
                price=target_price,
                position_side=PositionSide.SHORT,
                client_order_id=f"swing_target_short_{int(datetime.now().timestamp())}"
            )
            orders.append(take_profit_order)
            
            self.logger.info(f"生成摆动开空头订单: 数量={quantity}, 入场={market_data.current_price}, 目标={target_price}, 止损={stop_price}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成摆动开空头订单失败: {e}")
            return []
    
    async def _generate_add_to_long_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成加仓多头订单"""
        # 摆动策略通常不加仓，简化处理
        return []
    
    async def _generate_add_to_short_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成加仓空头订单"""
        # 摆动策略通常不加仓，简化处理
        return []
    
    async def _generate_exit_long_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成退出多头订单"""
        try:
            if self.state.current_position.quantity <= 0:
                return []
            
            orders = []
            
            # 平仓订单：市价单
            exit_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_exit_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.SELL,
                quantity=abs(self.state.current_position.quantity),
                position_side=PositionSide.LONG,
                client_order_id=f"swing_exit_long_{int(datetime.now().timestamp())}"
            )
            orders.append(exit_order)
            
            # 重置摆动状态
            self.swing_state.update({
                'in_swing': False,
                'swing_entry_price': Decimal('0'),
                'swing_target_price': Decimal('0'),
                'swing_stop_price': Decimal('0'),
                'swing_direction': 'unknown'
            })
            
            self.logger.info(f"生成摆动退出多头订单: 数量={abs(self.state.current_position.quantity)}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成摆动退出多头订单失败: {e}")
            return []
    
    async def _generate_exit_short_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成退出空头订单"""
        try:
            if self.state.current_position.quantity >= 0:
                return []
            
            orders = []
            
            # 平仓订单：市价单
            exit_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_swing_exit_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.BUY,
                quantity=abs(self.state.current_position.quantity),
                position_side=PositionSide.SHORT,
                client_order_id=f"swing_exit_short_{int(datetime.now().timestamp())}"
            )
            orders.append(exit_order)
            
            # 重置摆动状态
            self.swing_state.update({
                'in_swing': False,
                'swing_entry_price': Decimal('0'),
                'swing_target_price': Decimal('0'),
                'swing_stop_price': Decimal('0'),
                'swing_direction': 'unknown'
            })
            
            self.logger.info(f"生成摆动退出空头订单: 数量={abs(self.state.current_position.quantity)}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成摆动退出空头订单失败: {e}")
            return []
    
    async def _generate_take_profit_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成止盈订单"""
        if self.state.current_position.quantity > 0:
            return await self._generate_exit_long_orders(market_data, signal)
        elif self.state.current_position.quantity < 0:
            return await self._generate_exit_short_orders(market_data, signal)
        else:
            return []
    
    async def _generate_stop_loss_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成止损订单"""
        if self.state.current_position.quantity > 0:
            return await self._generate_exit_long_orders(market_data, signal)
        elif self.state.current_position.quantity < 0:
            return await self._generate_exit_short_orders(market_data, signal)
        else:
            return []
    
    def _calculate_swing_position_size(self, market_data: FuturesMarketData, direction: str) -> Decimal:
        """计算摆动仓位大小"""
        try:
            # 基础仓位大小
            base_size = self.config.base_quantity
            
            # 根据波动性调整
            volatility = self.pattern_analyzer._calculate_volatility(self.pattern_analyzer.price_history[-20:] if len(self.pattern_analyzer.price_history) >= 20 else self.pattern_analyzer.price_history)
            volatility_multiplier = min(volatility / self.volatility_threshold, Decimal('1.5'))  # 最大1.5倍
            
            # 计算最终仓位大小
            final_size = base_size * volatility_multiplier
            
            # 限制在最大仓位内
            final_size = min(final_size, self.config.max_position_size)
            
            # 确保订单大小在允许范围内
            final_size = max(self.config.min_order_size, min(final_size, self.config.max_order_size))
            
            self.logger.debug(f"计算摆动仓位大小: 基础={base_size}, 波动性倍数={volatility_multiplier}, 最终={final_size}")
            return final_size
            
        except Exception as e:
            self.logger.error(f"计算摆动仓位大小失败: {e}")
            return self.config.min_order_size
    
    def _record_swing_signal(self, signal: Dict[str, Any], swing_analysis: Dict[str, Any]):
        """记录摆动交易信号"""
        try:
            self.signal_history.append({
                'timestamp': datetime.now(),
                'signal': signal,
                'swing_analysis': swing_analysis,
                'swing_state': self.swing_state.copy(),
                'position': {
                    'quantity': float(self.state.current_position.quantity),
                    'side': self.state.current_position.get_position_side_name()
                }
            })
            
            # 保持信号历史在合理范围内
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-50:]
            
            # 更新最后信号
            self.last_signal = signal['action']
            
            # 记录信号日志
            self.logger.info(
                f"摆动信号: {signal['action']}, "
                f"模式: {swing_analysis['pattern']}, "
                f"方向: {swing_analysis['direction']}, "
                f"强度: {signal['strength']:.2f}, "
                f"原因: {'; '.join(signal['reasons'])}"
            )
            
        except Exception as e:
            self.logger.error(f"记录摆动信号失败: {e}")
    
    async def process_order_result(self, order_result: FuturesOrderResult) -> bool:
        """处理订单执行结果"""
        try:
            self.update_state_after_order(order_result, self.last_market_data)
            
            # 如果是完整的摆动交易完成，重置摆动状态
            if 'exit' in order_result.order_id or 'stop' in order_result.order_id or 'target' in order_result.order_id:
                if self.state.current_position.quantity == 0:  # 仓位已清零
                    self.swing_state.update({
                        'in_swing': False,
                        'swing_entry_price': Decimal('0'),
                        'swing_target_price': Decimal('0'),
                        'swing_stop_price': Decimal('0'),
                        'swing_direction': 'unknown'
                    })
            
            # 记录资金费率影响
            if order_result.funding_rate:
                funding_impact = abs(self.state.current_position.quantity) * self.last_market_data.current_price * order_result.funding_rate
                self.state.funding_rate_paid += funding_impact
            
            self.logger.info(f"摆动订单处理完成: {order_result.order_id}, 成功: {order_result.success}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理摆动订单结果失败: {e}")
            self.state.error_count += 1
            self.state.last_error = str(e)
            return False
    
    def update_state_after_order(self, order_result: FuturesOrderResult, market_data: Optional[FuturesMarketData]):
        """更新策略状态（订单执行后）"""
        self.state.total_orders += 1
        
        if order_result.success:
            self.state.filled_orders += 1
            
            # 更新仓位
            if self.state.current_position:
                current_qty = self.state.current_position.quantity
                
                if any(keyword in order_result.order_id for keyword in ['swing_long', 'swing_buy']):
                    # 买入订单
                    self.state.current_position.quantity += order_result.filled_quantity
                elif any(keyword in order_result.order_id for keyword in ['swing_short', 'swing_sell']):
                    # 卖出订单
                    self.state.current_position.quantity -= order_result.filled_quantity
                elif 'swing_exit' in order_result.order_id:
                    # 平仓订单
                    self.state.current_position.quantity = Decimal('0')
                
                # 更新平均价格
                if market_data:
                    total_value = (current_qty * self.state.current_position.average_price) + \
                                 (order_result.filled_quantity * order_result.average_price)
                    total_quantity = current_qty + order_result.filled_quantity
                    
                    if total_quantity != 0:
                        self.state.current_position.average_price = total_value / total_quantity
            
            # 更新盈亏
            if market_data:
                current_value = abs(self.state.current_position.quantity) * market_data.current_price
                cost_value = abs(self.state.current_position.quantity) * self.state.current_position.average_price
                self.state.current_position.unrealized_pnl = current_value - cost_value
            
            self.state.realized_pnl += order_result.average_price * order_result.filled_quantity - order_result.commission
            self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
            self.state.commission_paid += order_result.commission
            
        else:
            self.state.failed_orders += 1
        
        # 更新性能指标
        self.state.update_performance_metrics()
        
        # 记录历史
        self.performance_history.append({
            'timestamp': datetime.now(),
            'order_id': order_result.order_id,
            'success': order_result.success,
            'pnl': float(self.state.total_profit),
            'drawdown': float(self.state.current_drawdown)
        })
        
        # 保持历史记录在合理范围内
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]