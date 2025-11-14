"""
基础条件类定义
提供所有条件类型的基础框架和通用功能
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import uuid


class ConditionType(Enum):
    """条件类型枚举"""
    PRICE = "price"
    VOLUME = "volume"
    TIME = "time"
    TECHNICAL_INDICATOR = "technical_indicator"
    MARKET_ALERT = "market_alert"
    COMPOSITE = "composite"


class ConditionOperator(Enum):
    """条件操作符枚举"""
    # 比较操作符
    GREATER_THAN = "gt"
    GREATER_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_EQUAL = "le"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    
    # 范围操作符
    IN_RANGE = "in_range"
    OUT_OF_RANGE = "out_of_range"
    BETWEEN = "between"
    
    # 模式匹配操作符
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    
    # 逻辑操作符
    AND = "and"
    OR = "or"
    NOT = "not"


class ConditionResult:
    """条件评估结果"""
    
    def __init__(self, satisfied: bool, value: Any = None, details: str = ""):
        self.satisfied = satisfied
        self.value = value
        self.details = details
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"ConditionResult(satisfied={self.satisfied}, value={self.value}, details='{self.details}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "value": self.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    price: float
    volume_24h: float
    price_change_24h: float
    price_change_percent_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime
    
    # 技术指标数据
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    moving_average_20: Optional[float] = None
    moving_average_50: Optional[float] = None
    
    # 其他市场数据
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None


class Condition(ABC):
    """基础条件抽象类"""
    
    def __init__(
        self,
        condition_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        enabled: bool = True,
        priority: int = 1,
        timeout_seconds: Optional[int] = None,
        custom_data: Dict[str, Any] = None
    ):
        self.condition_id = condition_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.enabled = enabled
        self.priority = priority
        self.timeout_seconds = timeout_seconds
        self.custom_data = custom_data or {}
        self.created_at = datetime.now()
        self.last_evaluated: Optional[datetime] = None
        self.evaluation_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    @property
    @abstractmethod
    def condition_type(self) -> ConditionType:
        """返回条件类型"""
        pass
    
    @abstractmethod
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估条件是否满足"""
        pass
    
    def is_satisfied(self, market_data: MarketData) -> bool:
        """快速检查条件是否满足"""
        return self.evaluate(market_data).satisfied
    
    def get_value(self, market_data: MarketData) -> Any:
        """获取条件的当前值"""
        return self.evaluate(market_data).value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "condition_id": self.condition_id,
            "condition_type": self.condition_type.value,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "custom_data": self.custom_data,
            "created_at": self.created_at.isoformat(),
            "last_evaluated": self.last_evaluated.isoformat() if self.last_evaluated else None,
            "evaluation_count": self.evaluation_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }
    
    def from_dict(self, data: Dict[str, Any]) -> 'Condition':
        """从字典创建条件实例"""
        # 子类应该重写此方法来正确设置特定属性
        self.condition_id = data.get("condition_id", self.condition_id)
        self.name = data.get("name", self.name)
        self.description = data.get("description", self.description)
        self.enabled = data.get("enabled", self.enabled)
        self.priority = data.get("priority", self.priority)
        self.timeout_seconds = data.get("timeout_seconds", self.timeout_seconds)
        self.custom_data = data.get("custom_data", self.custom_data)
        
        if data.get("created_at"):
            self.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_evaluated"):
            self.last_evaluated = datetime.fromisoformat(data["last_evaluated"])
        
        self.evaluation_count = data.get("evaluation_count", 0)
        self.success_count = data.get("success_count", 0)
        self.failure_count = data.get("failure_count", 0)
        
        return self
    
    def _update_statistics(self, result: ConditionResult):
        """更新评估统计信息"""
        self.last_evaluated = datetime.now()
        self.evaluation_count += 1
        
        if result.satisfied:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.evaluation_count == 0:
            return 0.0
        return self.success_count / self.evaluation_count
    
    def __str__(self):
        return f"{self.condition_type.value}({self.name or 'Unnamed'})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id='{self.condition_id}', name='{self.name}')>"


class CompositeCondition(Condition):
    """复合条件基类"""
    
    def __init__(
        self,
        conditions: List[Condition],
        name: str = "",
        description: str = "",
        enabled: bool = True,
        priority: int = 1
    ):
        super().__init__(name=name, description=description, enabled=enabled, priority=priority)
        self.conditions = conditions
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.COMPOSITE
    
    def add_condition(self, condition: Condition):
        """添加条件"""
        self.conditions.append(condition)
    
    def remove_condition(self, condition_id: str):
        """移除条件"""
        self.conditions = [c for c in self.conditions if c.condition_id != condition_id]
    
    def get_condition(self, condition_id: str) -> Optional[Condition]:
        """获取指定ID的条件"""
        for condition in self.conditions:
            if condition.condition_id == condition_id:
                return condition
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["conditions"] = [c.to_dict() for c in self.conditions]
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'CompositeCondition':
        super().from_dict(data)
        # 子类应该重写此方法来正确创建子条件
        return self


class AndCondition(CompositeCondition):
    """AND逻辑条件（所有子条件都必须满足）"""
    
    def __init__(
        self,
        conditions: List[Condition],
        name: str = "AND条件",
        description: str = "所有子条件都必须满足"
    ):
        super().__init__(conditions, name, description)
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        if not self.conditions:
            return ConditionResult(False, False, "没有子条件")
        
        failed_conditions = []
        
        for condition in self.conditions:
            if not condition.enabled:
                continue
            
            result = condition.evaluate(market_data)
            if not result.satisfied:
                failed_conditions.append(condition.name or condition.condition_id)
        
        if not failed_conditions:
            return ConditionResult(True, True, "所有条件都满足")
        else:
            details = f"不满足的条件: {', '.join(failed_conditions)}"
            return ConditionResult(False, False, details)


class OrCondition(CompositeCondition):
    """OR逻辑条件（至少一个子条件满足）"""
    
    def __init__(
        self,
        conditions: List[Condition],
        name: str = "OR条件",
        description: str = "至少一个子条件必须满足"
    ):
        super().__init__(conditions, name, description)
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        if not self.conditions:
            return ConditionResult(False, False, "没有子条件")
        
        satisfied_conditions = []
        
        for condition in self.conditions:
            if not condition.enabled:
                continue
            
            result = condition.evaluate(market_data)
            if result.satisfied:
                satisfied_conditions.append(condition.name or condition.condition_id)
        
        if satisfied_conditions:
            details = f"满足的条件: {', '.join(satisfied_conditions)}"
            return ConditionResult(True, True, details)
        else:
            return ConditionResult(False, False, "没有条件满足")


class NotCondition(Condition):
    """NOT逻辑条件（取反条件）"""
    
    def __init__(
        self,
        condition: Condition,
        name: str = "NOT条件",
        description: str = "取反指定条件的结果"
    ):
        super().__init__(name=name, description=description)
        self.condition = condition
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.COMPOSITE
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        if not self.condition.enabled:
            return ConditionResult(False, False, "子条件未启用")
        
        result = self.condition.evaluate(market_data)
        inverted_result = not result.satisfied
        
        if inverted_result:
            details = f"NOT ({result.details})"
        else:
            details = f"NOT ({result.details})"
        
        return ConditionResult(inverted_result, inverted_result, details)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["condition"] = self.condition.to_dict()
        return data


# 具体的条件类将在后续文件中实现
class PriceCondition(Condition):
    """价格条件"""
    
    def __init__(
        self,
        symbol: str,
        operator: ConditionOperator,
        threshold: float,
        name: str = "",
        description: str = ""
    ):
        super().__init__(name=name, description=description)
        self.symbol = symbol
        self.operator = operator
        self.threshold = threshold
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.PRICE
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        # TODO: 后续实现具体的评估逻辑
        return ConditionResult(True, market_data.price, "模拟评估")


class VolumeCondition(Condition):
    """成交量条件"""
    
    def __init__(
        self,
        symbol: str,
        operator: ConditionOperator,
        threshold: float,
        name: str = "",
        description: str = ""
    ):
        super().__init__(name=name, description=description)
        self.symbol = symbol
        self.operator = operator
        self.threshold = threshold
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.VOLUME
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        # TODO: 后续实现具体的评估逻辑
        return ConditionResult(True, market_data.volume_24h, "模拟评估")


class TimeCondition(Condition):
    """时间条件"""
    
    def __init__(
        self,
        operator: ConditionOperator,
        time_value: Union[str, datetime],
        name: str = "",
        description: str = ""
    ):
        super().__init__(name=name, description=description)
        self.operator = operator
        self.time_value = time_value
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.TIME
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        # TODO: 后续实现具体的评估逻辑
        return ConditionResult(True, datetime.now(), "模拟评估")


class TechnicalIndicatorCondition(Condition):
    """技术指标条件"""
    
    def __init__(
        self,
        symbol: str,
        indicator: str,
        operator: ConditionOperator,
        threshold: float,
        name: str = "",
        description: str = ""
    ):
        super().__init__(name=name, description=description)
        self.symbol = symbol
        self.indicator = indicator
        self.operator = operator
        self.threshold = threshold
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.TECHNICAL_INDICATOR
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        # TODO: 后续实现具体的评估逻辑
        return ConditionResult(True, 50.0, "模拟评估")


class MarketAlertCondition(Condition):
    """市场警报条件"""
    
    def __init__(
        self,
        alert_type: str,
        symbol: str,
        threshold: float,
        name: str = "",
        description: str = ""
    ):
        super().__init__(name=name, description=description)
        self.alert_type = alert_type
        self.symbol = symbol
        self.threshold = threshold
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.MARKET_ALERT
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        # TODO: 后续实现具体的评估逻辑
        return ConditionResult(True, True, "模拟评估")
