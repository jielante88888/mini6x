"""
Metrics Calculator
Utility functions for calculating various performance metrics
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import structlog
import numpy as np
from datetime import datetime, timezone

logger = structlog.get_logger()


class MetricsCalculator:
    """Calculate various AI model performance metrics"""
    
    def __init__(self):
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def calculate_classification_metrics(self, 
                                             predictions: List[int], 
                                             actuals: List[int]) -> Dict[str, Decimal]:
        """Calculate classification performance metrics"""
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have the same length")
        
        if not predictions:
            return {}
        
        # Convert to numpy arrays for calculation
        pred_array = np.array(predictions)
        actual_array = np.array(actuals)
        
        # Calculate confusion matrix components
        tp = np.sum((pred_array == 1) & (actual_array == 1))  # True Positives
        tn = np.sum((pred_array == 0) & (actual_array == 0))  # True Negatives
        fp = np.sum((pred_array == 1) & (actual_array == 0))  # False Positives
        fn = np.sum((pred_array == 0) & (actual_array == 1))  # False Negatives
        
        total = len(predictions)
        
        # Calculate metrics
        accuracy = Decimal((tp + tn) / total) if total > 0 else Decimal("0")
        precision = Decimal(tp / (tp + fp)) if (tp + fp) > 0 else Decimal("0")
        recall = Decimal(tp / (tp + fn)) if (tp + fn) > 0 else Decimal("0")
        
        # F1 Score
        f1_score = Decimal(2 * (precision * recall) / (precision + recall)) if (precision + recall) > 0 else Decimal("0")
        
        # Specificity (True Negative Rate)
        specificity = Decimal(tn / (tn + fp)) if (tn + fp) > 0 else Decimal("0")
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "specificity": specificity,
            "true_positives": Decimal(tp),
            "true_negatives": Decimal(tn),
            "false_positives": Decimal(fp),
            "false_negatives": Decimal(fn),
            "total_predictions": Decimal(total)
        }
    
    async def calculate_regression_metrics(self, 
                                         predictions: List[float], 
                                         actuals: List[float]) -> Dict[str, Decimal]:
        """Calculate regression performance metrics"""
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have the same length")
        
        if not predictions:
            return {}
        
        pred_array = np.array(predictions)
        actual_array = np.array(actuals)
        
        # Mean Absolute Error (MAE)
        mae = Decimal(np.mean(np.abs(pred_array - actual_array)))
        
        # Mean Squared Error (MSE)
        mse = Decimal(np.mean((pred_array - actual_array) ** 2))
        
        # Root Mean Squared Error (RMSE)
        rmse = Decimal(np.sqrt(float(mse)))
        
        # Mean Absolute Percentage Error (MAPE)
        mape = Decimal(np.mean(np.abs((actual_array - pred_array) / actual_array)) * 100)
        
        # R-squared (Coefficient of Determination)
        ss_res = np.sum((actual_array - pred_array) ** 2)
        ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
        r2 = Decimal(1 - (ss_res / ss_tot)) if ss_tot != 0 else Decimal("0")
        
        # Explained Variance Score
        explained_variance = Decimal(1 - (np.var(actual_array - pred_array) / np.var(actual_array)))
        
        return {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "mape": mape,
            "r2_score": r2,
            "explained_variance": explained_variance
        }
    
    async def calculate_prediction_confidence_metrics(self, 
                                                    confidence_scores: List[float]) -> Dict[str, Decimal]:
        """Calculate metrics related to prediction confidence"""
        if not confidence_scores:
            return {}
        
        conf_array = np.array(confidence_scores)
        
        return {
            "average_confidence": Decimal(np.mean(conf_array)),
            "min_confidence": Decimal(np.min(conf_array)),
            "max_confidence": Decimal(np.max(conf_array)),
            "std_confidence": Decimal(np.std(conf_array)),
            "median_confidence": Decimal(np.median(conf_array)),
            "low_confidence_count": Decimal(np.sum(conf_array < 0.5)),
            "high_confidence_count": Decimal(np.sum(conf_array > 0.8))
        }
    
    async def calculate_data_drift_score(self, 
                                       current_data: List[float], 
                                       reference_data: List[float]) -> Decimal:
        """Calculate data drift score using statistical tests"""
        if len(current_data) < 10 or len(reference_data) < 10:
            return Decimal("0.0")
        
        current_array = np.array(current_data)
        reference_array = np.array(reference_data)
        
        # Kolmogorov-Smirnov test for distribution drift
        try:
            from scipy import stats
            ks_statistic, p_value = stats.ks_2samp(current_array, reference_array)
            
            # Drift score based on KS statistic (higher = more drift)
            drift_score = Decimal(ks_statistic)
            
            return min(drift_score, Decimal("1.0"))  # Cap at 1.0
            
        except ImportError:
            # Fallback: Simple statistical comparison
            current_mean = np.mean(current_array)
            reference_mean = np.mean(reference_array)
            
            current_std = np.std(current_array)
            reference_std = np.std(reference_array)
            
            # Combined drift score
            mean_drift = abs(current_mean - reference_mean) / (reference_std + 1e-8)
            std_drift = abs(current_std - reference_std) / (reference_std + 1e-8)
            
            drift_score = Decimal((mean_drift + std_drift) / 2)
            
            return min(drift_score, Decimal("1.0"))
    
    async def calculate_concept_drift_score(self, 
                                          recent_predictions: List[int], 
                                          recent_actuals: List[int],
                                          historical_predictions: List[int], 
                                          historical_actuals: List[int]) -> Decimal:
        """Calculate concept drift score by comparing recent vs historical performance"""
        if not recent_predictions or not historical_predictions:
            return Decimal("0.0")
        
        # Calculate recent accuracy
        recent_metrics = await self.calculate_classification_metrics(recent_predictions, recent_actuals)
        recent_accuracy = recent_metrics.get("accuracy", Decimal("0"))
        
        # Calculate historical accuracy
        historical_metrics = await self.calculate_classification_metrics(historical_predictions, historical_actuals)
        historical_accuracy = historical_metrics.get("accuracy", Decimal("0"))
        
        # Concept drift score based on accuracy difference
        accuracy_diff = abs(recent_accuracy - historical_accuracy)
        
        # Also consider precision/recall changes
        recent_precision = recent_metrics.get("precision", Decimal("0"))
        historical_precision = historical_metrics.get("precision", Decimal("0"))
        precision_diff = abs(recent_precision - historical_precision)
        
        recent_recall = recent_metrics.get("recall", Decimal("0"))
        historical_recall = historical_metrics.get("recall", Decimal("0"))
        recall_diff = abs(recent_recall - historical_recall)
        
        # Combined concept drift score
        concept_drift = (accuracy_diff + precision_diff + recall_diff) / 3
        
        return min(concept_drift, Decimal("1.0"))
    
    async def calculate_performance_trend(self, 
                                        performance_history: List[Dict[str, Any]], 
                                        metric_name: str) -> Dict[str, Any]:
        """Calculate performance trend over time"""
        if len(performance_history) < 2:
            return {"trend": "stable", "slope": Decimal("0"), "confidence": Decimal("0")}
        
        # Extract metric values
        values = [Decimal(str(item.get(metric_name, 0))) for item in performance_history]
        timestamps = [item.get("timestamp", datetime.now(timezone.utc)) for item in performance_history]
        
        # Calculate linear trend
        x = list(range(len(values)))
        y = [float(v) for v in values]
        
        # Simple linear regression
        n = len(values)
        if n < 2:
            return {"trend": "stable", "slope": Decimal("0"), "confidence": Decimal("0")}
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            slope = Decimal("0")
        else:
            slope = Decimal((n * sum_xy - sum_x * sum_y) / denominator)
        
        # Determine trend direction
        if float(slope) > 0.01:
            trend = "improving"
        elif float(slope) < -0.01:
            trend = "declining"
        else:
            trend = "stable"
        
        # Calculate trend confidence (how consistent the trend is)
        if n > 2:
            # Calculate R-squared for trend confidence
            y_mean = sum_y / n
            ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
            ss_res = sum((y[i] - (float(slope) * x[i] + y_mean - float(slope) * sum_x / n)) ** 2 for i in range(n))
            
            r_squared = Decimal(1 - (ss_res / ss_tot)) if ss_tot > 0 else Decimal("0")
            confidence = max(Decimal("0"), min(Decimal("1"), r_squared))
        else:
            confidence = Decimal("0.5")
        
        return {
            "trend": trend,
            "slope": slope,
            "confidence": confidence,
            "data_points": n,
            "latest_value": values[-1] if values else Decimal("0"),
            "first_value": values[0] if values else Decimal("0"),
            "total_change": values[-1] - values[0] if len(values) > 1 else Decimal("0")
        }
    
    async def aggregate_performance_metrics(self, 
                                          metrics_history: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Aggregate performance metrics over time"""
        if not metrics_history:
            return {}
        
        # Calculate averages
        avg_accuracy = Decimal("0")
        avg_precision = Decimal("0")
        avg_recall = Decimal("0")
        avg_f1 = Decimal("0")
        avg_latency = Decimal("0")
        avg_error_rate = Decimal("0")
        
        if metrics_history:
            count = len(metrics_history)
            
            # Sum all metrics
            for metrics in metrics_history:
                avg_accuracy += metrics.get("accuracy", Decimal("0"))
                avg_precision += metrics.get("precision", Decimal("0"))
                avg_recall += metrics.get("recall", Decimal("0"))
                avg_f1 += metrics.get("f1_score", Decimal("0"))
                avg_latency += metrics.get("prediction_latency_ms", Decimal("0"))
                avg_error_rate += metrics.get("error_rate", Decimal("0"))
            
            # Calculate averages
            avg_accuracy /= count
            avg_precision /= count
            avg_recall /= count
            avg_f1 /= count
            avg_latency /= count
            avg_error_rate /= count
        
        return {
            "avg_accuracy": avg_accuracy,
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1_score": avg_f1,
            "avg_prediction_latency_ms": avg_latency,
            "avg_error_rate": avg_error_rate
        }
    
    async def detect_performance_anomalies(self, 
                                         recent_metrics: List[Dict[str, Any]], 
                                         baseline_metrics: Dict[str, Decimal]) -> List[Dict[str, Any]]:
        """Detect performance anomalies compared to baseline"""
        anomalies = []
        
        if not recent_metrics:
            return anomalies
        
        # Use the most recent metric for anomaly detection
        current = recent_metrics[-1]
        
        # Define threshold percentages for anomaly detection
        thresholds = {
            "accuracy": Decimal("0.05"),      # 5% drop
            "precision": Decimal("0.05"),     # 5% drop
            "recall": Decimal("0.05"),        # 5% drop
            "f1_score": Decimal("0.05"),      # 5% drop
            "prediction_latency_ms": Decimal("0.50"),  # 50% increase
            "error_rate": Decimal("0.50")     # 50% increase
        }
        
        # Check each metric for anomalies
        for metric_name, current_value in current.items():
            if metric_name in thresholds and metric_name in baseline_metrics:
                baseline_value = baseline_metrics[metric_name]
                
                if baseline_value > 0:
                    if metric_name in ["accuracy", "precision", "recall", "f1_score"]:
                        # For performance metrics, check for drops
                        if current_value < baseline_value * (1 - thresholds[metric_name]):
                            drop_percent = (baseline_value - current_value) / baseline_value
                            anomalies.append({
                                "metric": metric_name,
                                "type": "performance_degradation",
                                "current_value": float(current_value),
                                "baseline_value": float(baseline_value),
                                "drop_percent": float(drop_percent),
                                "severity": "high" if drop_percent > 0.1 else "medium"
                            })
                    
                    elif metric_name in ["prediction_latency_ms", "error_rate"]:
                        # For cost metrics, check for increases
                        if current_value > baseline_value * (1 + thresholds[metric_name]):
                            increase_percent = (current_value - baseline_value) / baseline_value
                            anomalies.append({
                                "metric": metric_name,
                                "type": "cost_increase",
                                "current_value": float(current_value),
                                "baseline_value": float(baseline_value),
                                "increase_percent": float(increase_percent),
                                "severity": "high" if increase_percent > 0.5 else "medium"
                            })
        
        return anomalies
    
    async def calculate_model_health_score(self, 
                                         metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall model health score"""
        # Extract key metrics
        accuracy = metrics.get("accuracy", Decimal("0"))
        latency = metrics.get("prediction_latency_ms", Decimal("1000"))
        error_rate = metrics.get("error_rate", Decimal("1"))
        drift_score = metrics.get("data_drift_score", Decimal("0"))
        
        # Normalize and weight metrics
        # Accuracy score (0-1, higher is better)
        accuracy_score = min(accuracy, Decimal("1"))
        
        # Latency score (0-1, lower latency is better)
        latency_score = max(Decimal("0"), Decimal("1") - (latency / Decimal("2000")))  # 2000ms = poor
        
        # Error rate score (0-1, lower error rate is better)
        error_score = max(Decimal("0"), Decimal("1") - error_rate)
        
        # Drift score (0-1, lower drift is better)
        drift_score = max(Decimal("0"), Decimal("1") - drift_score)
        
        # Weighted overall health score
        weights = {
            "accuracy": Decimal("0.4"),
            "latency": Decimal("0.2"),
            "error_rate": Decimal("0.2"),
            "drift": Decimal("0.2")
        }
        
        health_score = (
            accuracy_score * weights["accuracy"] +
            latency_score * weights["latency"] +
            error_score * weights["error_rate"] +
            drift_score * weights["drift"]
        )
        
        # Determine health category
        if health_score >= Decimal("0.8"):
            health_category = "excellent"
        elif health_score >= Decimal("0.6"):
            health_category = "good"
        elif health_score >= Decimal("0.4"):
            health_category = "fair"
        else:
            health_category = "poor"
        
        return {
            "overall_health_score": float(health_score),
            "health_category": health_category,
            "component_scores": {
                "accuracy_score": float(accuracy_score),
                "latency_score": float(latency_score),
                "error_score": float(error_score),
                "drift_score": float(drift_score)
            },
            "recommendations": await self._generate_health_recommendations(
                health_score, accuracy, latency, error_rate, drift_score
            )
        }
    
    async def _generate_health_recommendations(self, 
                                             health_score: Decimal,
                                             accuracy: Decimal,
                                             latency: Decimal,
                                             error_rate: Decimal,
                                             drift_score: Decimal) -> List[str]:
        """Generate recommendations based on model health"""
        recommendations = []
        
        if health_score < Decimal("0.6"):
            recommendations.append("模型整体健康状况较差，建议立即检查和优化")
        
        if accuracy < Decimal("0.8"):
            recommendations.append("模型准确率偏低，建议重新训练或调整特征")
        
        if latency > Decimal("1000"):
            recommendations.append("预测延迟过高，建议优化模型架构或硬件配置")
        
        if error_rate > Decimal("0.05"):
            recommendations.append("错误率较高，建议检查数据质量和模型参数")
        
        if drift_score > Decimal("0.1"):
            recommendations.append("检测到数据漂移，建议更新训练数据")
        
        if not recommendations:
            recommendations.append("模型运行状况良好，继续保持当前配置")
        
        return recommendations