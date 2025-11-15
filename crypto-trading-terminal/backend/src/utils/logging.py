"""
日志工具模块
配置Structured Logging和系统监控
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from ..config import settings


def setup_logging():
    """配置Structured Logging"""
    
    # 设置日志级别
    if settings.DEBUG:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    
    # 配置标准库logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
    
    # 配置Structlog
    structlog.configure(
        processors=[
            # 首先处理时间戳
            structlog.stdlib.filter_by_level,
            
            # 添加logger名称
            structlog.stdlib.add_logger_name,
            
            # 添加日志级别
            structlog.stdlib.add_log_level,
            
            # 使用ISO格式的时间戳
            structlog.processors.TimeStamper(fmt="iso"),
            
            # 添加进程和线程信息
            structlog.processors.add_log_level,
            
            # 格式化异常
            structlog.processors.format_exc_info,
            
            # 缓存logger在第一次使用后
            structlog.stdlib.PositionalArgumentsFormatter(),
            
            # 环境变量处理器
            structlog.processors.add_log_level,
            
            # JSON渲染器
            structlog.processors.JSONRenderer()
        ],
        
        # 包装器类
        wrapper_class=structlog.stdlib.BoundLogger,
        
        # Logger工厂
        logger_factory=structlog.stdlib.LoggerFactory(),
        
        # 缓存配置
        cache_logger_on_first_use=True,
    )
    
    # 配置特定的logger级别
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        structlog.get_logger(logger_name).setLevel(log_level)
    
    # 开发环境下增加详细日志
    if settings.DEBUG:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer(colors=True),
                structlog.processors.TimeStamper(fmt="iso"),
            ]
        )


def get_logger(name: str = None, module: str = None) -> structlog.BoundLogger:
    """获取配置好的logger"""
    if name:
        return structlog.get_logger(name)
    elif module:
        return structlog.get_logger(module)
    else:
        return structlog.get_logger()


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, request_id: str = None):
        self.request_id = request_id or "unknown"
        self.logger = get_logger("request")
    
    def log_request(self, method: str, path: str, client_ip: str, user_agent: str = None, **kwargs):
        """记录请求开始"""
        self.logger.info(
            "HTTP请求开始",
            request_id=self.request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
            **kwargs
        )
    
    def log_response(self, method: str, path: str, status_code: int, 
                    duration_ms: float, response_size: int = None, **kwargs):
        """记录请求响应"""
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        
        getattr(self.logger, level)(
            "HTTP请求响应",
            request_id=self.request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            response_size=response_size,
            **kwargs
        )
    
    def log_error(self, error: Exception, **kwargs):
        """记录错误"""
        self.logger.error(
            "请求处理错误",
            request_id=self.request_id,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


class DatabaseLogger:
    """数据库日志记录器"""
    
    def __init__(self):
        self.logger = get_logger("database")
    
    def log_query(self, query: str, params: Dict[str, Any] = None, duration_ms: float = None):
        """记录数据库查询"""
        self.logger.debug(
            "数据库查询",
            query=query,
            params=params,
            duration_ms=duration_ms
        )
    
    def log_transaction(self, operation: str, table: str, record_id: int = None, **kwargs):
        """记录数据库事务"""
        self.logger.info(
            "数据库事务",
            operation=operation,
            table=table,
            record_id=record_id,
            **kwargs
        )
    
    def log_error(self, operation: str, error: Exception, **kwargs):
        """记录数据库错误"""
        self.logger.error(
            "数据库错误",
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


class ExchangeLogger:
    """交易所日志记录器"""
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.logger = get_logger("exchange", exchange_name)
    
    def log_api_call(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                    duration_ms: float = None, status_code: int = None, **kwargs):
        """记录交易所API调用"""
        level = "info" if status_code and status_code < 400 else "warning"
        
        getattr(self.logger, level)(
            "交易所API调用",
            exchange=self.exchange_name,
            method=method,
            endpoint=endpoint,
            params=params,
            duration_ms=duration_ms,
            status_code=status_code,
            **kwargs
        )
    
    def log_market_data(self, symbol: str, price: float, timestamp: datetime, **kwargs):
        """记录市场数据"""
        self.logger.debug(
            "市场数据更新",
            exchange=self.exchange_name,
            symbol=symbol,
            price=price,
            timestamp=timestamp.isoformat(),
            **kwargs
        )
    
    def log_order(self, order_id: str, symbol: str, side: str, quantity: float, 
                 price: float = None, status: str = None, **kwargs):
        """记录订单操作"""
        self.logger.info(
            "订单操作",
            exchange=self.exchange_name,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status=status,
            **kwargs
        )
    
    def log_error(self, operation: str, error: Exception, **kwargs):
        """记录交易所错误"""
        self.logger.error(
            "交易所错误",
            exchange=self.exchange_name,
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


class TradingLogger:
    """交易日志记录器"""
    
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.logger = get_logger("trading", "user" if user_id else "system")
    
    def log_order_created(self, order_id: str, symbol: str, side: str, quantity: float,
                         order_type: str, price: float = None, **kwargs):
        """记录订单创建"""
        self.logger.info(
            "订单创建",
            user_id=self.user_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            **kwargs
        )
    
    def log_order_filled(self, order_id: str, filled_quantity: float, 
                        average_price: float, commission: float = None, **kwargs):
        """记录订单成交"""
        self.logger.info(
            "订单成交",
            user_id=self.user_id,
            order_id=order_id,
            filled_quantity=filled_quantity,
            average_price=average_price,
            commission=commission,
            **kwargs
        )
    
    def log_trade_executed(self, trade_id: str, symbol: str, side: str, 
                          price: float, quantity: float, **kwargs):
        """记录交易执行"""
        self.logger.info(
            "交易执行",
            user_id=self.user_id,
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            **kwargs
        )
    
    def log_strategy_execution(self, strategy_name: str, action: str, 
                              symbol: str = None, **kwargs):
        """记录策略执行"""
        self.logger.info(
            "策略执行",
            user_id=self.user_id,
            strategy_name=strategy_name,
            action=action,
            symbol=symbol,
            **kwargs
        )
    
    def log_risk_alert(self, alert_type: str, message: str, **kwargs):
        """记录风险警告"""
        self.logger.warning(
            "风险警告",
            user_id=self.user_id,
            alert_type=alert_type,
            message=message,
            **kwargs
        )


class SystemLogger:
    """系统日志记录器"""
    
    def __init__(self):
        self.logger = get_logger("system")
    
    def log_startup(self, component: str, version: str, config: Dict[str, Any] = None):
        """记录组件启动"""
        self.logger.info(
            "系统启动",
            component=component,
            version=version,
            config=config
        )
    
    def log_shutdown(self, component: str, duration_seconds: float = None):
        """记录组件关闭"""
        self.logger.info(
            "系统关闭",
            component=component,
            duration_seconds=duration_seconds
        )
    
    def log_config_change(self, config_key: str, old_value: Any, new_value: Any, 
                         changed_by: str = "system"):
        """记录配置变更"""
        self.logger.info(
            "配置变更",
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by
        )
    
    def log_performance(self, metric: str, value: float, unit: str = None, **kwargs):
        """记录性能指标"""
        self.logger.info(
            "性能指标",
            metric=metric,
            value=value,
            unit=unit,
            **kwargs
        )


# 便捷的logger实例
request_logger = RequestLogger()
database_logger = DatabaseLogger()
system_logger = SystemLogger()


def get_exchange_logger(exchange_name: str) -> ExchangeLogger:
    """获取交易所专用logger"""
    return ExchangeLogger(exchange_name)


def get_trading_logger(user_id: int = None) -> TradingLogger:
    """获取交易专用logger"""
    return TradingLogger(user_id)


if __name__ == "__main__":
    # 测试日志配置
    setup_logging()
    logger = get_logger("test")
    
    logger.info("测试信息日志", test_field="test_value")
    logger.debug("测试调试日志", debug_info="debug_value")
    logger.warning("测试警告日志", warning_type="test")
    logger.error("测试错误日志", error_code="TEST_ERROR")
    
    # 测试专用logger
    exchange_logger = get_exchange_logger("binance")
    exchange_logger.log_api_call("GET", "/api/v3/ticker/24hr", duration_ms=100.5)
    
    trading_logger = get_trading_logger(123)
    trading_logger.log_order_created("test_order_1", "BTCUSDT", "buy", 0.1, "limit", 50000.0)