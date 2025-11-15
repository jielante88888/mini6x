"""
Data Processing Pipeline
Handles data preparation, validation, and preprocessing for AI model training
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
import structlog
import warnings
warnings.filterwarnings('ignore')

logger = structlog.get_logger()


class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class DataValidationResult:
    """Data validation result"""
    is_valid: bool
    quality: DataQuality
    issues: List[str]
    statistics: Dict[str, Any]
    recommendations: List[str]


@dataclass
class ProcessedDataset:
    """Processed dataset for training"""
    features: pd.DataFrame
    targets: pd.DataFrame
    metadata: Dict[str, Any]
    validation_result: DataValidationResult
    preprocessing_steps: List[str]


class DataProcessor:
    """Comprehensive data processing pipeline for AI model training"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "min_data_points": 100,
            "max_missing_ratio": 0.1,
            "outlier_threshold": 3.0,
            "feature_scaling": "standard",
            "sequence_length": 60,
            "validation_split": 0.2,
            "test_split": 0.1,
            "random_seed": 42
        }
        
        # Data quality thresholds
        self.quality_thresholds = {
            DataQuality.EXCELLENT: {"missing_ratio": 0.01, "outlier_ratio": 0.01},
            DataQuality.GOOD: {"missing_ratio": 0.05, "outlier_ratio": 0.05},
            DataQuality.FAIR: {"missing_ratio": 0.1, "outlier_ratio": 0.1},
            DataQuality.POOR: {"missing_ratio": 0.2, "outlier_ratio": 0.2}
        }
        
        # Feature engineering rules
        self.feature_rules = {
            "price_features": ["open", "high", "low", "close", "volume"],
            "technical_indicators": ["rsi", "macd", "bb_upper", "bb_lower", "sma", "ema"],
            "derived_features": ["volatility", "momentum", "price_change", "volume_change"]
        }
        
        logger.info("数据处理器初始化完成", config=self.config)
    
    async def process_training_data(self, raw_data: List[Dict[str, Any]], 
                                  model_type: str) -> ProcessedDataset:
        """Process raw training data for specific model type"""
        logger.info("开始处理训练数据", model_type=model_type, data_size=len(raw_data))
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(raw_data)
            
            # Validate data quality
            validation_result = await self._validate_data_quality(df)
            
            if not validation_result.is_valid:
                raise ValueError(f"数据质量不符合要求: {validation_result.issues}")
            
            # Clean and preprocess data
            cleaned_data = await self._clean_data(df)
            
            # Engineer features based on model type
            if model_type == "LSTM":
                features, targets = await self._prepare_lstm_data(cleaned_data)
            elif model_type == "LightGBM":
                features, targets = await self._prepare_lightgbm_data(cleaned_data)
            elif model_type == "DQN":
                features, targets = await self._prepare_dqn_data(cleaned_data)
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")
            
            # Create processed dataset
            processed_dataset = ProcessedDataset(
                features=features,
                targets=targets,
                metadata={
                    "model_type": model_type,
                    "original_size": len(raw_data),
                    "processed_size": len(features),
                    "feature_count": len(features.columns),
                    "target_count": len(targets.columns),
                    "processing_timestamp": datetime.now(timezone.utc).isoformat()
                },
                validation_result=validation_result,
                preprocessing_steps=[
                    "data_validation",
                    "missing_value_handling",
                    "outlier_detection",
                    "feature_engineering",
                    "normalization",
                    "sequence_creation"
                ]
            )
            
            logger.info("训练数据处理完成", 
                       model_type=model_type,
                       features_shape=features.shape,
                       targets_shape=targets.shape)
            
            return processed_dataset
            
        except Exception as e:
            logger.error("训练数据处理失败", error=str(e))
            raise e
    
    async def _validate_data_quality(self, df: pd.DataFrame) -> DataValidationResult:
        """Validate data quality and return validation result"""
        issues = []
        recommendations = []
        statistics = {}
        
        # Basic statistics
        statistics["total_rows"] = len(df)
        statistics["total_columns"] = len(df.columns)
        statistics["data_types"] = df.dtypes.to_dict()
        
        # Missing value analysis
        missing_counts = df.isnull().sum()
        missing_ratios = missing_counts / len(df)
        statistics["missing_counts"] = missing_counts.to_dict()
        statistics["missing_ratios"] = missing_ratios.to_dict()
        
        # Check for excessive missing values
        max_allowed_missing = self.config["max_missing_ratio"]
        high_missing_cols = missing_ratios[missing_ratios > max_allowed_missing]
        if len(high_missing_cols) > 0:
            issues.append(f"列缺失值比例过高: {high_missing_cols.to_dict()}")
            recommendations.append(f"考虑删除缺失值比例超过{max_allowed_missing}的列")
        
        # Outlier detection
        outlier_stats = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - self.config["outlier_threshold"] * iqr
            upper_bound = q3 + self.config["outlier_threshold"] * iqr
            
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            outlier_ratio = outliers / len(df)
            outlier_stats[col] = {
                "count": outliers,
                "ratio": outlier_ratio,
                "bounds": {"lower": lower_bound, "upper": upper_bound}
            }
        
        statistics["outlier_stats"] = outlier_stats
        
        # Check for excessive outliers
        high_outlier_cols = [col for col, stats in outlier_stats.items() 
                           if stats["ratio"] > 0.1]
        if len(high_outlier_cols) > 0:
            issues.append(f"列异常值比例过高: {high_outlier_cols}")
            recommendations.append("考虑使用稳健的统计方法或变换处理异常值")
        
        # Data completeness check
        total_missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        statistics["total_missing_ratio"] = total_missing_ratio
        
        if total_missing_ratio > 0.2:
            issues.append(f"总体缺失值比例过高: {total_missing_ratio:.2%}")
            recommendations.append("考虑数据补全或增加数据源")
        
        # Determine data quality
        if total_missing_ratio <= 0.01 and len(high_outlier_cols) == 0:
            quality = DataQuality.EXCELLENT
        elif total_missing_ratio <= 0.05 and len(high_outlier_cols) <= 1:
            quality = DataQuality.GOOD
        elif total_missing_ratio <= 0.1 and len(high_outlier_cols) <= 3:
            quality = DataQuality.FAIR
        else:
            quality = DataQuality.POOR
        
        # Data size validation
        if len(df) < self.config["min_data_points"]:
            issues.append(f"数据点数量不足: {len(df)} < {self.config['min_data_points']}")
            recommendations.append(f"需要至少{self.config['min_data_points']}个数据点进行有效训练")
        
        is_valid = len(issues) == 0 and len(df) >= self.config["min_data_points"]
        
        return DataValidationResult(
            is_valid=is_valid,
            quality=quality,
            issues=issues,
            statistics=statistics,
            recommendations=recommendations
        )
    
    async def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess data"""
        cleaned_df = df.copy()
        
        # Handle missing values
        # For numeric columns, use forward fill then backward fill
        numeric_cols = cleaned_df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if cleaned_df[col].isnull().any():
                cleaned_df[col] = cleaned_df[col].fillna(method='ffill').fillna(method='bfill')
        
        # For categorical columns, use mode
        categorical_cols = cleaned_df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if cleaned_df[col].isnull().any():
                mode_value = cleaned_df[col].mode()
                if len(mode_value) > 0:
                    cleaned_df[col] = cleaned_df[col].fillna(mode_value[0])
        
        # Remove duplicate rows
        initial_size = len(cleaned_df)
        cleaned_df = cleaned_df.drop_duplicates()
        final_size = len(cleaned_df)
        
        if initial_size > final_size:
            logger.info("删除重复数据", removed=initial_size - final_size)
        
        # Reset index
        cleaned_df = cleaned_df.reset_index(drop=True)
        
        return cleaned_df
    
    async def _prepare_lstm_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare data for LSTM model"""
        # Sort by timestamp if available
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        # Extract features for LSTM
        feature_cols = []
        for category, cols in self.feature_rules.items():
            for col in cols:
                if col in df.columns:
                    feature_cols.append(col)
        
        # Add derived features
        if 'close' in df.columns and 'open' in df.columns:
            df['price_change'] = (df['close'] - df['open']) / df['open']
            feature_cols.append('price_change')
        
        if 'volume' in df.columns:
            df['volume_change'] = df['volume'].pct_change()
            feature_cols.append('volume_change')
        
        # Create sequences
        sequence_length = self.config["sequence_length"]
        features_sequences = []
        targets = []
        
        for i in range(sequence_length, len(df)):
            # Extract sequence
            sequence = df.iloc[i-sequence_length:i][feature_cols]
            features_sequences.append(sequence.values.flatten())
            
            # Extract target (next price or price change)
            if 'close' in df.columns:
                next_price = df.iloc[i]['close']
                targets.append([next_price])
            else:
                # Use last price change as target
                if 'price_change' in df.columns:
                    targets.append([df.iloc[i]['price_change']])
                else:
                    targets.append([0.0])
        
        # Convert to DataFrames
        feature_names = [f"feature_{j}" for j in range(len(features_sequences[0]))]
        features_df = pd.DataFrame(features_sequences, columns=feature_names)
        targets_df = pd.DataFrame(targets, columns=['target'])
        
        return features_df, targets_df
    
    async def _prepare_lightgbm_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare data for LightGBM model"""
        # Sort by timestamp if available
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        # Extract features for LightGBM
        feature_cols = []
        for category, cols in self.feature_rules.items():
            for col in cols:
                if col in df.columns:
                    feature_cols.append(col)
        
        # Create target variable (signal classification)
        if 'close' in df.columns:
            df['price_change_pct'] = df['close'].pct_change()
            
            # Create signal labels based on price changes
            df['signal'] = 'hold'
            df.loc[df['price_change_pct'] > 0.02, 'signal'] = 'buy'
            df.loc[df['price_change_pct'] < -0.02, 'signal'] = 'sell'
            df.loc[(df['price_change_pct'] > 0.005) & (df['price_change_pct'] <= 0.02), 'signal'] = 'weak_buy'
            df.loc[(df['price_change_pct'] < -0.005) & (df['price_change_pct'] >= -0.02), 'signal'] = 'weak_sell'
        
        # Remove rows with missing targets
        if 'signal' in df.columns:
            df = df.dropna(subset=['signal'])
        
        # Prepare features and targets
        features_df = df[feature_cols].copy()
        targets_df = pd.DataFrame({'signal': df['signal']}) if 'signal' in df.columns else pd.DataFrame()
        
        return features_df, targets_df
    
    async def _prepare_dqn_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare data for DQN model"""
        # Sort by timestamp if available
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        # Create state features for DQN
        state_features = []
        
        # Technical indicators as state features
        if 'rsi' in df.columns:
            state_features.append('rsi')
        if 'macd' in df.columns:
            state_features.append('macd')
        if 'volatility' in df.columns:
            state_features.append('volatility')
        
        # Price and volume features
        if 'close' in df.columns:
            state_features.append('close')
        if 'volume' in df.columns:
            state_features.append('volume')
        
        # Create target (optimal action based on future returns)
        if 'close' in df.columns:
            df['future_return'] = df['close'].shift(-1) / df['close'] - 1
            
            # Define optimal actions based on future returns
            df['optimal_action'] = 0  # hold
            df.loc[df['future_return'] > 0.01, 'optimal_action'] = 1  # buy
            df.loc[df['future_return'] < -0.01, 'optimal_action'] = 2  # sell
        
        # Remove rows with missing targets
        if 'optimal_action' in df.columns:
            df = df.dropna(subset=['optimal_action'])
        
        # Prepare features and targets
        features_df = df[state_features].copy()
        targets_df = pd.DataFrame({'action': df['optimal_action']}) if 'optimal_action' in df.columns else pd.DataFrame()
        
        return features_df, targets_df
    
    async def split_dataset(self, dataset: ProcessedDataset, 
                          validation_split: Optional[float] = None,
                          test_split: Optional[float] = None) -> Dict[str, ProcessedDataset]:
        """Split dataset into train/validation/test sets"""
        val_split = validation_split or self.config["validation_split"]
        test_s = test_split or self.config["test_split"]
        
        # Calculate split indices
        n = len(dataset.features)
        val_size = int(n * val_split)
        test_size = int(n * test_s)
        train_size = n - val_size - test_size
        
        # Split data
        train_features = dataset.features.iloc[:train_size]
        train_targets = dataset.targets.iloc[:train_size]
        
        val_features = dataset.features.iloc[train_size:train_size + val_size]
        val_targets = dataset.targets.iloc[train_size:train_size + val_size]
        
        test_features = dataset.features.iloc[train_size + val_size:]
        test_targets = dataset.targets.iloc[train_size + val_size:]
        
        # Create split datasets
        splits = {
            "train": ProcessedDataset(
                features=train_features,
                targets=train_targets,
                metadata={**dataset.metadata, "split": "train"},
                validation_result=dataset.validation_result,
                preprocessing_steps=dataset.preprocessing_steps
            ),
            "validation": ProcessedDataset(
                features=val_features,
                targets=val_targets,
                metadata={**dataset.metadata, "split": "validation"},
                validation_result=dataset.validation_result,
                preprocessing_steps=dataset.preprocessing_steps
            ),
            "test": ProcessedDataset(
                features=test_features,
                targets=test_targets,
                metadata={**dataset.metadata, "split": "test"},
                validation_result=dataset.validation_result,
                preprocessing_steps=dataset.preprocessing_steps
            )
        }
        
        logger.info("数据集分割完成",
                   train_size=len(train_features),
                   validation_size=len(val_features),
                   test_size=len(test_features))
        
        return splits
    
    def get_processing_statistics(self, dataset: ProcessedDataset) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        stats = {
            "dataset_info": dataset.metadata,
            "data_quality": {
                "level": dataset.validation_result.quality.value,
                "issues_count": len(dataset.validation_result.issues),
                "recommendations_count": len(dataset.validation_result.recommendations)
            },
            "feature_statistics": {
                "count": len(dataset.features.columns),
                "missing_values": dataset.features.isnull().sum().to_dict(),
                "data_types": dataset.features.dtypes.to_dict(),
                "summary": dataset.features.describe().to_dict() if len(dataset.features) > 0 else {}
            },
            "target_statistics": {
                "count": len(dataset.targets.columns),
                "unique_values": dataset.targets.nunique().to_dict() if len(dataset.targets) > 0 else {},
                "summary": dataset.targets.describe().to_dict() if len(dataset.targets) > 0 else {}
            }
        }
        
        return stats