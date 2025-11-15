"""
合约趋势跟踪策略
实现基于技术指标的趋势识别和跟踪功能
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


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def simple_moving_average(prices: List[Decimal], period: int) -> Optional[Decimal]:
        """简单移动平均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / Decimal(str(period))
    
    @staticmethod
    def exponential_moving_average(prices: List[Decimal], period: int) -> Optional[Decimal]:
        """指数移动平均线"""
        if len(prices) < period:
            return None
        
        if len(prices) == period:
            # 第一EMA值使用SMA
            multiplier = Decimal('2') / Decimal(str(period + 1))
            sma = sum(prices[-period:]) / Decimal(str(period))
            return sma
        
        # 计算EMA
        multiplier = Decimal('2') / Decimal(str(period + 1))
        ema_prev = TechnicalIndicators.simple_moving_average(prices[:-1], period) or prices[-2]
        ema = (prices[-1] * multiplier) + (ema_prev * (Decimal('1') - multiplier))
        return ema
    
    @staticmethod
    def relative_strength_index(prices: List[Decimal], period: int = 14) -> Optional[Decimal]:
        """相对强弱指数 (RSI)"""
        if len(prices) < period + 1:
            return None
        
        # 计算价格变化
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            changes.append(change)
        
        if len(changes) < period:
            return None
        
        # 分离涨跌
        gains = [max(change, Decimal('0')) for change in changes[-period:]]
        losses = [abs(min(change, Decimal('0'))) for change in changes[-period:]]
        
        # 计算平均涨幅和跌幅
        avg_gain = sum(gains) / Decimal(str(period))
        avg_loss = sum(losses) / Decimal(str(period))
        
        if avg_loss == 0:
            return Decimal('100')
        
        # 计算RSI
        rs = avg_gain / avg_loss
        rsi = Decimal('100') - (Decimal('100') / (Decimal('1') + rs))
        
        return rsi
    
    @staticmethod
    def bollinger_bands(prices: List[Decimal], period: int = 20, std_dev: Decimal = Decimal('2')) -> Dict[str, Decimal]:
        """布林带"""
        if len(prices) < period:
            return {}
        
        sma = TechnicalIndicators.simple_moving_average(prices, period)
        if sma is None:
            return {}
        
        # 计算标准差
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / Decimal(str(period))
        std = variance.sqrt()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    @staticmethod
    def macd(prices: List[Decimal], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Decimal]:
        """MACD指标"""
        if len(prices) < slow_period:
            return {}
        
        ema_fast = TechnicalIndicators.exponential_moving_average(prices, fast_period)
        ema_slow = TechnicalIndicators.exponential_moving_average(prices, slow_period)
        
        if ema_fast is None or ema_slow is None:
            return {}
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线（简化为简单移动平均）
        # 实际应该使用指数移动平均，这里简化处理
        signal_line = macd_line  # 简化处理
        
        # 计算柱状图
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }


class TrendAnalysis:
    """趋势分析类"""
    
    def __init__(self):
        self.price_history: List[Decimal] = []
        self.volume_history: List[Decimal] = []
        self.timestamp_history: List[datetime] = []
    
    def add_data_point(self, price: Decimal, volume: Decimal, timestamp: datetime):
        """添加数据点"""
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)
        
        # 保持历史数据在合理范围内
        if len(self.price_history) > 500:
            self.price_history = self.price_history[-250:]
            self.volume_history = self.volume_history[-250:]
            self.timestamp_history = self.timestamp_history[-250:]
    
    def analyze_trend(self, lookback_period: int = 20) -> Dict[str, Any]:
        """分析趋势"""
        if len(self.price_history) < lookback_period:
            return {'trend': 'unknown', 'strength': Decimal('0'), 'confidence': Decimal('0')}
        
        recent_prices = self.price_history[-lookback_period:]
        recent_volumes = self.volume_history[-lookback_period:]
        
        # 计算价格趋势
        price_trend = self._calculate_price_trend(recent_prices)
        
        # 计算成交量趋势
        volume_trend = self._calculate_volume_trend(recent_volumes)
        
        # 计算趋势强度
        strength = self._calculate_trend_strength(recent_prices)
        
        # 计算趋势确认度
        confidence = self._calculate_confidence(price_trend, volume_trend, strength)
        
        # 综合判断
        overall_trend = self._determine_overall_trend(price_trend, volume_trend, strength)
        
        return {
            'trend': overall_trend,
            'price_trend': price_trend,
            'volume_trend': volume_trend,
            'strength': strength,
            'confidence': confidence,
            'direction': 'up' if price_trend > 0 else 'down' if price_trend < 0 else 'sideways'
        }
    
    def _calculate_price_trend(self, prices: List[Decimal]) -> Decimal:
        """计算价格趋势（线性回归斜率）"""
        if len(prices) < 2:
            return Decimal('0')
        
        n = len(prices)
        x_values = list(range(n))
        
        # 计算斜率
        sum_x = sum(x_values)
        sum_y = sum(prices)
        sum_xy = sum(x * float(price) for x, price in zip(x_values, prices))
        sum_x2 = sum(x * x for x in x_values)
        
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return Decimal(str(slope))
        except ZeroDivisionError:
            return Decimal('0')
    
    def _calculate_volume_trend(self, volumes: List[Decimal]) -> Decimal:
        """计算成交量趋势"""
        if len(volumes) < 2:
            return Decimal('0')
        
        # 计算成交量变化率
        avg_volume = sum(volumes) / Decimal(str(len(volumes)))
        if avg_volume == 0:
            return Decimal('0')
        
        recent_volume = sum(volumes[-5:]) / Decimal('5') if len(volumes) >= 5 else volumes[-1]
        volume_change = (recent_volume - avg_volume) / avg_volume
        
        return volume_change
    
    def _calculate_trend_strength(self, prices: List[Decimal]) -> Decimal:
        """计算趋势强度"""
        if len(prices) < 3:
            return Decimal('0')
        
        # 计算价格变化的一致性
        changes = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1]
            changes.append(change)
        
        if not changes:
            return Decimal('0')
        
        # 计算变化方向的集中度
        positive_changes = sum(1 for change in changes if change > 0)
        negative_changes = sum(1 for change in changes if change < 0)
        
        total_changes = len(changes)
        strength = max(positive_changes, negative_changes) / Decimal(str(total_changes))
        
        return strength
    
    def _calculate_confidence(self, price_trend: Decimal, volume_trend: Decimal, strength: Decimal) -> Decimal:
        """计算趋势确认度"""
        # 价格趋势与成交量趋势的一致性
        trend_alignment = Decimal('1')
        if price_trend > 0 and volume_trend > 0:
            trend_alignment = Decimal('1')  # 上涨趋势 + 成交量放大
        elif price_trend < 0 and volume_trend < 0:
            trend_alignment = Decimal('1')  # 下跌趋势 + 成交量放大
        else:
            trend_alignment = Decimal('0.5')  # 趋势与成交量不一致
        
        # 综合确认度
        confidence = (strength + trend_alignment) / Decimal('2')
        
        return confidence
    
    def _determine_overall_trend(self, price_trend: Decimal, volume_trend: Decimal, strength: Decimal) -> str:
        """确定整体趋势"""
        if strength < Decimal('0.6'):
            return 'sideways'
        
        if price_trend > 0 and volume_trend >= 0:
            return 'bullish'
        elif price_trend < 0 and volume_trend >= 0:
            return 'bearish'
        else:
            return 'sideways'


class TrendFollowingStrategy(BaseFuturesStrategy):
    """合约趋势跟踪策略"""
    
    def __init__(self, config: FuturesStrategyConfig, order_manager: Optional[Any] = None):
        super().__init__(config, order_manager)
        
        # 验证策略类型
        if config.strategy_type != FuturesStrategyType.TREND_FOLLOWING:
            raise ValidationException("策略类型不匹配")
        
        self.trend_analyzer = TrendAnalysis()
        self.last_signal: Optional[str] = None
        self.signal_history: List[Dict[str, Any]] = []
        
        # 策略参数
        self.trend_period = config.trend_period
        self.confirmation_periods = config.trend_confirmation_periods
        self.strength_threshold = config.trend_strength_threshold
        
        # 技术指标参数
        self.ma_short_period = 10
        self.ma_long_period = 20
        self.rsi_period = 14
        self.bollinger_period = 20
        
        self.logger = logging.getLogger(f"futures_trend.{config.strategy_id}")
    
    async def _initialize_specific(self):
        """初始化趋势策略特定功能"""
        self.logger.info("初始化趋势跟踪策略")
        
        # 初始化技术指标缓存
        self.technical_indicators = {
            'sma_short': [],
            'sma_long': [],
            'ema_fast': [],
            'ema_slow': [],
            'rsi': [],
            'macd': [],
            'bollinger': {}
        }
    
    async def _start_specific(self):
        """启动趋势策略特定功能"""
        self.logger.info("启动趋势跟踪策略")
        # 可以在这里启动额外的监控任务
    
    async def _pause_specific(self):
        """暂停趋势策略特定功能"""
        self.logger.info("暂停趋势跟踪策略")
    
    async def _resume_specific(self):
        """恢复趋势策略特定功能"""
        self.logger.info("恢复趋势跟踪策略")
    
    async def _stop_specific(self):
        """停止趋势策略特定功能"""
        self.logger.info("停止趋势跟踪策略")
    
    async def get_next_orders(self, market_data: FuturesMarketData) -> List[FuturesOrderRequest]:
        """获取下一批订单"""
        try:
            if not self.state.is_trading_allowed():
                return []
            
            # 添加市场数据到趋势分析器
            self.trend_analyzer.add_data_point(
                market_data.current_price,
                market_data.volume_24h,
                market_data.timestamp
            )
            
            # 更新技术指标
            self._update_technical_indicators(market_data)
            
            # 分析趋势
            trend_analysis = self.trend_analyzer.analyze_trend(self.trend_period)
            
            # 生成交易信号
            signal = self._generate_trading_signal(market_data, trend_analysis)
            
            orders = []
            
            if signal['action'] == 'buy':
                orders = await self._generate_buy_orders(market_data, signal)
            elif signal['action'] == 'sell':
                orders = await self._generate_sell_orders(market_data, signal)
            elif signal['action'] == 'close_long':
                orders = await self._generate_close_long_orders(market_data, signal)
            elif signal['action'] == 'close_short':
                orders = await self._generate_close_short_orders(market_data, signal)
            
            # 记录信号
            self._record_signal(signal)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取订单失败: {e}")
            return []
    
    def _update_technical_indicators(self, market_data: FuturesMarketData):
        """更新技术指标"""
        try:
            prices = self.trend_analyzer.price_history
            
            # 移动平均线
            self.technical_indicators['sma_short'].append(
                TechnicalIndicators.simple_moving_average(prices, self.ma_short_period)
            )
            self.technical_indicators['sma_long'].append(
                TechnicalIndicators.simple_moving_average(prices, self.ma_long_period)
            )
            
            # 指数移动平均线
            self.technical_indicators['ema_fast'].append(
                TechnicalIndicators.exponential_moving_average(prices, 12)
            )
            self.technical_indicators['ema_slow'].append(
                TechnicalIndicators.exponential_moving_average(prices, 26)
            )
            
            # RSI
            self.technical_indicators['rsi'].append(
                TechnicalIndicators.relative_strength_index(prices, self.rsi_period)
            )
            
            # MACD
            self.technical_indicators['macd'].append(
                TechnicalIndicators.macd(prices)
            )
            
            # 布林带
            self.technical_indicators['bollinger'] = TechnicalIndicators.bollinger_bands(
                prices, self.bollinger_period
            )
            
            # 保持历史数据在合理范围内
            for key in ['sma_short', 'sma_long', 'ema_fast', 'ema_slow', 'rsi']:
                if len(self.technical_indicators[key]) > 100:
                    self.technical_indicators[key] = self.technical_indicators[key][-50:]
            
        except Exception as e:
            self.logger.error(f"更新技术指标失败: {e}")
    
    def _generate_trading_signal(self, market_data: FuturesMarketData, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成交易信号"""
        signal = {
            'action': 'hold',
            'confidence': trend_analysis['confidence'],
            'strength': trend_analysis['strength'],
            'trend': trend_analysis['trend'],
            'reasons': []
        }
        
        try:
            # 基础趋势判断
            if trend_analysis['strength'] < self.strength_threshold:
                signal['reasons'].append(f"趋势强度不足: {trend_analysis['strength']}")
                return signal
            
            # 技术指标信号
            ma_signal = self._get_ma_signal()
            rsi_signal = self._get_rsi_signal()
            macd_signal = self._get_macd_signal()
            bollinger_signal = self._get_bollinger_signal()
            
            # 综合信号判断
            bullish_signals = sum([
                ma_signal['bullish'],
                rsi_signal['bullish'],
                macd_signal['bullish'],
                bollinger_signal['bullish']
            ])
            
            bearish_signals = sum([
                ma_signal['bearish'],
                rsi_signal['bearish'],
                macd_signal['bearish'],
                bollinger_signal['bearish']
            ])
            
            # 趋势确认
            trend_confirmation = self._check_trend_confirmation(trend_analysis, ma_signal)
            
            # 生成信号
            current_position = self.state.current_position
            
            if bullish_signals >= 3 and trend_confirmation['bullish']:
                if current_position.quantity < 0:  # 当前有空头持仓
                    signal['action'] = 'close_short'
                    signal['reasons'].append(f"空头平仓: 多头信号数量={bullish_signals}")
                elif current_position.quantity == 0:  # 当前无持仓
                    signal['action'] = 'buy'
                    signal['reasons'].append(f"开多头: 多头信号数量={bullish_signals}")
                
            elif bearish_signals >= 3 and trend_confirmation['bearish']:
                if current_position.quantity > 0:  # 当前有多头持仓
                    signal['action'] = 'close_long'
                    signal['reasons'].append(f"多头平仓: 空头信号数量={bearish_signals}")
                elif current_position.quantity == 0:  # 当前无持仓
                    signal['action'] = 'sell'
                    signal['reasons'].append(f"开空头: 空头信号数量={bearish_signals}")
            
            # 添加信号详情
            signal.update({
                'ma_signal': ma_signal,
                'rsi_signal': rsi_signal,
                'macd_signal': macd_signal,
                'bollinger_signal': bollinger_signal,
                'trend_confirmation': trend_confirmation
            })
            
        except Exception as e:
            self.logger.error(f"生成交易信号失败: {e}")
            signal['reasons'].append(f"信号生成错误: {e}")
        
        return signal
    
    def _get_ma_signal(self) -> Dict[str, Any]:
        """获取移动平均线信号"""
        try:
            sma_short = self.technical_indicators['sma_short'][-1] if self.technical_indicators['sma_short'] else None
            sma_long = self.technical_indicators['sma_long'][-1] if self.technical_indicators['sma_long'] else None
            
            if sma_short is None or sma_long is None:
                return {'bullish': False, 'bearish': False, 'reason': '数据不足'}
            
            bullish = sma_short > sma_long
            bearish = sma_short < sma_long
            
            return {
                'bullish': bullish,
                'bearish': bearish,
                'sma_short': sma_short,
                'sma_long': sma_long,
                'reason': f"短均线{'高于' if bullish else '低于'}长均线"
            }
        except Exception as e:
            return {'bullish': False, 'bearish': False, 'reason': f'计算错误: {e}'}
    
    def _get_rsi_signal(self) -> Dict[str, Any]:
        """获取RSI信号"""
        try:
            rsi = self.technical_indicators['rsi'][-1] if self.technical_indicators['rsi'] else None
            
            if rsi is None:
                return {'bullish': False, 'bearish': False, 'reason': 'RSI数据不足'}
            
            # RSI > 70 超买（看跌信号），RSI < 30 超卖（看涨信号）
            bullish = rsi < 30
            bearish = rsi > 70
            
            return {
                'bullish': bullish,
                'bearish': bearish,
                'rsi': rsi,
                'reason': f"RSI {'超卖' if bullish else '超买' if bearish else '正常'}: {rsi:.2f}"
            }
        except Exception as e:
            return {'bullish': False, 'bearish': False, 'reason': f'RSI计算错误: {e}'}
    
    def _get_macd_signal(self) -> Dict[str, Any]:
        """获取MACD信号"""
        try:
            macd_data = self.technical_indicators['macd'][-1] if self.technical_indicators['macd'] else {}
            
            if not macd_data:
                return {'bullish': False, 'bearish': False, 'reason': 'MACD数据不足'}
            
            macd_line = macd_data.get('macd', Decimal('0'))
            signal_line = macd_data.get('signal', Decimal('0'))
            histogram = macd_data.get('histogram', Decimal('0'))
            
            # MACD线上穿信号线为看涨，下穿为看跌
            bullish = macd_line > signal_line and histogram > 0
            bearish = macd_line < signal_line and histogram < 0
            
            return {
                'bullish': bullish,
                'bearish': bearish,
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram,
                'reason': f"MACD {'金叉' if bullish else '死叉' if bearish else '横盘'}"
            }
        except Exception as e:
            return {'bullish': False, 'bearish': False, 'reason': f'MACD计算错误: {e}'}
    
    def _get_bollinger_signal(self) -> Dict[str, Any]:
        """获取布林带信号"""
        try:
            bollinger = self.technical_indicators['bollinger']
            
            if not bollinger:
                return {'bullish': False, 'bearish': False, 'reason': '布林带数据不足'}
            
            current_price = self.trend_analyzer.price_history[-1] if self.trend_analyzer.price_history else None
            
            if current_price is None:
                return {'bullish': False, 'bearish': False, 'reason': '价格数据不足'}
            
            upper_band = bollinger.get('upper', Decimal('0'))
            lower_band = bollinger.get('lower', Decimal('0'))
            middle_band = bollinger.get('middle', Decimal('0'))
            
            # 价格触及下轨为看涨信号，触及上轨为看跌信号
            bullish = current_price <= lower_band
            bearish = current_price >= upper_band
            
            return {
                'bullish': bullish,
                'bearish': bearish,
                'current_price': current_price,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'middle_band': middle_band,
                'reason': f"价格{'触下轨' if bullish else '触上轨' if bearish else '在中轨'}"
            }
        except Exception as e:
            return {'bullish': False, 'bearish': False, 'reason': f'布林带计算错误: {e}'}
    
    def _check_trend_confirmation(self, trend_analysis: Dict[str, Any], ma_signal: Dict[str, Any]) -> Dict[str, bool]:
        """检查趋势确认"""
        try:
            # 基础趋势确认
            bullish_trend = trend_analysis['trend'] == 'bullish' and trend_analysis['strength'] > self.strength_threshold
            bearish_trend = trend_analysis['trend'] == 'bearish' and trend_analysis['strength'] > self.strength_threshold
            
            # 成交量确认
            volume_confirmation = trend_analysis.get('volume_trend', Decimal('0')) > Decimal('0')
            
            # 综合确认
            bullish = bullish_trend and (ma_signal.get('bullish', False) or volume_confirmation)
            bearish = bearish_trend and (ma_signal.get('bearish', False) or volume_confirmation)
            
            return {
                'bullish': bullish,
                'bearish': bearish,
                'trend_strength': trend_analysis['strength'],
                'volume_confirmation': volume_confirmation
            }
        except Exception as e:
            self.logger.error(f"趋势确认检查失败: {e}")
            return {'bullish': False, 'bearish': False}
    
    async def _generate_buy_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成买入订单"""
        try:
            orders = []
            
            # 计算订单数量
            quantity = self._calculate_position_size(market_data, 'long')
            
            if quantity <= 0:
                return orders
            
            # 主订单：限价单
            price_buffer = Decimal('0.001')  # 0.1%价格缓冲
            limit_price = market_data.current_price * (Decimal('1') - price_buffer)
            
            order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_buy_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.BUY,
                quantity=quantity,
                price=limit_price,
                position_side=PositionSide.LONG,
                client_order_id=f"trend_buy_{int(datetime.now().timestamp())}"
            )
            orders.append(order)
            
            # 止损订单
            stop_price = market_data.current_price * (Decimal('1') - self.config.stop_loss)
            stop_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_stop_buy_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.STOP,
                order_side=OrderSide.SELL,
                quantity=quantity,
                stop_price=stop_price,
                position_side=PositionSide.LONG,
                client_order_id=f"trend_stop_buy_{int(datetime.now().timestamp())}"
            )
            orders.append(stop_order)
            
            self.logger.info(f"生成买入订单: 数量={quantity}, 价格={limit_price}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成买入订单失败: {e}")
            return []
    
    async def _generate_sell_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成卖出订单"""
        try:
            orders = []
            
            # 计算订单数量
            quantity = self._calculate_position_size(market_data, 'short')
            
            if quantity <= 0:
                return orders
            
            # 主订单：限价单
            price_buffer = Decimal('0.001')  # 0.1%价格缓冲
            limit_price = market_data.current_price * (Decimal('1') + price_buffer)
            
            order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_sell_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.LIMIT,
                order_side=OrderSide.SELL,
                quantity=quantity,
                price=limit_price,
                position_side=PositionSide.SHORT,
                client_order_id=f"trend_sell_{int(datetime.now().timestamp())}"
            )
            orders.append(order)
            
            # 止损订单
            stop_price = market_data.current_price * (Decimal('1') + self.config.stop_loss)
            stop_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_stop_sell_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.STOP,
                order_side=OrderSide.BUY,
                quantity=quantity,
                stop_price=stop_price,
                position_side=PositionSide.SHORT,
                client_order_id=f"trend_stop_sell_{int(datetime.now().timestamp())}"
            )
            orders.append(stop_order)
            
            self.logger.info(f"生成卖出订单: 数量={quantity}, 价格={limit_price}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成卖出订单失败: {e}")
            return []
    
    async def _generate_close_long_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成平多头订单"""
        try:
            if self.state.current_position.quantity <= 0:
                return []
            
            orders = []
            
            # 平仓订单：市价单
            close_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_close_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.SELL,
                quantity=abs(self.state.current_position.quantity),
                position_side=PositionSide.LONG,
                client_order_id=f"trend_close_long_{int(datetime.now().timestamp())}"
            )
            orders.append(close_order)
            
            self.logger.info(f"生成平多头订单: 数量={abs(self.state.current_position.quantity)}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成平多头订单失败: {e}")
            return []
    
    async def _generate_close_short_orders(self, market_data: FuturesMarketData, signal: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """生成平空头订单"""
        try:
            if self.state.current_position.quantity >= 0:
                return []
            
            orders = []
            
            # 平仓订单：市价单
            close_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_close_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.BUY,
                quantity=abs(self.state.current_position.quantity),
                position_side=PositionSide.SHORT,
                client_order_id=f"trend_close_short_{int(datetime.now().timestamp())}"
            )
            orders.append(close_order)
            
            self.logger.info(f"生成平空头订单: 数量={abs(self.state.current_position.quantity)}")
            return orders
            
        except Exception as e:
            self.logger.error(f"生成平空头订单失败: {e}")
            return []
    
    def _calculate_position_size(self, market_data: FuturesMarketData, direction: str) -> Decimal:
        """计算仓位大小"""
        try:
            # 基础仓位大小
            base_size = self.config.base_quantity
            
            # 根据趋势强度调整
            trend_strength = self.trend_analyzer.analyze_trend(self.trend_period)['strength']
            strength_multiplier = min(trend_strength / self.strength_threshold, Decimal('2'))  # 最大2倍
            
            # 根据保证金情况调整
            margin_buffer = Decimal('0.8')  # 使用80%的保证金
            max_size = self.config.max_position_size * margin_buffer
            
            # 计算最终仓位大小
            final_size = base_size * strength_multiplier
            
            # 限制在最大仓位内
            final_size = min(final_size, max_size)
            
            # 确保订单大小在允许范围内
            final_size = max(self.config.min_order_size, min(final_size, self.config.max_order_size))
            
            self.logger.debug(f"计算仓位大小: 基础={base_size}, 强度倍数={strength_multiplier}, 最终={final_size}")
            return final_size
            
        except Exception as e:
            self.logger.error(f"计算仓位大小失败: {e}")
            return self.config.min_order_size
    
    def _record_signal(self, signal: Dict[str, Any]):
        """记录交易信号"""
        try:
            self.signal_history.append({
                'timestamp': datetime.now(),
                'signal': signal,
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
                f"交易信号: {signal['action']}, "
                f"置信度: {signal['confidence']:.2f}, "
                f"强度: {signal['strength']:.2f}, "
                f"原因: {'; '.join(signal['reasons'])}"
            )
            
        except Exception as e:
            self.logger.error(f"记录信号失败: {e}")
    
    async def process_order_result(self, order_result: FuturesOrderResult) -> bool:
        """处理订单执行结果"""
        try:
            self.update_state_after_order(order_result, self.last_market_data)
            
            # 更新保证金信息
            if order_result.success and self.state.current_position:
                self.state.current_position.margin_used = order_result.commission  # 简化处理
                self.state.total_margin_used = order_result.commission
            
            # 记录资金费率影响
            if order_result.funding_rate:
                funding_impact = abs(self.state.current_position.quantity) * self.last_market_data.current_price * order_result.funding_rate
                self.state.funding_rate_paid += funding_impact
            
            self.logger.info(f"订单处理完成: {order_result.order_id}, 成功: {order_result.success}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理订单结果失败: {e}")
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
                
                if order_result.order_id.startswith(f"{self.config.strategy_id}_buy_"):
                    # 买入订单
                    self.state.current_position.quantity += order_result.filled_quantity
                elif order_result.order_id.startswith(f"{self.config.strategy_id}_sell_"):
                    # 卖出订单
                    self.state.current_position.quantity -= order_result.filled_quantity
                elif "close" in order_result.order_id:
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
