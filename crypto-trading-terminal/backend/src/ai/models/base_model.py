"""
Base AI Model framework
Provides common interface and functionality for all AI models
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from decimal import Decimal
import asyncio
import time
import json
from pathlib import Path


class ModelStatus:
    """Model status enumeration"""
    INITIALIZING = "initializing"
    TRAINING = "training"
    READY = "ready"
    ERROR = "error"
    UPDATING = "updating"
    MAINTENANCE = "maintenance"


class ModelMetadata:
    """Metadata about AI model"""
    
    def __init__(self, model_id: str, model_type: str, version: str):
        self.model_id = model_id
        self.model_type = model_type
        self.version = version
        self.created_at = datetime.now(timezone.utc)
        self.last_trained = None
        self.last_prediction = None
        self.prediction_count = 0
        self.accuracy_metrics = {}
        self.performance_metrics = {}
        self.status = ModelStatus.INITIALIZING
        self.features = []
        self.hyperparameters = {}
        self.training_data_size = 0
        self.validation_data_size = 0
        self.model_size_mb = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "last_prediction": self.last_prediction.isoformat() if self.last_prediction else None,
            "prediction_count": self.prediction_count,
            "accuracy_metrics": self.accuracy_metrics,
            "performance_metrics": self.performance_metrics,
            "status": self.status,
            "features": self.features,
            "hyperparameters": self.hyperparameters,
            "training_data_size": self.training_data_size,
            "validation_data_size": self.validation_data_size,
            "model_size_mb": self.model_size_mb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create metadata from dictionary"""
        metadata = cls(
            model_id=data["model_id"],
            model_type=data["model_type"],
            version=data["version"]
        )
        
        metadata.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_trained"):
            metadata.last_trained = datetime.fromisoformat(data["last_trained"])
        if data.get("last_prediction"):
            metadata.last_prediction = datetime.fromisoformat(data["last_prediction"])
        
        metadata.prediction_count = data.get("prediction_count", 0)
        metadata.accuracy_metrics = data.get("accuracy_metrics", {})
        metadata.performance_metrics = data.get("performance_metrics", {})
        metadata.status = data.get("status", ModelStatus.INITIALIZING)
        metadata.features = data.get("features", [])
        metadata.hyperparameters = data.get("hyperparameters", {})
        metadata.training_data_size = data.get("training_data_size", 0)
        metadata.validation_data_size = data.get("validation_data_size", 0)
        metadata.model_size_mb = data.get("model_size_mb", 0)
        
        return metadata


class BaseAIModel(ABC):
    """Base class for all AI models"""
    
    def __init__(self, model_id: str, model_type: str, version: str):
        self.model_id = model_id
        self.model_type = model_type
        self.version = version
        self.metadata = ModelMetadata(model_id, model_type, version)
        self.is_trained = False
        self.performance_history = []
        
        # Performance tracking
        self.prediction_times = []
        self.prediction_latency_target = 2.0  # seconds
        self.accuracy_target = 0.85  # 85%
        
        # Error handling
        self.error_count = 0
        self.last_error = None
        self.error_threshold = 5
        
    @abstractmethod
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction using the model"""
        pass
    
    @abstractmethod
    async def train(self, training_data: List[Dict[str, Any]], 
                   validation_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Train the model with data"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and capabilities"""
        pass
    
    async def _track_prediction_start(self) -> float:
        """Track prediction start time"""
        return time.time()
    
    async def _track_prediction_end(self, start_time: float) -> float:
        """Track prediction end time and update metrics"""
        end_time = time.time()
        latency = end_time - start_time
        
        self.prediction_times.append(latency)
        self.metadata.prediction_count += 1
        self.metadata.last_prediction = datetime.now(timezone.utc)
        
        # Keep only last 1000 prediction times
        if len(self.prediction_times) > 1000:
            self.prediction_times = self.prediction_times[-1000:]
        
        return latency
    
    def get_average_latency(self) -> float:
        """Get average prediction latency"""
        if not self.prediction_times:
            return 0.0
        return sum(self.prediction_times) / len(self.prediction_times)
    
    def meets_latency_requirement(self) -> bool:
        """Check if model meets latency requirement"""
        avg_latency = self.get_average_latency()
        return avg_latency <= self.prediction_latency_target
    
    def get_prediction_confidence(self, data: Dict[str, Any]) -> Decimal:
        """Calculate prediction confidence score (0-1)"""
        # Default implementation - subclasses should override
        return Decimal("0.8")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data before prediction"""
        if not isinstance(data, dict):
            return False
        
        # Check for required fields ( subclasses can add more)
        required_fields = self.metadata.features
        return all(field in data for field in required_fields)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the model"""
        health_status = {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "status": self.metadata.status,
            "is_trained": self.is_trained,
            "is_healthy": True,
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check model status
        if self.metadata.status == ModelStatus.ERROR:
            health_status["is_healthy"] = False
            health_status["checks"]["status"] = "error"
        
        # Check prediction latency
        avg_latency = self.get_average_latency()
        latency_ok = avg_latency <= self.prediction_latency_target
        health_status["checks"]["latency"] = {
            "ok": latency_ok,
            "average_latency": avg_latency,
            "target": self.prediction_latency_target
        }
        if not latency_ok:
            health_status["is_healthy"] = False
        
        # Check error count
        error_rate = self.error_count / max(self.metadata.prediction_count, 1)
        error_rate_ok = error_rate < 0.1  # Less than 10% error rate
        health_status["checks"]["error_rate"] = {
            "ok": error_rate_ok,
            "error_rate": error_rate,
            "error_count": self.error_count,
            "prediction_count": self.metadata.prediction_count
        }
        if not error_rate_ok:
            health_status["is_healthy"] = False
        
        return health_status
    
    async def update_metadata(self, **kwargs):
        """Update model metadata"""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
    
    def record_error(self, error: Exception):
        """Record an error occurred during prediction/training"""
        self.error_count += 1
        self.last_error = {
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Update status if too many errors
        if self.error_count >= self.error_threshold:
            self.metadata.status = ModelStatus.ERROR
    
    def reset_errors(self):
        """Reset error count and status"""
        self.error_count = 0
        self.last_error = None
        if self.metadata.status == ModelStatus.ERROR:
            self.metadata.status = ModelStatus.READY
    
    async def save_model(self, save_path: str):
        """Save model to file"""
        model_dir = Path(save_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata.to_dict(), f, indent=2, default=str)
        
        # Save model state (to be implemented by subclasses)
        await self._save_model_state(model_dir)
        
        self.metadata.model_size_mb = self._calculate_model_size(model_dir)
    
    async def load_model(self, load_path: str):
        """Load model from file"""
        model_dir = Path(load_path)
        
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {load_path}")
        
        # Load metadata
        metadata_path = model_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata_data = json.load(f)
            self.metadata = ModelMetadata.from_dict(metadata_data)
        
        # Load model state (to be implemented by subclasses)
        await self._load_model_state(model_dir)
        
        self.is_trained = True
        self.metadata.status = ModelStatus.READY
    
    async def _save_model_state(self, model_dir: Path):
        """Save model-specific state (to be implemented by subclasses)"""
        # Subclasses should override this method
        pass
    
    async def _load_model_state(self, model_dir: Path):
        """Load model-specific state (to be implemented by subclasses)"""
        # Subclasses should override this method
        pass
    
    def _calculate_model_size(self, model_dir: Path) -> float:
        """Calculate model size in MB"""
        total_size = 0
        for file_path in model_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    
    def __str__(self) -> str:
        return f"{self.model_type}({self.model_id}, v{self.version}, status={self.metadata.status})"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(model_id='{self.model_id}', "
                f"model_type='{self.model_type}', version='{self.version}')")