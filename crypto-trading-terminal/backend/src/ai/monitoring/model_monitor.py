"""
Model Performance Monitor
Comprehensive monitoring system for AI model performance tracking and alerting
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
import numpy as np
from pathlib import Path

from ..utils.metrics_calculator import MetricsCalculator
from ..utils.alert_manager import AlertManager

logger = structlog.get_logger()


class ModelStatus(Enum):
    """Model operational status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RETRAINING = "retraining"
    OFFLINE = "offline"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics snapshot"""
    model_id: str
    timestamp: datetime
    accuracy: Decimal
    precision: Decimal
    recall: Decimal
    f1_score: Decimal
    auc_score: Decimal
    prediction_latency_ms: Decimal
    throughput_predictions_per_second: Decimal
    data_drift_score: Decimal
    concept_drift_score: Decimal
    prediction_confidence_avg: Decimal
    error_rate: Decimal
    memory_usage_mb: Decimal
    cpu_usage_percent: Decimal


@dataclass
class ModelAlert:
    """Model performance alert"""
    alert_id: str
    model_id: str
    alert_level: AlertLevel
    title: str
    message: str
    metric_name: str
    current_value: Decimal
    threshold_value: Decimal
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelVersion:
    """Model version information"""
    version_id: str
    model_id: str
    version_number: str
    creation_time: datetime
    performance_metrics: ModelPerformanceMetrics
    training_data_hash: str
    model_file_path: str
    is_active: bool
    notes: str = ""
    rollback_data: Dict[str, Any] = field(default_factory=dict)


class ModelPerformanceMonitor:
    """Advanced model performance monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "monitoring_interval_seconds": 60,
            "alert_thresholds": {
                "accuracy_drop": Decimal("0.05"),  # 5% accuracy drop
                "prediction_latency_max": Decimal("2000"),  # 2 seconds
                "error_rate_max": Decimal("0.02"),  # 2%
                "data_drift_threshold": Decimal("0.1"),  # 10%
                "memory_usage_max": Decimal("1000"),  # 1GB
                "cpu_usage_max": Decimal("80")  # 80%
            },
            "retraining_triggers": {
                "accuracy_threshold": Decimal("0.85"),
                "performance_decline_streak": 3,  # Consecutive periods below threshold
                "data_drift_threshold": Decimal("0.15"),
                "days_since_last_training": 30
            },
            "history_retention_days": 90
        }
        
        # Performance tracking
        self.model_metrics: Dict[str, List[ModelPerformanceMetrics]] = {}
        self.model_alerts: Dict[str, List[ModelAlert]] = {}
        self.model_versions: Dict[str, List[ModelVersion]] = {}
        self.model_status: Dict[str, ModelStatus] = {}
        
        # Performance calculator and alert manager
        self.metrics_calculator = MetricsCalculator()
        self.alert_manager = AlertManager()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_alerts_generated = 0
        self.total_retraining_triggers = 0
        self.avg_model_accuracy = Decimal("0.0")
        
        logger.info("模型性能监控器初始化完成", config=self.config)
    
    async def start_monitoring(self):
        """Start continuous model performance monitoring"""
        if self.is_monitoring:
            logger.warning("模型性能监控已在运行")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("模型性能监控已启动")
    
    async def stop_monitoring(self):
        """Stop model performance monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("模型性能监控已停止")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Monitor all registered models
                await self._monitor_all_models()
                
                # Check for retraining triggers
                await self._check_retraining_triggers()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config["monitoring_interval_seconds"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("监控循环错误", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _monitor_all_models(self):
        """Monitor performance of all registered models"""
        model_ids = list(self.model_status.keys())
        
        for model_id in model_ids:
            try:
                await self._monitor_model(model_id)
            except Exception as e:
                logger.error("模型监控失败", model_id=model_id, error=str(e))
                
                # Update model status to offline
                self.model_status[model_id] = ModelStatus.OFFLINE
                
                # Generate critical alert
                await self._generate_alert(
                    model_id=model_id,
                    alert_level=AlertLevel.CRITICAL,
                    title="模型监控失败",
                    message=f"模型 {model_id} 监控失败: {str(e)}",
                    metric_name="monitoring_error",
                    current_value=Decimal("1"),
                    threshold_value=Decimal("0"),
                    metadata={"error": str(e)}
                )
    
    async def _monitor_model(self, model_id: str):
        """Monitor performance of a specific model"""
        try:
            # Simulate model performance metrics (in real implementation, this would come from actual model)
            metrics = await self._collect_model_metrics(model_id)
            
            # Store metrics
            if model_id not in self.model_metrics:
                self.model_metrics[model_id] = []
            self.model_metrics[model_id].append(metrics)
            
            # Keep only recent metrics (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            self.model_metrics[model_id] = [
                m for m in self.model_metrics[model_id] if m.timestamp > cutoff_time
            ]
            
            # Update model status
            await self._update_model_status(model_id, metrics)
            
            # Check for performance alerts
            await self._check_performance_alerts(model_id, metrics)
            
            logger.debug("模型监控完成", 
                        model_id=model_id,
                        accuracy=float(metrics.accuracy),
                        latency_ms=float(metrics.prediction_latency_ms))
            
        except Exception as e:
            logger.error("模型监控错误", model_id=model_id, error=str(e))
            raise
    
    async def _collect_model_metrics(self, model_id: str) -> ModelPerformanceMetrics:
        """Collect current performance metrics for a model"""
        # In a real implementation, this would collect metrics from actual model inference
        # For now, we'll simulate realistic metrics
        
        current_time = datetime.now(timezone.utc)
        
        # Simulate realistic performance metrics with some variation
        base_accuracy = Decimal("0.87")  # Base accuracy
        
        # Add some realistic variation
        import random
        accuracy_variation = Decimal(str(random.uniform(-0.05, 0.05)))
        current_accuracy = max(Decimal("0.5"), base_accuracy + accuracy_variation)
        
        # Generate correlated metrics
        precision = current_accuracy * Decimal(str(random.uniform(0.9, 1.1)))
        recall = current_accuracy * Decimal(str(random.uniform(0.9, 1.1)))
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else Decimal("0")
        
        return ModelPerformanceMetrics(
            model_id=model_id,
            timestamp=current_time,
            accuracy=current_accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            auc_score=Decimal(str(random.uniform(0.8, 0.95))),
            prediction_latency_ms=Decimal(str(random.uniform(100, 800))),
            throughput_predictions_per_second=Decimal(str(random.uniform(50, 200))),
            data_drift_score=Decimal(str(random.uniform(0, 0.2))),
            concept_drift_score=Decimal(str(random.uniform(0, 0.1))),
            prediction_confidence_avg=Decimal(str(random.uniform(0.6, 0.9))),
            error_rate=Decimal(str(random.uniform(0.001, 0.05))),
            memory_usage_mb=Decimal(str(random.uniform(200, 800))),
            cpu_usage_percent=Decimal(str(random.uniform(20, 70)))
        )
    
    async def _update_model_status(self, model_id: str, metrics: ModelPerformanceMetrics):
        """Update model status based on current performance"""
        thresholds = self.config["alert_thresholds"]
        
        # Check critical conditions
        critical_conditions = [
            metrics.accuracy < Decimal("0.6"),
            metrics.error_rate > thresholds["error_rate_max"],
            metrics.prediction_latency_ms > thresholds["prediction_latency_max"],
            metrics.data_drift_score > thresholds["data_drift_threshold"],
            metrics.memory_usage_mb > thresholds["memory_usage_max"]
        ]
        
        if any(critical_conditions):
            self.model_status[model_id] = ModelStatus.CRITICAL
        
        # Check degraded conditions
        elif (metrics.accuracy < Decimal("0.8") or 
              metrics.error_rate > Decimal("0.01") or
              metrics.data_drift_score > Decimal("0.05")):
            self.model_status[model_id] = ModelStatus.DEGRADED
        
        else:
            self.model_status[model_id] = ModelStatus.HEALTHY
    
    async def _check_performance_alerts(self, model_id: str, metrics: ModelPerformanceMetrics):
        """Check for performance alert conditions"""
        thresholds = self.config["alert_thresholds"]
        
        # Accuracy alert
        if len(self.model_metrics[model_id]) > 1:
            previous_metrics = self.model_metrics[model_id][-2]
            accuracy_drop = previous_metrics.accuracy - metrics.accuracy
            
            if accuracy_drop > thresholds["accuracy_drop"]:
                await self._generate_alert(
                    model_id=model_id,
                    alert_level=AlertLevel.WARNING,
                    title="模型准确率下降",
                    message=f"模型准确率下降 {float(accuracy_drop):.2%}",
                    metric_name="accuracy",
                    current_value=metrics.accuracy,
                    threshold_value=previous_metrics.accuracy - thresholds["accuracy_drop"],
                    metadata={"previous_accuracy": float(previous_metrics.accuracy)}
                )
        
        # High latency alert
        if metrics.prediction_latency_ms > thresholds["prediction_latency_max"]:
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.WARNING,
                title="模型预测延迟过高",
                message=f"预测延迟 {float(metrics.prediction_latency_ms)}ms 超过阈值",
                metric_name="prediction_latency",
                current_value=metrics.prediction_latency_ms,
                threshold_value=thresholds["prediction_latency_max"]
            )
        
        # High error rate alert
        if metrics.error_rate > thresholds["error_rate_max"]:
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.CRITICAL,
                title="模型错误率过高",
                message=f"错误率 {float(metrics.error_rate):.2%} 超过阈值",
                metric_name="error_rate",
                current_value=metrics.error_rate,
                threshold_value=thresholds["error_rate_max"]
            )
        
        # High data drift alert
        if metrics.data_drift_score > thresholds["data_drift_threshold"]:
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.WARNING,
                title="数据漂移检测",
                message=f"数据漂移分数 {float(metrics.data_drift_score):.2%} 超过阈值",
                metric_name="data_drift_score",
                current_value=metrics.data_drift_score,
                threshold_value=thresholds["data_drift_threshold"]
            )
        
        # High resource usage alerts
        if metrics.memory_usage_mb > thresholds["memory_usage_max"]:
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.WARNING,
                title="内存使用率过高",
                message=f"内存使用 {float(metrics.memory_usage_mb):.0f}MB 超过阈值",
                metric_name="memory_usage",
                current_value=metrics.memory_usage_mb,
                threshold_value=thresholds["memory_usage_max"]
            )
        
        if metrics.cpu_usage_percent > thresholds["cpu_usage_max"]:
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.WARNING,
                title="CPU使用率过高",
                message=f"CPU使用率 {float(metrics.cpu_usage_percent):.1f}% 超过阈值",
                metric_name="cpu_usage",
                current_value=metrics.cpu_usage_percent,
                threshold_value=thresholds["cpu_usage_max"]
            )
    
    async def _generate_alert(self, model_id: str, alert_level: AlertLevel, title: str,
                            message: str, metric_name: str, current_value: Decimal,
                            threshold_value: Decimal, metadata: Dict[str, Any] = None):
        """Generate a performance alert"""
        alert = ModelAlert(
            alert_id=f"alert_{model_id}_{int(datetime.now().timestamp())}",
            model_id=model_id,
            alert_level=alert_level,
            title=title,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        # Store alert
        if model_id not in self.model_alerts:
            self.model_alerts[model_id] = []
        self.model_alerts[model_id].append(alert)
        self.total_alerts_generated += 1
        
        # Send alert through alert manager
        await self.alert_manager.send_alert(
            level=alert_level.value,
            title=title,
            message=message,
            metadata={
                "model_id": model_id,
                "metric_name": metric_name,
                "current_value": float(current_value),
                "threshold_value": float(threshold_value),
                **metadata
            }
        )
        
        logger.info("生成性能警报", 
                   model_id=model_id,
                   level=alert_level.value,
                   title=title,
                   metric=metric_name)
    
    async def _check_retraining_triggers(self):
        """Check for retraining trigger conditions"""
        for model_id in self.model_status.keys():
            if await self._should_trigger_retraining(model_id):
                await self._trigger_model_retraining(model_id)
    
    async def _should_trigger_retraining(self, model_id: str) -> bool:
        """Determine if retraining should be triggered for a model"""
        if model_id not in self.model_metrics or len(self.model_metrics[model_id]) < 3:
            return False
        
        triggers = self.config["retraining_triggers"]
        recent_metrics = self.model_metrics[model_id][-3:]  # Last 3 measurements
        
        # Check accuracy threshold
        avg_accuracy = sum(m.accuracy for m in recent_metrics) / len(recent_metrics)
        if avg_accuracy < triggers["accuracy_threshold"]:
            logger.info("触发重新训练：准确率低于阈值", 
                       model_id=model_id, 
                       avg_accuracy=float(avg_accuracy))
            return True
        
        # Check performance decline streak
        performance_decline_count = 0
        for i in range(1, len(recent_metrics)):
            if recent_metrics[i].accuracy < recent_metrics[i-1].accuracy:
                performance_decline_count += 1
        
        if performance_decline_count >= triggers["performance_decline_streak"]:
            logger.info("触发重新训练：连续性能下降", 
                       model_id=model_id, 
                       decline_count=performance_decline_count)
            return True
        
        # Check data drift
        latest_drift = recent_metrics[-1].data_drift_score
        if latest_drift > triggers["data_drift_threshold"]:
            logger.info("触发重新训练：数据漂移严重", 
                       model_id=model_id, 
                       drift_score=float(latest_drift))
            return True
        
        # Check days since last training
        if model_id in self.model_versions and self.model_versions[model_id]:
            last_training = max(v.creation_time for v in self.model_versions[model_id])
            days_since_training = (datetime.now(timezone.utc) - last_training).days
            
            if days_since_training >= triggers["days_since_last_training"]:
                logger.info("触发重新训练：定期重训练", 
                           model_id=model_id, 
                           days_since_training=days_since_training)
                return True
        
        return False
    
    async def _trigger_model_retraining(self, model_id: str):
        """Trigger model retraining process"""
        try:
            # Update model status
            self.model_status[model_id] = ModelStatus.RETRAINING
            
            # Log retraining trigger
            logger.info("开始模型重新训练", model_id=model_id)
            
            # In a real implementation, this would:
            # 1. Prepare training data
            # 2. Start retraining pipeline
            # 3. Monitor training progress
            # 4. Validate new model
            # 5. Deploy if performance improves
            
            # Simulate retraining process
            await asyncio.sleep(5)  # Simulate training time
            
            # Create new model version
            new_version = await self._create_model_version(model_id)
            
            # Restore model status based on new performance
            if new_version.performance_metrics.accuracy > Decimal("0.85"):
                self.model_status[model_id] = ModelStatus.HEALTHY
                logger.info("模型重新训练完成，性能良好", model_id=model_id)
            else:
                self.model_status[model_id] = ModelStatus.DEGRADED
                logger.warning("模型重新训练完成，性能仍需改进", model_id=model_id)
            
            self.total_retraining_triggers += 1
            
            # Generate retraining alert
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.INFO,
                title="模型重新训练完成",
                message=f"模型重新训练完成，新版本: {new_version.version_number}",
                metric_name="retraining",
                current_value=Decimal("1"),
                threshold_value=Decimal("0"),
                metadata={
                    "new_version": new_version.version_number,
                    "new_accuracy": float(new_version.performance_metrics.accuracy)
                }
            )
            
        except Exception as e:
            logger.error("模型重新训练失败", model_id=model_id, error=str(e))
            
            # Restore model status and generate error alert
            self.model_status[model_id] = ModelStatus.CRITICAL
            
            await self._generate_alert(
                model_id=model_id,
                alert_level=AlertLevel.EMERGENCY,
                title="模型重新训练失败",
                message=f"模型重新训练失败: {str(e)}",
                metric_name="retraining_error",
                current_value=Decimal("1"),
                threshold_value=Decimal("0"),
                metadata={"error": str(e)}
            )
    
    async def _create_model_version(self, model_id: str) -> ModelVersion:
        """Create a new model version"""
        # Generate version number
        if model_id not in self.model_versions:
            version_number = "v1.0"
        else:
            existing_versions = [v.version_number for v in self.model_versions[model_id]]
            # Simple version increment (in real implementation, would use semantic versioning)
            max_version = max(existing_versions) if existing_versions else "v0.0"
            version_parts = max_version.split(".")
            major = int(version_parts[0][1:]) if version_parts[0].startswith("v") else 0
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            version_number = f"v{major}.{minor + 1}"
        
        # Create new version with simulated metrics
        new_metrics = await self._collect_model_metrics(model_id)
        
        version = ModelVersion(
            version_id=f"{model_id}_{version_number}",
            model_id=model_id,
            version_number=version_number,
            creation_time=datetime.now(timezone.utc),
            performance_metrics=new_metrics,
            training_data_hash="abc123def456",  # Simulated hash
            model_file_path=f"/models/{model_id}/{version_number}.pkl",
            is_active=True,
            notes=f"Auto-generated version at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Store version and deactivate previous versions
        if model_id not in self.model_versions:
            self.model_versions[model_id] = []
        
        # Deactivate previous versions
        for v in self.model_versions[model_id]:
            v.is_active = False
        
        self.model_versions[model_id].append(version)
        
        return version
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config["history_retention_days"])
        
        # Clean old metrics
        for model_id in list(self.model_metrics.keys()):
            self.model_metrics[model_id] = [
                m for m in self.model_metrics[model_id] if m.timestamp > cutoff_time
            ]
            
            # Remove model entirely if no recent metrics
            if not self.model_metrics[model_id]:
                del self.model_metrics[model_id]
        
        # Clean old alerts (keep unacknowledged ones)
        for model_id in list(self.model_alerts.keys()):
            self.model_alerts[model_id] = [
                a for a in self.model_alerts[model_id] 
                if not a.acknowledged or a.timestamp > cutoff_time
            ]
            
            if not self.model_alerts[model_id]:
                del self.model_alerts[model_id]
        
        # Clean old versions (keep last 10 versions)
        for model_id in list(self.model_versions.keys()):
            self.model_versions[model_id].sort(key=lambda v: v.creation_time, reverse=True)
            if len(self.model_versions[model_id]) > 10:
                self.model_versions[model_id] = self.model_versions[model_id][:10]
        
        logger.debug("清理旧数据完成")
    
    # Public API methods
    
    async def register_model(self, model_id: str, model_type: str = "unknown"):
        """Register a model for monitoring"""
        self.model_status[model_id] = ModelStatus.HEALTHY
        logger.info("模型已注册监控", model_id=model_id, model_type=model_type)
    
    async def get_model_performance_summary(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for a model"""
        if model_id not in self.model_metrics or not self.model_metrics[model_id]:
            return None
        
        metrics = self.model_metrics[model_id]
        latest = metrics[-1]
        
        # Calculate trends (if we have enough data)
        trend_data = {}
        if len(metrics) > 1:
            recent_metrics = metrics[-5:]  # Last 5 measurements
            accuracy_trend = self._calculate_trend([m.accuracy for m in recent_metrics])
            latency_trend = self._calculate_trend([m.prediction_latency_ms for m in recent_metrics])
            
            trend_data = {
                "accuracy_trend": accuracy_trend,
                "latency_trend": latency_trend
            }
        
        return {
            "model_id": model_id,
            "status": self.model_status.get(model_id, ModelStatus.OFFLINE).value,
            "latest_metrics": {
                "accuracy": float(latest.accuracy),
                "precision": float(latest.precision),
                "recall": float(latest.recall),
                "f1_score": float(latest.f1_score),
                "auc_score": float(latest.auc_score),
                "prediction_latency_ms": float(latest.prediction_latency_ms),
                "throughput_predictions_per_second": float(latest.throughput_predictions_per_second),
                "data_drift_score": float(latest.data_drift_score),
                "concept_drift_score": float(latest.concept_drift_score),
                "prediction_confidence_avg": float(latest.prediction_confidence_avg),
                "error_rate": float(latest.error_rate),
                "memory_usage_mb": float(latest.memory_usage_mb),
                "cpu_usage_percent": float(latest.cpu_usage_percent)
            },
            "trends": trend_data,
            "last_updated": latest.timestamp.isoformat()
        }
    
    def _calculate_trend(self, values: List[Decimal]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        x = list(range(len(values)))
        y = [float(v) for v in values]
        
        # Calculate slope
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"
    
    async def get_model_alerts(self, model_id: str, 
                             alert_level: Optional[AlertLevel] = None,
                             acknowledged: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts for a model with optional filtering"""
        if model_id not in self.model_alerts:
            return []
        
        alerts = self.model_alerts[model_id]
        
        # Apply filters
        if alert_level:
            alerts = [a for a in alerts if a.alert_level == alert_level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "alert_id": alert.alert_id,
                "model_id": alert.model_id,
                "level": alert.alert_level.value,
                "title": alert.title,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "current_value": float(alert.current_value),
                "threshold_value": float(alert.threshold_value),
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "metadata": alert.metadata
            }
            for alert in alerts
        ]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for model_alerts in self.model_alerts.values():
            for alert in model_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info("警报已确认", alert_id=alert_id)
                    return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for model_alerts in self.model_alerts.values():
            for alert in model_alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.acknowledged = True
                    logger.info("警报已解决", alert_id=alert_id)
                    return True
        return False
    
    async def get_model_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """Get version history for a model"""
        if model_id not in self.model_versions:
            return []
        
        versions = sorted(self.model_versions[model_id], 
                         key=lambda v: v.creation_time, reverse=True)
        
        return [
            {
                "version_id": version.version_id,
                "model_id": version.model_id,
                "version_number": version.version_number,
                "creation_time": version.creation_time.isoformat(),
                "accuracy": float(version.performance_metrics.accuracy),
                "f1_score": float(version.performance_metrics.f1_score),
                "prediction_latency_ms": float(version.performance_metrics.prediction_latency_ms),
                "training_data_hash": version.training_data_hash,
                "model_file_path": version.model_file_path,
                "is_active": version.is_active,
                "notes": version.notes
            }
            for version in versions
        ]
    
    async def rollback_to_version(self, model_id: str, version_id: str) -> bool:
        """Rollback model to a previous version"""
        if model_id not in self.model_versions:
            return False
        
        # Find the target version
        target_version = None
        for version in self.model_versions[model_id]:
            if version.version_id == version_id:
                target_version = version
                break
        
        if not target_version:
            return False
        
        # Deactivate current active version
        for version in self.model_versions[model_id]:
            version.is_active = False
        
        # Activate target version
        target_version.is_active = True
        
        logger.info("模型版本回滚完成", 
                   model_id=model_id, 
                   target_version=target_version.version_number)
        
        return True
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring system statistics"""
        total_models = len(self.model_status)
        healthy_models = sum(1 for status in self.model_status.values() 
                           if status == ModelStatus.HEALTHY)
        degraded_models = sum(1 for status in self.model_status.values() 
                            if status == ModelStatus.DEGRADED)
        critical_models = sum(1 for status in self.model_status.values() 
                            if status == ModelStatus.CRITICAL)
        
        # Calculate average accuracy
        all_accuracies = []
        for metrics_list in self.model_metrics.values():
            if metrics_list:
                all_accuracies.append(float(metrics_list[-1].accuracy))
        
        avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0.0
        
        return {
            "monitoring_status": "active" if self.is_monitoring else "inactive",
            "total_models": total_models,
            "model_status_breakdown": {
                "healthy": healthy_models,
                "degraded": degraded_models,
                "critical": critical_models,
                "retraining": sum(1 for status in self.model_status.values() 
                                if status == ModelStatus.RETRAINING),
                "offline": sum(1 for status in self.model_status.values() 
                             if status == ModelStatus.OFFLINE)
            },
            "statistics": {
                "total_alerts_generated": self.total_alerts_generated,
                "total_retraining_triggers": self.total_retraining_triggers,
                "average_model_accuracy": avg_accuracy
            },
            "data_retention": {
                "history_retention_days": self.config["history_retention_days"],
                "models_with_metrics": len(self.model_metrics),
                "total_alerts": sum(len(alerts) for alerts in self.model_alerts.values()),
                "total_versions": sum(len(versions) for versions in self.model_versions.values())
            }
        }