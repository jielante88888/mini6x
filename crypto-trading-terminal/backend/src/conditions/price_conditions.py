"""
价格条件处理器
提供基于价格的各种条件类型和评估逻辑
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import statistics

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    PriceCondition as BasePriceCondition
)


class PriceType(Enum):
    """价格类型枚举"""
    CURRENT_PRICE = "current_price"
    OPEN_PRICE = "open_price"
    HIGH_PRICE = "high_price"
    LOW_PRICE = "low_price"
    CLOSE_PRICE = "close_price"
    PREVIOUS_CLOSE = "previous_close"
    PRICE_CHANGE = "price_change"
    PRICE_CHANGE_PERCENT = "price_change_percent"
    VOLUME_WEIGHTED_PRICE = "vwap"


class PriceCondition(BasePriceCondition):
    """价格条件"""
    
    def __init__(
        self,
        symbol: str,
        price_type: PriceType,
        operator: ConditionOperator,
        threshold: Union[float, str],
        comparison_price: Optional[float] = None,
        lookback_period: int = 1,
        name: str = "",
        description: str = "",
        alert_level: str = "normal"  # normal, warning, critical
    ):
        # 调用父类初始化
        super().__init__(
            symbol=symbol,
            operator=operator,
            threshold=float(threshold) if isinstance(threshold, (int, float)) else threshold,
            name=name,
            description=description
        )
        
        self.price_type = price_type
        self.comparison_price = comparison_price
        self.lookback_period = lookback_period
        self.alert_level = alert_level
        self.price_history: List[float] = []
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估价格条件"""
        try:
            # 获取价格值
            current_price = self._get_price_value(market_data)
            if current_price is None:
                return ConditionResult(
                    False, 
                    None, 
                    f"无法获取 {self.symbol} 的 {self.price_type.value} 价格"
                )
            
            # 获取比较价格
            compare_price = self._get_comparison_price(market_data)
            
            # 执行条件检查
            result = self._check_condition(current_price, compare_price)
            
            # 更新统计信息
            self._update_statistics(result)
            
            return result
            
        except Exception as e:
            error_result = ConditionResult(
                False, 
                None, 
                f"价格条件评估错误: {str(e)}"
            )
            self._update_statistics(error_result)
            return error_result
    
    def _get_price_value(self, market_data: MarketData) -> Optional[float]:
        """获取指定类型的当前价格"""
        switcher = {
            PriceType.CURRENT_PRICE: market_data.price,
            PriceType.OPEN_PRICE: market_data.price - market_data.price_change,  # 估算开盘价
            PriceType.HIGH_PRICE: market_data.high_24h,
            PriceType.LOW_PRICE: market_data.low_24h,
            PriceType.CLOSE_PRICE: market_data.price,
            PriceType.PREVIOUS_CLOSE: market_data.price - market_data.price_change,
            PriceType.PRICE_CHANGE: market_data.price_change,
            PriceType.PRICE_CHANGE_PERCENT: market_data.price_change_percent_24h,
            PriceType.VOLUME_WEIGHTED_PRICE: market_data.price,  # 简化处理
        }
        
        return switcher.get(self.price_type)
    
    def _get_comparison_price(self, market_data: MarketData) -> Optional[float]:
        """获取比较价格"""
        if self.comparison_price is not None:
            return self.comparison_price
        
        # 如果没有指定比较价格，使用历史价格
        if self.price_history and len(self.price_history) >= self.lookback_period:
            return self.price_history[-self.lookback_period]
        
        return None
    
    def _check_condition(self, current_price: float, compare_price: Optional[float]) -> ConditionResult:
        """检查条件是否满足"""
        try:
            operator = self.operator
            threshold = self.threshold
            
            # 根据操作符类型执行不同的检查
            if operator in [ConditionOperator.GREATER_THAN, ConditionOperator.GREATER_EQUAL]:
                return self._check_greater_than(current_price, compare_price, operator)
            elif operator in [ConditionOperator.LESS_THAN, ConditionOperator.LESS_EQUAL]:
                return self._check_less_than(current_price, compare_price, operator)
            elif operator == ConditionOperator.EQUAL:
                return self._check_equal(current_price, compare_price)
            elif operator == ConditionOperator.NOT_EQUAL:
                return self._check_not_equal(current_price, compare_price)
            elif operator == ConditionOperator.IN_RANGE:
                return self._check_in_range(current_price)
            elif operator == ConditionOperator.OUT_OF_RANGE:
                return self._check_out_of_range(current_price)
            elif operator == ConditionOperator.BETWEEN:
                return self._check_between(current_price)
            else:
                return ConditionResult(False, current_price, f"不支持的操作符: {operator.value}")
                
        except Exception as e:
            return ConditionResult(False, current_price, f"条件检查错误: {str(e)}")
    
    def _check_greater_than(self, current: float, compare: Optional[float], operator: ConditionOperator) -> ConditionResult:
        """检查大于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较价格")
        
        threshold_value = float(self.threshold)
        target_value = compare * (1 + threshold_value / 100) if isinstance(self.threshold, str) and '%' in str(self.threshold) else threshold_value
        
        satisfied = current > target_value if operator == ConditionOperator.GREATER_THAN else current >= target_value
        details = f"当前价格: {current:.4f}, 目标价格: {target_value:.4f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_less_than(self, current: float, compare: Optional[float], operator: ConditionOperator) -> ConditionResult:
        """检查小于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较价格")
        
        threshold_value = float(self.threshold)
        target_value = compare * (1 - threshold_value / 100) if isinstance(self.threshold, str) and '%' in str(self.threshold) else threshold_value
        
        satisfied = current < target_value if operator == ConditionOperator.LESS_THAN else current <= target_value
        details = f"当前价格: {current:.4f}, 目标价格: {target_value:.4f}, 操作符: {operator.value}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_equal(self, current: float, compare: Optional[float]) -> ConditionResult:
        """检查等于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较价格")
        
        tolerance = float(self.threshold) if isinstance(self.threshold, (int, float)) else 0.01
        satisfied = abs(current - compare) <= tolerance
        details = f"当前价格: {current:.4f}, 比较价格: {compare:.4f}, 容差: {tolerance}"
        
        return ConditionResult(satisfied, current, details)
    
    def _check_not_equal(self, current: float, compare: Optional[float]) -> ConditionResult:
        """检查不等于条件"""
        if compare is None:
            return ConditionResult(False, current, "缺少比较价格")
        
        tolerance = float(self.threshold) if isinstance(self.threshold, (int, float)) else 0.01
        satisfied = abs(current - compare) > tolerance
        details = f"当前价格: {current:.4f}, 比较价格: {compare:.4f}, 容差: {tolerance}"
        
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
            details = f"当前价格: {current:.4f}, 范围: [{min_val:.4f}, {max_val:.4f}]"
            
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
    
    def _check_between(self, current: float) -> ConditionResult:
        """检查是否在两个值之间（与IN_RANGE相同）"""
        return self._check_in_range(current)
    
    def update_price_history(self, price: float):
        """更新价格历史"""
        self.price_history.append(price)
        # 保持最近100个价格记录
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
    
    def get_price_statistics(self) -> Dict[str, Any]:
        """获取价格统计信息"""
        if not self.price_history:
            return {"message": "没有价格历史数据"}
        
        prices = self.price_history[-20:]  # 最近20个价格
        return {
            "count": len(prices),
            "min": min(prices),
            "max": max(prices),
            "mean": statistics.mean(prices),
            "median": statistics.median(prices),
            "std_dev": statistics.stdev(prices) if len(prices) > 1 else 0,
            "latest": prices[-1] if prices else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            "price_type": self.price_type.value,
            "comparison_price": self.comparison_price,
            "lookback_period": self.lookback_period,
            "alert_level": self.alert_level,
            "price_history": self.price_history[-10:],  # 只保存最近10个价格
            "price_statistics": self.get_price_statistics()
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'PriceCondition':
        """从字典创建实例"""
        super().from_dict(data)
        
        self.price_type = PriceType(data.get("price_type", PriceType.CURRENT_PRICE.value))
        self.comparison_price = data.get("comparison_price")
        self.lookback_period = data.get("lookback_period", 1)
        self.alert_level = data.get("alert_level", "normal")
        self.price_history = data.get("price_history", [])
        
        return self


class PriceBreakoutCondition(PriceCondition):
    """价格突破条件"""
    
    def __init__(
        self,
        symbol: str,
        breakout_level: float,
        direction: str = "up",  # "up" 或 "down"
        confirmation_period: int = 1,
        name: str = "",
        description: str = ""
    ):
        # 使用价格百分比变化作为阈值
        super().__init__(
            symbol=symbol,
            price_type=PriceType.PRICE_CHANGE_PERCENT,
            operator=ConditionOperator.GREATER_THAN if direction == "up" else ConditionOperator.LESS_THAN,
            threshold=breakout_level,
            name=name or f"{symbol} 价格突破 {'向上' if direction == 'up' else '向下'}",
            description=description or f"监控 {symbol} 价格突破 {breakout_level}%"
        )
        
        self.breakout_level = breakout_level
        self.direction = direction
        self.confirmation_period = confirmation_period
        self.breakout_count = 0
        self.last_breakout_time: Optional[datetime] = None
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估突破条件"""
        result = super().evaluate(market_data)
        
        # 更新突破计数
        if result.satisfied:
            self.breakout_count += 1
            self.last_breakout_time = datetime.now()
        else:
            self.breakout_count = max(0, self.breakout_count - 1)
        
        # 检查是否确认突破
        confirmed = self.breakout_count >= self.confirmation_period
        
        if confirmed:
            details = f"突破确认! 连续 {self.breakout_count} 次满足条件"
            confirmed_result = ConditionResult(True, result.value, details)
            self._update_statistics(confirmed_result)
            return confirmed_result
        else:
            details = f"突破未确认，还需要 {self.confirmation_period - self.breakout_count} 次确认"
            return ConditionResult(False, result.value, details)


class PriceDivergenceCondition(PriceCondition):
    """价格背离条件"""
    
    def __init__(
        self,
        symbol: str,
        primary_price_type: PriceType,
        secondary_price_type: PriceType,
        divergence_threshold: float,
        name: str = "",
        description: str = ""
    ):
        super().__init__(
            symbol=symbol,
            price_type=primary_price_type,
            operator=ConditionOperator.GREATER_THAN,
            threshold=divergence_threshold,
            name=name or f"{symbol} 价格背离",
            description=description or f"监控 {symbol} 两种价格类型的背离"
        )
        
        self.secondary_price_type = secondary_price_type
        self.divergence_threshold = divergence_threshold
        self.primary_history: List[float] = []
        self.secondary_history: List[float] = []
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估背离条件"""
        # 获取主要价格
        primary_price = self._get_price_value(market_data)
        
        # 获取次要价格
        secondary_price = self._get_secondary_price_value(market_data)
        
        if primary_price is None or secondary_price is None:
            return ConditionResult(False, None, "无法获取价格数据")
        
        # 更新历史数据
        self.primary_history.append(primary_price)
        self.secondary_history.append(secondary_price)
        
        # 保持历史记录长度
        if len(self.primary_history) > 50:
            self.primary_history = self.primary_history[-25:]
            self.secondary_history = self.secondary_history[-25:]
        
        # 计算背离
        divergence = abs(primary_price - secondary_price)
        percentage_divergence = (divergence / min(primary_price, secondary_price)) * 100
        
        satisfied = percentage_divergence >= self.divergence_threshold
        details = f"主要价格: {primary_price:.4f}, 次要价格: {secondary_price:.4f}, 背离: {percentage_divergence:.2f}%"
        
        return ConditionResult(satisfied, percentage_divergence, details)
    
    def _get_secondary_price_value(self, market_data: MarketData) -> Optional[float]:
        """获取次要价格类型的价格"""
        switcher = {
            PriceType.CURRENT_PRICE: market_data.price,
            PriceType.OPEN_PRICE: market_data.price - market_data.price_change,
            PriceType.HIGH_PRICE: market_data.high_24h,
            PriceType.LOW_PRICE: market_data.low_24h,
            PriceType.CLOSE_PRICE: market_data.price,
            PriceType.PREVIOUS_CLOSE: market_data.price - market_data.price_change,
            PriceType.PRICE_CHANGE: market_data.price_change,
            PriceType.PRICE_CHANGE_PERCENT: market_data.price_change_percent_24h,
            PriceType.VOLUME_WEIGHTED_PRICE: market_data.price,
        }
        
        return switcher.get(self.secondary_price_type)


from enum import Enum
