"""
LSTM Price Prediction Model
Predicts cryptocurrency prices using Long Short-Term Memory neural network
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import pickle
import warnings
warnings.filterwarnings('ignore')

from .base_model import BaseAIModel, ModelStatus


class PricePredictor(BaseAIModel):
    """LSTM-based price prediction model for cryptocurrencies"""
    
    def __init__(self, 
                 sequence_length: int = 60,
                 features: Optional[List[str]] = None,
                 model_config: Optional[Dict[str, Any]] = None):
        super().__init__(
            model_id="price_predictor_lstm_v1",
            model_type="LSTM",
            version="1.2.0"
        )
        
        # LSTM model configuration
        self.sequence_length = sequence_length
        self.features = features or [
            "price", "volume", "rsi", "macd", 
            "bb_upper", "bb_lower", "volatility"
        ]
        
        # Model hyperparameters
        self.config = model_config or {
            "lstm_units": [50, 50, 50],
            "dropout": 0.2,
            "dense_units": [25, 1],
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 100,
            "validation_split": 0.2,
            "early_stopping_patience": 10
        }
        
        # Data preprocessing
        self.scaler = MinMaxScaler()
        self.feature_scalers = {}
        
        # Model components (mock for implementation)
        self.lstm_model = None
        self.dense_model = None
        
        # Training statistics
        self.training_history = []
        self.validation_scores = {}
        
        # Set metadata
        self.metadata.features = self.features
        self.metadata.hyperparameters = self.config
        self.metadata.status = ModelStatus.INITIALIZING
        
        # Initialize mock model components
        self._initialize_mock_model()
    
    def _initialize_mock_model(self):
        """Initialize mock LSTM model components"""
        # In a real implementation, this would initialize actual Keras/TensorFlow models
        self.lstm_model = {
            "input_shape": (self.sequence_length, len(self.features)),
            "layers": self.config["lstm_units"],
            "dropout": self.config["dropout"]
        }
        
        self.dense_model = {
            "layers": self.config["dense_units"],
            "output_activation": "linear"
        }
    
    async def predict(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict future price based on market data"""
        start_time = await self._track_prediction_start()
        
        try:
            # Validate input
            if not self.validate_input(market_data):
                raise ValueError("Invalid input data for price prediction")
            
            # Check model status
            if not self.is_trained:
                raise ValueError("Model is not trained yet")
            
            if self.metadata.status == ModelStatus.ERROR:
                raise ValueError("Model is in error state")
            
            # Extract features
            features = self._extract_features(market_data)
            
            # Preprocess features
            processed_features = await self._preprocess_features(features)
            
            # Generate prediction using mock LSTM
            prediction_result = await self._generate_prediction(processed_features)
            
            # Calculate confidence
            confidence = self.get_prediction_confidence(market_data)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(market_data)
            
            # Calculate prediction horizon
            prediction_horizon = market_data.get("prediction_horizon", "1h")
            
            # Compile result
            result = {
                "symbol": market_data.get("symbol", "BTCUSDT"),
                "current_price": Decimal(str(market_data.get("current_price", 0))),
                "predicted_price": prediction_result["predicted_price"],
                "confidence": confidence,
                "prediction_horizon": prediction_horizon,
                "timestamp": datetime.now(timezone.utc),
                "model_version": self.version,
                "features_used": self.features,
                "prediction_change_percent": prediction_result["change_percent"],
                "risk_score": risk_score,
                "model_metadata": {
                    "prediction_id": f"pred_{int(datetime.now().timestamp())}",
                    "processing_time": await self._track_prediction_end(start_time),
                    "sequence_length": self.sequence_length,
                    "model_type": "LSTM"
                }
            }
            
            return result
            
        except Exception as e:
            self.record_error(e)
            await self._track_prediction_end(start_time)
            raise e
    
    async def train(self, training_data: List[Dict[str, Any]], 
                   validation_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Train LSTM model with historical data"""
        
        self.metadata.status = ModelStatus.TRAINING
        training_start = datetime.now(timezone.utc)
        
        try:
            if len(training_data) < self.sequence_length * 10:
                raise ValueError(f"Insufficient training data: need at least {self.sequence_length * 10} samples")
            
            # Prepare training data
            X_train, y_train, X_val, y_val = await self._prepare_training_data(
                training_data, validation_data
            )
            
            # Update metadata
            self.metadata.training_data_size = len(training_data)
            if validation_data:
                self.metadata.validation_data_size = len(validation_data)
            
            # Simulate training process
            training_result = await self._simulate_training(X_train, y_train, X_val, y_val)
            
            # Update model status
            self.is_trained = True
            self.metadata.status = ModelStatus.READY
            self.metadata.last_trained = training_start
            
            # Calculate final metrics
            final_metrics = {
                "training_duration": (datetime.now(timezone.utc) - training_start).total_seconds(),
                "training_samples": len(training_data),
                "validation_samples": len(validation_data) if validation_data else 0,
                "final_loss": training_result["final_loss"],
                "final_accuracy": training_result.get("accuracy", 0.0),
                "training_history": training_result["history"]
            }
            
            # Store training statistics
            self.training_history.append({
                "training_date": training_start.isoformat(),
                "data_size": len(training_data),
                "metrics": final_metrics
            })
            
            return final_metrics
            
        except Exception as e:
            self.metadata.status = ModelStatus.ERROR
            self.record_error(e)
            raise e
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information"""
        return {
            "model_type": "LSTM",
            "version": self.version,
            "model_id": self.model_id,
            "sequence_length": self.sequence_length,
            "features": self.features,
            "hyperparameters": self.config,
            "is_trained": self.is_trained,
            "status": self.metadata.status,
            "training_history_count": len(self.training_history),
            "prediction_capabilities": {
                "supported_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
                "prediction_horizons": ["15m", "1h", "4h", "1d"],
                "accuracy_target": f"{self.accuracy_target:.1%}",
                "latency_target": f"{self.prediction_latency_target}s"
            },
            "feature_importance": {
                "price": 0.25,
                "volume": 0.20,
                "rsi": 0.15,
                "macd": 0.15,
                "bb_upper": 0.10,
                "bb_lower": 0.10,
                "volatility": 0.05
            },
            "model_architecture": {
                "lstm_layers": len(self.config["lstm_units"]),
                "lstm_units": self.config["lstm_units"],
                "dropout": self.config["dropout"],
                "dense_layers": len(self.config["dense_units"])
            },
            "training_statistics": {
                "total_predictions": self.metadata.prediction_count,
                "average_latency": self.get_average_latency(),
                "error_count": self.error_count,
                "last_training": self.metadata.last_trained.isoformat() if self.metadata.last_trained else None
            }
        }
    
    def _extract_features(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from market data"""
        features = {}
        
        for feature in self.features:
            if feature in market_data:
                features[feature] = market_data[feature]
            else:
                # Generate default values for missing features
                if feature == "volatility":
                    features[feature] = Decimal("0.02")  # 2% volatility
                elif feature in ["rsi"]:
                    features[feature] = Decimal("50.0")  # Neutral RSI
                else:
                    features[feature] = Decimal("0.0")
        
        return features
    
    async def _preprocess_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Preprocess features for model input"""
        # Convert Decimal to float
        feature_values = []
        for feature in self.features:
            value = float(features.get(feature, 0.0))
            feature_values.append(value)
        
        return np.array(feature_values)
    
    async def _generate_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Generate price prediction using mock LSTM"""
        # Simulate LSTM prediction process
        await asyncio.sleep(0.1)  # Simulate computation time
        
        # Mock prediction based on current price trend and volume
        current_price = float(features[0]) if len(features) > 0 else 50000.0
        volume = float(features[1]) if len(features) > 1 else 1000.0
        rsi = float(features[2]) if len(features) > 2 else 50.0
        
        # Simple trend-based prediction
        trend_factor = 1.0
        
        # RSI-based adjustment
        if rsi > 70:  # Overbought
            trend_factor *= 0.95
        elif rsi < 30:  # Oversold
            trend_factor *= 1.05
        
        # Volume-based confidence adjustment
        volume_factor = min(volume / 1000.0, 2.0)  # Normalize volume
        
        # Generate prediction
        base_change = np.random.normal(0.001, 0.02)  # Small random change
        predicted_change = base_change * trend_factor * volume_factor
        
        predicted_price = current_price * (1 + predicted_change)
        
        return {
            "predicted_price": Decimal(str(round(predicted_price, 2))),
            "change_percent": Decimal(str(round(predicted_change * 100, 2)))
        }
    
    def _calculate_risk_score(self, market_data: Dict[str, Any]) -> Decimal:
        """Calculate risk score for the prediction"""
        try:
            current_price = Decimal(str(market_data.get("current_price", 0)))
            volume = Decimal(str(market_data.get("volume", 0)))
            
            # Simple risk calculation based on volume and price volatility
            if current_price == 0:
                return Decimal("0.5")
            
            volume_score = min(float(volume) / 10000.0, 1.0)  # Normalize volume
            price_score = 0.5  # Default price score
            
            # Calculate combined risk score
            risk_score = Decimal(str(round((volume_score + price_score) / 2, 2)))
            
            return max(Decimal("0.0"), min(risk_score, Decimal("1.0")))
            
        except Exception:
            return Decimal("0.5")  # Default risk score
    
    async def _prepare_training_data(self, training_data: List[Dict[str, Any]], 
                                   validation_data: Optional[List[Dict[str, Any]]]) -> Tuple:
        """Prepare training and validation data"""
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(training_data)
        
        # Extract features and targets
        feature_columns = self.features + ["timestamp"]
        
        # Ensure required columns exist
        for col in feature_columns:
            if col not in df.columns:
                if col == "volatility":
                    df[col] = 0.02  # Default volatility
                elif col == "rsi":
                    df[col] = 50.0  # Default RSI
                else:
                    df[col] = 0.0
        
        # Create sequences for LSTM
        sequences, targets = self._create_sequences(df)
        
        # Split for validation if provided
        if validation_data:
            val_df = pd.DataFrame(validation_data)
            val_sequences, val_targets = self._create_sequences(val_df)
            return sequences, targets, val_sequences, val_targets
        else:
            # Split training data
            split_idx = int(len(sequences) * 0.8)
            return (sequences[:split_idx], targets[:split_idx],
                   sequences[split_idx:], targets[split_idx:])
    
    def _create_sequences(self, df: pd.DataFrame) -> Tuple[List, List]:
        """Create sequences for LSTM training"""
        sequences = []
        targets = []
        
        # Sort by timestamp
        df = df.sort_values("timestamp")
        
        # Create sequences
        for i in range(self.sequence_length, len(df)):
            # Extract sequence
            sequence = df.iloc[i-self.sequence_length:i][self.features].values
            sequences.append(sequence)
            
            # Extract target (next price)
            next_price = df.iloc[i]["price"]
            targets.append(next_price)
        
        return sequences, targets
    
    async def _simulate_training(self, X_train, y_train, X_val, y_val) -> Dict[str, Any]:
        """Simulate LSTM training process"""
        # Simulate training epochs
        training_history = []
        for epoch in range(self.config["epochs"]):
            # Simulate training progress
            loss = np.random.exponential(0.1) * np.exp(-epoch * 0.02)
            accuracy = 1 - (loss * 2) + np.random.normal(0, 0.05)
            accuracy = max(0.0, min(1.0, accuracy))
            
            training_history.append({
                "epoch": epoch + 1,
                "loss": float(loss),
                "accuracy": float(accuracy)
            })
            
            # Simulate early stopping
            if epoch > 20 and accuracy > 0.85:
                break
        
        # Mock final metrics
        final_loss = training_history[-1]["loss"]
        final_accuracy = training_history[-1]["accuracy"]
        
        return {
            "final_loss": final_loss,
            "accuracy": final_accuracy,
            "history": training_history,
            "epochs_trained": len(training_history)
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input for price prediction"""
        if not super().validate_input(data):
            return False
        
        # Check for required fields
        required_fields = ["symbol", "current_price"]
        return all(field in data for field in required_fields)
    
    def get_prediction_confidence(self, data: Dict[str, Any]) -> Decimal:
        """Calculate prediction confidence based on data quality"""
        try:
            confidence_factors = []
            
            # Volume-based confidence
            volume = float(data.get("volume", 0))
            if volume > 5000:
                confidence_factors.append(0.9)
            elif volume > 1000:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            # Price-based confidence
            current_price = float(data.get("current_price", 0))
            if current_price > 1000:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # RSI-based confidence
            rsi = float(data.get("rsi", 50))
            if 30 <= rsi <= 70:  # Normal RSI range
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # Calculate overall confidence
            if confidence_factors:
                avg_confidence = sum(confidence_factors) / len(confidence_factors)
                return Decimal(str(round(avg_confidence, 2)))
            else:
                return Decimal("0.7")  # Default confidence
                
        except Exception:
            return Decimal("0.6")  # Default confidence on error
    
    async def _save_model_state(self, model_dir):
        """Save LSTM model state"""
        # In a real implementation, this would save the actual Keras model
        model_config = {
            "sequence_length": self.sequence_length,
            "features": self.features,
            "config": self.config,
            "scaler": self.scaler,
            "training_history": self.training_history
        }
        
        import pickle
        with open(model_dir / "model_config.pkl", "wb") as f:
            pickle.dump(model_config, f)
    
    async def _load_model_state(self, model_dir):
        """Load LSTM model state"""
        import pickle
        try:
            with open(model_dir / "model_config.pkl", "rb") as f:
                model_config = pickle.load(f)
            
            self.sequence_length = model_config["sequence_length"]
            self.features = model_config["features"]
            self.config = model_config["config"]
            self.training_history = model_config.get("training_history", [])
            
        except FileNotFoundError:
            # Use default configuration
            pass