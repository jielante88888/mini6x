"""
自定义异常类定义
包含系统各个层面的异常类型
"""

from typing import List, Optional, Any, Dict
from fastapi import HTTPException
import structlog

logger = structlog.get_logger()


class BaseAPIException(Exception):
    """基础API异常类"""
    
    def __init__(self, message: str, code: str = None, details: Any = None):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


class ValidationError(BaseAPIException):
    """参数验证错误"""
    
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", errors)
        self.errors = errors or []


class AuthenticationError(BaseAPIException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(BaseAPIException):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class ExchangeConnectionError(BaseAPIException):
    """交易所连接错误"""
    
    def __init__(self, exchange: str, message: str = None):
        if not message:
            message = f"无法连接到交易所 {exchange}"
        super().__init__(message, "EXCHANGE_CONNECTION_ERROR")
        self.exchange = exchange


class ExchangeAPIError(BaseAPIException):
    """交易所API错误"""
    
    def __init__(self, exchange: str, api_error: str = None):
        if not api_error:
            api_error = f"{exchange} API调用失败"
        super().__init__(api_error, "EXCHANGE_API_ERROR")
        self.exchange = exchange


class InsufficientFundsError(BaseAPIException):
    """资金不足错误"""
    
    def __init__(self, message: str = "资金余额不足"):
        super().__init__(message, "INSUFFICIENT_FUNDS_ERROR")


class InvalidOrderError(BaseAPIException):
    """订单无效错误"""
    
    def __init__(self, message: str = "订单参数无效"):
        super().__init__(message, "INVALID_ORDER_ERROR")


class OrderNotFoundError(BaseAPIException):
    """订单不存在错误"""
    
    def __init__(self, message: str = "订单不存在"):
        super().__init__(message, "ORDER_NOT_FOUND_ERROR")


class TradingPairNotFoundError(BaseAPIException):
    """交易对不存在错误"""
    
    def __init__(self, symbol: str, message: str = None):
        if not message:
            message = f"交易对 {symbol} 不存在"
        super().__init__(message, "TRADING_PAIR_NOT_FOUND_ERROR")
        self.symbol = symbol


class MarketDataError(BaseAPIException):
    """市场数据错误"""
    
    def __init__(self, message: str = "市场数据获取失败"):
        super().__init__(message, "MARKET_DATA_ERROR")


class DatabaseError(BaseAPIException):
    """数据库错误"""
    
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, "DATABASE_ERROR")


class CacheError(BaseAPIException):
    """缓存错误"""
    
    def __init__(self, message: str = "缓存操作失败"):
        super().__init__(message, "CACHE_ERROR")


class WebSocketError(BaseAPIException):
    """WebSocket错误"""
    
    def __init__(self, message: str = "WebSocket连接失败"):
        super().__init__(message, "WEBSOCKET_ERROR")


class StrategyError(BaseAPIException):
    """策略执行错误"""
    
    def __init__(self, message: str = "策略执行失败"):
        super().__init__(message, "STRATEGY_ERROR")


class RiskManagementError(BaseAPIException):
    """风险管理错误"""
    
    def __init__(self, message: str = "风险管理检查失败"):
        super().__init__(message, "RISK_MANAGEMENT_ERROR")


class NotificationError(BaseAPIException):
    """通知发送错误"""
    
    def __init__(self, message: str = "通知发送失败"):
        super().__init__(message, "NOTIFICATION_ERROR")


class ConfigurationError(BaseAPIException):
    """配置错误"""
    
    def __init__(self, message: str = "系统配置错误"):
        super().__init__(message, "CONFIGURATION_ERROR")


class ServiceUnavailableError(BaseAPIException):
    """服务不可用错误"""
    
    def __init__(self, message: str = "服务暂时不可用"):
        super().__init__(message, "SERVICE_UNAVAILABLE_ERROR")


class RateLimitExceededError(BaseAPIException):
    """API速率限制错误"""
    
    def __init__(self, message: str = "API调用频率超限"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED_ERROR")


# HTTP状态码映射
HTTP_STATUS_MAPPING = {
    ValidationError: 422,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ExchangeConnectionError: 503,
    ExchangeAPIError: 502,
    InsufficientFundsError: 400,
    InvalidOrderError: 400,
    OrderNotFoundError: 404,
    TradingPairNotFoundError: 404,
    MarketDataError: 503,
    DatabaseError: 500,
    CacheError: 503,
    WebSocketError: 503,
    StrategyError: 400,
    RiskManagementError: 400,
    NotificationError: 503,
    ConfigurationError: 500,
    ServiceUnavailableError: 503,
    RateLimitExceededError: 429,
}


def get_http_status_code(exception_class) -> int:
    """获取异常对应的HTTP状态码"""
    for exc_class, status_code in HTTP_STATUS_MAPPING.items():
        if isinstance(exception_class, exc_class):
            return status_code
    return 500


def handle_exception(exception: Exception) -> HTTPException:
    """处理异常并转换为HTTP异常"""
    if isinstance(exception, BaseAPIException):
        status_code = get_http_status_code(type(exception))
        
        # 记录异常日志
        logger.error(
            "API异常",
            error_type=type(exception).__name__,
            error_code=exception.code,
            error_message=exception.message,
            error_details=exception.details
        )
        
        return HTTPException(
            status_code=status_code,
            detail=exception.to_dict()
        )
    else:
        # 处理未知异常
        logger.error(
            "未处理的异常",
            error_type=type(exception).__name__,
            error_message=str(exception)
        )
        
        return HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "error_type": type(exception).__name__
            }
        )


# 异常装饰器
def handle_api_exceptions(func):
    """API异常处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise handle_exception(e)
    return wrapper


# 验证函数
def validate_symbol(symbol: str, supported_symbols: List[str] = None):
    """验证交易对符号"""
    if not symbol:
        raise ValidationError("交易对符号不能为空")
    
    # 检查格式
    if not symbol.isalnum() and '-' not in symbol:
        raise ValidationError(f"无效的交易对格式: {symbol}")
    
    # 检查是否支持
    if supported_symbols and symbol not in supported_symbols:
        raise TradingPairNotFoundError(symbol)
    
    return True


def validate_order_params(symbol: str, quantity: float, price: float = None, order_type: str = None):
    """验证订单参数"""
    if not symbol:
        raise ValidationError("交易对不能为空")
    
    if not quantity or quantity <= 0:
        raise ValidationError("订单数量必须大于0")
    
    if order_type in ["limit", "stop_limit"] and (not price or price <= 0):
        raise ValidationError("限价单必须提供有效价格")
    
    return True


def validate_exchange_name(exchange: str, supported_exchanges: List[str] = None):
    """验证交易所名称"""
    if not exchange:
        raise ValidationError("交易所名称不能为空")
    
    if supported_exchanges and exchange not in supported_exchanges:
        raise ValidationError(f"不支持的交易所: {exchange}")
    
    return True


if __name__ == "__main__":
    # 测试异常类
    try:
        raise ValidationError("测试验证错误", errors=[{"field": "symbol", "message": "格式无效"}])
    except BaseAPIException as e:
        print(f"异常类型: {type(e).__name__}")
        print(f"异常信息: {e.message}")
        print(f"异常详情: {e.to_dict()}")
        print(f"HTTP状态码: {get_http_status_code(e)}")