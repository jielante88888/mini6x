"""
技术指标条件处理器
支持各种技术指标的条件判断和信号分析
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import statistics

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    TechnicalIndicatorCondition as BaseTechnicalIndicatorCondition
)


class IndicatorType(Enum):
    """技术指标类型枚举"""
    # 趋势指标
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_MOVING_AVERAGE = "ema"
    MACD = "macd"
    MACD_SIGNAL = "macd_signal"
    MACD_HISTOGRAM = "macd_histogram"
    
    # 动量指标
    RSI = "rsi"
    STOCHASTIC_K = "stochastic_k"
    STOCHASTIC_D = "stochastic_d"
    WILLIAMS_R = "williams_r"
    
    # 波动率指标
    BOLLINGER_UPPER = "bollinger_upper"
    BOLLINGER_MIDDLE = "bollinger_middle"
    BOLLINGER_LOWER = "bollinger_lower"
    ATR = "atr"  # Average True Range
    
    # 成交量指标
    OBV = "obv",  # On-Balance Volume
    VWAP = "vwap",  # Volume Weighted Average Price
    
    # 支撑阻力
    SUPPORT_LEVEL = "support_level"
    RESISTANCE_LEVEL = "resistance_level"
    
    # 自定义指标
    CUSTOM = "custom"


class SignalType(Enum):
    """信号类型枚举"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    STRONG_BULLISH = "strong_bullish"
    STRONG_BEARISH = "strong_bearish"


class TechnicalIndicatorCondition(BaseTechnicalIndicatorCondition):
    """技术指标条件"""
    
    def __init__(
        self,
        symbol: str,
        indicator: IndicatorType,
        operator: ConditionOperator,
        threshold: Union[float, str],
        period: int = 14,
        comparison_indicator: Optional[IndicatorType] = None,
        signal_type: Optional[SignalType] = None,
        name: str = "",
        description: str = "",
        alert_level: str = "normal"
    ):
        # 调用父类初始化
        super().__init__(
            symbol=symbol,
            indicator=indicator.value,
            operator=operator,
            threshold=threshold,
            name=name,
            description=description
        )
        
        self.indicator_type = indicator
        self.period = period
        self.comparison_indicator = comparison_indicator
        self.signal_type = signal_type
        self.alert_level = alert_level
        
        # 数据存储
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.high_history: List[float] = []
        self.low_history: List[float] = []
        self.indicator_values: List[float] = []
        self.signal_history: List[SignalType] = []
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估技术指标条件"""
        try:
            # 更新历史数据
            self._update_historical_data(market_data)
            
            # 计算指标值
            indicator_value = self._calculate_indicator_value(market_data)
            if indicator_value is None:
                return ConditionResult(
                    False, 
                    None, 
                    f"无法计算 {self.indicator_type.value} 指标"
                )
            
            # 评估条件
            result = self._evaluate_condition(indicator_value, market_data)
            
            # 更新统计信息
            self._update_statistics(result)
            
            return result
            
        except Exception as e:
            error_result = ConditionResult(
                False, 
                None, 
                f"技术指标条件评估错误: {str(e)}"
            )
            self._update_statistics(error_result)
            return error_result
    
    def _update_historical_data(self, market_data: MarketData):
        """更新历史数据"""
        self.price_history.append(market_data.price)
        self.volume_history.append(market_data.volume_24h)
        self.high_history.append(market_data.high_24h)
        self.low_history.append(market_data.low_24h)
        
        # 保持历史数据长度
        max_history = max(self.period * 2, 100)
        for history_list in [self.price_history, self.volume_history, self.high_history, self.low_history]:
            if len(history_list) > max_history:
                history_list[:] = history_list[-max_history:]
    
    def _calculate_indicator_value(self, market_data: MarketData) -> Optional[float]:
        """计算技术指标值"""
        try:
            # 如果市场数据已经有指标值，直接使用
            if hasattr(market_data, self._get_market_data_field()):
                return getattr(market_data, self._get_market_data_field())
            
            # 否则计算指标值
            return self._calculate_indicator_from_history()
            
        except Exception:
            return None
    
    def _get_market_data_field(self) -> str:
        """获取市场数据中对应的字段名"""
        field_mapping = {
            IndicatorType.RSI: "rsi",
            IndicatorType.MACD: "macd",
            IndicatorType.MACD_SIGNAL: "macd_signal",
            IndicatorType.BOLLINGER_UPPER: "bollinger_upper",
            IndicatorType.BOLLINGER_LOWER: "bollinger_lower",
            IndicatorType.MOVING_AVERAGE_20: "moving_average_20",
            IndicatorType.MOVING_AVERAGE_50: "moving_average_50",
        }
        return field_mapping.get(self.indicator_type, "")
    
    def _calculate_indicator_from_history(self) -> Optional[float]:
        """从历史数据计算指标值"""
        if len(self.price_history) < self.period:
            return None
        
        prices = self.price_history[-self.period:]
        volumes = self.volume_history[-self.period:] if self.volume_history else []
        
        switcher = {
            IndicatorType.MOVING_AVERAGE: self._calculate_sma,
            IndicatorType.EXPONENTIAL_MOVING_AVERAGE: self._calculate_ema,
            IndicatorType.RSI: self._calculate_rsi,
            IndicatorType.MACD: self._calculate_macd,
            IndicatorType.MACD_SIGNAL: self._calculate_macd_signal,
            IndicatorType.BOLLINGER_UPPER: lambda p, v: self._calculate_bollinger_bands(p)[0],
            IndicatorType.BOLLINGER_MIDDLE: lambda p, v: self._calculate_bollinger_bands(p)[1],
            IndicatorType.BOLLINGER_LOWER: lambda p, v: self._calculate_bollinger_bands(p)[2],
            IndicatorType.ATR: self._calculate_atr,
            IndicatorType.VWAP: self._calculate_vwap,
        }
        
        calculator = switcher.get(self.indicator_type)
        if calculator:
            return calculator(prices, volumes)
        
        return None
    
    def _calculate_sma(self, prices: List[float], volumes: List[float]) -> float:
        """计算简单移动平均"""
        return statistics.mean(prices)
    
    def _calculate_ema(self, prices: List[float], volumes: List[float]) -> float:
        """计算指数移动平均"""
        if len(prices) == 0:
            return 0.0
        
        multiplier = 2 / (len(prices) + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], volumes: List[float]) -> float:
        """计算RSI指标"""
        if len(prices) < 2:
            return 50.0  # 默认中性值
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if not gains or not losses:
            return 50.0
        
        avg_gain = statistics.mean(gains)
        avg_loss = statistics.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: List[float], volumes: List[float]) -> float:
        """计算MACD指标"""
        if len(prices) < 26:
            return 0.0
        
        # 使用12和26周期EMA计算MACD
        ema12 = self._calculate_ema(prices[-12:], volumes)
        ema26 = self._calculate_ema(prices[-26:], volumes)
        return ema12 - ema26
    
    def _calculate_macd_signal(self, prices: List[float], volumes: List[float]) -> float:
        """计算MACD信号线"""
        if len(prices) < 9:
            return 0.0
        
        macd_values = []
        for i in range(max(0, len(prices) - 9), len(prices)):
            subset_prices = prices[:i+1]
            if len(subset_prices) >= 12:
                macd_value = self._calculate_macd(subset_prices, volumes)
                macd_values.append(macd_value)
        
        if len(macd_values) >= 9:
            return self._calculate_ema(macd_values[-9:], volumes[-9:])
        
        return 0.0
    
    def _calculate_bollinger_bands(self, prices: List[float]) -> Tuple[float, float, float]:
        """计算布林带"""
        if len(prices) < self.period:
            return (prices[-1], prices[-1], prices[-1]) if prices else (0, 0, 0)
        
        sma = statistics.mean(prices[-self.period:])
        variance = statistics.variance(prices[-self.period:]) if len(prices) >= 2 else 0
        std_dev = math.sqrt(variance)
        
        upper_band = sma + (std_dev * 2)
        middle_band = sma
        lower_band = sma - (std_dev * 2)
        
        return (upper_band, middle_band, lower_band)
    
    def _calculate_atr(self, prices: List[float], volumes: List[float]) -> float:
        """计算ATR (平均真实范围)"""
        if len(prices) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(prices)):
            high = self.high_history[-(len(prices) - i)] if len(self.high_history) >= len(prices) - i else prices[i]
            low = self.low_history[-(len(prices) - i)] if len(self.low_history) >= len(prices) - i else prices[i]
            prev_close = prices[i-1]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return statistics.mean(true_ranges) if true_ranges else 0.0
    
    def _calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        """计算VWAP (成交量加权平均价格)"""
        if not prices or not volumes or len(prices) != len(volumes):
            return prices[-1] if prices else 0.0
        
        total_price_volume = sum(p * v for p, v in zip(prices, volumes))
        total_volume = sum(volumes)
        
        return total_price_volume / total_volume if total_volume > 0 else prices[-1]
    
    def _evaluate_condition(self, indicator_value: float, market_data: MarketData) -> ConditionResult:
        """评估指标条件"""
        operator = self.operator
        threshold = self.threshold
        
        # 如果指定了比较指标
        if self.comparison_indicator:
            comparison_value = self._get_comparison_indicator_value()
            if comparison_value is not None:
                return self._compare_indicators(indicator_value, comparison_value)
        
        # 如果指定了信号类型
        if self.signal_type:
            signal = self._determine_signal(indicator_value, market_data)
            satisfied = signal == self.signal_type
            details = f"信号: {signal.value}, 目标信号: {self.signal_type.value}"
            return ConditionResult(satisfied, indicator_value, details)
        
        # 标准的数值比较
        return self._standard_comparison(indicator_value, threshold)
    
    def _get_comparison_indicator_value(self) -> Optional[float]:
        """获取比较指标的值"""
        # 这里需要实现比较指标的计算逻辑
        # 暂时返回None，需要在完整实现中添加
        return None
    
    def _compare_indicators(self, primary: float, secondary: float) -> ConditionResult:
        """比较两个指标值"""
        operator = self.operator
        
        switcher = {
            ConditionOperator.GREATER_THAN: primary > secondary,
            ConditionOperator.GREATER_EQUAL: primary >= secondary,
            ConditionOperator.LESS_THAN: primary < secondary,
            ConditionOperator.LESS_EQUAL: primary <= secondary,
            ConditionOperator.EQUAL: abs(primary - secondary) < 0.01,
            ConditionOperator.NOT_EQUAL: abs(primary - secondary) >= 0.01,
        }
        
        satisfied = switcher.get(operator, False)
        details = f"主指标: {primary:.4f}, 比较指标: {secondary:.4f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, primary, details)
    
    def _standard_comparison(self, value: float, threshold: Union[float, str]) -> ConditionResult:
        """标准数值比较"""
        operator = self.operator
        
        if isinstance(threshold, str):
            # 处理百分比或字符串格式的阈值
            if '%' in threshold:
                threshold = float(threshold.replace('%', '')) / 100
                if operator in [ConditionOperator.GREATER_THAN, ConditionOperator.GREATER_EQUAL]:
                    threshold = value * (1 + threshold)
                else:
                    threshold = value * (1 - threshold)
            else:
                threshold = float(threshold)
        
        switcher = {
            ConditionOperator.GREATER_THAN: value > threshold,
            ConditionOperator.GREATER_EQUAL: value >= threshold,
            ConditionOperator.LESS_THAN: value < threshold,
            ConditionOperator.LESS_EQUAL: value <= threshold,
            ConditionOperator.EQUAL: abs(value - threshold) < 0.01,
            ConditionOperator.NOT_EQUAL: abs(value - threshold) >= 0.01,
        }
        
        satisfied = switcher.get(operator, False)
        details = f"指标值: {value:.4f}, 阈值: {threshold:.4f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, value, details)
    
    def _determine_signal(self, indicator_value: float, market_data: MarketData) -> SignalType:
        """确定技术信号"""
        if self.indicator_type == IndicatorType.RSI:
            return self._rsi_signal(indicator_value)
        elif self.indicator_type in [IndicatorType.MACD, IndicatorType.MACD_SIGNAL]:
            return self._macd_signal(indicator_value, market_data)
        elif self.indicator_type in [IndicatorType.BOLLINGER_UPPER, IndicatorType.BOLLINGER_LOWER]:
            return self._bollinger_signal(indicator_value, market_data)
        else:
            return SignalType.NEUTRAL
    
    def _rsi_signal(self, rsi_value: float) -> SignalType:
        """RSI信号判断"""
        if rsi_value >= 70:
            return SignalType.STRONG_BEARISH
        elif rsi_value >= 60:
            return SignalType.BEARISH
        elif rsi_value <= 30:
            return SignalType.STRONG_BULLISH
        elif rsi_value <= 40:
            return SignalType.BULLISH
        else:
            return SignalType.NEUTRAL
    
    def _macd_signal(self, macd_value: float, market_data: MarketData) -> SignalType:
        """MACD信号判断"""
        if len(self.price_history) < 2:
            return SignalType.NEUTRAL
        
        prev_macd = self._calculate_macd(self.price_history[:-1], self.volume_history[:-1])
        macd_signal = self._calculate_macd_signal(self.price_history, self.volume_history)
        
        current_cross = macd_value > macd_signal
        prev_cross = prev_macd <= self._calculate_macd_signal(self.price_history[:-1], self.volume_history[:-1])
        
        if current_cross and not prev_cross:
            return SignalType.BULLISH
        elif not current_cross and prev_cross:
            return SignalType.BEARISH
        else:
            return SignalType.NEUTRAL
    
    def _bollinger_signal(self, band_value: float, market_data: MarketData) -> SignalType:
        """布林带信号判断"""
        upper, middle, lower = self._calculate_bollinger_bands(self.price_history[-self.period:])
        
        if band_value == upper and market_data.price > upper:
            return SignalType.STRONG_BEARISH  # 价格触及上轨，可能超买
        elif band_value == lower and market_data.price < lower:
            return SignalType.STRONG_BULLISH  # 价格触及下轨，可能超卖
        elif band_value == upper:
            return SignalType.BEARISH
        elif band_value == lower:
            return SignalType.BULLISH
        else:
            return SignalType.NEUTRAL
    
    def get_indicator_statistics(self) -> Dict[str, Any]:
        """获取指标统计信息"""
        if not self.indicator_values:
            return {"message": "没有指标历史数据"}
        
        values = self.indicator_values[-20:]  # 最近20个值
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1] if values else None
        }
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计信息"""
        if not self.signal_history:
            return {"message": "没有信号历史数据"}
        
        signal_counts = {}
        for signal in self.signal_history:
            signal_counts[signal.value] = signal_counts.get(signal.value, 0) + 1
        
        return {
            "total_signals": len(self.signal_history),
            "signal_distribution": signal_counts,
            "latest_signal": self.signal_history[-1].value if self.signal_history else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            "indicator_type": self.indicator_type.value,
            "period": self.period,
            "comparison_indicator": self.comparison_indicator.value if self.comparison_indicator else None,
            "signal_type": self.signal_type.value if self.signal_type else None,
            "alert_level": self.alert_level,
            "price_history": self.price_history[-10:],  # 保存最近10个价格
            "indicator_statistics": self.get_indicator_statistics(),
            "signal_statistics": self.get_signal_statistics()
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'TechnicalIndicatorCondition':
        """从字典创建实例"""
        super().from_dict(data)
        
        self.indicator_type = IndicatorType(data.get("indicator_type", IndicatorType.MOVING_AVERAGE.value))
        self.period = data.get("period", 14)
        self.comparison_indicator = IndicatorType(data.get("comparison_indicator")) if data.get("comparison_indicator") else None
        self.signal_type = SignalType(data.get("signal_type")) if data.get("signal_type") else None
        self.alert_level = data.get("alert_level", "normal")
        self.price_history = data.get("price_history", [])
        
        return self


class IndicatorCrossoverCondition(TechnicalIndicatorCondition):
    """指标交叉条件"""
    
    def __init__(
        self,
        symbol: str,
        primary_indicator: IndicatorType,
        secondary_indicator: IndicatorType,
        crossover_type: str = "golden_cross",  # "golden_cross" 或 "death_cross"
        period: int = 14,
        name: str = "",
        description: str = ""
    ):
        super().__init__(
            symbol=symbol,
            indicator=primary_indicator,
            operator=ConditionOperator.GREATER_THAN,
            threshold=0,  # 不使用标准阈值
            period=period,
            name=name,
            description=description
        )
        
        self.primary_indicator = primary_indicator
        self.secondary_indicator = secondary_indicator
        self.crossover_type = crossover_type
        self.primary_history: List[float] = []
        self.secondary_history: List[float] = []
        self.crossover_count = 0
        self.last_crossover_time: Optional[datetime] = None
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估交叉条件"""
        # 更新数据
        self._update_historical_data(market_data)
        
        # 计算指标值
        primary_value = self._calculate_specific_indicator(self.primary_indicator)
        secondary_value = self._calculate_specific_indicator(self.secondary_indicator)
        
        if primary_value is None or secondary_value is None:
            return ConditionResult(False, None, "无法计算指标值")
        
        # 更新历史
        self.primary_history.append(primary_value)
        self.secondary_history.append(secondary_value)
        
        # 保持历史长度
        if len(self.primary_history) > 50:
            self.primary_history = self.primary_history[-25:]
            self.secondary_history = self.secondary_history[-25:]
        
        # 检查交叉
        crossover_result = self._check_crossover()
        
        if crossover_result.satisfied:
            self.crossover_count += 1
            self.last_crossover_time = datetime.now()
        
        return crossover_result
    
    def _calculate_specific_indicator(self, indicator: IndicatorType) -> Optional[float]:
        """计算特定指标"""
        original_indicator = self.indicator_type
        self.indicator_type = indicator
        
        try:
            result = self._calculate_indicator_from_history()
            return result
        finally:
            self.indicator_type = original_indicator
    
    def _check_crossover(self) -> ConditionResult:
        """检查交叉"""
        if len(self.primary_history) < 2 or len(self.secondary_history) < 2:
            return ConditionResult(False, None, "历史数据不足")
        
        current_primary = self.primary_history[-1]
        current_secondary = self.secondary_history[-1]
        
        prev_primary = self.primary_history[-2]
        prev_secondary = self.secondary_history[-2]
        
        # 检查金叉或死叉
        golden_cross = (prev_primary <= prev_secondary and current_primary > current_secondary)
        death_cross = (prev_primary >= prev_secondary and current_primary < current_secondary)
        
        if self.crossover_type == "golden_cross":
            satisfied = golden_cross
            details = "金叉信号" if satisfied else "未出现金叉"
        else:  # death_cross
            satisfied = death_cross
            details = "死叉信号" if satisfied else "未出现死叉"
        
        return ConditionResult(satisfied, current_primary - current_secondary, details)
