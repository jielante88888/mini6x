"""
成交量条件处理器
提供基于成交量的各种条件类型和评估逻辑
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import statistics
import math

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    VolumeCondition as BaseVolumeCondition
)


class VolumeType(Enum):
    """成交量类型枚举"""
    VOLUME_24H = "volume_24h"
    VOLUME_1H = "volume_1h"
    VOLUME_30M = "volume_30m"
    VOLUME_5M = "volume_5m"
    VOLUME_MOVING_AVERAGE = "volume_ma"
    VOLUME_RATIO = "volume_ratio"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_PERCENTILE = "volume_percentile"
    OBV = "obv"  # On-Balance Volume
    VWAP = "vwap"  # Volume Weighted Average Price
    VOLUME_PROFILE = "volume_profile"


class VolumeAlertLevel(Enum):
    """成交量警告级别"""
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"
    UNUSUAL = "unusual"


class VolumeCondition(BaseVolumeCondition):
    """成交量条件"""
    
    def __init__(
        self,
        symbol: str,
        volume_type: VolumeType,
        operator: ConditionOperator,
        threshold: Union[float, str],
        period: int = 20,
        comparison_period: Optional[int] = None,
        alert_level: VolumeAlertLevel = VolumeAlertLevel.NORMAL,
        name: str = "",
        description: str = ""
    ):
        # 调用父类初始化
        super().__init__(
            symbol=symbol,
            operator=operator,
            threshold=threshold,
            name=name,
            description=description
        )
        
        self.volume_type = volume_type
        self.period = period
        self.comparison_period = comparison_period
        self.alert_level = alert_level
        
        # 数据存储
        self.volume_history: List[float] = []
        self.price_history: List[float] = []
        self.volume_alerts: List[Dict[str, Any]] = []
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估成交量条件"""
        try:
            # 更新历史数据
            self._update_historical_data(market_data)
            
            # 获取成交量值
            current_volume = self._get_volume_value(market_data)
            if current_volume is None:
                return ConditionResult(
                    False, 
                    None, 
                    f"无法获取 {self.symbol} 的 {self.volume_type.value} 成交量"
                )
            
            # 获取比较成交量
            comparison_volume = self._get_comparison_volume(market_data)
            
            # 执行条件检查
            result = self._check_volume_condition(current_volume, comparison_volume)
            
            # 检查成交量警报
            if result.satisfied:
                self._check_volume_alerts(current_volume, comparison_volume)
            
            # 更新统计信息
            self._update_statistics(result)
            
            return result
            
        except Exception as e:
            error_result = ConditionResult(
                False, 
                None, 
                f"成交量条件评估错误: {str(e)}"
            )
            self._update_statistics(error_result)
            return error_result
    
    def _update_historical_data(self, market_data: MarketData):
        """更新历史数据"""
        self.volume_history.append(market_data.volume_24h)
        self.price_history.append(market_data.price)
        
        # 保持历史数据长度
        max_history = max(self.period * 3, 200)
        if len(self.volume_history) > max_history:
            self.volume_history = self.volume_history[-max_history:]
            self.price_history = self.price_history[-max_history:]
    
    def _get_volume_value(self, market_data: MarketData) -> Optional[float]:
        """获取指定类型的当前成交量"""
        switcher = {
            VolumeType.VOLUME_24H: market_data.volume_24h,
            VolumeType.OBV: self._calculate_obv(),
            VolumeType.VWAP: self._calculate_vwap(),
            VolumeType.VOLUME_MOVING_AVERAGE: self._calculate_volume_ma(),
            VolumeType.VOLUME_RATIO: self._calculate_volume_ratio(),
            VolumeType.VOLUME_SPIKE: self._calculate_volume_spike(),
            VolumeType.VOLUME_PERCENTILE: self._calculate_volume_percentile(),
        }
        
        return switcher.get(self.volume_type)
    
    def _get_comparison_volume(self, market_data: MarketData) -> Optional[float]:
        """获取比较成交量"""
        if self.comparison_period:
            if len(self.volume_history) >= self.comparison_period:
                return statistics.mean(self.volume_history[-self.comparison_period:])
        
        # 使用标准周期
        if len(self.volume_history) >= self.period:
            return statistics.mean(self.volume_history[-self.period:])
        
        return None
    
    def _check_volume_condition(self, current_volume: float, comparison_volume: Optional[float]) -> ConditionResult:
        """检查成交量条件"""
        try:
            operator = self.operator
            threshold = self.threshold
            
            # 根据成交量类型执行不同的检查
            if self.volume_type == VolumeType.VOLUME_RATIO:
                return self._check_volume_ratio(current_volume, comparison_volume)
            elif self.volume_type == VolumeType.VOLUME_SPIKE:
                return self._check_volume_spike(current_volume, comparison_volume)
            elif self.volume_type == VolumeType.VOLUME_PERCENTILE:
                return self._check_volume_percentile(current_volume)
            elif operator in [ConditionOperator.GREATER_THAN, ConditionOperator.GREATER_EQUAL]:
                return self._check_greater_than(current_volume, comparison_volume, operator)
            elif operator in [ConditionOperator.LESS_THAN, ConditionOperator.LESS_EQUAL]:
                return self._check_less_than(current_volume, comparison_volume, operator)
            elif operator == ConditionOperator.EQUAL:
                return self._check_equal(current_volume, comparison_volume)
            elif operator == ConditionOperator.NOT_EQUAL:
                return self._check_not_equal(current_volume, comparison_volume)
            elif operator == ConditionOperator.IN_RANGE:
                return self._check_in_range(current_volume)
            elif operator == ConditionOperator.OUT_OF_RANGE:
                return self._check_out_of_range(current_volume)
            else:
                return ConditionResult(False, current_volume, f"不支持的操作符: {operator.value}")
                
        except Exception as e:
            return ConditionResult(False, current_volume, f"成交量条件检查错误: {str(e)}")
    
    def _calculate_obv(self) -> float:
        """计算OBV (On-Balance Volume)"""
        if len(self.volume_history) < 2:
            return self.volume_history[-1] if self.volume_history else 0
        
        obv = 0
        for i in range(1, min(len(self.price_history), len(self.volume_history))):
            if self.price_history[i] > self.price_history[i-1]:
                obv += self.volume_history[i]
            elif self.price_history[i] < self.price_history[i-1]:
                obv -= self.volume_history[i]
            # 如果价格相等，OBV保持不变
        
        return obv
    
    def _calculate_vwap(self) -> float:
        """计算VWAP (Volume Weighted Average Price)"""
        if not self.volume_history or not self.price_history or len(self.volume_history) != len(self.price_history):
            return self.price_history[-1] if self.price_history else 0
        
        total_pv = sum(p * v for p, v in zip(self.price_history, self.volume_history))
        total_volume = sum(self.volume_history)
        
        return total_pv / total_volume if total_volume > 0 else self.price_history[-1]
    
    def _calculate_volume_ma(self) -> float:
        """计算成交量移动平均"""
        if len(self.volume_history) < self.period:
            return self.volume_history[-1] if self.volume_history else 0
        
        return statistics.mean(self.volume_history[-self.period:])
    
    def _calculate_volume_ratio(self) -> float:
        """计算成交量比率"""
        comparison_volume = self._get_comparison_volume(MarketData(
            symbol="", price=0, volume_24h=0, price_change_24h=0,
            price_change_percent_24h=0, high_24h=0, low_24h=0, timestamp=datetime.now()
        ))
        
        if comparison_volume is None or comparison_volume == 0:
            return 0
        
        current_volume = self.volume_history[-1] if self.volume_history else 0
        return current_volume / comparison_volume
    
    def _calculate_volume_spike(self) -> float:
        """计算成交量突增"""
        if len(self.volume_history) < self.period:
            return 0
        
        current_volume = self.volume_history[-1]
        historical_mean = statistics.mean(self.volume_history[-self.period:])
        historical_std = statistics.stdev(self.volume_history[-self.period:]) if len(self.volume_history[-self.period:]) > 1 else 0
        
        if historical_std == 0:
            return 0
        
        # 计算Z-score
        spike_score = (current_volume - historical_mean) / historical_std
        return spike_score
    
    def _calculate_volume_percentile(self) -> float:
        """计算成交量百分位"""
        if not self.volume_history:
            return 0
        
        current_volume = self.volume_history[-1]
        historical_volumes = self.volume_history[:-1]  # 排除当前值
        
        if not historical_volumes:
            return 50  # 如果没有历史数据，返回50%百分位
        
        # 计算百分位
        sorted_volumes = sorted(historical_volumes)
        position = len([v for v in sorted_volumes if v <= current_volume])
        percentile = (position / len(sorted_volumes)) * 100
        
        return percentile
    
    def _check_volume_ratio(self, current_volume: float, comparison_volume: Optional[float]) -> ConditionResult:
        """检查成交量比率"""
        if comparison_volume is None or comparison_volume == 0:
            return ConditionResult(False, 0, "缺少比较成交量")
        
        ratio = current_volume / comparison_volume
        threshold = float(self.threshold) if isinstance(self.threshold, (int, float)) else 2.0
        
        satisfied = ratio >= threshold
        details = f"当前成交量: {current_volume:.0f}, 比较成交量: {comparison_volume:.0f}, 比率: {ratio:.2f}, 阈值: {threshold}"
        
        return ConditionResult(satisfied, ratio, details)
    
    def _check_volume_spike(self, current_volume: float, comparison_volume: Optional[float]) -> ConditionResult:
        """检查成交量突增"""
        spike_score = current_volume  # 这里已经是计算好的spike score
        
        threshold = float(self.threshold) if isinstance(self.threshold, (int, float)) else 2.0
        
        satisfied = spike_score >= threshold
        details = f"成交量突增分数: {spike_score:.2f}, 阈值: {threshold}"
        
        return ConditionResult(satisfied, spike_score, details)
    
    def _check_volume_percentile(self, current_volume: float) -> ConditionResult:
        """检查成交量百分位"""
        percentile = current_volume  # 这里已经是计算好的percentile
        
        threshold = float(self.threshold) if isinstance(self.threshold, (int, float)) else 90
        
        satisfied = percentile >= threshold
        details = f"成交量百分位: {percentile:.1f}%, 阈值: {threshold}%"
        
        return ConditionResult(satisfied, percentile, details)
    
    def _check_greater_than(self, current: float, compare: Optional[float], operator: ConditionOperator) -> ConditionResult:
        """检查大于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较成交量")
        
        threshold_value = float(self.threshold) if isinstance(self.threshold, (int, float)) else compare * 1.5
        
        satisfied = current > threshold_value if operator == ConditionOperator.GREATER_THAN else current >= threshold_value
        details = f"当前成交量: {current:.0f}, 目标成交量: {threshold_value:.0f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_less_than(self, current: float, compare: Optional[float], operator: ConditionOperator) -> ConditionResult:
        """检查小于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较成交量")
        
        threshold_value = float(self.threshold) if isinstance(self.threshold, (int, float)) else compare * 0.5
        
        satisfied = current < threshold_value if operator == ConditionOperator.LESS_THAN else current <= threshold_value
        details = f"当前成交量: {current:.0f}, 目标成交量: {threshold_value:.0f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_equal(self, current: float, compare: Optional[float]) -> ConditionResult:
        """检查等于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较成交量")
        
        tolerance = float(self.threshold) if isinstance(self.threshold, (int, float)) else current * 0.1
        satisfied = abs(current - compare) <= tolerance
        details = f"当前成交量: {current:.0f}, 比较成交量: {compare:.0f}, 容差: {tolerance:.0f}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_not_equal(self, current: float, compare: Optional[float]) -> ConditionResult:
        """检查不等于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较成交量")
        
        tolerance = float(self.threshold) if isinstance(self.threshold, (int, float)) else current * 0.1
        satisfied = abs(current - compare) > tolerance
        details = f"当前成交量: {current:.0f}, 比较成交量: {compare:.0f}, 容差: {tolerance:.0f}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_in_range(self, current: float) -> ConditionResult:
        """检查是否在范围内"""
        try:
            # 阈值格式: "min,max" 或 {"min": x, "max": y}
            if isinstance(self.threshold, str):
                min_val, max_val = map(float, self.threshold.split(','))
            elif isinstance(self.threshold, dict):
                min_val = self.threshold.get('min', 0)
                max_val = self.threshold.get('max', float('inf'))
            else:
                # 单个阈值表示范围为 [0, threshold]
                min_val = 0
                max_val = float(self.threshold)
            
            satisfied = min_val <= current <= max_val
            details = f"当前成交量: {current:.0f}, 范围: [{min_val:.0f}, {max_val:.0f}]"
            
            return ConditionResult(satisfied, current, details)
            
        except Exception as e:
            return ConditionResult(False, current, f"范围检查错误: {str(e)}")
    
    def _check_out_of_range(self, current: float) -> ConditionResult:
        """检查是否在范围外"""
        in_range_result = self._check_in_range(current)
        return ConditionResult(
            not in_range_result.satisfied, 
            current, 
            f"Out of range - {in_range_result.details}"
        )
    
    def _check_volume_alerts(self, current_volume: float, comparison_volume: Optional[float]):
        """检查成交量警报"""
        if comparison_volume is None:
            return
        
        ratio = current_volume / comparison_volume
        
        alert_data = {
            "timestamp": datetime.now(),
            "volume": current_volume,
            "comparison_volume": comparison_volume,
            "ratio": ratio,
            "alert_level": self.alert_level.value
        }
        
        # 根据比率判断警报级别
        if ratio >= 5.0:
            alert_data["alert_type"] = "extreme_volume"
            alert_data["message"] = f"极异常成交量：当前是平均值的{ratio:.1f}倍"
        elif ratio >= 3.0:
            alert_data["alert_type"] = "high_volume"
            alert_data["message"] = f"高成交量：当前是平均值的{ratio:.1f}倍"
        elif ratio <= 0.2:
            alert_data["alert_type"] = "low_volume"
            alert_data["message"] = f"低成交量：仅为平均值的{ratio:.1f}倍"
        
        self.volume_alerts.append(alert_data)
        
        # 保持警报记录数量
        if len(self.volume_alerts) > 50:
            self.volume_alerts = self.volume_alerts[-25:]
    
    def get_volume_statistics(self) -> Dict[str, Any]:
        """获取成交量统计信息"""
        if not self.volume_history:
            return {"message": "没有成交量历史数据"}
        
        recent_volumes = self.volume_history[-self.period:] if len(self.volume_history) >= self.period else self.volume_history
        
        return {
            "count": len(recent_volumes),
            "min": min(recent_volumes),
            "max": max(recent_volumes),
            "mean": statistics.mean(recent_volumes),
            "median": statistics.median(recent_volumes),
            "std_dev": statistics.stdev(recent_volumes) if len(recent_volumes) > 1 else 0,
            "latest": recent_volumes[-1] if recent_volumes else None,
            "total_volume": sum(recent_volumes)
        }
    
    def get_volume_trend(self) -> Dict[str, Any]:
        """获取成交量趋势分析"""
        if len(self.volume_history) < 10:
            return {"message": "数据不足，无法分析趋势"}
        
        recent_volumes = self.volume_history[-10:]
        older_volumes = self.volume_history[-20:-10] if len(self.volume_history) >= 20 else self.volume_history[:-10]
        
        if not older_volumes:
            return {"message": "数据不足，无法比较"}
        
        recent_avg = statistics.mean(recent_volumes)
        older_avg = statistics.mean(older_volumes)
        trend_ratio = recent_avg / older_avg if older_avg > 0 else 1
        
        if trend_ratio > 1.5:
            trend = "strong_increase"
        elif trend_ratio > 1.2:
            trend = "increase"
        elif trend_ratio < 0.5:
            trend = "strong_decrease"
        elif trend_ratio < 0.8:
            trend = "decrease"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "trend_ratio": trend_ratio,
            "change_percent": (trend_ratio - 1) * 100
        }
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的成交量警报"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.volume_alerts 
            if alert["timestamp"] >= cutoff_time
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            "volume_type": self.volume_type.value,
            "period": self.period,
            "comparison_period": self.comparison_period,
            "alert_level": self.alert_level.value,
            "volume_history": self.volume_history[-20:],  # 保存最近20个成交量
            "volume_statistics": self.get_volume_statistics(),
            "volume_trend": self.get_volume_trend(),
            "recent_alerts": self.get_recent_alerts()
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'VolumeCondition':
        """从字典创建实例"""
        super().from_dict(data)
        
        self.volume_type = VolumeType(data.get("volume_type", VolumeType.VOLUME_24H.value))
        self.period = data.get("period", 20)
        self.comparison_period = data.get("comparison_period")
        self.alert_level = VolumeAlertLevel(data.get("alert_level", VolumeAlertLevel.NORMAL.value))
        self.volume_history = data.get("volume_history", [])
        
        return self


class VolumeSpikeCondition(VolumeCondition):
    """成交量突增条件"""
    
    def __init__(
        self,
        symbol: str,
        spike_threshold: float = 2.0,  # 标准差倍数
        confirmation_period: int = 1,
        name: str = "",
        description: str = ""
    ):
        super().__init__(
            symbol=symbol,
            volume_type=VolumeType.VOLUME_SPIKE,
            operator=ConditionOperator.GREATER_THAN,
            threshold=spike_threshold,
            period=20,
            name=name or f"{symbol} 成交量突增",
            description=description or f"监控 {symbol} 成交量异常突增"
        )
        
        self.spike_threshold = spike_threshold
        self.confirmation_period = confirmation_period
        self.spike_count = 0
        self.last_spike_time: Optional[datetime] = None
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估成交量突增条件"""
        result = super().evaluate(market_data)
        
        # 更新突增计数
        if result.satisfied:
            self.spike_count += 1
            self.last_spike_time = datetime.now()
        else:
            self.spike_count = max(0, self.spike_count - 1)
        
        # 检查是否确认突增
        confirmed = self.spike_count >= self.confirmation_period
        
        if confirmed:
            details = f"成交量突增确认! 连续 {self.spike_count} 次满足条件"
            confirmed_result = ConditionResult(True, result.value, details)
            self._update_statistics(confirmed_result)
            return confirmed_result
        else:
            details = f"突增未确认，还需要 {self.confirmation_period - self.spike_count} 次确认"
            return ConditionResult(False, result.value, details)


class VolumeDivergenceCondition(VolumeCondition):
    """成交量背离条件"""
    
    def __init__(
        self,
        symbol: str,
        price_condition_type: str = "increase",  # "increase", "decrease", "volatile"
        volume_threshold: float = 1.5,
        name: str = "",
        description: str = ""
    ):
        super().__init__(
            symbol=symbol,
            volume_type=VolumeType.VOLUME_RATIO,
            operator=ConditionOperator.GREATER_THAN,
            threshold=volume_threshold,
            period=20,
            name=name or f"{symbol} 成交量背离",
            description=description or f"监控 {symbol} 价格与成交量的背离"
        )
        
        self.price_condition_type = price_condition_type
        self.volume_threshold = volume_threshold
        self.divergence_count = 0
        self.last_divergence_time: Optional[datetime] = None
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估成交量背离条件"""
        # 首先获取成交量比率
        volume_ratio = self._calculate_volume_ratio()
        
        # 分析价格变化
        price_analysis = self._analyze_price_change()
        
        # 检查背离条件
        divergence_detected = False
        details = ""
        
        if self.price_condition_type == "increase" and price_analysis["trend"] == "increase":
            if volume_ratio < 1.0:  # 价格上涨但成交量下降
                divergence_detected = True
                details = "价格上涨但成交量下降，存在背离"
        elif self.price_condition_type == "decrease" and price_analysis["trend"] == "decrease":
            if volume_ratio < 1.0:  # 价格下跌但成交量下降
                divergence_detected = True
                details = "价格下跌但成交量下降，存在背离"
        elif self.price_condition_type == "volatile":
            if volume_ratio < 0.8:  # 高波动但低成交量
                divergence_detected = True
                details = "价格波动大但成交量偏低，存在背离"
        
        # 结合成交量阈值检查
        if divergence_detected and volume_ratio >= self.volume_threshold:
            self.divergence_count += 1
            self.last_divergence_time = datetime.now()
            details += f" (成交量比率: {volume_ratio:.2f})"
            return ConditionResult(True, volume_ratio, details)
        else:
            return ConditionResult(False, volume_ratio, details)
    
    def _analyze_price_change(self) -> Dict[str, Any]:
        """分析价格变化"""
        if len(self.price_history) < 10:
            return {"trend": "insufficient_data"}
        
        recent_prices = self.price_history[-10:]
        
        # 计算价格变化
        price_changes = []
        for i in range(1, len(recent_prices)):
            change = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            price_changes.append(change)
        
        # 判断趋势
        positive_changes = sum(1 for c in price_changes if c > 0)
        negative_changes = sum(1 for c in price_changes if c < 0)
        
        if positive_changes >= 7:
            trend = "increase"
        elif negative_changes >= 7:
            trend = "decrease"
        else:
            trend = "volatile"
        
        # 计算波动性
        volatility = statistics.stdev(price_changes) if len(price_changes) > 1 else 0
        
        return {
            "trend": trend,
            "volatility": volatility,
            "positive_ratio": positive_changes / len(price_changes),
            "negative_ratio": negative_changes / len(price_changes)
        }
