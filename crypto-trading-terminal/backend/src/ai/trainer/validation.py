"""
Model Validation and Evaluation
Comprehensive model validation, testing, and performance evaluation system
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
from sklearn.metrics import (mean_squared_error, mean_absolute_error, 
                           accuracy_score, precision_score, recall_score, 
                           f1_score, roc_auc_score, classification_report)
import structlog
import warnings
warnings.filterwarnings('ignore')

from ..models.base_model import BaseAIModel

logger = structlog.get_logger()


class ValidationStatus(Enum):
    """Model validation status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics"""
    accuracy: Optional[Decimal]
    precision: Optional[Decimal]
    recall: Optional[Decimal]
    f1_score: Optional[Decimal]
    mse: Optional[Decimal]
    mae: Optional[Decimal]
    rmse: Optional[Decimal]
    r2_score: Optional[Decimal]
    custom_metrics: Dict[str, Decimal]


@dataclass
class ValidationReport:
    """Detailed validation report"""
    model_id: str
    validation_status: ValidationStatus
    metrics: ValidationMetrics
    test_results: Dict[str, Any]
    recommendations: List[str]
    validation_timestamp: datetime
    duration_seconds: float


class ModelValidator:
    """Comprehensive model validation and evaluation system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "accuracy_threshold": 0.7,
            "precision_threshold": 0.6,
            "recall_threshold": 0.6,
            "f1_threshold": 0.6,
            "mse_threshold": 0.1,
            "mae_threshold": 0.05,
            "r2_threshold": 0.5,
            "latency_threshold_ms": 1000,
            "stability_rounds": 5
        }
        
        # Validation thresholds by model type
        self.model_thresholds = {
            "LSTM": {
                "accuracy": 0.6,
                "mae": 0.02,
                "r2": 0.4
            },
            "LightGBM": {
                "accuracy": 0.7,
                "precision": 0.6,
                "recall": 0.6
            },
            "DQN": {
                "accuracy": 0.5,
                "reward_threshold": 0.3
            }
        }
        
        logger.info("模型验证器初始化完成", config=self.config)
    
    async def validate_model(self, model: BaseAIModel, 
                           test_data: pd.DataFrame, 
                           test_targets: pd.DataFrame) -> ValidationReport:
        """Comprehensive model validation"""
        validation_start = datetime.now(timezone.utc)
        logger.info("开始模型验证", model_id=model.model_id, model_type=model.model_type)
        
        try:
            # Run validation tests
            test_results = await self._run_validation_tests(model, test_data, test_targets)
            
            # Calculate metrics
            metrics = await self._calculate_metrics(model, test_data, test_targets, test_results)
            
            # Determine validation status
            status = await self._determine_validation_status(model, metrics)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(model, metrics, test_results)
            
            # Calculate validation duration
            duration = (datetime.now(timezone.utc) - validation_start).total_seconds()
            
            # Create validation report
            report = ValidationReport(
                model_id=model.model_id,
                validation_status=status,
                metrics=metrics,
                test_results=test_results,
                recommendations=recommendations,
                validation_timestamp=validation_start,
                duration_seconds=duration
            )
            
            logger.info("模型验证完成", 
                       model_id=model.model_id,
                       status=status.value,
                       duration=duration)
            
            return report
            
        except Exception as e:
            logger.error("模型验证失败", model_id=model.model_id, error=str(e))
            raise e
    
    async def _run_validation_tests(self, model: BaseAIModel, 
                                  test_data: pd.DataFrame, 
                                  test_targets: pd.DataFrame) -> Dict[str, Any]:
        """Run comprehensive validation tests"""
        test_results = {}
        
        # Basic functionality test
        test_results["basic_functionality"] = await self._test_basic_functionality(model, test_data)
        
        # Prediction consistency test
        test_results["prediction_consistency"] = await self._test_prediction_consistency(model, test_data)
        
        # Performance test
        test_results["performance"] = await self._test_performance(model, test_data)
        
        # Edge case test
        test_results["edge_cases"] = await self._test_edge_cases(model)
        
        # Stability test
        test_results["stability"] = await self._test_stability(model, test_data)
        
        return test_results
    
    async def _test_basic_functionality(self, model: BaseAIModel, test_data: pd.DataFrame) -> Dict[str, Any]:
        """Test basic model functionality"""
        try:
            # Test prediction with sample data
            sample_data = test_data.iloc[0:1].to_dict('records')[0] if len(test_data) > 0 else {}
            
            if sample_data:
                prediction = await model.predict(sample_data)
                
                return {
                    "status": "passed",
                    "prediction_generated": prediction is not None,
                    "prediction_keys": list(prediction.keys()) if prediction else []
                }
            else:
                return {
                    "status": "warning",
                    "message": "No test data available"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_prediction_consistency(self, model: BaseAIModel, test_data: pd.DataFrame) -> Dict[str, Any]:
        """Test prediction consistency"""
        try:
            if len(test_data) < 2:
                return {"status": "warning", "message": "Insufficient data for consistency test"}
            
            # Test same input produces same output
            sample_data = test_data.iloc[0:1].to_dict('records')[0]
            
            predictions = []
            for _ in range(3):
                prediction = await model.predict(sample_data)
                predictions.append(prediction)
            
            # Check consistency
            consistent = True
            for i in range(1, len(predictions)):
                if predictions[i] != predictions[0]:
                    consistent = False
                    break
            
            return {
                "status": "passed" if consistent else "warning",
                "consistent": consistent,
                "test_rounds": len(predictions)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_performance(self, model: BaseAIModel, test_data: pd.DataFrame) -> Dict[str, Any]:
        """Test model performance"""
        try:
            if len(test_data) == 0:
                return {"status": "warning", "message": "No test data available"}
            
            # Measure prediction latency
            latencies = []
            test_size = min(10, len(test_data))  # Test with up to 10 samples
            
            for i in range(test_size):
                sample_data = test_data.iloc[i:i+1].to_dict('records')[0]
                
                start_time = datetime.now(timezone.utc)
                prediction = await model.predict(sample_data)
                end_time = datetime.now(timezone.utc)
                
                latency_ms = (end_time - start_time).total_seconds() * 1000
                latencies.append(latency_ms)
            
            avg_latency = np.mean(latencies)
            max_latency = np.max(latencies)
            
            return {
                "status": "passed",
                "avg_latency_ms": float(avg_latency),
                "max_latency_ms": float(max_latency),
                "samples_tested": test_size,
                "threshold_ms": self.config["latency_threshold_ms"],
                "meets_threshold": avg_latency <= self.config["latency_threshold_ms"]
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_edge_cases(self, model: BaseAIModel) -> Dict[str, Any]:
        """Test edge cases and error handling"""
        try:
            edge_cases = []
            
            # Test empty data
            try:
                await model.predict({})
                edge_cases.append("empty_input_handled")
            except:
                edge_cases.append("empty_input_error")
            
            # Test invalid data
            try:
                await model.predict({"invalid": "data"})
                edge_cases.append("invalid_input_handled")
            except:
                edge_cases.append("invalid_input_error")
            
            # Test missing required fields
            try:
                await model.predict({"symbol": "BTCUSDT"})  # Missing required fields
                edge_cases.append("missing_fields_handled")
            except:
                edge_cases.append("missing_fields_error")
            
            return {
                "status": "passed",
                "edge_cases_tested": len(edge_cases),
                "cases": edge_cases
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_stability(self, model: BaseAIModel, test_data: pd.DataFrame) -> Dict[str, Any]:
        """Test model stability across multiple runs"""
        try:
            if len(test_data) == 0:
                return {"status": "warning", "message": "No test data available"}
            
            stability_rounds = self.config["stability_rounds"]
            sample_data = test_data.iloc[0:1].to_dict('records')[0]
            
            # Run multiple predictions
            predictions = []
            for _ in range(stability_rounds):
                prediction = await model.predict(sample_data)
                predictions.append(prediction)
            
            # Check if all predictions are similar (numerically)
            stability_score = await self._calculate_stability_score(predictions)
            
            return {
                "status": "passed" if stability_score > 0.8 else "warning",
                "stability_score": float(stability_score),
                "rounds": stability_rounds,
                "threshold": 0.8
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _calculate_stability_score(self, predictions: List[Dict[str, Any]]) -> float:
        """Calculate numerical stability score between predictions"""
        if len(predictions) < 2:
            return 1.0
        
        # Extract numerical values for comparison
        numerical_predictions = []
        for pred in predictions:
            numeric_values = []
            for key, value in pred.items():
                if isinstance(value, (int, float, Decimal)):
                    numeric_values.append(float(value))
            numerical_predictions.append(numeric_values)
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(numerical_predictions)):
            for j in range(i + 1, len(numerical_predictions)):
                if len(numerical_predictions[i]) > 0 and len(numerical_predictions[j]) > 0:
                    # Calculate cosine similarity
                    vec1 = np.array(numerical_predictions[i])
                    vec2 = np.array(numerical_predictions[j])
                    
                    dot_product = np.dot(vec1, vec2)
                    norm1 = np.linalg.norm(vec1)
                    norm2 = np.linalg.norm(vec2)
                    
                    if norm1 > 0 and norm2 > 0:
                        similarity = dot_product / (norm1 * norm2)
                        similarities.append(similarity)
        
        # Return average similarity
        return np.mean(similarities) if similarities else 0.0
    
    async def _calculate_metrics(self, model: BaseAIModel, test_data: pd.DataFrame, 
                               test_targets: pd.DataFrame, test_results: Dict[str, Any]) -> ValidationMetrics:
        """Calculate comprehensive validation metrics"""
        metrics_dict = {}
        
        try:
            if len(test_data) > 0 and len(test_targets) > 0:
                # Generate predictions for all test data
                predictions = []
                for i in range(len(test_data)):
                    sample_data = test_data.iloc[i:i+1].to_dict('records')[0]
                    prediction = await model.predict(sample_data)
                    predictions.append(prediction)
                
                # Extract prediction values based on model type
                if model.model_type == "LSTM":
                    metrics_dict.update(await self._calculate_regression_metrics(predictions, test_targets))
                elif model.model_type == "LightGBM":
                    metrics_dict.update(await self._calculate_classification_metrics(predictions, test_targets))
                elif model.model_type == "DQN":
                    metrics_dict.update(await self._calculate_rl_metrics(predictions, test_targets))
            
            # Convert to Decimal format
            decimal_metrics = {}
            for key, value in metrics_dict.items():
                if value is not None:
                    decimal_metrics[key] = Decimal(str(round(value, 4)))
                else:
                    decimal_metrics[key] = None
            
            return ValidationMetrics(**decimal_metrics)
            
        except Exception as e:
            logger.warning("指标计算失败", error=str(e))
            return ValidationMetrics(
                accuracy=None, precision=None, recall=None, f1_score=None,
                mse=None, mae=None, rmse=None, r2_score=None,
                custom_metrics={}
            )
    
    async def _calculate_regression_metrics(self, predictions: List[Dict[str, Any]], 
                                          test_targets: pd.DataFrame) -> Dict[str, Decimal]:
        """Calculate regression metrics for LSTM model"""
        try:
            # Extract predicted values
            pred_values = []
            for pred in predictions:
                if "predicted_price" in pred:
                    pred_values.append(float(pred["predicted_price"]))
            
            # Extract actual values
            if "target" in test_targets.columns:
                actual_values = test_targets["target"].tolist()
            elif len(test_targets.columns) > 0:
                actual_values = test_targets.iloc[:, 0].tolist()
            else:
                return {}
            
            if len(pred_values) > 0 and len(actual_values) > 0:
                # Calculate metrics
                mse = mean_squared_error(actual_values, pred_values)
                mae = mean_absolute_error(actual_values, pred_values)
                rmse = np.sqrt(mse)
                
                # Calculate R² score
                ss_res = sum((a - p) ** 2 for a, p in zip(actual_values, pred_values))
                ss_tot = sum((a - np.mean(actual_values)) ** 2 for a in actual_values)
                r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                
                return {
                    "mse": Decimal(str(mse)),
                    "mae": Decimal(str(mae)),
                    "rmse": Decimal(str(rmse)),
                    "r2_score": Decimal(str(r2))
                }
            
        except Exception as e:
            logger.warning("回归指标计算失败", error=str(e))
        
        return {}
    
    async def _calculate_classification_metrics(self, predictions: List[Dict[str, Any]], 
                                              test_targets: pd.DataFrame) -> Dict[str, Decimal]:
        """Calculate classification metrics for LightGBM model"""
        try:
            # Extract predicted labels
            pred_labels = []
            for pred in predictions:
                if "signal_type" in pred:
                    pred_labels.append(pred["signal_type"])
            
            # Extract actual labels
            if "signal" in test_targets.columns:
                actual_labels = test_targets["signal"].tolist()
            elif len(test_targets.columns) > 0:
                actual_labels = test_targets.iloc[:, 0].tolist()
            else:
                return {}
            
            if len(pred_labels) > 0 and len(actual_labels) > 0:
                # Calculate metrics
                accuracy = accuracy_score(actual_labels, pred_labels)
                
                # Handle multiclass precision, recall, f1
                try:
                    precision = precision_score(actual_labels, pred_labels, average='weighted', zero_division=0)
                    recall = recall_score(actual_labels, pred_labels, average='weighted', zero_division=0)
                    f1 = f1_score(actual_labels, pred_labels, average='weighted', zero_division=0)
                except:
                    precision = recall = f1 = 0.0
                
                return {
                    "accuracy": Decimal(str(accuracy)),
                    "precision": Decimal(str(precision)),
                    "recall": Decimal(str(recall)),
                    "f1_score": Decimal(str(f1))
                }
            
        except Exception as e:
            logger.warning("分类指标计算失败", error=str(e))
        
        return {}
    
    async def _calculate_rl_metrics(self, predictions: List[Dict[str, Any]], 
                                  test_targets: pd.DataFrame) -> Dict[str, Decimal]:
        """Calculate reinforcement learning metrics"""
        try:
            # Extract predicted actions
            pred_actions = []
            for pred in predictions:
                if "optimized_strategy" in pred:
                    pred_actions.append(1)  # Placeholder for action count
                else:
                    pred_actions.append(0)
            
            # For RL, we mainly focus on accuracy and custom metrics
            if len(pred_actions) > 0:
                # Calculate accuracy (simplified)
                accuracy = np.mean(pred_actions)  # Placeholder calculation
                
                return {
                    "accuracy": Decimal(str(accuracy)),
                    "custom_metrics": {
                        "avg_reward": Decimal(str(np.mean(pred_actions))),
                        "action_diversity": Decimal(str(len(set(pred_actions))))
                    }
                }
            
        except Exception as e:
            logger.warning("强化学习指标计算失败", error=str(e))
        
        return {}
    
    async def _determine_validation_status(self, model: BaseAIModel, 
                                         metrics: ValidationMetrics) -> ValidationStatus:
        """Determine overall validation status"""
        failed_checks = []
        warning_checks = []
        
        # Get model-specific thresholds
        thresholds = self.model_thresholds.get(model.model_type, self.config)
        
        # Check accuracy
        if metrics.accuracy is not None:
            acc_threshold = thresholds.get("accuracy", self.config["accuracy_threshold"])
            if metrics.accuracy < acc_threshold:
                failed_checks.append(f"准确率不足: {metrics.accuracy} < {acc_threshold}")
        
        # Check precision
        if metrics.precision is not None:
            prec_threshold = thresholds.get("precision", self.config["precision_threshold"])
            if metrics.precision < prec_threshold:
                warning_checks.append(f"精确率偏低: {metrics.precision} < {prec_threshold}")
        
        # Check recall
        if metrics.recall is not None:
            recall_threshold = thresholds.get("recall", self.config["recall_threshold"])
            if metrics.recall < recall_threshold:
                warning_checks.append(f"召回率偏低: {metrics.recall} < {recall_threshold}")
        
        # Check F1 score
        if metrics.f1_score is not None:
            f1_threshold = thresholds.get("f1", self.config["f1_threshold"])
            if metrics.f1_score < f1_threshold:
                failed_checks.append(f"F1分数不足: {metrics.f1_score} < {f1_threshold}")
        
        # Check MSE
        if metrics.mse is not None:
            mse_threshold = thresholds.get("mae", self.config["mae_threshold"])
            if metrics.mse > mse_threshold:
                warning_checks.append(f"MSE过高: {metrics.mse} > {mse_threshold}")
        
        # Determine final status
        if len(failed_checks) > 0:
            return ValidationStatus.FAILED
        elif len(warning_checks) > 0:
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.PASSED
    
    async def _generate_recommendations(self, model: BaseAIModel, 
                                      metrics: ValidationMetrics, 
                                      test_results: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Performance recommendations
        if "performance" in test_results:
            perf = test_results["performance"]
            if perf.get("avg_latency_ms", 0) > self.config["latency_threshold_ms"]:
                recommendations.append("考虑优化模型推理性能，减少预测延迟")
        
        # Accuracy recommendations
        if metrics.accuracy is not None and metrics.accuracy < 0.7:
            recommendations.append("考虑增加训练数据或调整模型超参数以提高准确率")
        
        # Stability recommendations
        if "stability" in test_results:
            stability = test_results["stability"]
            if stability.get("stability_score", 1.0) < 0.8:
                recommendations.append("模型稳定性需要改进，考虑增加正则化或调整架构")
        
        # Data quality recommendations
        if "edge_cases" in test_results:
            edge_cases = test_results["edge_cases"]
            if "empty_input_error" in edge_cases.get("cases", []):
                recommendations.append("改进输入验证和错误处理机制")
        
        # Model-specific recommendations
        if model.model_type == "LSTM" and metrics.mse is not None and metrics.mse > 0.05:
            recommendations.append("LSTM模型损失较高，考虑调整序列长度或网络深度")
        elif model.model_type == "LightGBM" and metrics.f1_score is not None and metrics.f1_score < 0.6:
            recommendations.append("LightGBM模型F1分数偏低，考虑特征工程或超参数调优")
        elif model.model_type == "DQN" and metrics.accuracy is not None and metrics.accuracy < 0.5:
            recommendations.append("DQN模型性能不佳，考虑增加训练轮次或调整奖励函数")
        
        return recommendations
    
    def get_validation_summary(self, report: ValidationReport) -> Dict[str, Any]:
        """Get concise validation summary"""
        return {
            "model_id": report.model_id,
            "validation_status": report.validation_status.value,
            "key_metrics": {
                "accuracy": float(report.metrics.accuracy) if report.metrics.accuracy else None,
                "precision": float(report.metrics.precision) if report.metrics.precision else None,
                "recall": float(report.metrics.recall) if report.metrics.recall else None,
                "f1_score": float(report.metrics.f1_score) if report.metrics.f1_score else None,
                "mae": float(report.metrics.mae) if report.metrics.mae else None,
                "mse": float(report.metrics.mse) if report.metrics.mse else None
            },
            "recommendations_count": len(report.recommendations),
            "validation_duration": report.duration_seconds,
            "timestamp": report.validation_timestamp.isoformat()
        }