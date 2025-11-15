"""
Model Trainer
Centralized training coordinator for all AI models
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from enum import Enum
import structlog

from ..models.base_model import BaseAIModel, ModelStatus
from ..models.price_predictor import PricePredictor
from ..models.signal_scorer import SignalScorer
from ..models.strategy_optimizer import StrategyOptimizer
from .data_processor import DataProcessor, ProcessedDataset
from .validation import ModelValidator, ValidationReport, ValidationStatus

logger = structlog.get_logger()


class TrainingMode(Enum):
    """Training mode options"""
    FULL = "full"           # Full training from scratch
    INCREMENTAL = "incremental"  # Incremental training
    FINE_TUNE = "fine_tune" # Fine-tune existing model
    CONTINUE = "continue"   # Continue interrupted training


@dataclass
class TrainingConfig:
    """Training configuration"""
    mode: TrainingMode
    epochs: int
    batch_size: int
    learning_rate: float
    validation_split: float
    early_stopping_patience: int
    model_specific_params: Dict[str, Any]
    save_checkpoints: bool
    checkpoint_frequency: int


@dataclass
class TrainingResult:
    """Training result information"""
    training_id: str
    model_id: str
    model_type: str
    success: bool
    final_metrics: Dict[str, Decimal]
    training_duration: float
    epochs_completed: int
    validation_report: Optional[ValidationReport]
    checkpoints_saved: List[str]
    final_model_path: Optional[str]
    training_logs: List[str]
    error_message: Optional[str]


class ModelTrainer:
    """Centralized AI model training coordinator"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_concurrent_training": 2,
            "default_training_timeout_hours": 4,
            "checkpoint_dir": "./checkpoints",
            "model_output_dir": "./models",
            "default_validation_split": 0.2,
            "enable_early_stopping": True,
            "save_best_only": True
        }
        
        # Initialize components
        self.data_processor = DataProcessor()
        self.validator = ModelValidator()
        
        # Model registry
        self.models: Dict[str, BaseAIModel] = {}
        self.model_classes = {
            "LSTM": PricePredictor,
            "LightGBM": SignalScorer,
            "DQN": StrategyOptimizer
        }
        
        # Active training jobs
        self.active_training: Dict[str, TrainingResult] = {}
        
        # Model performance tracking
        self.training_history: Dict[str, List[TrainingResult]] = {}
        
        logger.info("模型训练器初始化完成", config=self.config)
    
    async def train_model(self, model_id: str, training_data: List[Dict[str, Any]],
                         training_config: Optional[Dict[str, Any]] = None) -> TrainingResult:
        """Train a model with provided data and configuration"""
        training_id = str(uuid.uuid4())
        logger.info("开始模型训练", 
                   training_id=training_id,
                   model_id=model_id,
                   data_size=len(training_data))
        
        try:
            # Determine model type
            model_type = self._determine_model_type(model_id, training_config)
            
            # Create training configuration
            config = self._create_training_config(model_type, training_config)
            
            # Initialize training result
            result = TrainingResult(
                training_id=training_id,
                model_id=model_id,
                model_type=model_type,
                success=False,
                final_metrics={},
                training_duration=0.0,
                epochs_completed=0,
                validation_report=None,
                checkpoints_saved=[],
                final_model_path=None,
                training_logs=[],
                error_message=None
            )
            
            self.active_training[training_id] = result
            
            # Log start
            result.training_logs.append(f"训练开始: {datetime.now(timezone.utc).isoformat()}")
            result.training_logs.append(f"模型类型: {model_type}")
            result.training_logs.append(f"训练模式: {config.mode.value}")
            result.training_logs.append(f"训练样本数: {len(training_data)}")
            
            # Process training data
            logger.info("处理训练数据", training_id=training_id)
            processed_dataset = await self.data_processor.process_training_data(
                training_data, model_type
            )
            
            result.training_logs.append(f"数据处理完成: {processed_dataset.metadata['processed_size']} 样本")
            
            # Split dataset
            dataset_splits = await self.data_processor.split_dataset(processed_dataset)
            
            train_data = dataset_splits["train"]
            validation_data = dataset_splits["validation"]
            test_data = dataset_splits["test"]
            
            result.training_logs.append(
                f"数据分割: 训练 {len(train_data.features)}, "
                f"验证 {len(validation_data.features)}, "
                f"测试 {len(test_data.features)}"
            )
            
            # Get or create model
            model = await self._get_or_create_model(model_id, model_type, config)
            
            # Start training
            training_start = datetime.now(timezone.utc)
            
            # Convert data format for training
            if model_type == "LSTM":
                training_list = training_data  # LSTM uses original format
            else:
                # Convert to DataFrame for other models
                import pandas as pd
                training_df = pd.DataFrame(training_data)
                validation_df = pd.DataFrame(validation_data.features.to_dict('records'))
                training_list = training_df.to_dict('records')
                validation_list = validation_df.to_dict('records')
            
            # Train model
            logger.info("执行模型训练", training_id=training_id)
            final_metrics = await model.train(training_list, validation_list)
            
            result.final_metrics = final_metrics
            result.epochs_completed = final_metrics.get("epochs_trained", config.epochs)
            
            training_end = datetime.now(timezone.utc)
            result.training_duration = (training_end - training_start).total_seconds()
            
            result.training_logs.append(f"训练完成: 耗时 {result.training_duration:.2f} 秒")
            result.training_logs.append(f"最终指标: {final_metrics}")
            
            # Run validation if test data available
            if len(test_data.features) > 0:
                logger.info("运行模型验证", training_id=training_id)
                validation_report = await self.validator.validate_model(
                    model, test_data.features, test_data.targets
                )
                result.validation_report = validation_report
                
                if validation_report.validation_status == ValidationStatus.PASSED:
                    result.training_logs.append("模型验证通过")
                elif validation_report.validation_status == ValidationStatus.WARNING:
                    result.training_logs.append("模型验证警告")
                else:
                    result.training_logs.append("模型验证失败")
            
            # Save model
            model_path = await self._save_model(model, model_id)
            result.final_model_path = model_path
            
            # Update model registry
            self.models[model_id] = model
            
            # Store training result
            if model_id not in self.training_history:
                self.training_history[model_id] = []
            self.training_history[model_id].append(result)
            
            result.success = True
            result.training_logs.append("模型训练成功完成")
            
            logger.info("模型训练完成", 
                       training_id=training_id,
                       model_id=model_id,
                       success=True,
                       duration=result.training_duration)
            
            return result
            
        except Exception as e:
            logger.error("模型训练失败", 
                        training_id=training_id,
                        model_id=model_id,
                        error=str(e))
            
            if training_id in self.active_training:
                self.active_training[training_id].success = False
                self.active_training[training_id].error_message = str(e)
                self.active_training[training_id].training_logs.append(f"训练失败: {str(e)}")
            
            raise e
        
        finally:
            # Clean up active training
            if training_id in self.active_training:
                del self.active_training[training_id]
    
    async def retrain_model(self, model_id: str, new_data: List[Dict[str, Any]],
                          retrain_config: Optional[Dict[str, Any]] = None) -> TrainingResult:
        """Retrain an existing model with new data"""
        logger.info("开始模型重训练", model_id=model_id, data_size=len(new_data))
        
        # Use incremental training mode
        if retrain_config is None:
            retrain_config = {}
        retrain_config["mode"] = TrainingMode.INCREMENTAL
        
        return await self.train_model(model_id, new_data, retrain_config)
    
    async def fine_tune_model(self, model_id: str, fine_tune_data: List[Dict[str, Any]],
                            fine_tune_config: Optional[Dict[str, Any]] = None) -> TrainingResult:
        """Fine-tune an existing model"""
        logger.info("开始模型微调", model_id=model_id, data_size=len(fine_tune_data))
        
        # Use fine-tune mode
        if fine_tune_config is None:
            fine_tune_config = {}
        fine_tune_config["mode"] = TrainingMode.FINE_TUNE
        
        return await self.train_model(model_id, fine_tune_data, fine_tune_config)
    
    async def evaluate_model(self, model_id: str, test_data: List[Dict[str, Any]]) -> ValidationReport:
        """Evaluate a trained model"""
        if model_id not in self.models:
            raise ValueError(f"模型未找到: {model_id}")
        
        model = self.models[model_id]
        
        # Convert test data to DataFrame
        import pandas as pd
        test_df = pd.DataFrame(test_data)
        
        # Extract features and targets (simplified)
        features = test_df.drop(columns=["timestamp", "symbol"]) if "timestamp" in test_df.columns else test_df
        targets = pd.DataFrame({"target": [0] * len(features)})  # Placeholder targets
        
        return await self.validator.validate_model(model, features, targets)
    
    def _determine_model_type(self, model_id: str, training_config: Optional[Dict[str, Any]]) -> str:
        """Determine model type from ID or configuration"""
        if training_config and "model_type" in training_config:
            return training_config["model_type"]
        
        # Try to infer from model ID
        model_id_lower = model_id.lower()
        if "lstm" in model_id_lower or "price" in model_id_lower:
            return "LSTM"
        elif "lightgbm" in model_id_lower or "signal" in model_id_lower:
            return "LightGBM"
        elif "dqn" in model_id_lower or "optimizer" in model_id_lower:
            return "DQN"
        
        # Default to LSTM
        return "LSTM"
    
    def _create_training_config(self, model_type: str, 
                              config_override: Optional[Dict[str, Any]] = None) -> TrainingConfig:
        """Create training configuration based on model type"""
        base_config = {
            "epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.001,
            "validation_split": self.config["default_validation_split"],
            "early_stopping_patience": 10,
            "save_checkpoints": True,
            "checkpoint_frequency": 10
        }
        
        # Model-specific defaults
        if model_type == "LSTM":
            base_config.update({
                "epochs": 100,
                "batch_size": 32,
                "learning_rate": 0.001,
                "sequence_length": 60
            })
        elif model_type == "LightGBM":
            base_config.update({
                "epochs": 200,
                "batch_size": 64,
                "learning_rate": 0.1
            })
        elif model_type == "DQN":
            base_config.update({
                "epochs": 1000,
                "batch_size": 32,
                "learning_rate": 0.001
            })
        
        # Apply overrides
        if config_override:
            base_config.update(config_override)
        
        # Create TrainingConfig object
        mode = config_override.get("mode", TrainingMode.FULL) if config_override else TrainingMode.FULL
        
        return TrainingConfig(
            mode=mode,
            epochs=base_config["epochs"],
            batch_size=base_config["batch_size"],
            learning_rate=base_config["learning_rate"],
            validation_split=base_config["validation_split"],
            early_stopping_patience=base_config["early_stopping_patience"],
            model_specific_params={k: v for k, v in base_config.items() 
                                 if k not in ["mode", "epochs", "batch_size", "learning_rate", 
                                            "validation_split", "early_stopping_patience"]},
            save_checkpoints=base_config["save_checkpoints"],
            checkpoint_frequency=base_config["checkpoint_frequency"]
        )
    
    async def _get_or_create_model(self, model_id: str, model_type: str, 
                                 config: TrainingConfig) -> BaseAIModel:
        """Get existing model or create new one"""
        if model_id in self.models:
            model = self.models[model_id]
            
            # Update model configuration if needed
            if hasattr(model, 'config'):
                model.config.update(config.model_specific_params)
            
            return model
        
        # Create new model
        model_class = self.model_classes.get(model_type, PricePredictor)
        
        if model_type == "LSTM":
            model = model_class(
                sequence_length=config.model_specific_params.get("sequence_length", 60),
                model_config=config.model_specific_params
            )
        elif model_type == "LightGBM":
            model = model_class(
                signal_threshold=config.model_specific_params.get("signal_threshold", 0.7),
                model_config=config.model_specific_params
            )
        elif model_type == "DQN":
            model = model_class(
                state_dim=config.model_specific_params.get("state_dim", 20),
                action_dim=config.model_specific_params.get("action_dim", 10),
                model_config=config.model_specific_params
            )
        else:
            model = model_class()
        
        logger.info("创建新模型", model_id=model_id, model_type=model_type)
        return model
    
    async def _save_model(self, model: BaseAIModel, model_id: str) -> str:
        """Save trained model"""
        from pathlib import Path
        
        model_dir = Path(self.config["model_output_dir"]) / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model using the model's save method
        await model._save_model_state(model_dir)
        
        # Save model metadata
        metadata = {
            "model_id": model_id,
            "model_type": model.model_type,
            "version": model.version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "model_info": model.get_model_info()
        }
        
        import json
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        model_path = str(model_dir)
        logger.info("模型已保存", model_id=model_id, path=model_path)
        
        return model_path
    
    async def load_model(self, model_id: str, model_path: str) -> BaseAIModel:
        """Load trained model from path"""
        from pathlib import Path
        
        model_dir = Path(model_path)
        
        if not model_dir.exists():
            raise ValueError(f"模型路径不存在: {model_path}")
        
        # Load metadata
        import json
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        model_type = metadata["model_type"]
        
        # Create model instance
        model_class = self.model_classes.get(model_type, PricePredictor)
        model = model_class()
        
        # Load model state
        await model._load_model_state(model_dir)
        
        # Update model metadata
        model.metadata.status = ModelStatus.READY
        model.is_trained = True
        
        # Register model
        self.models[model_id] = model
        
        logger.info("模型已加载", model_id=model_id, model_type=model_type)
        
        return model
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a model"""
        if model_id not in self.models:
            return None
        
        model = self.models[model_id]
        training_history = self.training_history.get(model_id, [])
        
        return {
            "model_id": model_id,
            "model_info": model.get_model_info(),
            "training_count": len(training_history),
            "last_training": training_history[-1].training_id if training_history else None,
            "is_trained": model.is_trained,
            "status": model.metadata.status.value
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        return [self.get_model_info(model_id) for model_id in self.models.keys()]
    
    def get_training_history(self, model_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get training history for a model"""
        if model_id not in self.training_history:
            return []
        
        history = self.training_history[model_id]
        history.sort(key=lambda x: x.training_duration, reverse=True)
        
        return [
            {
                "training_id": result.training_id,
                "success": result.success,
                "duration": result.training_duration,
                "epochs_completed": result.epochs_completed,
                "final_metrics": result.final_metrics,
                "validation_status": result.validation_report.validation_status.value if result.validation_report else None,
                "trained_at": result.training_duration  # Using duration as placeholder
            }
            for result in history[:limit]
        ]
    
    def get_training_status(self, training_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active training"""
        if training_id not in self.active_training:
            return None
        
        result = self.active_training[training_id]
        
        return {
            "training_id": result.training_id,
            "model_id": result.model_id,
            "model_type": result.model_type,
            "success": result.success,
            "training_duration": result.training_duration,
            "epochs_completed": result.epochs_completed,
            "final_metrics": result.final_metrics,
            "validation_report": result.validation_report.get_validation_summary() if result.validation_report else None,
            "checkpoints_saved": result.checkpoints_saved,
            "final_model_path": result.final_model_path,
            "training_logs": result.training_logs[-10:],  # Last 10 log entries
            "error_message": result.error_message
        }