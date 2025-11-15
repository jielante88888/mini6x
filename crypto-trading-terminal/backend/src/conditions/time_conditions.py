"""
时间条件处理器
提供基于时间的各种条件类型和评估逻辑
"""

from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Union, Set
from dataclasses import dataclass
from enum import Enum

# 可选的时区支持
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    print("Warning: pytz not available, time conditions will use UTC timezone")

from .base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    ConditionType
)


class TimeType(Enum):
    """时间类型枚举"""
    CURRENT_TIME = "current_time"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    TRADING_HOURS = "trading_hours"
    TIME_RANGE = "time_range"
    RECURRING_TIME = "recurring_time"
    TIME_ELAPSED = "time_elapsed"
    MARKET_SESSION = "market_session"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    COUNTDOWN = "countdown"


class TimeZone(Enum):
    """时区枚举"""
    UTC = "UTC"
    EST = "America/New_York"
    PST = "America/Los_Angeles"
    GMT = "Europe/London"
    CET = "Europe/Berlin"
    JST = "Asia/Tokyo"
    CST = "Asia/Shanghai"
    HKT = "Asia/Hong_Kong"


class MarketSession(Enum):
    """市场交易时段"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    OVERNIGHT = "overnight"
    CLOSED = "closed"


class DayOfWeek(Enum):
    """星期枚举"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class TimeCondition(Condition):
    """时间条件"""
    
    def __init__(
        self,
        time_type: TimeType,
        operator: ConditionOperator,
        time_value: Union[str, datetime, time, Dict[str, Any]],
        timezone: TimeZone = TimeZone.UTC,
        target_market: str = "crypto",  # "crypto", "stock", "forex"
        include_weekends: bool = True,
        name: str = "",
        description: str = "",
        enabled: bool = True,
        priority: int = 1
    ):
        super().__init__(name=name, description=description, enabled=enabled, priority=priority)
        
        self.time_type = time_type
        self.operator = operator
        self.time_value = time_value
        self.timezone = timezone
        self.target_market = target_market
        self.include_weekends = include_weekends
        
        self.time_type = time_type
        self.timezone = timezone
        self.target_market = target_market
        self.include_weekends = include_weekends
        
        # 时区对象
        if PYTZ_AVAILABLE:
            self.tz = pytz.timezone(timezone.value)
        else:
            # 简单的时区处理
            self.tz = datetime.timezone.utc
        
        # 数据存储
        self.time_history: List[datetime] = []
        self.market_sessions: List[Dict[str, Any]] = []
        self.time_triggers: List[Dict[str, Any]] = []
    
    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.TIME
    
    def evaluate(self, market_data: MarketData) -> ConditionResult:
        """评估时间条件"""
        try:
            # 获取当前时间
            current_time = datetime.now(self.tz)
            
            # 更新历史
            self.time_history.append(current_time)
            if len(self.time_history) > 1000:
                self.time_history = self.time_history[-500:]
            
            # 根据时间类型执行评估
            result = self._evaluate_time_condition(current_time, market_data)
            
            # 记录触发时间
            if result.satisfied:
                self._record_time_trigger(current_time, result)
            
            # 更新统计信息
            self._update_statistics(result)
            
            return result
            
        except Exception as e:
            error_result = ConditionResult(
                False, 
                None, 
                f"时间条件评估错误: {str(e)}"
            )
            self._update_statistics(error_result)
            return error_result
    
    def _evaluate_time_condition(self, current_time: datetime, market_data: MarketData) -> ConditionResult:
        """评估具体的时间条件"""
        switcher = {
            TimeType.CURRENT_TIME: self._check_current_time,
            TimeType.MARKET_OPEN: self._check_market_open,
            TimeType.MARKET_CLOSE: self._check_market_close,
            TimeType.TRADING_HOURS: self._check_trading_hours,
            TimeType.TIME_RANGE: self._check_time_range,
            TimeType.RECURRING_TIME: self._check_recurring_time,
            TimeType.TIME_ELAPSED: self._check_time_elapsed,
            TimeType.MARKET_SESSION: self._check_market_session,
            TimeType.WEEKEND: self._check_weekend,
            TimeType.HOLIDAY: self._check_holiday,
            TimeType.COUNTDOWN: self._check_countdown,
        }
        
        checker = switcher.get(self.time_type)
        if checker:
            return checker(current_time)
        else:
            return ConditionResult(False, current_time, f"不支持的时间类型: {self.time_type.value}")
    
    def _check_current_time(self, current_time: datetime) -> ConditionResult:
        """检查当前时间"""
        if isinstance(self.time_value, datetime):
            target_time = self.time_value
        elif isinstance(self.time_value, time):
            target_time = current_time.replace(
                hour=self.time_value.hour,
                minute=self.time_value.minute,
                second=self.time_value.second,
                microsecond=0
            )
        elif isinstance(self.time_value, str):
            # 解析时间字符串 "HH:MM" 或 "HH:MM:SS"
            time_parts = self.time_value.split(':')
            if len(time_parts) >= 2:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                target_time = current_time.replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )
            else:
                return ConditionResult(False, current_time, "无效的时间格式")
        else:
            return ConditionResult(False, current_time, "无效的时间值")
        
        return self._compare_times(current_time, target_time)
    
    def _check_market_open(self, current_time: datetime) -> ConditionResult:
        """检查市场开盘时间"""
        market_hours = self._get_market_hours(current_time.weekday())
        
        if market_hours["is_trading_day"]:
            market_open_time = current_time.replace(
                hour=market_hours["open_hour"],
                minute=market_hours["open_minute"],
                second=0,
                microsecond=0
            )
            
            # 考虑预开盘时间（开盘前30分钟）
            pre_market_time = market_open_time - timedelta(minutes=30)
            
            # 检查是否在开盘时间或预开盘时间内
            satisfied = pre_market_time <= current_time <= market_open_time + timedelta(minutes=5)
            details = f"当前时间: {current_time.strftime('%H:%M')}, 开盘时间: {market_open_time.strftime('%H:%M')}"
            
            return ConditionResult(satisfied, current_time, details)
        else:
            return ConditionResult(False, current_time, "非交易日")
    
    def _check_market_close(self, current_time: datetime) -> ConditionResult:
        """检查市场收盘时间"""
        market_hours = self._get_market_hours(current_time.weekday())
        
        if market_hours["is_trading_day"]:
            market_close_time = current_time.replace(
                hour=market_hours["close_hour"],
                minute=market_hours["close_minute"],
                second=0,
                microsecond=0
            )
            
            # 考虑收盘后时间（收盘后30分钟内）
            post_market_time = market_close_time + timedelta(minutes=30)
            
            # 检查是否在收盘时间或收盘后时间内
            satisfied = market_close_time - timedelta(minutes=5) <= current_time <= post_market_time
            details = f"当前时间: {current_time.strftime('%H:%M')}, 收盘时间: {market_close_time.strftime('%H:%M')}"
            
            return ConditionResult(satisfied, current_time, details)
        else:
            return ConditionResult(False, current_time, "非交易日")
    
    def _check_trading_hours(self, current_time: datetime) -> ConditionResult:
        """检查是否在交易时间内"""
        market_hours = self._get_market_hours(current_time.weekday())
        
        if not market_hours["is_trading_day"]:
            return ConditionResult(False, current_time, "非交易日")
        
        market_open = current_time.replace(
            hour=market_hours["open_hour"],
            minute=market_hours["open_minute"],
            second=0,
            microsecond=0
        )
        
        market_close = current_time.replace(
            hour=market_hours["close_hour"],
            minute=market_hours["close_minute"],
            second=0,
            microsecond=0
        )
        
        satisfied = market_open <= current_time <= market_close
        
        if satisfied:
            # 计算剩余交易时间
            remaining_time = market_close - current_time
            details = f"交易中，剩余时间: {remaining_time}"
        else:
            # 计算距离下次开盘时间
            next_open = self._get_next_trading_day(current_time)
            if next_open:
                time_to_open = next_open - current_time
                details = f"休市，距离下次开盘: {time_to_open}"
            else:
                details = "休市"
        
        return ConditionResult(satisfied, current_time, details)
    
    def _check_time_range(self, current_time: datetime) -> ConditionResult:
        """检查是否在指定时间范围内"""
        try:
            if isinstance(self.time_value, dict):
                start_time_str = self.time_value.get("start", "00:00")
                end_time_str = self.time_value.get("end", "23:59")
            elif isinstance(self.time_value, str):
                # 格式: "start-end" 例如 "09:00-17:00"
                if "-" in self.time_value:
                    start_time_str, end_time_str = self.time_value.split("-")
                else:
                    return ConditionResult(False, current_time, "无效的时间范围格式")
            else:
                return ConditionResult(False, current_time, "无效的时间范围值")
            
            # 解析开始和结束时间
            start_parts = start_time_str.split(":")
            end_parts = end_time_str.split(":")
            
            start_hour = int(start_parts[0])
            start_minute = int(start_parts[1]) if len(start_parts) > 1 else 0
            
            end_hour = int(end_parts[0])
            end_minute = int(end_parts[1]) if len(end_parts) > 1 else 0
            
            start_time = current_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            end_time = current_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            # 处理跨日情况
            if end_time <= start_time:
                end_time += timedelta(days=1)
                if current_time < start_time:
                    current_time += timedelta(days=1)
            
            satisfied = start_time <= current_time <= end_time
            details = f"当前: {current_time.strftime('%H:%M')}, 范围: {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
            
            return ConditionResult(satisfied, current_time, details)
            
        except Exception as e:
            return ConditionResult(False, current_time, f"时间范围检查错误: {str(e)}")
    
    def _check_recurring_time(self, current_time: datetime) -> ConditionResult:
        """检查是否在循环时间点"""
        try:
            if isinstance(self.time_value, dict):
                time_pattern = self.time_value.get("pattern", "daily")
                time_spec = self.time_value.get("time", "12:00")
                weekdays = self.time_value.get("weekdays", list(range(7)))  # 0-6, 0是周一
            else:
                return ConditionResult(False, current_time, "无效的循环时间配置")
            
            current_weekday = current_time.weekday()  # 0是周一
            
            # 检查是否为指定的星期几
            if current_weekday not in weekdays:
                return ConditionResult(False, current_time, f"不是指定的交易日期")
            
            # 解析时间
            time_parts = time_spec.split(":")
            target_hour = int(time_parts[0])
            target_minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            target_time = current_time.replace(
                hour=target_hour,
                minute=target_minute,
                second=0,
                microsecond=0
            )
            
            # 检查是否在指定时间范围内（例如前后5分钟）
            tolerance = timedelta(minutes=5)
            satisfied = abs(current_time - target_time) <= tolerance
            
            if satisfied:
                details = f"循环时间触发: {target_time.strftime('%H:%M')} ({current_time.strftime('%H:%M')})"
            else:
                details = f"下次触发时间: {target_time.strftime('%H:%M')}"
            
            return ConditionResult(satisfied, current_time, details)
            
        except Exception as e:
            return ConditionResult(False, current_time, f"循环时间检查错误: {str(e)}")
    
    def _check_time_elapsed(self, current_time: datetime) -> ConditionResult:
        """检查时间间隔"""
        try:
            if not self.time_history:
                return ConditionResult(False, current_time, "没有时间历史")
            
            # 获取参考时间
            if isinstance(self.time_value, dict):
                reference_type = self.time_value.get("reference", "last_trigger")
                threshold_minutes = self.time_value.get("minutes", 60)
            elif isinstance(self.time_value, str) and self.time_value.isdigit():
                threshold_minutes = int(self.time_value)
                reference_type = "last_trigger"
            else:
                return ConditionResult(False, current_time, "无效的时间间隔配置")
            
            # 获取参考时间点
            if reference_type == "last_trigger" and self.time_history:
                reference_time = self.time_history[-1]
            elif reference_type == "market_open" and self.time_history:
                # 使用最近的交易日开始时间作为参考
                last_trading_day = self._get_last_trading_day(current_time)
                if last_trading_day:
                    market_hours = self._get_market_hours(last_trading_day.weekday())
                    reference_time = last_trading_day.replace(
                        hour=market_hours["open_hour"],
                        minute=market_hours["open_minute"],
                        second=0,
                        microsecond=0
                    )
                else:
                    return ConditionResult(False, current_time, "无法确定参考时间")
            else:
                return ConditionResult(False, current_time, "不支持的参考类型")
            
            # 计算时间间隔
            elapsed = current_time - reference_time
            threshold = timedelta(minutes=threshold_minutes)
            
            satisfied = elapsed >= threshold
            details = f"已过去: {elapsed}, 阈值: {threshold}"
            
            return ConditionResult(satisfied, current_time, details)
            
        except Exception as e:
            return ConditionResult(False, current_time, f"时间间隔检查错误: {str(e)}")
    
    def _check_market_session(self, current_time: datetime) -> ConditionResult:
        """检查市场交易时段"""
        market_session = self._determine_market_session(current_time)
        target_session = self.time_value if isinstance(self.time_value, str) else "regular"
        
        satisfied = market_session.value == target_session
        
        session_descriptions = {
            MarketSession.PRE_MARKET: "盘前",
            MarketSession.REGULAR: "常规交易",
            MarketSession.AFTER_HOURS: "盘后",
            MarketSession.OVERNIGHT: "隔夜",
            MarketSession.CLOSED: "休市"
        }
        
        details = f"当前时段: {session_descriptions.get(market_session, market_session.value)}, 目标: {target_session}"
        
        return ConditionResult(satisfied, current_time, details)
    
    def _check_weekend(self, current_time: datetime) -> ConditionResult:
        """检查是否为周末"""
        is_weekend = current_time.weekday() >= 5  # 周六(5)或周日(6)
        
        operator = self.operator
        if operator == ConditionOperator.EQUAL:
            satisfied = is_weekend
            details = "周末" if is_weekend else "非周末"
        elif operator == ConditionOperator.NOT_EQUAL:
            satisfied = not is_weekend
            details = "非周末" if not is_weekend else "周末"
        else:
            # 对于其他操作符，将其转换为布尔值比较
            target_value = 1 if self.time_value in ["true", "True", True, 1] else 0
            actual_value = 1 if is_weekend else 0
            
            if operator == ConditionOperator.GREATER_THAN:
                satisfied = actual_value > target_value
            elif operator == ConditionOperator.LESS_THAN:
                satisfied = actual_value < target_value
            else:
                satisfied = actual_value == target_value
            
            details = f"周末状态: {is_weekend}"
        
        return ConditionResult(satisfied, current_time, details)
    
    def _check_holiday(self, current_time: datetime) -> ConditionResult:
        """检查是否为节假日"""
        # 这里应该集成真实的节假日数据
        # 暂时返回基于简单规则的判断
        holidays = self._get_market_holidays(current_time.year)
        
        current_date = current_time.date()
        is_holiday = current_date in holidays
        
        satisfied = is_holiday if self.operator == ConditionOperator.EQUAL else not is_holiday
        details = f"{'节假日' if is_holiday else '非节假日'}"
        
        return ConditionResult(satisfied, current_time, details)
    
    def _check_countdown(self, current_time: datetime) -> ConditionResult:
        """检查倒计时"""
        try:
            if isinstance(self.time_value, dict):
                target_datetime_str = self.time_value.get("target")
                threshold_seconds = self.time_value.get("threshold_seconds", 0)
            else:
                target_datetime_str = str(self.time_value)
                threshold_seconds = 0
            
            # 解析目标时间
            if target_datetime_str:
                target_datetime = datetime.fromisoformat(target_datetime_str)
                if target_datetime.tzinfo is None:
                    target_datetime = self.tz.localize(target_datetime)
            else:
                return ConditionResult(False, current_time, "缺少目标时间")
            
            # 计算倒计时
            time_remaining = target_datetime - current_time
            
            if time_remaining.total_seconds() >= 0:
                # 正向倒计时
                satisfied = time_remaining.total_seconds() <= threshold_seconds
                details = f"剩余: {time_remaining}, 阈值: {threshold_seconds}秒"
            else:
                # 负向倒计时（已过期）
                satisfied = True
                details = f"已过期: {-time_remaining}"
            
            return ConditionResult(satisfied, abs(time_remaining.total_seconds()), details)
            
        except Exception as e:
            return ConditionResult(False, current_time, f"倒计时检查错误: {str(e)}")
    
    def _compare_times(self, current_time: datetime, target_time: datetime) -> ConditionResult:
        """比较时间"""
        operator = self.operator
        
        if operator == ConditionOperator.EQUAL:
            # 精确匹配（考虑分钟精度）
            tolerance = timedelta(minutes=1)
            satisfied = abs(current_time - target_time) <= tolerance
        elif operator == ConditionOperator.GREATER_THAN:
            satisfied = current_time > target_time
        elif operator == ConditionOperator.GREATER_EQUAL:
            satisfied = current_time >= target_time
        elif operator == ConditionOperator.LESS_THAN:
            satisfied = current_time < target_time
        elif operator == ConditionOperator.LESS_EQUAL:
            satisfied = current_time <= target_time
        else:
            return ConditionResult(False, current_time, f"不支持的时间比较操作符: {operator.value}")
        
        details = f"当前: {current_time.strftime('%H:%M:%S')}, 目标: {target_time.strftime('%H:%M:%S')}"
        
        return ConditionResult(satisfied, current_time, details)
    
    def _get_market_hours(self, weekday: int) -> Dict[str, Any]:
        """获取市场交易时间"""
        # 根据目标市场类型返回不同的交易时间
        if self.target_market == "crypto":
            # 加密货币市场24/7交易
            return {
                "is_trading_day": True,
                "open_hour": 0,
                "open_minute": 0,
                "close_hour": 23,
                "close_minute": 59
            }
        elif self.target_market == "stock":
            # 股票市场交易时间（周一到周五）
            is_trading_day = weekday < 5 and not self._is_holiday(weekday)
            return {
                "is_trading_day": is_trading_day,
                "open_hour": 9 if is_trading_day else 0,
                "open_minute": 30 if is_trading_day else 0,
                "close_hour": 16 if is_trading_day else 0,
                "close_minute": 0 if is_trading_day else 0
            }
        elif self.target_market == "forex":
            # 外汇市场交易时间
            # 外汇市场周一到周五，主要交易时间
            is_trading_day = weekday < 5
            return {
                "is_trading_day": is_trading_day,
                "open_hour": 0,
                "open_minute": 0,
                "close_hour": 23,
                "close_minute": 59
            }
        else:
            return {
                "is_trading_day": True,
                "open_hour": 0,
                "open_minute": 0,
                "close_hour": 23,
                "close_minute": 59
            }
    
    def _determine_market_session(self, current_time: datetime) -> MarketSession:
        """确定当前市场时段"""
        weekday = current_time.weekday()
        market_hours = self._get_market_hours(weekday)
        
        if not market_hours["is_trading_day"]:
            return MarketSession.CLOSED
        
        market_open = current_time.replace(
            hour=market_hours["open_hour"],
            minute=market_hours["open_minute"],
            second=0,
            microsecond=0
        )
        
        market_close = current_time.replace(
            hour=market_hours["close_hour"],
            minute=market_hours["close_minute"],
            second=0,
            microsecond=0
        )
        
        # 盘前：开盘前30分钟到开盘
        if market_open - timedelta(minutes=30) <= current_time < market_open:
            return MarketSession.PRE_MARKET
        
        # 常规交易时间
        if market_open <= current_time <= market_close:
            return MarketSession.REGULAR
        
        # 盘后：收盘后到收盘后2小时
        if market_close < current_time <= market_close + timedelta(hours=2):
            return MarketSession.AFTER_HOURS
        
        # 隔夜：其他时间
        return MarketSession.OVERNIGHT
    
    def _get_next_trading_day(self, current_time: datetime) -> Optional[datetime]:
        """获取下一个交易日"""
        for i in range(1, 8):  # 检查未来7天
            next_day = current_time + timedelta(days=i)
            market_hours = self._get_market_hours(next_day.weekday())
            if market_hours["is_trading_day"]:
                return next_day
        return None
    
    def _get_last_trading_day(self, current_time: datetime) -> Optional[datetime]:
        """获取上一个交易日"""
        for i in range(1, 8):  # 检查过去7天
            last_day = current_time - timedelta(days=i)
            market_hours = self._get_market_hours(last_day.weekday())
            if market_hours["is_trading_day"]:
                return last_day
        return None
    
    def _get_market_holidays(self, year: int) -> Set[datetime.date]:
        """获取市场节假日"""
        # 这里应该返回真实的节假日列表
        # 暂时返回一些示例节假日
        holidays = set()
        
        # 新年
        holidays.add(datetime.date(year, 1, 1))
        
        # 圣诞节（如果适用）
        holidays.add(datetime.date(year, 12, 25))
        
        return holidays
    
    def _is_holiday(self, weekday: int) -> bool:
        """检查是否为节假日"""
        # 简单的节假日检查逻辑
        # 在实际应用中，这里应该查询真实的节假日数据
        return False
    
    def _record_time_trigger(self, trigger_time: datetime, result: ConditionResult):
        """记录时间触发事件"""
        trigger_record = {
            "timestamp": trigger_time,
            "time_type": self.time_type.value,
            "satisfied": result.satisfied,
            "details": result.details,
            "value": result.value
        }
        
        self.time_triggers.append(trigger_record)
        
        # 保持记录数量
        if len(self.time_triggers) > 100:
            self.time_triggers = self.time_triggers[-50:]
    
    def get_time_statistics(self) -> Dict[str, Any]:
        """获取时间统计信息"""
        if not self.time_history:
            return {"message": "没有时间历史数据"}
        
        recent_times = self.time_history[-100:]
        
        # 计算小时分布
        hour_distribution = {}
        for dt in recent_times:
            hour = dt.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
        
        # 计算星期分布
        weekday_distribution = {}
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for dt in recent_times:
            weekday = dt.weekday()
            weekday_name = weekdays[weekday]
            weekday_distribution[weekday_name] = weekday_distribution.get(weekday_name, 0) + 1
        
        return {
            "total_evaluations": len(recent_times),
            "hour_distribution": hour_distribution,
            "weekday_distribution": weekday_distribution,
            "latest_evaluation": recent_times[-1].isoformat(),
            "most_active_hour": max(hour_distribution, key=hour_distribution.get) if hour_distribution else None
        }
    
    def get_trigger_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取触发摘要"""
        cutoff_time = datetime.now(self.tz) - timedelta(hours=hours)
        
        recent_triggers = [
            trigger for trigger in self.time_triggers 
            if trigger["timestamp"] >= cutoff_time
        ]
        
        total_triggers = len(recent_triggers)
        successful_triggers = sum(1 for trigger in recent_triggers if trigger["satisfied"])
        
        return {
            "period_hours": hours,
            "total_triggers": total_triggers,
            "successful_triggers": successful_triggers,
            "success_rate": successful_triggers / total_triggers if total_triggers > 0 else 0,
            "time_type_distribution": self._get_trigger_type_distribution(recent_triggers)
        }
    
    def _get_trigger_type_distribution(self, triggers: List[Dict[str, Any]]) -> Dict[str, int]:
        """获取触发类型分布"""
        distribution = {}
        for trigger in triggers:
            trigger_type = trigger["time_type"]
            distribution[trigger_type] = distribution.get(trigger_type, 0) + 1
        return distribution
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        
        # 转换时间值为可序列化格式
        time_value = self.time_value
        if isinstance(time_value, datetime):
            time_value = time_value.isoformat()
        elif isinstance(time_value, time):
            time_value = time_value.strftime("%H:%M:%S")
        
        data.update({
            "time_type": self.time_type.value,
            "timezone": self.timezone.value,
            "target_market": self.target_market,
            "include_weekends": self.include_weekends,
            "time_value": time_value,
            "time_history": [t.isoformat() for t in self.time_history[-20:]],  # 保存最近20个时间
            "time_statistics": self.get_time_statistics(),
            "trigger_summary": self.get_trigger_summary()
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]) -> 'TimeCondition':
        """从字典创建实例"""
        super().from_dict(data)
        
        self.time_type = TimeType(data.get("time_type", TimeType.CURRENT_TIME.value))
        self.timezone = TimeZone(data.get("timezone", TimeZone.UTC.value))
        self.target_market = data.get("target_market", "crypto")
        self.include_weekends = data.get("include_weekends", True)
        
        # 重建时区对象
        if PYTZ_AVAILABLE:
            self.tz = pytz.timezone(self.timezone.value)
        else:
            self.tz = datetime.timezone.utc
        
        # 重建时间历史
        time_history_strs = data.get("time_history", [])
        self.time_history = [
            datetime.fromisoformat(time_str) for time_str in time_history_strs
        ]
        
        return self
