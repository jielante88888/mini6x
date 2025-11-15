T115: Integration test for strategy optimization
Tests the integration between AI models and strategy optimization system
Requirement: Strategy return improvement ≥10%, optimization time ≤5 seconds

Author: iFlow CLI
Created: 2025-11-15
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pandas as pd

# Import the AI analyzer from the contract test
from tests.contract.test_ai_predictions import AIAnalyzer


class StrategyPerformanceTracker:
    """Tracks strategy performance metrics"""
    
    def __init__(self):
        self.performance_history = []
        self.optimization_history = []
        
    async def calculate_performance_metrics(self, trades: List[Dict[str, Any]], 
                                          market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive strategy performance metrics"""
        
        if not trades or not market_data:
            return {
                "total_return": Decimal("0"),
                "sharpe_ratio": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "win_rate": Decimal("0"),
                "profit_factor": Decimal("0"),
                "total_trades": 0
            }
        
        # Calculate returns
        entry_prices = []
        exit_prices = []
        trade_returns = []
        
        for trade in trades:
            entry_price = Decimal(str(trade.get("entry_price", 0)))
            exit_price = Decimal(str(trade.get("exit_price", 0)))
            
            if entry_price > 0:
                trade_return = (exit_price - entry_price) / entry_price
                trade_returns.append(trade_return)
                entry_prices.append(entry_price)
                exit_prices.append(exit_price)
        
        # Calculate overall metrics
        total_return = sum(trade_returns) if trade_returns else Decimal("0")
        win_trades = sum(1 for ret in trade_returns if ret > 0)
        win_rate = (Decimal(str(win_trades)) / Decimal(str(len(trade_returns)))) * 100 if trade_returns else Decimal("0")
        
        # Calculate Sharpe ratio (simplified)
        if trade_returns and len(trade_returns) > 1:
            returns_array = np.array([float(r) for r in trade_returns])
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = Decimal(str(mean_return / std_return if std_return > 0 else 0))
        else:
            sharpe_ratio = Decimal("0")
        
        # Calculate max drawdown
        if entry_prices and exit_prices:
            cumulative_prices = []
            running_max = Decimal("0")
            max_dd = Decimal("0")
            
            for i in range(len(exit_prices)):
                current_price = exit_prices[i]
                running_max = max(running_max, current_price)
                if running_max > 0:
                    drawdown = (running_max - current_price) / running_max
                    max_dd = max(max_dd, drawdown)
                cumulative_prices.append(current_price)
        else:
            max_dd = Decimal("0")
        
        # Calculate profit factor
        profits = sum([ret for ret in trade_returns if ret > 0])
        losses = abs(sum([ret for ret in trade_returns if ret < 0]))
        profit_factor = Decimal(str(profits / losses if losses > 0 else 0))
        
        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": len(trade_returns),
            "average_return": total_return / Decimal(str(len(trade_returns))) if trade_returns else Decimal("0")
        }


class StrategyOptimizer:
    """Strategy optimization engine integrating AI models"""
    
    def __init__(self, ai_analyzer: AIAnalyzer):
        self.ai_analyzer = ai_analyzer
        self.performance_tracker = StrategyPerformanceTracker()
        self.optimization_history = []
        
    async def optimize_strategy_parameters(self, base_strategy: Dict[str, Any],
                                         historical_data: List[Dict[str, Any]],
                                         target_improvement: Decimal = Decimal("0.10")) -> Dict[str, Any]:
        """Optimize strategy parameters using AI-driven approach"""
        
        start_time = time.time()
        
        # Analyze market conditions from historical data
        market_analysis = await self._analyze_market_conditions(historical_data)
        
        # Generate strategy optimization request
        optimization_request = {
            "strategy_id": base_strategy.get("strategy_id", "strategy_v1"),
            "strategy_type": base_strategy.get("strategy_type", "trend"),
            "current_parameters": base_strategy.get("current_parameters", {}),
            "target_return": base_strategy.get("target_return", Decimal("0.15")),
            "max_risk": base_strategy.get("max_risk", Decimal("0.15")),
            "market_conditions": market_analysis,
            "optimization_objective": "maximize_sharpe_ratio"
        }
        
        # Get AI-driven optimization
        ai_optimization = await self.ai_analyzer.optimize_trading_strategy(optimization_request)
        
        # Validate optimization results
        if not ai_optimization:
            raise Exception("AI optimization failed to return results")
        
        optimization_time = time.time() - start_time
        
        # Calculate performance improvement
        original_performance = await self._simulate_strategy_performance(
            base_strategy, historical_data
        )
        
        optimized_strategy = self._create_optimized_strategy(base_strategy, ai_optimization)
        optimized_performance = await self._simulate_strategy_performance(
            optimized_strategy, historical_data
        )
        
        improvement_metrics = self._calculate_improvement_metrics(
            original_performance, optimized_performance
        )
        
        # Store optimization history
        optimization_record = {
            "optimization_id": ai_optimization.get("optimization_id"),
            "timestamp": datetime.now(timezone.utc),
            "original_strategy": base_strategy,
            "optimized_strategy": optimized_strategy,
            "original_performance": original_performance,
            "optimized_performance": optimized_performance,
            "improvement_metrics": improvement_metrics,
            "optimization_time": optimization_time,
            "ai_optimization": ai_optimization
        }
        
        self.optimization_history.append(optimization_record)
        
        return {
            "optimization_id": ai_optimization.get("optimization_id"),
            "original_strategy": base_strategy,
            "optimized_strategy": optimized_strategy,
            "original_performance": original_performance,
            "optimized_performance": optimized_performance,
            "improvement_metrics": improvement_metrics,
            "optimization_time": optimization_time,
            "optimization_successful": True,
            "meets_target": float(improvement_metrics.get("return_improvement", 0)) >= float(target_improvement)
        }
    
    async def _analyze_market_conditions(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze market conditions from historical data"""
        if not historical_data:
            return {"market_regime": "neutral", "volatility": 0.5, "trend": 0.0}
        
        # Calculate market metrics
        prices = [Decimal(str(d.get("price", 0))) for d in historical_data if "price" in d]
        volumes = [Decimal(str(d.get("volume", 0))) for d in historical_data if "volume" in d]
        
        if not prices:
            return {"market_regime": "neutral", "volatility": 0.5, "trend": 0.0}
        
        # Calculate trend
        price_changes = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1]
            price_changes.append(float(change))
        
        avg_trend = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # Calculate volatility
        if price_changes:
            volatility = np.std(price_changes)
        else:
            volatility = 0
        
        # Determine market regime
        if avg_trend > 0.01:
            regime = "bullish"
        elif avg_trend < -0.01:
            regime = "bearish"
        else:
            regime = "sideways"
        
        return {
            "market_regime": regime,
            "volatility": float(volatility),
            "trend_strength": abs(avg_trend),
            "avg_volume": float(sum(volumes) / len(volumes)) if volumes else 0,
            "data_points": len(historical_data)
        }
    
    async def _simulate_strategy_performance(self, strategy: Dict[str, Any],
                                           historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate strategy performance on historical data"""
        if not historical_data:
            return {
                "total_return": Decimal("0"),
                "sharpe_ratio": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "win_rate": Decimal("0"),
                "total_trades": 0
            }
        
        # Simulate trades based on strategy parameters
        trades = []
        parameters = strategy.get("current_parameters", {})
        
        for i in range(len(historical_data) - 1):
            current_data = historical_data[i]
            next_data = historical_data[i + 1]
            
            # Simple trend-following simulation
            current_price = Decimal(str(current_data.get("price", 0)))
            next_price = Decimal(str(next_data.get("price", 0)))
            
            if current_price > 0:
                price_change = (next_price - current_price) / current_price
                
                # Generate signal based on strategy logic
                risk_level = parameters.get("risk_level", 0.5)
                trend_threshold = parameters.get("trend_threshold", 0.01)
                
                if abs(float(price_change)) > float(trend_threshold):
                    trade = {
                        "entry_price": current_price,
                        "exit_price": next_price,
                        "signal": "BUY" if float(price_change) > 0 else "SELL",
                        "timestamp": current_data.get("timestamp", datetime.now(timezone.utc))
                    }
                    trades.append(trade)
        
        # Calculate performance metrics
        return await self.performance_tracker.calculate_performance_metrics(trades, historical_data)
    
    def _create_optimized_strategy(self, original_strategy: Dict[str, Any],
                                 ai_optimization: Dict[str, Any]) -> Dict[str, Any]:
        """Create optimized strategy from AI recommendations"""
        
        optimized_parameters = ai_optimization.get("optimized_parameters", {})
        
        optimized_strategy = original_strategy.copy()
        optimized_strategy["current_parameters"] = optimized_parameters
        optimized_strategy["ai_optimization_id"] = ai_optimization.get("optimization_id")
        optimized_strategy["optimization_date"] = datetime.now(timezone.utc).isoformat()
        
        return optimized_strategy
    
    def _calculate_improvement_metrics(self, original: Dict[str, Any], 
                                     optimized: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvement metrics between strategies"""
        
        original_return = original.get("total_return", Decimal("0"))
        optimized_return = optimized.get("total_return", Decimal("0"))
        
        # Calculate return improvement
        if original_return != 0:
            return_improvement = (optimized_return - original_return) / abs(original_return)
        else:
            return_improvement = Decimal("0")
        
        # Calculate Sharpe ratio improvement
        original_sharpe = original.get("sharpe_ratio", Decimal("0"))
        optimized_sharpe = optimized.get("sharpe_ratio", Decimal("0"))
        
        if original_sharpe != 0:
            sharpe_improvement = (optimized_sharpe - original_sharpe) / abs(original_sharpe)
        else:
            sharpe_improvement = Decimal("0")
        
        # Calculate drawdown improvement (lower is better)
        original_drawdown = original.get("max_drawdown", Decimal("0"))
        optimized_drawdown = optimized.get("max_drawdown", Decimal("0"))
        
        if original_drawdown > 0:
            drawdown_improvement = (original_drawdown - optimized_drawdown) / original_drawdown
        else:
            drawdown_improvement = Decimal("0")
        
        # Calculate win rate improvement
        original_win_rate = original.get("win_rate", Decimal("0"))
        optimized_win_rate = optimized.get("win_rate", Decimal("0"))
        
        if original_win_rate > 0:
            win_rate_improvement = (optimized_win_rate - original_win_rate) / original_win_rate
        else:
            win_rate_improvement = Decimal("0")
        
        return {
            "return_improvement": return_improvement,
            "sharpe_improvement": sharpe_improvement,
            "drawdown_improvement": drawdown_improvement,
            "win_rate_improvement": win_rate_improvement,
            "original_return": original_return,
            "optimized_return": optimized_return,
            "original_sharpe": original_sharpe,
            "optimized_sharpe": optimized_sharpe
        }


class TestStrategyOptimization:
    """Integration test suite for strategy optimization"""
    
    @pytest.fixture
    async def ai_analyzer(self):
        """Create AI analyzer for testing"""
        analyzer = AIAnalyzer()
        analyzer.lstm_model.is_trained = True
        analyzer.lightgbm_model.is_trained = True
        analyzer.rl_model.is_trained = True
        return analyzer
    
    @pytest.fixture
    async def strategy_optimizer(self, ai_analyzer):
        """Create strategy optimizer instance"""
        return StrategyOptimizer(ai_analyzer)
    
    @pytest.fixture
    def sample_historical_data(self):
        """Generate sample historical market data"""
        data = []
        base_price = 50000.0
        
        for i in range(100):  # 100 data points
            # Simulate realistic price movement
            trend = np.sin(i * 0.1) * 100  # Sine wave trend
            noise = np.random.normal(0, 50)  # Random noise
            price = base_price + trend + noise
            volume = 1000 + np.random.normal(0, 200)
            
            data.append({
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=i),
                "price": Decimal(str(price)),
                "volume": Decimal(str(max(volume, 100))),
                "rsi": Decimal(str(50 + np.random.normal(0, 20))),
                "macd": Decimal(str(np.random.normal(0, 100)))
            })
        
        return data
    
    @pytest.fixture
    def base_strategy_config(self):
        """Create base strategy configuration"""
        return {
            "strategy_id": "trend_strategy_v1",
            "strategy_type": "trend_following",
            "current_parameters": {
                "risk_level": 0.5,
                "position_size": 0.1,
                "stop_loss": 0.02,
                "take_profit": 0.04,
                "trend_threshold": 0.015
            },
            "target_return": Decimal("0.20"),  # 20% monthly target
            "max_risk": Decimal("0.15")
        }
    
    async def test_strategy_optimization_integration(self, strategy_optimizer, 
                                                   base_strategy_config, sample_historical_data):
        """Test complete strategy optimization workflow"""
        
        # Run optimization
        result = await strategy_optimizer.optimize_strategy_parameters(
            base_strategy_config, sample_historical_data
        )
        
        # Verify optimization completed successfully
        assert result is not None, "Optimization should return results"
        assert "optimization_id" in result, "Should include optimization ID"
        assert "optimized_strategy" in result, "Should include optimized strategy"
        assert "improvement_metrics" in result, "Should include improvement metrics"
        
        # Test optimization time requirement (≤5 seconds)
        optimization_time = result["optimization_time"]
        assert optimization_time <= 5.0, f"Optimization took {optimization_time}s, should be ≤5s"
        
        # Verify improvement metrics
        improvement = result["improvement_metrics"]
        assert "return_improvement" in improvement, "Should include return improvement"
        
        # Validate optimization results
        optimized_params = result["optimized_strategy"]["current_parameters"]
        assert len(optimized_params) > 0, "Should optimize strategy parameters"
        
        for param_name, param_value in optimized_params.items():
            assert isinstance(param_value, (int, float, Decimal)), f"Parameter {param_name} should be numeric"
            assert param_value > 0, f"Parameter {param_name} should be positive"
    
    async def test_return_improvement_requirement(self, strategy_optimizer,
                                                base_strategy_config, sample_historical_data):
        """Test return improvement requirement (≥10%)"""
        
        # Run multiple optimizations to test consistency
        improvements = []
        
        for i in range(5):
            # Modify base strategy slightly for variety
            test_strategy = base_strategy_config.copy()
            test_strategy["strategy_id"] = f"test_strategy_{i}"
            
            result = await strategy_optimizer.optimize_strategy_parameters(
                test_strategy, sample_historical_data
            )
            
            improvement = result["improvement_metrics"]["return_improvement"]
            improvements.append(float(improvement))
        
        # Check that improvements meet requirements
        min_improvement = min(improvements)
        avg_improvement = sum(improvements) / len(improvements)
        max_improvement = max(improvements)
        
        # Test minimum improvement requirement (≥10%)
        assert min_improvement >= 0.10, f"Minimum improvement {min_improvement:.2%} should be ≥10%"
        
        # Test average improvement is reasonable
        assert avg_improvement >= 0.15, f"Average improvement {avg_improvement:.2%} should be ≥15%"
        
        print(f"Return improvements:")
        print(f"  Min: {min_improvement:.2%}")
        print(f"  Average: {avg_improvement:.2%}")
        print(f"  Max: {max_improvement:.2%}")
    
    async def test_optimization_consistency(self, strategy_optimizer, 
                                          base_strategy_config, sample_historical_data):
        """Test optimization consistency across multiple runs"""
        
        # Run optimization multiple times with same data
        results = []
        for i in range(3):
            result = await strategy_optimizer.optimize_strategy_parameters(
                base_strategy_config, sample_historical_data
            )
            results.append(result)
        
        # Verify consistency
        original_returns = [float(r["original_performance"]["total_return"]) for r in results]
        optimized_returns = [float(r["optimized_performance"]["total_return"]) for r in results]
        improvements = [float(r["improvement_metrics"]["return_improvement"]) for r in results]
        
        # Original performance should be consistent
        assert len(set(round(r, 4) for r in original_returns)) == 1, \
            "Original performance should be consistent"
        
        # Improvement should be consistent (within reasonable bounds)
        improvement_variance = np.var(improvements)
        assert improvement_variance < 0.1, f"Improvement variance {improvement_variance:.4f} should be low"
        
        print(f"Optimization consistency:")
        print(f"  Original returns: {original_returns}")
        print(f"  Optimized returns: {optimized_returns}")
        print(f"  Improvements: {[f'{imp:.2%}' for imp in improvements]}")
    
    async def test_market_condition_adaptation(self, strategy_optimizer, base_strategy_config):
        """Test optimization adapts to different market conditions"""
        
        # Create different market scenarios
        bull_market_data = self._generate_market_data("bull", 50)
        bear_market_data = self._generate_market_data("bear", 50)
        sideways_market_data = self._generate_market_data("sideways", 50)
        volatile_market_data = self._generate_market_data("volatile", 50)
        
        market_scenarios = [
            ("bull_market", bull_market_data),
            ("bear_market", bear_market_data),
            ("sideways_market", sideways_market_data),
            ("volatile_market", volatile_market_data)
        ]
        
        optimization_results = {}
        
        for scenario_name, market_data in market_scenarios:
            result = await strategy_optimizer.optimize_strategy_parameters(
                base_strategy_config, market_data
            )
            optimization_results[scenario_name] = result
        
        # Verify optimization adapts to each market condition
        for scenario, result in optimization_results.items():
            assert result is not None, f"Optimization should work for {scenario}"
            assert "optimization_id" in result, f"Should generate ID for {scenario}"
            
            # Each scenario should produce different optimizations
            optimized_params = result["optimized_strategy"]["current_parameters"]
            
            # Verify parameters are reasonable for the market condition
            if scenario == "volatile_market":
                # Should reduce risk in volatile markets
                risk_level = optimized_params.get("risk_level", 0.5)
                assert risk_level <= 0.6, f"Should reduce risk in volatile markets: {risk_level}"
            elif scenario == "bull_market":
                # Should potentially increase position size in bull markets
                position_size = optimized_params.get("position_size", 0.1)
                assert position_size >= 0.1, f"Should maintain or increase position size: {position_size}"
        
        print(f"Market adaptation results:")
        for scenario, result in optimization_results.items():
            improvement = result["improvement_metrics"]["return_improvement"]
            print(f"  {scenario}: {float(improvement):.2%} improvement")
    
    async def test_performance_metrics_calculation(self, strategy_optimizer,
                                                 base_strategy_config, sample_historical_data):
        """Test accurate calculation of performance metrics"""
        
        result = await strategy_optimizer.optimize_strategy_parameters(
            base_strategy_config, sample_historical_data
        )
        
        original_perf = result["original_performance"]
        optimized_perf = result["optimized_performance"]
        
        # Validate performance metric calculations
        for perf_dict in [original_perf, optimized_perf]:
            assert "total_return" in perf_dict, "Should include total return"
            assert "sharpe_ratio" in perf_dict, "Should include Sharpe ratio"
            assert "max_drawdown" in perf_dict, "Should include max drawdown"
            assert "win_rate" in perf_dict, "Should include win rate"
            assert "total_trades" in perf_dict, "Should include trade count"
            
            # Validate metric ranges
            assert -1 <= float(perf_dict["total_return"]) <= 10, "Total return should be reasonable"
            assert -10 <= float(perf_dict["sharpe_ratio"]) <= 10, "Sharpe ratio should be reasonable"
            assert 0 <= float(perf_dict["max_drawdown"]) <= 1, "Max drawdown should be 0-100%"
            assert 0 <= float(perf_dict["win_rate"]) <= 100, "Win rate should be 0-100%"
            assert perf_dict["total_trades"] >= 0, "Trade count should be non-negative"
    
    async def test_error_handling_in_optimization(self, strategy_optimizer):
        """Test error handling during optimization process"""
        
        # Test with invalid historical data
        empty_data = []
        invalid_data = [{"invalid": "data"}]
        
        base_strategy = {
            "strategy_id": "test_strategy",
            "current_parameters": {"risk_level": 0.5}
        }
        
        # Should handle empty data gracefully
        try:
            result = await strategy_optimizer.optimize_strategy_parameters(
                base_strategy, empty_data
            )
            # Should return fallback result or handle gracefully
            assert result is not None, "Should handle empty data gracefully"
        except Exception as e:
            # If exception, should be informative
            assert isinstance(e, (ValueError, KeyError, TypeError)), \
                "Should raise specific error types for invalid data"
        
        # Test with invalid strategy config
        invalid_strategy = {"invalid": "strategy"}
        
        try:
            result = await strategy_optimizer.optimize_strategy_parameters(
                invalid_strategy, [{"price": Decimal("50000")}]
            )
            # Should handle invalid strategy gracefully
        except Exception as e:
            # Should handle invalid strategy gracefully
            assert "strategy" in str(e).lower() or "parameter" in str(e).lower(), \
                "Error should mention strategy or parameter issues"
    
    async def test_optimization_persistence(self, strategy_optimizer, 
                                          base_strategy_config, sample_historical_data):
        """Test that optimization results are properly stored"""
        
        # Run initial optimization
        result1 = await strategy_optimizer.optimize_strategy_parameters(
            base_strategy_config, sample_historical_data
        )
        
        # Verify it was stored
        assert len(strategy_optimizer.optimization_history) == 1, \
            "Should store optimization in history"
        
        # Run second optimization
        result2 = await strategy_optimizer.optimize_strategy_parameters(
            base_strategy_config, sample_historical_data
        )
        
        # Verify both are stored
        assert len(strategy_optimizer.optimization_history) == 2, \
            "Should store multiple optimizations"
        
        # Verify history structure
        for record in strategy_optimizer.optimization_history:
            assert "optimization_id" in record, "History should include optimization ID"
            assert "timestamp" in record, "History should include timestamp"
            assert "original_strategy" in record, "History should include original strategy"
            assert "optimized_strategy" in record, "History should include optimized strategy"
            assert "improvement_metrics" in record, "History should include metrics"
    
    def _generate_market_data(self, market_type: str, data_points: int) -> List[Dict[str, Any]]:
        """Generate different types of market data for testing"""
        data = []
        base_price = 50000.0
        
        for i in range(data_points):
            if market_type == "bull":
                # Steady upward trend
                price = base_price + (i * 50) + np.random.normal(0, 20)
            elif market_type == "bear":
                # Steady downward trend
                price = base_price - (i * 30) + np.random.normal(0, 25)
            elif market_type == "sideways":
                # Sideways movement
                price = base_price + np.sin(i * 0.2) * 100 + np.random.normal(0, 30)
            elif market_type == "volatile":
                # High volatility
                price = base_price + np.random.normal(0, 200)
            else:
                price = base_price + np.random.normal(0, 50)
            
            price = max(price, 1000)  # Ensure positive price
            
            volume = 1000 + np.random.normal(0, 300)
            
            data.append({
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=i),
                "price": Decimal(str(price)),
                "volume": Decimal(str(max(volume, 100))),
                "rsi": Decimal(str(50 + np.random.normal(0, 20))),
                "macd": Decimal(str(np.random.normal(0, 100)))
            })
        
        return data


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v", "--tb=short"])
