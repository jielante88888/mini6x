"""
交易所健康监控和分析服务
实时监控交易所连接状态、性能指标和健康状况
"""

import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import weakref

import structlog

from ..adapters.base import BaseExchangeAdapter
from ..storage.redis_cache import get_market_cache
from ..utils.exceptions import ExchangeConnectionError, HealthCheckError

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    exchange: str
    market_type: str
    timestamp: datetime
    response_time_ms: float
    success_rate: float
    error_count: int
    total_requests: int
    data_freshness: float
    uptime_percentage: float
    latency_trend: str  # "improving", "stable", "degrading"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    exchange: str
    market_type: str
    status: HealthStatus
    response_time_ms: float
    error_message: Optional[str] = None
    last_successful_check: Optional[datetime] = None
    consecutive_failures: int = 0
    performance_score: float = 0.0


@dataclass
class AlertEvent:
    """告警事件"""
    id: str
    exchange: str
    market_type: str
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False


class ExchangeHealthMonitor:
    """交易所健康监控器"""
    
    def __init__(self):
        self.health_checks: Dict[str, Dict[str, HealthCheckResult]] = defaultdict(dict)
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.alert_handlers: List[Callable] = []
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.cache_manager = get_market_cache()
        
        # 监控配置
        self.check_interval = 30  # 秒
        self.failure_threshold = 3
        self.performance_threshold = 0.8
        self.timeout_threshold = 10.0  # 秒
        
        # 统计信息
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        
        logger.info("交易所健康监控器初始化完成")
    
    async def start_monitoring(self, adapters: Dict[str, BaseExchangeAdapter]):
        """开始健康监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(adapters))
        
        logger.info("交易所健康监控已启动")
    
    async def stop_monitoring(self):
        """停止健康监控"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("交易所健康监控已停止")
    
    async def _monitoring_loop(self, adapters: Dict[str, BaseExchangeAdapter]):
        """监控循环"""
        try:
            while self.monitoring_active:
                for adapter_key, adapter in adapters.items():
                    exchange, market_type = adapter_key.split('_', 1)
                    
                    try:
                        await self._check_exchange_health(exchange, market_type, adapter)
                    except Exception as e:
                        logger.error(f"健康检查失败 {adapter_key}: {e}")
                
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("交易所健康监控任务已取消")
        except Exception as e:
            logger.error(f"健康监控循环错误: {e}")
    
    async def _check_exchange_health(
        self, 
        exchange: str, 
        market_type: str, 
        adapter: BaseExchangeAdapter
    ) -> HealthCheckResult:
        """检查交易所健康状态"""
        adapter_key = f"{exchange}_{market_type}"
        check_start_time = time.time()
        self.total_checks += 1
        
        try:
            # 执行健康检查
            start_time = time.perf_counter()
            is_healthy = await self._execute_health_check(adapter)
            response_time = (time.perf_counter() - start_time) * 1000
            
            # 获取性能指标
            metrics = await self._get_performance_metrics(exchange, market_type)
            
            # 确定健康状态
            status = self._determine_health_status(
                is_healthy, response_time, metrics
            )
            
            # 获取历史失败次数
            previous_result = self.health_checks.get(exchange, {}).get(market_type)
            consecutive_failures = (previous_result.consecutive_failures + 1) if not is_healthy else 0
            
            # 计算性能得分
            performance_score = self._calculate_performance_score(metrics)
            
            # 创建健康检查结果
            result = HealthCheckResult(
                exchange=exchange,
                market_type=market_type,
                status=status,
                response_time_ms=response_time,
                error_message=None if is_healthy else "健康检查失败",
                last_successful_check=datetime.now(timezone.utc) if is_healthy else None,
                consecutive_failures=consecutive_failures,
                performance_score=performance_score
            )
            
            # 存储结果
            if exchange not in self.health_checks:
                self.health_checks[exchange] = {}
            self.health_checks[exchange][market_type] = result
            
            # 更新性能历史
            self.performance_history[adapter_key].append(metrics)
            
            # 检查是否需要告警
            await self._check_and_trigger_alerts(result)
            
            # 更新统计
            if is_healthy:
                self.successful_checks += 1
            else:
                self.failed_checks += 1
            
            logger.debug(f"健康检查完成 {adapter_key}: {status.value} ({response_time:.2f}ms)")
            
            return result
            
        except Exception as e:
            self.failed_checks += 1
            
            error_result = HealthCheckResult(
                exchange=exchange,
                market_type=market_type,
                status=HealthStatus.CRITICAL,
                response_time_ms=(time.time() - check_start_time) * 1000,
                error_message=str(e),
                consecutive_failures=(
                    self.health_checks.get(exchange, {}).get(market_type, HealthCheckResult('', '', HealthStatus.UNKNOWN)).consecutive_failures + 1
                )
            )
            
            if exchange not in self.health_checks:
                self.health_checks[exchange] = {}
            self.health_checks[exchange][market_type] = error_result
            
            await self._trigger_alert(error_result, AlertLevel.ERROR, f"健康检查异常: {e}")
            
            return error_result
    
    async def _execute_health_check(self, adapter: BaseExchangeAdapter) -> bool:
        """执行具体的健康检查"""
        try:
            # 检查连接状态
            if not await adapter.is_healthy():
                return False
            
            # 执行简单的API调用测试
            if hasattr(adapter, 'get_spot_ticker'):
                await adapter.get_spot_ticker('BTCUSDT')
            elif hasattr(adapter, 'get_futures_ticker'):
                await adapter.get_futures_ticker('BTCUSDT-PERP')
            else:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _get_performance_metrics(
        self, 
        exchange: str, 
        market_type: str
    ) -> PerformanceMetrics:
        """获取性能指标"""
        adapter_key = f"{exchange}_{market_type}"
        history = self.performance_history[adapter_key]
        
        if history:
            # 使用最近的指标或计算平均值
            recent_metrics = list(history)[-10:] if len(history) >= 10 else list(history)
            
            avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
            avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
            total_requests = sum(m.total_requests for m in recent_metrics)
            total_errors = sum(m.error_count for m in recent_metrics)
            avg_data_freshness = sum(m.data_freshness for m in recent_metrics) / len(recent_metrics)
            avg_uptime = sum(m.uptime_percentage for m in recent_metrics) / len(recent_metrics)
            
            # 计算延迟趋势
            if len(recent_metrics) >= 5:
                recent_avg = sum(m.response_time_ms for m in recent_metrics[-5:]) / 5
                previous_avg = sum(m.response_time_ms for m in recent_metrics[-10:-5]) / 5 if len(recent_metrics) >= 10 else recent_avg
                
                if recent_avg < previous_avg * 0.9:
                    latency_trend = "improving"
                elif recent_avg > previous_avg * 1.1:
                    latency_trend = "degrading"
                else:
                    latency_trend = "stable"
            else:
                latency_trend = "stable"
            
            return PerformanceMetrics(
                exchange=exchange,
                market_type=market_type,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=avg_response_time,
                success_rate=avg_success_rate,
                error_count=total_errors,
                total_requests=total_requests,
                data_freshness=avg_data_freshness,
                uptime_percentage=avg_uptime,
                latency_trend=latency_trend
            )
        else:
            # 初始指标
            return PerformanceMetrics(
                exchange=exchange,
                market_type=market_type,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=0.0,
                success_rate=1.0,
                error_count=0,
                total_requests=0,
                data_freshness=1.0,
                uptime_percentage=100.0,
                latency_trend="stable"
            )
    
    def _determine_health_status(
        self, 
        is_healthy: bool, 
        response_time: float, 
        metrics: PerformanceMetrics
    ) -> HealthStatus:
        """确定健康状态"""
        if not is_healthy:
            return HealthStatus.CRITICAL
        
        # 基于响应时间的评估
        if response_time > 5000:  # 5秒
            return HealthStatus.CRITICAL
        elif response_time > 2000:  # 2秒
            return HealthStatus.UNHEALTHY
        elif response_time > 1000:  # 1秒
            return HealthStatus.DEGRADED
        
        # 基于成功率的评估
        if metrics.success_rate < 0.8:
            return HealthStatus.UNHEALTHY
        elif metrics.success_rate < 0.9:
            return HealthStatus.DEGRADED
        
        # 基于数据新鲜度的评估
        if metrics.data_freshness < 0.7:
            return HealthStatus.DEGRADED
        elif metrics.data_freshness < 0.5:
            return HealthStatus.UNHEALTHY
        
        # 基于可用性的评估
        if metrics.uptime_percentage < 95:
            return HealthStatus.UNHEALTHY
        elif metrics.uptime_percentage < 98:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """计算性能得分（0-1）"""
        score = 0.0
        
        # 响应时间得分 (40%)
        if metrics.response_time_ms < 100:
            response_score = 1.0
        elif metrics.response_time_ms < 500:
            response_score = 0.8
        elif metrics.response_time_ms < 1000:
            response_score = 0.6
        else:
            response_score = 0.4
        
        score += response_score * 0.4
        
        # 成功率得分 (30%)
        score += metrics.success_rate * 0.3
        
        # 数据新鲜度得分 (20%)
        score += metrics.data_freshness * 0.2
        
        # 可用性得分 (10%)
        score += (metrics.uptime_percentage / 100.0) * 0.1
        
        return min(1.0, max(0.0, score))
    
    async def _check_and_trigger_alerts(self, result: HealthCheckResult):
        """检查并触发告警"""
        # 连续失败告警
        if result.consecutive_failures >= self.failure_threshold:
            await self._trigger_alert(
                result,
                AlertLevel.ERROR,
                f"连续 {result.consecutive_failures} 次健康检查失败"
            )
        
        # 性能降级告警
        if result.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            await self._trigger_alert(
                result,
                AlertLevel.WARNING,
                f"交易所性能降级: {result.status.value}, 响应时间: {result.response_time_ms:.2f}ms"
            )
        
        # 性能恢复告警
        if result.consecutive_failures == 0 and result.status == HealthStatus.HEALTHY:
            previous_result = self.health_checks.get(result.exchange, {}).get(result.market_type)
            if previous_result and previous_result.status != HealthStatus.HEALTHY:
                await self._trigger_alert(
                    result,
                    AlertLevel.INFO,
                    f"交易所性能已恢复: {result.exchange} {result.market_type}"
                )
    
    async def _trigger_alert(
        self, 
        result: HealthCheckResult, 
        level: AlertLevel, 
        message: str
    ):
        """触发告警"""
        alert = AlertEvent(
            id=f"{result.exchange}_{result.market_type}_{int(time.time())}",
            exchange=result.exchange,
            market_type=result.market_type,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 存储告警（可选）
        logger.warning(f"交易所告警 - {result.exchange}/{result.market_type}: {message}")
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
    
    def add_alert_handler(self, handler: Callable[[AlertEvent], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def get_exchange_health(self, exchange: str, market_type: str) -> Optional[HealthCheckResult]:
        """获取交易所健康状态"""
        return self.health_checks.get(exchange, {}).get(market_type)
    
    def get_all_exchanges_health(self) -> Dict[str, Dict[str, HealthCheckResult]]:
        """获取所有交易所健康状态"""
        return dict(self.health_checks)
    
    def get_performance_metrics(
        self, 
        exchange: str, 
        market_type: str
    ) -> List[PerformanceMetrics]:
        """获取性能指标历史"""
        adapter_key = f"{exchange}_{market_type}"
        return list(self.performance_history[adapter_key])
    
    def get_overall_health_summary(self) -> Dict[str, Any]:
        """获取总体健康摘要"""
        total_exchanges = len(self.health_checks)
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        critical_count = 0
        
        for exchange_data in self.health_checks.values():
            for result in exchange_data.values():
                if result.status == HealthStatus.HEALTHY:
                    healthy_count += 1
                elif result.status == HealthStatus.DEGRADED:
                    degraded_count += 1
                elif result.status == HealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                elif result.status == HealthStatus.CRITICAL:
                    critical_count += 1
        
        success_rate = (self.successful_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        
        return {
            "total_exchanges": total_exchanges,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "critical_count": critical_count,
            "success_rate": success_rate,
            "total_checks": self.total_checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class MarketAnalyzer:
    """市场分析和异常检测服务"""
    
    def __init__(self):
        self.health_monitor = ExchangeHealthMonitor()
        self.anomaly_detectors: List[Callable] = []
        self.market_patterns: Dict[str, List[Dict]] = defaultdict(list)
        
        logger.info("市场分析器初始化完成")
    
    async def start_analysis(self, adapters: Dict[str, BaseExchangeAdapter]):
        """开始市场分析"""
        await self.health_monitor.start_monitoring(adapters)
        
        # 添加基本异常检测器
        self.add_anomaly_detector(self._detect_response_time_anomalies)
        self.add_anomaly_detector(self._detect_success_rate_anomalies)
        self.add_anomaly_detector(self._detect_data_consistency_anomalies)
        
        # 启动异常检测任务
        asyncio.create_task(self._anomaly_detection_loop())
        
        logger.info("市场分析器已启动")
    
    async def stop_analysis(self):
        """停止市场分析"""
        await self.health_monitor.stop_monitoring()
        logger.info("市场分析器已停止")
    
    def add_anomaly_detector(self, detector: Callable):
        """添加异常检测器"""
        self.anomaly_detectors.append(detector)
    
    async def _anomaly_detection_loop(self):
        """异常检测循环"""
        while True:
            try:
                await self._run_anomaly_detection()
                await asyncio.sleep(60)  # 每分钟检测一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"异常检测循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _run_anomaly_detection(self):
        """运行异常检测"""
        for detector in self.anomaly_detectors:
            try:
                await detector()
            except Exception as e:
                logger.error(f"异常检测器执行失败: {e}")
    
    async def _detect_response_time_anomalies(self):
        """检测响应时间异常"""
        for exchange_data in self.health_monitor.health_checks.values():
            for market_type, result in exchange_data.items():
                metrics_list = self.health_monitor.get_performance_metrics(result.exchange, market_type)
                
                if len(metrics_list) >= 10:
                    recent_responses = [m.response_time_ms for m in metrics_list[-10:]]
                    avg_response = sum(recent_responses) / len(recent_responses)
                    
                    # 检测响应时间突然增加
                    latest_response = recent_responses[-1]
                    if latest_response > avg_response * 2 and latest_response > 1000:
                        logger.warning(
                            f"响应时间异常检测: {result.exchange}/{market_type} "
                            f"最新响应 {latest_response:.2f}ms 超过平均值 {avg_response:.2f}ms 的2倍"
                        )
    
    async def _detect_success_rate_anomalies(self):
        """检测成功率异常"""
        for exchange_data in self.health_monitor.health_checks.values():
            for market_type, result in exchange_data.items():
                metrics_list = self.health_monitor.get_performance_metrics(result.exchange, market_type)
                
                if len(metrics_list) >= 5:
                    recent_rates = [m.success_rate for m in metrics_list[-5:]]
                    avg_rate = sum(recent_rates) / len(recent_rates)
                    
                    # 检测成功率下降
                    if avg_rate < 0.8:
                        logger.warning(
                            f"成功率异常检测: {result.exchange}/{market_type} "
                            f"近期成功率 {avg_rate:.2f} 低于80%"
                        )
    
    async def _detect_data_consistency_anomalies(self):
        """检测数据一致性异常"""
        # 比较同一币种在不同交易所的价格差异
        for exchange_data in self.health_monitor.health_checks.items():
            exchange, markets = exchange_data
            
            if 'spot' in markets and 'futures' in markets:
                spot_result = markets['spot']
                futures_result = markets['futures']
                
                # 检查现货和期货价格是否存在异常差异
                if (spot_result.status == HealthStatus.HEALTHY and 
                    futures_result.status == HealthStatus.HEALTHY):
                    
                    # 这里可以添加具体的价差计算逻辑
                    # 目前只是示例，实际实现需要获取实时价格数据
    
    def get_market_analysis_report(self) -> Dict[str, Any]:
        """获取市场分析报告"""
        health_summary = self.health_monitor.get_overall_health_summary()
        
        # 添加性能趋势分析
        performance_trends = {}
        for exchange_data in self.health_monitor.health_checks.items():
            exchange, markets = exchange_data
            
            exchange_trends = {}
            for market_type, result in markets.items():
                metrics_list = self.health_monitor.get_performance_metrics(exchange, market_type)
                
                if len(metrics_list) >= 5:
                    recent_avg = sum(m.response_time_ms for m in metrics_list[-5:]) / 5
                    previous_avg = sum(m.response_time_ms for m in metrics_list[-10:-5]) / 5 if len(metrics_list) >= 10 else recent_avg
                    
                    if recent_avg < previous_avg * 0.9:
                        trend = "improving"
                    elif recent_avg > previous_avg * 1.1:
                        trend = "degrading"
                    else:
                        trend = "stable"
                    
                    exchange_trends[market_type] = {
                        "trend": trend,
                        "recent_avg_latency": recent_avg,
                        "performance_score": result.performance_score
                    }
            
            if exchange_trends:
                performance_trends[exchange] = exchange_trends
        
        return {
            "health_summary": health_summary,
            "performance_trends": performance_trends,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# 全局实例
_market_analyzer: Optional[MarketAnalyzer] = None


async def get_market_analyzer() -> MarketAnalyzer:
    """获取全局市场分析器实例"""
    global _market_analyzer
    
    if _market_analyzer is None:
        _market_analyzer = MarketAnalyzer()
    
    return _market_analyzer


async def shutdown_market_analyzer():
    """关闭市场分析器"""
    global _market_analyzer
    
    if _market_analyzer:
        await _market_analyzer.stop_analysis()
        _market_analyzer = None


if __name__ == "__main__":
    # 测试市场分析器
    import asyncio
    
    async def test_market_analyzer():
        print("测试市场分析器...")
        
        try:
            analyzer = await get_market_analyzer()
            
            # 获取健康摘要
            health_summary = analyzer.health_monitor.get_overall_health_summary()
            print(f"健康摘要: {health_summary}")
            
            # 获取分析报告
            report = analyzer.get_market_analysis_report()
            print(f"分析报告: {json.dumps(report, indent=2, default=str)}")
            
        except Exception as e:
            print(f"测试失败: {e}")
        finally:
            await shutdown_market_analyzer()
    
    asyncio.run(test_market_analyzer())