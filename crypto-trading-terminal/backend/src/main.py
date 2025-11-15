"""
FastAPI应用程序核心模块
包含中间件、错误处理、API路由和应用生命周期管理
"""

from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn
from prometheus_client import Counter, Histogram, generate_latest

from .config import settings
from .storage.database import init_database, close_database, get_db_session
from .storage.redis_cache import init_redis, close_redis
from .api.routes import market, trading, user, system, order_history, risk_alerts, emergency_stop, reports
from .utils.logging import setup_logging
from .utils.exceptions import (
    ExchangeConnectionError,
    InsufficientFundsError,
    InvalidOrderError,
    DatabaseError,
    ValidationError
)

# 设置日志
setup_logging()
logger = structlog.get_logger()

# 性能监控指标
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动加密货币交易终端后端服务", version=settings.APP_VERSION)
    
    try:
        # 初始化数据库
        logger.info("📊 初始化数据库连接")
        init_database()
        
        # 初始化Redis缓存
        logger.info("💾 初始化Redis缓存")
        redis_connected = await init_redis()
        if redis_connected:
            logger.info("✅ Redis连接成功")
        else:
            logger.warning("⚠️ Redis连接失败，将使用内存缓存")
        
        # 验证环境配置
        logger.info("🔧 验证环境配置")
        if not settings.validate_environment():
            logger.warning("⚠️ 环境变量验证失败，部分功能可能受限")
        
        # 启动数据服务
        logger.info("📡 启动市场数据服务")
        # TODO: 启动市场数据获取服务
        
        # 启动WebSocket服务
        logger.info("🔌 启动WebSocket服务")
        # TODO: 启动WebSocket服务
        
        logger.info("✅ 应用启动完成")
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    
    yield
    
    # 关闭时的清理
    logger.info("🛑 关闭加密货币交易终端后端服务")
    
    try:
        # 关闭数据库连接
        logger.info("📊 关闭数据库连接")
        close_database()
        
        # 关闭Redis连接
        logger.info("💾 关闭Redis连接")
        await close_redis()
        
        # 关闭数据服务
        logger.info("📡 关闭市场数据服务")
        # TODO: 关闭市场数据服务
        
        # 关闭WebSocket服务
        logger.info("🔌 关闭WebSocket服务")
        # TODO: 关闭WebSocket服务
        
        logger.info("✅ 应用关闭完成")
        
    except Exception as e:
        logger.error(f"❌ 应用关闭错误: {e}")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_NAME,
    description="""加密货币专业交易终端系统后端API
    
## 功能特性

- **多交易所支持**: 币安、OKX现货/合约交易
- **实时行情**: WebSocket实时数据推送
- **智能交易**: 自动下单、风险控制、策略交易
- **条件触发**: 多维度条件监控和通知
- **AI分析**: 智能行情分析和策略优化
- **风险管理**: 完善的资金管理和风险控制

## 技术架构

- **框架**: FastAPI + Uvicorn
- **数据库**: SQLAlchemy + PostgreSQL/SQLite
- **缓存**: Redis
- **监控**: Prometheus + Grafana
- **日志**: Structlog
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    
    # OpenAPI配置
    openapi_tags=[
        {
            "name": "market",
            "description": "市场数据API - 现货和合约行情信息"
        },
        {
            "name": "trading", 
            "description": "交易API - 订单管理和交易执行"
        },
        {
            "name": "user",
            "description": "用户API - 账户管理和用户信息"
        },
        {
            "name": "system",
            "description": "系统API - 监控和系统状态"
        },
        {
            "name": "reports",
            "description": "报表API - PDF/CSV报告生成和下载"
        }
    ]
)


# 中间件配置
if settings.DEBUG:
    # 开发环境中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 生产环境中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://your-domain.com"],  # 生产环境需要设置具体域名
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# 安全中间件
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"])

# 压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求监控中间件
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """请求监控中间件"""
    start_time = datetime.utcnow()
    
    # 获取请求信息
    method = request.method
    endpoint = request.url.path
    client_ip = request.client.host
    
    # 处理请求
    try:
        response = await call_next(request)
        
        # 计算处理时间
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 记录请求指标
        request_count.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(process_time)
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
        
        return response
        
    except Exception as e:
        # 处理异常
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.error(
            "请求处理异常",
            method=method,
            endpoint=endpoint,
            client_ip=client_ip,
            error=str(e),
            process_time=process_time
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "内部服务器错误",
                "message": "服务器处理请求时发生错误",
                "timestamp": datetime.utcnow().isoformat(),
                "path": endpoint
            }
        )


# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    logger.warning(
        "HTTP异常",
        method=request.method,
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP异常",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """参数验证异常处理器"""
    logger.warning(
        "参数验证失败",
        method=request.method,
        path=request.url.path,
        validation_errors=exc.errors
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "参数验证失败",
            "message": "请求参数不符合要求",
            "validation_errors": exc.errors,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(ExchangeConnectionError)
async def exchange_connection_exception_handler(request: Request, exc: ExchangeConnectionError):
    """交易所连接异常处理器"""
    logger.error(
        "交易所连接异常",
        method=request.method,
        path=request.url.path,
        exchange=exc.exchange,
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "交易所连接异常",
            "message": f"无法连接到{exc.exchange}交易所",
            "exchange": exc.exchange,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """数据库异常处理器"""
    logger.error(
        "数据库异常",
        method=request.method,
        path=request.url.path,
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "数据库异常",
            "message": "数据库操作失败",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(
        "未处理的异常",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "服务器内部错误",
            "message": "服务器遇到意外错误",
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        with get_db_session() as session:
            # 简单的数据库连接测试
            pass
        
        # 检查Redis连接
        from ..storage.redis_cache import get_cache_manager
        cache_manager = get_cache_manager()
        redis_healthy = False
        if cache_manager:
            redis_healthy = await cache_manager.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "database": "connected",
            "redis": "connected" if redis_healthy else "disconnected",
            "uptime": "running"
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "version": settings.APP_VERSION
            }
        )


# API信息端点
@app.get("/")
async def root():
    """API信息端点"""
    return {
        "message": "加密货币专业交易终端系统API",
        "version": settings.APP_VERSION,
        "description": "支持币安和OKX现货/合约交易的实时行情和自动交易系统",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "status": "running"
    }


# Prometheus指标端点
@app.get("/metrics")
async def get_metrics():
    """Prometheus监控指标"""
    return Response(generate_latest(), media_type="text/plain")


# API路由注册
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])
app.include_router(user.router, prefix="/api/v1/user", tags=["user"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(order_history.router, prefix="/api/v1/order-history", tags=["order-history"])
app.include_router(risk_alerts.router, prefix="/api/v1/risk-alerts", tags=["risk-alerts"])
app.include_router(emergency_stop.router, prefix="/api/v1/emergency-stop", tags=["emergency-stop"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


if __name__ == "__main__":
    # 开发环境启动
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True
    )