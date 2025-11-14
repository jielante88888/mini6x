"""
市场预警条件处理器
提供各种市场预警和触发条件类型
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    ConditionType
)


class AlertType(Enum):
    """预警类型枚举"""
    PRICE_CHANGE = "price_change"
    PRICE_BREAKOUT = "price_breakout"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DIVERGENCE = "volume_divergence"
    TECHNICAL_BREAKOUT = "technical_breakout"
    MOVING_AVERAGE_CROSS = "moving_average_cross"
    RSI_OVERSOLD_OVERBOUGHT = "rsi_oversold_overbought"
    SUPPORT_RESISTANCE = "support_resistance"
    TREND_REVERSAL = "trend_reversal"
    CORRELATION_BREAK = "correlation_break"
    VOLATILITY_EXPLOSION = "volatility_explosion"
    GAPPING = "gapping"
    LIQUIDATION_CLUSTER = "liquidation_cluster"
    FUNDING_RATE_SPIKE = "funding_rate_spike"
    OPEN_INTEREST_CHANGE = "open_interest_change"
    MARKET_SENTIMENT = "market_sentiment"
    CUSTOM_ALERT = "custom_alert"


class AlertSeverity(Enum):
    """预警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertDirection(Enum):
    """预警方向"""
    UPWARD = "upward"
    DOWNWARD = "downward"
    BOTH = "both"
    NEUTRAL = "neutral"


@dataclass
class AlertLevel:
    """预警级别数据"""
    name: str
    value: float
    percentage: float
    is_breach: bool
    severity: AlertSeverity


@dataclass
class MarketAlertData:
    """市场预警数据"""
    alert_type: AlertType
    symbol: str
    current_value: float
    threshold_value: float
    severity: AlertSeverity
    direction: AlertDirection
    timestamp: datetime
    details: str
    levels: Optional[List[AlertLevel]] = None
    confidence_score: Optional[float] = None


class MarketAlertCondition(Condition):
    """市场预警条件"""
    
    def __init__(
        self,
        alert_type: AlertType,
        symbol: str,
        operator: ConditionOperator,
        threshold_value: Union[float, Dict[str, Any]],
        direction: AlertDirection = AlertDirection.BOTH,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        lookback_periods: int = 20,
        confidence_threshold: float = 0.7,
        name: str = "",
        description: str = "",
        enabled: bool = True,
        priority: int = 1
    ):
        super().__init__(name=name, description=description, enabled=enabled, priority=priority)
        
        self.alert_type = alert_type
        self.symbol = symbol
        self.operator = operator
        self.threshold_value = threshold_value
        self.direction = direction
        self.severity = severity
        self.lookback_periods = lookback_periods
        self.confidence_threshold = confidence_threshold
        
        # 数据存储
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.alert_history: List[MarketAlertData] = []
        self.statistics: Dict[str, Any] = {}
        self.alert_levels: List[AlertLevel] = []
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.MARKET_ALERT
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估市场预警条件"""
        try:
            # 更新历史数据
            self._update_history(market_data)
            
            # 根据预警类型执行评估
            alert_data = self._evaluate_alert_type(market_data)
            
            # 记录预警
            if alert_data:
                self.alert_history.append(alert_data)
                self._update_statistics(alert_data)
                
                # 保持历史数据大小
                if len(self.alert_history) > 1000:
                    self.alert_history = self.alert_history[-500:]
            
            # 评估条件是否满足
            if alert_data and self._check_condition(alert_data):
                return ConditionResult(
                    True, 
                    alert_data, 
                    f"{alert_type_to_chinese(self.alert_type)}预警: {alert_data.details}"
                )
            else:
                return ConditionResult(
                    False, 
                    alert_data, 
                    "预警条件未满足"
                )
                
        except Exception as e:
            error_result = ConditionResult(
                False, 
                None, 
                f"市场预警评估错误: {str(e)}"
            )
            self._update_statistics_error(str(e))
            return error_result
    
    def _update_history(self, market_data: MarketData):
        """更新历史数据"""
        self.price_history.append(market_data.price)
        self.volume_history.append(market_data.volume_24h)
        
        # 保持历史数据大小
        max_history = max(self.lookback_periods * 2, 100)
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-self.lookback_periods:]
        if len(self.volume_history) > max_history:
            self.volume_history = self.volume_history[-self.lookback_periods:]
    
    def _evaluate_alert_type(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """评估具体的预警类型"""
        evaluators = {
            AlertType.PRICE_CHANGE: self._check_price_change,
            AlertType.PRICE_BREAKOUT: self._check_price_breakout,
            AlertType.VOLUME_SPIKE: self._check_volume_spike,
            AlertType.VOLUME_DIVERGENCE: self._check_volume_divergence,
            AlertType.TECHNICAL_BREAKOUT: self._check_technical_breakout,
            AlertType.MOVING_AVERAGE_CROSS: self._check_moving_average_cross,
            AlertType.RSI_OVERSOLD_OVERBOUGHT: self._check_rsi_levels,
            AlertType.SUPPORT_RESISTANCE: self._check_support_resistance,
            AlertType.TREND_REVERSAL: self._check_trend_reversal,
            AlertType.CORRELATION_BREAK: self._check_correlation_break,
            AlertType.VOLATILITY_EXPLOSION: self._check_volatility_explosion,
            AlertType.GAPPING: self._check_gapping,
            AlertType.LIQUIDATION_CLUSTER: self._check_liquidation_cluster,
            AlertType.FUNDING_RATE_SPIKE: self._check_funding_rate_spike,
            AlertType.OPEN_INTEREST_CHANGE: self._check_open_interest_change,
            AlertType.MARKET_SENTIMENT: self._check_market_sentiment,
            AlertType.CUSTOM_ALERT: self._check_custom_alert,
        }
        
        evaluator = evaluators.get(self.alert_type)
        if evaluator:
            return evaluator(market_data)
        else:
            return None
    
    def _check_price_change(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查价格变动预警"""
        if len(self.price_history) < self.lookback_periods:
            return None
        
        # 计算价格变动
        current_price = market_data.price
        reference_price = self.price_history[-self.lookback_periods]
        
        price_change = (current_price - reference_price) / reference_price * 100
        abs_change = abs(price_change)
        
        # 确定预警级别
        threshold = self.threshold_value if isinstance(self.threshold_value, (int, float)) else 5.0
        
        is_significant_change = abs_change >= threshold
        
        direction = AlertDirection.UPWARD if price_change > 0 else AlertDirection.DOWNWARD
        
        # 检查方向匹配
        if self.direction != AlertDirection.BOTH and self.direction != direction:
            return None
        
        if is_significant_change:
            self._generate_alert_levels(abs_change, threshold, AlertSeverity.HIGH if abs_change > threshold * 2 else AlertSeverity.MEDIUM)
            
            return MarketAlertData(
                alert_type=AlertType.PRICE_CHANGE,
                symbol=self.symbol,
                current_value=abs_change,
                threshold_value=threshold,
                severity=AlertSeverity.HIGH if abs_change > threshold * 2 else AlertSeverity.MEDIUM,
                direction=direction,
                timestamp=datetime.now(),
                details=f"价格变动 {price_change:.2f}% (阈值: {threshold}%)",
                levels=self.alert_levels.copy()
            )
        
        return None
    
    def _check_price_breakout(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查价格突破预警"""
        if len(self.price_history) < self.lookback_periods:
            return None
        
        current_price = market_data.price
        
        # 计算支撑阻力位
        high_prices = self.price_history[-self.lookback_periods:]
        resistance_level = max(high_prices)
        support_level = min(high_prices)
        
        # 检查突破
        upper_breakout = current_price > resistance_level
        lower_breakout = current_price < support_level
        
        # 确定突破方向
        direction = None
        if upper_breakout:
            direction = AlertDirection.UPWARD
        elif lower_breakout:
            direction = AlertDirection.DOWNWARD
        
        if direction and (self.direction == AlertDirection.BOTH or self.direction == direction):
            severity = AlertSeverity.HIGH
            
            self._generate_breakout_levels(current_price, support_level, resistance_level, severity)
            
            return MarketAlertData(
                alert_type=AlertType.PRICE_BREAKOUT,
                symbol=self.symbol,
                current_value=current_price,
                threshold_value=resistance_level if direction == AlertDirection.UPWARD else support_level,
                severity=severity,
                direction=direction,
                timestamp=datetime.now(),
                details=f"价格突破 {direction.value} (当前: {current_price:.4f})",
                levels=self.alert_levels.copy()
            )
        
        return None
    
    def _check_volume_spike(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查成交量激增预警"""
        if len(self.volume_history) < self.lookback_periods:
            return None
        
        current_volume = market_data.volume_24h
        
        # 计算平均成交量
        avg_volume = statistics.mean(self.volume_history[-self.lookback_periods:])
        
        # 计算成交量比率
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        threshold = self.threshold_value if isinstance(self.threshold_value, (int, float)) else 2.0
        
        if volume_ratio >= threshold:
            severity = AlertSeverity.HIGH if volume_ratio >= threshold * 2 else AlertSeverity.MEDIUM
            
            self._generate_volume_levels(volume_ratio, threshold, severity)
            
            return MarketAlertData(
                alert_type=AlertType.VOLUME_SPIKE,
                symbol=self.symbol,
                current_value=volume_ratio,
                threshold_value=threshold,
                severity=severity,
                direction=AlertDirection.UPWARD,
                timestamp=datetime.now(),
                details=f"成交量激增 {volume_ratio:.2f}x (平均: {avg_volume:.0f})",
                levels=self.alert_levels.copy()
            )
        
        return None
    
    def _check_volume_divergence(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查量价背离预警"""
        if len(self.price_history) < self.lookback_periods or len(self.volume_history) < self.lookback_periods:
            return None
        
        # 分析价格和成交量的趋势
        price_trend = self._analyze_trend(self.price_history[-self.lookback_periods:])
        volume_trend = self._analyze_trend(self.volume_history[-self.lookback_periods:])
        
        # 检测背离
        divergence_detected = False
        direction = AlertDirection.NEUTRAL
        
        if price_trend > 0 and volume_trend < 0:
            # 价格上涨但成交量下降
            divergence_detected = True
            direction = AlertDirection.UPWARD
        elif price_trend < 0 and volume_trend > 0:
            # 价格下跌但成交量上升
            divergence_detected = True
            direction = AlertDirection.DOWNWARD
        
        if divergence_detected and (self.direction == AlertDirection.BOTH or self.direction == direction):
            return MarketAlertData(
                alert_type=AlertType.VOLUME_DIVERGENCE,
                symbol=self.symbol,
                current_value=1.0,  # 背离指标
                threshold_value=1.0,
                severity=AlertSeverity.MEDIUM,
                direction=direction,
                timestamp=datetime.now(),
                details=f"量价背离 - 价格趋势: {price_trend:.3f}, 成交量趋势: {volume_trend:.3f}",
                levels=[AlertLevel("背离", 1.0, 100.0, True, AlertSeverity.MEDIUM)]
            )
        
        return None
    
    def _check_technical_breakout(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查技术指标突破预警"""
        # 检查是否有技术指标数据
        if not any([market_data.rsi, market_data.macd, market_data.bollinger_upper, market_data.bollinger_lower]):
            return None
        
        current_price = market_data.price
        alerts = []
        
        # RSI 超买超卖检查
        if market_data.rsi:
            if market_data.rsi >= 70:
                alerts.append(self._create_rsi_alert(market_data.rsi, True))
            elif market_data.rsi <= 30:
                alerts.append(self._create_rsi_alert(market_data.rsi, False))
        
        # 布林带突破检查
        if market_data.bollinger_upper and market_data.bollinger_lower:
            if current_price > market_data.bollinger_upper:
                alerts.append(self._create_bollinger_alert(current_price, market_data.bollinger_upper, True))
            elif current_price < market_data.bollinger_lower:
                alerts.append(self._create_bollinger_alert(current_price, market_data.bollinger_lower, False))
        
        # 返回第一个匹配的预警
        if alerts:
            return alerts[0]
        
        return None
    
    def _check_moving_average_cross(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查移动平均线交叉预警"""
        if not (market_data.moving_average_20 and market_data.moving_average_50):
            return None
        
        ma20 = market_data.moving_average_20
        ma50 = market_data.moving_average_50
        
        # 需要历史数据来确定交叉方向
        if len(self.price_history) < 2:
            return None
        
        prev_ma20 = self.price_history[-2] if len(self.price_history) >= 2 else ma20  # 简化的计算
        prev_ma50 = ma50  # 简化处理
        
        # 检测金叉和死叉
        golden_cross = prev_ma20 <= prev_ma50 and ma20 > ma50
        death_cross = prev_ma20 >= prev_ma50 and ma20 < ma50
        
        if golden_cross:
            direction = AlertDirection.UPWARD
            details = f"金叉出现 (MA20: {ma20:.4f}, MA50: {ma50:.4f})"
        elif death_cross:
            direction = AlertDirection.DOWNWARD
            details = f"死叉出现 (MA20: {ma20:.4f}, MA50: {ma50:.4f})"
        else:
            return None
        
        if self.direction == AlertDirection.BOTH or self.direction == direction:
            return MarketAlertData(
                alert_type=AlertType.MOVING_AVERAGE_CROSS,
                symbol=self.symbol,
                current_value=ma20 - ma50,
                threshold_value=0,
                severity=AlertSeverity.HIGH,
                direction=direction,
                timestamp=datetime.now(),
                details=details,
                levels=[AlertLevel("交叉", ma20 - ma50, 100.0, True, AlertSeverity.HIGH)]
            )
        
        return None
    
    def _check_rsi_levels(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查RSI超买超卖预警"""
        if not market_data.rsi:
            return None
        
        rsi_value = market_data.rsi
        
        # 超买超卖阈值
        overbought_threshold = self.threshold_value.get('overbought', 70) if isinstance(self.threshold_value, dict) else 70
        oversold_threshold = self.threshold_value.get('oversold', 30) if isinstance(self.threshold_value, dict) else 30
        
        if rsi_value >= overbought_threshold:
            direction = AlertDirection.UPWARD
            severity = AlertSeverity.HIGH if rsi_value >= 80 else AlertSeverity.MEDIUM
            details = f"RSI 超买: {rsi_value:.2f} (阈值: {overbought_threshold})"
        elif rsi_value <= oversold_threshold:
            direction = AlertDirection.DOWNWARD
            severity = AlertSeverity.HIGH if rsi_value <= 20 else AlertSeverity.MEDIUM
            details = f"RSI 超卖: {rsi_value:.2f} (阈值: {oversold_threshold})"
        else:
            return None
        
        if self.direction == AlertDirection.BOTH or self.direction == direction:
            self._generate_rsi_levels(rsi_value, oversold_threshold, overbought_threshold, severity)
            
            return MarketAlertData(
                alert_type=AlertType.RSI_OVERSOLD_OVERBOUGHT,
                symbol=self.symbol,
                current_value=rsi_value,
                threshold_value=overbought_threshold if direction == AlertDirection.UPWARD else oversold_threshold,
                severity=severity,
                direction=direction,
                timestamp=datetime.now(),
                details=details,
                levels=self.alert_levels.copy()
            )
        
        return None
    
    def _check_support_resistance(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查支撑阻力位预警"""
        # 这里可以实现更复杂的支撑阻力位计算
        # 暂时返回None，实际应用中需要历史价格数据分析
        return None
    
    def _check_trend_reversal(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查趋势反转预警"""
        if len(self.price_history) < self.lookback_periods:
            return None
        
        # 简化的趋势反转检测
        recent_prices = self.price_history[-self.lookback_periods//2:]
        earlier_prices = self.price_history[-self.lookback_periods:-self.lookback_periods//2] if len(self.price_history) >= self.lookback_periods else []
        
        if len(earlier_prices) < 3:
            return None
        
        recent_trend = self._analyze_trend(recent_prices)
        earlier_trend = self._analyze_trend(earlier_prices)
        
        # 检测趋势反转
        reversal_detected = False
        direction = AlertDirection.NEUTRAL
        
        if earlier_trend > 0 and recent_trend < -0.5:
            reversal_detected = True
            direction = AlertDirection.DOWNWARD
        elif earlier_trend < 0 and recent_trend > 0.5:
            reversal_detected = True
            direction = AlertDirection.UPWARD
        
        if reversal_detected and (self.direction == AlertDirection.BOTH or self.direction == direction):
            return MarketAlertData(
                alert_type=AlertType.TREND_REVERSAL,
                symbol=self.symbol,
                current_value=abs(recent_trend - earlier_trend),
                threshold_value=1.0,
                severity=AlertSeverity.HIGH,
                direction=direction,
                timestamp=datetime.now(),
                details=f"趋势反转检测 - 近期趋势: {recent_trend:.3f}, 早期趋势: {earlier_trend:.3f}",
                levels=[AlertLevel("反转", abs(recent_trend - earlier_trend), 100.0, True, AlertSeverity.HIGH)]
            )
        
        return None
    
    def _check_correlation_break(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查相关性破坏预警"""
        # 这里需要与其他资产的相关性数据
        # 暂时返回None，实际应用中需要市场相关性分析
        return None
    
    def _check_volatility_explosion(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查波动率激增预警"""
        if len(self.price_history) < self.lookback_periods:
            return None
        
        # 计算价格波动率
        recent_prices = self.price_history[-self.lookback_periods:]
        returns = []
        
        for i in range(1, len(recent_prices)):
            returns.append((recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1])
        
        if len(returns) < 3:
            return None
        
        volatility = statistics.stdev(returns)
        threshold = self.threshold_value if isinstance(self.threshold_value, (int, float)) else 0.02
        
        if volatility >= threshold:
            severity = AlertSeverity.HIGH if volatility >= threshold * 2 else AlertSeverity.MEDIUM
            
            return MarketAlertData(
                alert_type=AlertType.VOLATILITY_EXPLOSION,
                symbol=self.symbol,
                current_value=volatility,
                threshold_value=threshold,
                severity=severity,
                direction=AlertDirection.UPWARD,
                timestamp=datetime.now(),
                details=f"波动率激增: {volatility:.4f} (阈值: {threshold})",
                levels=[AlertLevel("波动率", volatility, min(100, volatility/threshold*100), True, severity)]
            )
        
        return None
    
    def _check_gapping(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查跳空预警"""
        if len(self.price_history) < 2:
            return None
        
        current_price = market_data.price
        previous_price = self.price_history[-1]
        
        gap = abs(current_price - previous_price) / previous_price
        
        threshold = self.threshold_value if isinstance(self.threshold_value, (int, float)) else 0.01
        
        if gap >= threshold:
            direction = AlertDirection.UPWARD if current_price > previous_price else AlertDirection.DOWNWARD
            severity = AlertSeverity.HIGH if gap >= threshold * 2 else AlertSeverity.MEDIUM
            
            return MarketAlertData(
                alert_type=AlertType.GAPPING,
                symbol=self.symbol,
                current_value=gap,
                threshold_value=threshold,
                severity=severity,
                direction=direction,
                timestamp=datetime.now(),
                details=f"跳空 {gap*100:.2f}% (当前: {current_price:.4f}, 前一: {previous_price:.4f})",
                levels=[AlertLevel("跳空", gap, min(100, gap/threshold*100), True, severity)]
            )
        
        return None
    
    def _check_liquidation_cluster(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查清算集群预警"""
        # 这里需要清算数据，实际应用中需要接入清算数据源
        return None
    
    def _check_funding_rate_spike(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查资金费率激增预警"""
        if not market_data.funding_rate:
            return None
        
        funding_rate = abs(market_data.funding_rate)  # 使用绝对值
        threshold = self.threshold_value if isinstance(self.threshold_value, (int, float)) else 0.001
        
        if funding_rate >= threshold:
            direction = AlertDirection.UPWARD if market_data.funding_rate > 0 else AlertDirection.DOWNWARD
            severity = AlertSeverity.HIGH if funding_rate >= threshold * 2 else AlertSeverity.MEDIUM
            
            return MarketAlertData(
                alert_type=AlertType.FUNDING_RATE_SPIKE,
                symbol=self.symbol,
                current_value=funding_rate,
                threshold_value=threshold,
                severity=severity,
                direction=direction,
                timestamp=datetime.now(),
                details=f"资金费率异常: {funding_rate*100:.4f}% (当前: {market_data.funding_rate*100:.4f}%)",
                levels=[AlertLevel("资金费率", funding_rate, min(100, funding_rate/threshold*100), True, severity)]
            )
        
        return None
    
    def _check_open_interest_change(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查持仓量变化预警"""
        if not market_data.open_interest:
            return None
        
        # 这里需要历史持仓量数据来计算变化率
        # 暂时返回None，实际应用中需要存储历史持仓量数据
        return None
    
    def _check_market_sentiment(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查市场情绪预警"""
        # 这里需要市场情绪数据，如恐慌贪婪指数等
        # 暂时返回None，实际应用中需要接入情绪数据源
        return None
    
    def _check_custom_alert(self, market_data: MarketData) -> Optional[MarketAlertData]:
        """检查自定义预警"""
        # 根据自定义逻辑实现
        return None
    
    def _analyze_trend(self, data: List[float]) -> float:
        """分析数据趋势"""
        if len(data) < 2:
            return 0.0
        
        # 使用线性回归计算趋势
        n = len(data)
        x_values = list(range(n))
        
        try:
            slope = statistics.linear_regression(x_values, data).slope
            return slope / statistics.mean(data) if statistics.mean(data) != 0 else 0
        except:
            return 0.0
    
    def _check_condition(self, alert_data: MarketAlertData) -> bool:
        """检查条件是否满足"""
        # 根据操作符判断
        current_value = alert_data.current_value
        threshold_value = alert_data.threshold_value
        
        operator = self.operator
        
        if operator == ConditionOperator.GREATER_THAN:
            return current_value > threshold_value
        elif operator == ConditionOperator.GREATER_EQUAL:
            return current_value >= threshold_value
        elif operator == ConditionOperator.LESS_THAN:
            return current_value < threshold_value
        elif operator == ConditionOperator.LESS_EQUAL:
            return current_value <= threshold_value
        elif operator == ConditionOperator.EQUAL:
            return abs(current_value - threshold_value) < 0.001
        else:
            # 对于其他操作符，默认返回True
            return True
    
    def _generate_alert_levels(self, current_value: float, threshold: float, base_severity: AlertSeverity):
        """生成预警级别"""
        self.alert_levels = [
            AlertLevel("低风险", threshold * 0.5, 25.0, False, AlertSeverity.LOW),
            AlertLevel("中风险", threshold, 50.0, False, AlertSeverity.MEDIUM),
            AlertLevel("高风险", threshold * 1.5, 75.0, current_value >= threshold * 1.5, base_severity),
            AlertLevel("极高风险", threshold * 2.0, 100.0, current_value >= threshold * 2.0, AlertSeverity.CRITICAL)
        ]
    
    def _generate_breakout_levels(self, current: float, support: float, resistance: float, severity: AlertSeverity):
        """生成突破级别"""
        range_size = resistance - support
        self.alert_levels = [
            AlertLevel("接近支撑", support + range_size * 0.25, 25.0, False, AlertSeverity.LOW),
            AlertLevel("接近阻力", resistance - range_size * 0.25, 50.0, False, AlertSeverity.MEDIUM),
            AlertLevel("突破中", current, 75.0, True, severity)
        ]
    
    def _generate_volume_levels(self, ratio: float, threshold: float, severity: AlertSeverity):
        """生成成交量级别"""
        self.alert_levels = [
            AlertLevel("正常", threshold * 0.5, 25.0, False, AlertSeverity.LOW),
            AlertLevel("活跃", threshold, 50.0, False, AlertSeverity.MEDIUM),
            AlertLevel("激增", threshold * 1.5, 75.0, ratio >= threshold * 1.5, severity),
            AlertLevel("极度活跃", threshold * 2.0, 100.0, ratio >= threshold * 2.0, AlertSeverity.CRITICAL)
        ]
    
    def _generate_rsi_levels(self, rsi: float, oversold: float, overbought: float, severity: AlertSeverity):
        """生成RSI级别"""
        self.alert_levels = [
            AlertLevel("超卖", oversold, 25.0, rsi <= oversold, AlertSeverity.LOW),
            AlertLevel("正常", 50, 50.0, oversold < rsi < overbought, AlertSeverity.LOW),
            AlertLevel("超买", overbought, 75.0, rsi >= overbought, severity)
        ]
    
    def _create_rsi_alert(self, rsi_value: float, is_overbought: bool) -> MarketAlertData:
        """创建RSI预警"""
        direction = AlertDirection.UPWARD if is_overbought else AlertDirection.DOWNWARD
        severity = AlertSeverity.HIGH if (is_overbought and rsi_value >= 80) or (not is_overbought and rsi_value <= 20) else AlertSeverity.MEDIUM
        
        return MarketAlertData(
            alert_type=AlertType.RSI_OVERSOLD_OVERBOUGHT,
            symbol=self.symbol,
            current_value=rsi_value,
            threshold_value=70 if is_overbought else 30,
            severity=severity,
            direction=direction,
            timestamp=datetime.now(),
            details=f"RSI {'超买' if is_overbought else '超卖'}: {rsi_value:.2f}",
            levels=self._get_rsi_levels(rsi_value, is_overbought)
        )
    
    def _create_bollinger_alert(self, price: float, level: float, is_upper: bool) -> MarketAlertData:
        """创建布林带预警"""
        direction = AlertDirection.UPWARD if is_upper else AlertDirection.DOWNWARD
        severity = AlertSeverity.HIGH
        
        return MarketAlertData(
            alert_type=AlertType.TECHNICAL_BREAKOUT,
            symbol=self.symbol,
            current_value=price,
            threshold_value=level,
            severity=severity,
            direction=direction,
            timestamp=datetime.now(),
            details=f"布林带{'上轨' if is_upper else '下轨'}突破: {price:.4f}",
            levels=[AlertLevel("突破", price, 100.0, True, severity)]
        )
    
    def _get_rsi_levels(self, rsi: float, is_overbought: bool) -> List[AlertLevel]:
        """获取RSI级别"""
        return [
            AlertLevel("超卖区间", 30, 25.0, rsi <= 30, AlertSeverity.LOW),
            AlertLevel("正常区间", 50, 50.0, 30 < rsi < 70, AlertSeverity.LOW),
            AlertLevel("超买区间", 70, 75.0, rsi >= 70, AlertSeverity.MEDIUM)
        ]
    
    def _update_statistics(self, alert_data: MarketAlertData):
        """更新统计数据"""
        if not self.statistics:
            self.statistics = {
                "total_alerts": 0,
                "alerts_by_type": {},
                "alerts_by_severity": {},
                "alerts_by_direction": {},
                "latest_alert": None
            }
        
        self.statistics["total_alerts"] += 1
        
        # 按类型统计
        alert_type = alert_data.alert_type.value
        self.statistics["alerts_by_type"][alert_type] = self.statistics["alerts_by_type"].get(alert_type, 0) + 1
        
        # 按严重程度统计
        severity = alert_data.severity.value
        self.statistics["alerts_by_severity"][severity] = self.statistics["alerts_by_severity"].get(severity, 0) + 1
        
        # 按方向统计
        direction = alert_data.direction.value
        self.statistics["alerts_by_direction"][direction] = self.statistics["alerts_by_direction"].get(direction, 0) + 1
        
        self.statistics["latest_alert"] = alert_data.to_dict() if hasattr(alert_data, 'to_dict') else {
            "timestamp": alert_data.timestamp.isoformat(),
            "type": alert_data.alert_type.value,
            "symbol": alert_data.symbol,
            "details": alert_data.details
        }
    
    def _update_statistics_error(self, error: str):
        """更新错误统计"""
        if not self.statistics:
            self.statistics = {}
        
        if "errors" not in self.statistics:
            self.statistics["errors"] = []
        
        self.statistics["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        
        # 保持错误记录数量
        if len(self.statistics["errors"]) > 50:
            self.statistics["errors"] = self.statistics["errors"][-25:]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取预警统计信息"""
        if not self.statistics:
            return {"message": "没有预警统计数据"}
        
        recent_alerts = [a for a in self.alert_history if a.timestamp > datetime.now() - timedelta(hours=24)]
        
        stats = self.statistics.copy()
        stats.update({
            "recent_alerts_count": len(recent_alerts),
            "alert_frequency_24h": len(recent_alerts) / 24 if recent_alerts else 0,
            "most_common_alert_type": max(self.statistics.get("alerts_by_type", {}), key=self.statistics["alerts_by_type"].get) if self.statistics.get("alerts_by_type") else None,
            "alert_rate_by_severity": self.statistics.get("alerts_by_severity", {}),
            "direction_distribution": self.statistics.get("alerts_by_direction", {})
        })
        
        return stats
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的预警"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alert_history if a.timestamp >= cutoff_time]
        
        return [
            {
                "timestamp": alert.timestamp.isoformat(),
                "type": alert.alert_type.value,
                "symbol": alert.symbol,
                "severity": alert.severity.value,
                "direction": alert.direction.value,
                "details": alert.details,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value
            }
            for alert in recent_alerts
        ]
    
    def clear_alert_history(self):
        """清除预警历史"""
        self.alert_history.clear()
        self.statistics.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        
        # 转换threshold_value为可序列化格式
        threshold_value = self.threshold_value
        if isinstance(threshold_value, (int, float)):
            threshold_value = float(threshold_value)
        
        data.update({
            "alert_type": self.alert_type.value,
            "symbol": self.symbol,
            "operator": self.operator.value,
            "threshold_value": threshold_value,
            "direction": self.direction.value,
            "severity": self.severity.value,
            "lookback_periods": self.lookback_periods,
            "confidence_threshold": self.confidence_threshold,
            "alert_statistics": self.get_alert_statistics(),
            "recent_alerts": self.get_recent_alerts()
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'MarketAlertCondition':
        """从字典创建实例"""
        super().from_dict(data)
        
        self.alert_type = AlertType(data.get("alert_type", AlertType.PRICE_CHANGE.value))
        self.symbol = data.get("symbol", "")
        self.operator = ConditionOperator(data.get("operator", ConditionOperator.GREATER_THAN.value))
        self.threshold_value = data.get("threshold_value", 5.0)
        self.direction = AlertDirection(data.get("direction", AlertDirection.BOTH.value))
        self.severity = AlertSeverity(data.get("severity", AlertSeverity.MEDIUM.value))
        self.lookback_periods = data.get("lookback_periods", 20)
        self.confidence_threshold = data.get("confidence_threshold", 0.7)
        
        return self


def alert_type_to_chinese(alert_type: AlertType) -> str:
    """将预警类型转换为中文"""
    translations = {
        AlertType.PRICE_CHANGE: "价格变动",
        AlertType.PRICE_BREAKOUT: "价格突破",
        AlertType.VOLUME_SPIKE: "成交量激增",
        AlertType.VOLUME_DIVERGENCE: "量价背离",
        AlertType.TECHNICAL_BREAKOUT: "技术突破",
        AlertType.MOVING_AVERAGE_CROSS: "均线交叉",
        AlertType.RSI_OVERSOLD_OVERBOUGHT: "RSI超买超卖",
        AlertType.SUPPORT_RESISTANCE: "支撑阻力",
        AlertType.TREND_REVERSAL: "趋势反转",
        AlertType.CORRELATION_BREAK: "相关性破坏",
        AlertType.VOLATILITY_EXPLOSION: "波动率激增",
        AlertType.GAPPING: "跳空",
        AlertType.LIQUIDATION_CLUSTER: "清算集群",
        AlertType.FUNDING_RATE_SPIKE: "资金费率异常",
        AlertType.OPEN_INTEREST_CHANGE: "持仓量变化",
        AlertType.MARKET_SENTIMENT: "市场情绪",
        AlertType.CUSTOM_ALERT: "自定义预警"
    }
    return translations.get(alert_type, alert_type.value)