"""
Analysis Engine
Central coordinator for real-time AI analysis across all market data
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog

from .market_analyzer import MarketAnalyzer, MarketInsight
from .signal_analyzer import SignalAnalyzer, SignalInsight
from .performance_analyzer import PerformanceAnalyzer, PerformanceInsight
from .insight_generator import InsightGenerator, GeneratedInsight

logger = structlog.get_logger()


class AnalysisStatus(Enum):
    """Analysis engine status"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AnalysisConfig:
    """Analysis engine configuration"""
    analysis_interval_seconds: int
    max_concurrent_analyses: int
    enable_real_time: bool
    enable_insights: bool
    cache_expiry_minutes: int
    performance_tracking_enabled: bool
    alert_thresholds: Dict[str, Decimal]


class AnalysisEngine:
    """Central AI analysis engine coordinating all analysis components"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = AnalysisConfig(
            analysis_interval_seconds=30,
            max_concurrent_analyses=5,
            enable_real_time=True,
            enable_insights=True,
            cache_expiry_minutes=15,
            performance_tracking_enabled=True,
            alert_thresholds={
                "confidence": Decimal("0.7"),
                "volatility": Decimal("0.05"),
                "drawdown": Decimal("0.15")
            }
        )
        
        if config:
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        # Initialize analyzers
        self.market_analyzer = None
        self.signal_analyzer = None
        self.performance_analyzer = None
        self.insight_generator = None
        
        # Analysis state
        self.status = AnalysisStatus.STOPPED
        self.analysis_task: Optional[asyncio.Task] = None
        self.is_real_time_enabled = False
        
        # Data and results
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        self.analysis_results: Dict[str, Dict[str, Any]] = {}
        self.insights_cache: Dict[str, List[GeneratedInsight]] = {}
        
        # Performance tracking
        self.analysis_stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_confidence": Decimal("0.0"),
            "last_analysis_time": None,
            "processing_time_avg": 0.0
        }
        
        # Callbacks
        self.analysis_complete_callbacks: List[Callable] = []
        self.insight_generated_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        logger.info("分析引擎初始化完成", config=self.config.__dict__)
    
    async def initialize(self, ai_models: Dict[str, Any]):
        """Initialize analysis engine with AI models"""
        try:
            logger.info("初始化分析引擎组件")
            
            # Initialize analyzers with AI models
            self.market_analyzer = MarketAnalyzer(
                price_predictor=ai_models.get("price_predictor"),
                signal_scorer=ai_models.get("signal_scorer")
            )
            
            self.signal_analyzer = SignalAnalyzer(
                signal_scorer=ai_models.get("signal_scorer"),
                price_predictor=ai_models.get("price_predictor")
            )
            
            self.performance_analyzer = PerformanceAnalyzer()
            
            self.insight_generator = InsightGenerator(
                market_analyzer=self.market_analyzer,
                signal_analyzer=self.signal_analyzer,
                performance_analyzer=self.performance_analyzer
            )
            
            logger.info("分析引擎组件初始化完成")
            
        except Exception as e:
            logger.error("分析引擎初始化失败", error=str(e))
            self.status = AnalysisStatus.ERROR
            raise e
    
    async def start_real_time_analysis(self):
        """Start real-time analysis process"""
        if self.status == AnalysisStatus.RUNNING:
            logger.warning("分析引擎已在运行中")
            return
        
        if not all([self.market_analyzer, self.signal_analyzer, 
                   self.performance_analyzer, self.insight_generator]):
            raise ValueError("分析引擎尚未初始化，请先调用 initialize() 方法")
        
        self.status = AnalysisStatus.RUNNING
        self.is_real_time_enabled = True
        
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        
        logger.info("实时分析引擎已启动")
    
    async def stop_real_time_analysis(self):
        """Stop real-time analysis process"""
        if self.status == AnalysisStatus.STOPPED:
            return
        
        self.status = AnalysisStatus.STOPPED
        self.is_real_time_enabled = False
        
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        
        logger.info("实时分析引擎已停止")
    
    async def _analysis_loop(self):
        """Main analysis loop for real-time processing"""
        while self.status == AnalysisStatus.RUNNING and self.is_real_time_enabled:
            try:
                analysis_start = datetime.now(timezone.utc)
                
                # Get symbols to analyze
                symbols = list(self.market_data_cache.keys())
                
                if symbols:
                    # Process analyses in parallel
                    await self._process_symbol_analyses(symbols)
                
                # Clean up expired data
                await self._cleanup_expired_data()
                
                # Calculate processing time
                processing_time = (datetime.now(timezone.utc) - analysis_start).total_seconds()
                
                # Update statistics
                await self._update_analysis_stats(processing_time)
                
                # Wait for next analysis cycle
                await asyncio.sleep(self.config.analysis_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("分析循环错误", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _process_symbol_analyses(self, symbols: List[str]):
        """Process analysis for multiple symbols concurrently"""
        # Limit concurrent analyses
        semaphore = asyncio.Semaphore(self.config.max_concurrent_analyses)
        
        async def process_symbol(symbol: str):
            async with semaphore:
                try:
                    await self.analyze_market_data(symbol, self.market_data_cache[symbol])
                except Exception as e:
                    logger.error("符号分析失败", symbol=symbol, error=str(e))
        
        # Run analyses concurrently
        await asyncio.gather(*[process_symbol(symbol) for symbol in symbols])
    
    async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive market analysis for a symbol"""
        analysis_start = datetime.now(timezone.utc)
        
        try:
            logger.debug("开始市场数据分析", symbol=symbol)
            
            # Update cache
            self.market_data_cache[symbol] = {
                **market_data,
                "last_updated": datetime.now(timezone.utc)
            }
            
            # Run analyses in parallel
            market_insight, signal_insight = await asyncio.gather(
                self.market_analyzer.analyze_market(market_data),
                self.signal_analyzer.analyze_signals(market_data)
            )
            
            # Generate insights if enabled
            insights = []
            if self.config.enable_insights:
                insights = await self.insight_generator.generate_comprehensive_insights(market_data)
            
            # Compile results
            analysis_result = {
                "symbol": symbol,
                "analysis_timestamp": analysis_start.isoformat(),
                "processing_time": (datetime.now(timezone.utc) - analysis_start).total_seconds(),
                "market_insight": {
                    "trend_direction": market_insight.trend_direction.value,
                    "confidence": float(market_insight.confidence),
                    "market_regime": market_insight.regime.value,
                    "key_factors": market_insight.key_factors,
                    "prediction": market_insight.prediction
                },
                "signal_insight": {
                    "primary_signal": signal_insight.primary_signal.value,
                    "signal_strength": signal_insight.signal_strength.value,
                    "quality": signal_insight.quality.value,
                    "confidence": float(signal_insight.confidence),
                    "entry_points": {k: float(v) for k, v in signal_insight.entry_points.items()},
                    "exit_points": {k: float(v) for k, v in signal_insight.exit_points.items()},
                    "supporting_indicators": signal_insight.supporting_indicators,
                    "conflicting_indicators": signal_insight.conflicting_indicators
                },
                "insights": [
                    {
                        "insight_id": insight.insight_id,
                        "type": insight.insight_type.value,
                        "priority": insight.priority.value,
                        "title": insight.title,
                        "summary": insight.summary,
                        "confidence": float(insight.confidence),
                        "recommendations": insight.recommendations,
                        "tags": insight.tags
                    }
                    for insight in insights
                ],
                "overall_confidence": float(min(market_insight.confidence, signal_insight.confidence))
            }
            
            # Store results
            self.analysis_results[symbol] = analysis_result
            self.insights_cache[symbol] = insights
            
            # Update performance if enabled
            if self.config.performance_tracking_enabled:
                await self._update_performance_tracking(symbol, analysis_result)
            
            # Trigger callbacks
            await self._trigger_analysis_complete_callbacks(symbol, analysis_result)
            
            if insights:
                await self._trigger_insight_generated_callbacks(symbol, insights)
            
            # Check for alerts
            await self._check_alerts(symbol, analysis_result, insights)
            
            logger.debug("市场数据分析完成", 
                        symbol=symbol,
                        confidence=analysis_result["overall_confidence"],
                        insights_count=len(insights))
            
            return analysis_result
            
        except Exception as e:
            logger.error("市场数据分析失败", symbol=symbol, error=str(e))
            self.analysis_stats["failed_analyses"] += 1
            raise e
    
    async def _update_performance_tracking(self, symbol: str, analysis_result: Dict[str, Any]):
        """Update performance tracking for an entity"""
        try:
            # Extract performance metrics from analysis
            performance_data = {
                "trades": [],  # Would be populated from actual trade data
                "metrics": {
                    "total_return": analysis_result["overall_confidence"],  # Using confidence as proxy
                    "win_rate": 0.6,  # Placeholder
                    "sharpe_ratio": 1.2,  # Placeholder
                    "max_drawdown": 0.1  # Placeholder
                }
            }
            
            await self.performance_analyzer.analyze_performance(
                entity_id=symbol,
                entity_type="symbol",
                performance_data=performance_data
            )
            
        except Exception as e:
            logger.warning("性能跟踪更新失败", symbol=symbol, error=str(e))
    
    async def _check_alerts(self, symbol: str, analysis_result: Dict[str, Any], 
                          insights: List[GeneratedInsight]):
        """Check for alert conditions"""
        try:
            alerts = []
            
            # Low confidence alert
            overall_confidence = analysis_result["overall_confidence"]
            if overall_confidence < float(self.config.alert_thresholds["confidence"]):
                alerts.append({
                    "type": "low_confidence",
                    "symbol": symbol,
                    "message": f"{symbol} 分析置信度过低 ({overall_confidence:.2%})",
                    "severity": "medium"
                })
            
            # High volatility alert
            market_insight = analysis_result.get("market_insight", {})
            if "prediction" in market_insight:
                predicted_change = float(market_insight["prediction"].get("price_prediction", {}).get("change_percent", 0))
                if abs(predicted_change) > 10:  # 10% predicted change
                    alerts.append({
                        "type": "high_volatility",
                        "symbol": symbol,
                        "message": f"{symbol} 预测价格变化过大 ({predicted_change:.2f}%)",
                        "severity": "high"
                    })
            
            # Critical insights alert
            for insight in insights:
                if insight.priority.value in ["critical", "high"]:
                    alerts.append({
                        "type": "critical_insight",
                        "symbol": symbol,
                        "message": f"发现{insight.priority.value}级别洞察: {insight.title}",
                        "severity": insight.priority.value
                    })
            
            # Trigger alert callbacks
            for alert in alerts:
                await self._trigger_alert_callbacks(alert)
            
        except Exception as e:
            logger.warning("警报检查失败", symbol=symbol, error=str(e))
    
    async def _cleanup_expired_data(self):
        """Clean up expired cache data"""
        current_time = datetime.now(timezone.utc)
        expiry_threshold = current_time - timedelta(minutes=self.config.cache_expiry_minutes)
        
        # Clean market data cache
        expired_symbols = []
        for symbol, data in self.market_data_cache.items():
            last_updated = data.get("last_updated")
            if last_updated and last_updated < expiry_threshold:
                expired_symbols.append(symbol)
        
        for symbol in expired_symbols:
            del self.market_data_cache[symbol]
            if symbol in self.analysis_results:
                del self.analysis_results[symbol]
            if symbol in self.insights_cache:
                del self.insights_cache[symbol]
        
        if expired_symbols:
            logger.debug("清理过期数据", count=len(expired_symbols))
    
    async def _update_analysis_stats(self, processing_time: float):
        """Update analysis statistics"""
        self.analysis_stats["total_analyses"] += 1
        self.analysis_stats["successful_analyses"] += 1
        self.analysis_stats["last_analysis_time"] = datetime.now(timezone.utc)
        
        # Update average processing time
        current_avg = self.analysis_stats["processing_time_avg"]
        total_analyses = self.analysis_stats["total_analyses"]
        self.analysis_stats["processing_time_avg"] = (
            (current_avg * (total_analyses - 1) + processing_time) / total_analyses
        )
        
        # Update average confidence
        if self.analysis_results:
            confidences = [
                result["overall_confidence"] 
                for result in self.analysis_results.values()
            ]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                self.analysis_stats["average_confidence"] = Decimal(str(avg_confidence))
    
    async def _trigger_analysis_complete_callbacks(self, symbol: str, result: Dict[str, Any]):
        """Trigger analysis complete callbacks"""
        for callback in self.analysis_complete_callbacks:
            try:
                await callback(symbol, result)
            except Exception as e:
                logger.warning("分析完成回调失败", error=str(e))
    
    async def _trigger_insight_generated_callbacks(self, symbol: str, insights: List[GeneratedInsight]):
        """Trigger insight generated callbacks"""
        for callback in self.insight_generated_callbacks:
            try:
                await callback(symbol, insights)
            except Exception as e:
                logger.warning("洞察生成回调失败", error=str(e))
    
    async def _trigger_alert_callbacks(self, alert: Dict[str, Any]):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.warning("警报回调失败", error=str(e))
    
    async def get_analysis_results(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get analysis results for symbols"""
        if symbol:
            return self.analysis_results.get(symbol, {})
        else:
            return self.analysis_results
    
    async def get_insights(self, symbol: Optional[str] = None, 
                         insight_type: Optional[str] = None,
                         priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get generated insights with optional filtering"""
        all_insights = []
        
        # Collect all insights
        for symbol_insights in self.insights_cache.values():
            all_insights.extend(symbol_insights)
        
        # Apply filters
        if symbol:
            all_insights = [i for i in all_insights if i.entity_id == symbol]
        
        if insight_type:
            all_insights = [i for i in all_insights if i.insight_type.value == insight_type]
        
        if priority:
            all_insights = [i for i in all_insights if i.priority.value == priority]
        
        # Sort by timestamp (most recent first)
        all_insights.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "insight_id": insight.insight_id,
                "type": insight.insight_type.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "summary": insight.summary,
                "description": insight.description,
                "confidence": float(insight.confidence),
                "recommendations": insight.recommendations,
                "entity_id": insight.entity_id,
                "timestamp": insight.timestamp.isoformat(),
                "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
                "tags": insight.tags
            }
            for insight in all_insights
        ]
    
    async def get_performance_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for a symbol"""
        if not self.performance_analyzer:
            return None
        
        return await self.performance_analyzer.get_performance_summary(symbol)
    
    async def get_market_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market summary for a symbol"""
        if not self.market_analyzer:
            return None
        
        return await self.market_analyzer.get_market_summary(symbol)
    
    async def get_signal_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get signal summary for a symbol"""
        if not self.signal_analyzer:
            return None
        
        return await self.signal_analyzer.get_signal_summary(symbol)
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis engine statistics"""
        return {
            "status": self.status.value,
            "is_real_time_enabled": self.is_real_time_enabled,
            "stats": {
                "total_analyses": self.analysis_stats["total_analyses"],
                "successful_analyses": self.analysis_stats["successful_analyses"],
                "failed_analyses": self.analysis_stats["failed_analyses"],
                "success_rate": (
                    self.analysis_stats["successful_analyses"] / 
                    max(1, self.analysis_stats["total_analyses"])
                ),
                "average_confidence": float(self.analysis_stats["average_confidence"]),
                "average_processing_time": self.analysis_stats["processing_time_avg"],
                "last_analysis_time": (
                    self.analysis_stats["last_analysis_time"].isoformat() 
                    if self.analysis_stats["last_analysis_time"] else None
                )
            },
            "cache_info": {
                "cached_symbols": len(self.market_data_cache),
                "analysis_results": len(self.analysis_results),
                "insights_cache": len(self.insights_cache)
            }
        }
    
    def add_analysis_complete_callback(self, callback: Callable):
        """Add callback for analysis completion"""
        self.analysis_complete_callbacks.append(callback)
    
    def add_insight_generated_callback(self, callback: Callable):
        """Add callback for insight generation"""
        self.insight_generated_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alerts"""
        self.alert_callbacks.append(callback)
    
    async def clear_cache(self, symbol: Optional[str] = None):
        """Clear analysis cache"""
        if symbol:
            # Clear specific symbol data
            if symbol in self.market_data_cache:
                del self.market_data_cache[symbol]
            if symbol in self.analysis_results:
                del self.analysis_results[symbol]
            if symbol in self.insights_cache:
                del self.insights_cache[symbol]
            
            # Clear analyzer-specific caches
            if self.market_analyzer:
                self.market_analyzer.clear_cache(symbol)
            if self.signal_analyzer:
                self.signal_analyzer.clear_signals(symbol)
            if self.performance_analyzer:
                self.performance_analyzer.clear_performance_data(symbol)
        else:
            # Clear all caches
            self.market_data_cache.clear()
            self.analysis_results.clear()
            self.insights_cache.clear()
            
            # Clear analyzer caches
            if self.market_analyzer:
                self.market_analyzer.clear_cache()
            if self.signal_analyzer:
                self.signal_analyzer.clear_signals()
            if self.performance_analyzer:
                self.performance_analyzer.clear_performance_data()
        
        logger.info("清除分析缓存", symbol=symbol or "all")
    
    async def update_config(self, new_config: Dict[str, Any]):
        """Update analysis engine configuration"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        logger.info("更新分析引擎配置", new_config=new_config)