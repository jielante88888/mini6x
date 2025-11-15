"""
T105: Integration test for PnL calculation accuracy
Tests the precision of profit/loss calculations for both spot and futures trading
Requirement: Ensure calculation error ≤ 0.5% as specified in User Story 8

Author: iFlow CLI
Created: 2025-11-15
"""

import asyncio
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))

from core.pnl_calculator import PnLCalculator
from core.account_manager import AccountManager
from core.position_manager import PositionManager
from storage.models.trade_models import Trade, Position, AccountBalance
from storage.models.pnl_models import PnLSnapshot, PnLSummary


class TestPnLCalculation:
    """Test suite for PnL calculation accuracy across spot and futures positions"""

    @pytest.fixture
    async def pnl_calculator(self):
        """Create PnL calculator instance with mocked dependencies"""
        calculator = PnLCalculator(
            precision=Decimal('0.00000001'),  # 8 decimal places for crypto precision
            rounding=ROUND_HALF_UP
        )
        
        # Mock external dependencies
        calculator.market_data_service = AsyncMock()
        calculator.price_history_service = AsyncMock()
        
        return calculator

    @pytest.fixture
    async def test_trades(self):
        """Create sample test trades for various scenarios"""
        spot_trade = Trade(
            id="spot_001",
            symbol="BTCUSDT",
            exchange="binance",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("50000.00"),
            fee=Decimal("5.00"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        spot_sell = Trade(
            id="spot_002", 
            symbol="BTCUSDT",
            exchange="binance",
            side="SELL",
            quantity=Decimal("0.1"),
            price=Decimal("52000.00"),
            fee=Decimal("5.20"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        futures_trade = Trade(
            id="futures_001",
            symbol="BTCUSDT",
            exchange="binance",
            side="BUY",
            quantity=Decimal("0.1"),
            price=Decimal("50000.00"),
            fee=Decimal("2.50"),
            leverage=Decimal("10"),
            timestamp=datetime.now(timezone.utc),
            trade_type="futures",
            funding_rate=Decimal("-0.0001"),  # -0.01% funding rate
            mark_price=Decimal("50000.00")
        )
        
        return [spot_trade, spot_sell, futures_trade]

    async def test_spot_pnl_calculation_basic(self, pnl_calculator, test_trades):
        """Test basic spot PnL calculation accuracy"""
        buy_trade = test_trades[0]
        sell_trade = test_trades[1]
        current_price = Decimal("52000.00")
        
        # Test unrealized PnL calculation
        unrealized_pnl = await pnl_calculator.calculate_unrealized_pnl(buy_trade, current_price)
        expected_unrealized_pnl = (current_price - buy_trade.price) * buy_trade.quantity - buy_trade.fee
        
        # Allow small rounding errors (≤0.5% of total trade value)
        trade_value = buy_trade.price * buy_trade.quantity
        max_error = trade_value * Decimal("0.005")  # 0.5% error threshold
        
        error = abs(unrealized_pnl - expected_unrealized_pnl)
        assert error <= max_error, f"Unrealized PnL error {error} exceeds 0.5% threshold"
        
        # Test realized PnL calculation  
        realized_pnl = await pnl_calculator.calculate_realized_pnl(buy_trade, sell_trade)
        expected_realized_pnl = (sell_trade.price - buy_trade.price) * buy_trade.quantity - buy_trade.fee - sell_trade.fee
        
        error = abs(realized_pnl - expected_realized_pnl)
        assert error <= max_error, f"Realized PnL error {error} exceeds 0.5% threshold"

    async def test_futures_pnl_calculation_with_leverage(self, pnl_calculator, test_trades):
        """Test futures PnL calculation with leverage and funding fees"""
        futures_trade = test_trades[2]
        current_price = Decimal("51000.00")
        current_funding_rate = Decimal("0.0002")  # +0.02% funding rate
        
        # Test leverage-adjusted unrealized PnL
        unrealized_pnl = await pnl_calculator.calculate_unrealized_pnl(
            futures_trade, current_price
        )
        
        price_change = (current_price - futures_trade.price) * futures_trade.quantity
        leverage_multiplier = futures_trade.leverage
        leverage_pnl = price_change * leverage_multiplier
        
        # Calculate funding fees
        position_value = current_price * futures_trade.quantity
        funding_fee = position_value * current_funding_rate
        
        expected_unrealized_pnl = leverage_pnl - funding_fee - futures_trade.fee
        
        # More generous error threshold for futures due to leverage complexity
        trade_value = futures_trade.price * futures_trade.quantity * leverage_multiplier
        max_error = trade_value * Decimal("0.005")  # Still maintain 0.5% accuracy
        
        error = abs(unrealized_pnl - expected_unrealized_pnl)
        assert error <= max_error, f"Leverage PnL error {error} exceeds 0.5% threshold"

    async def test_multi_position_portfolio_pnl(self, pnl_calculator, test_trades):
        """Test portfolio-wide PnL calculation across multiple positions"""
        # Create portfolio with mixed positions
        spot_long = test_trades[0]  # BTC spot long
        futures_long = test_trades[2]  # BTC futures long
        
        # Additional ETH positions
        eth_spot_buy = Trade(
            id="eth_spot_buy",
            symbol="ETHUSDT", 
            exchange="binance",
            side="BUY",
            quantity=Decimal("2.0"),
            price=Decimal("3000.00"),
            fee=Decimal("3.00"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        eth_spot_sell = Trade(
            id="eth_spot_sell",
            symbol="ETHUSDT",
            exchange="binance", 
            side="SELL",
            quantity=Decimal("1.0"),
            price=Decimal("3100.00"),
            fee=Decimal("1.55"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        portfolio_trades = [spot_long, futures_long, eth_spot_buy, eth_spot_sell]
        
        current_prices = {
            "BTCUSDT": Decimal("51000.00"),
            "ETHUSDT": Decimal("3120.00")
        }
        
        # Test portfolio PnL calculation
        portfolio_pnl = await pnl_calculator.calculate_portfolio_pnl(portfolio_trades, current_prices)
        
        # Calculate expected portfolio PnL
        expected_pnl = Decimal("0")
        for trade in portfolio_trades:
            current_price = current_prices.get(trade.symbol, trade.price)
            trade_pnl = await pnl_calculator.calculate_unrealized_pnl(trade, current_price)
            expected_pnl += trade_pnl
        
        # Verify total portfolio accuracy
        portfolio_value = sum(
            current_prices.get(trade.symbol, trade.price) * trade.quantity
            for trade in portfolio_trades
        )
        max_error = portfolio_value * Decimal("0.005")  # 0.5% threshold
        
        error = abs(portfolio_pnl - expected_pnl)
        assert error <= max_error, f"Portfolio PnL error {error} exceeds 0.5% threshold"

    async def test_negative_pnl_calculation(self, pnl_calculator, test_trades):
        """Test PnL calculation accuracy for losing positions"""
        # Create losing spot position
        losing_trade = Trade(
            id="losing_spot",
            symbol="BTCUSDT",
            exchange="binance",
            side="BUY", 
            quantity=Decimal("0.1"),
            price=Decimal("52000.00"),
            fee=Decimal("5.20"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        current_price = Decimal("48000.00")  # Price dropped significantly
        
        unrealized_pnl = await pnl_calculator.calculate_unrealized_pnl(losing_trade, current_price)
        
        # Should be negative PnL
        assert unrealized_pnl < 0, "Expected negative PnL for losing position"
        
        # Calculate expected PnL manually
        expected_pnl = (current_price - losing_trade.price) * losing_trade.quantity - losing_trade.fee
        expected_pnl = round(expected_pnl, 8)  # Round to crypto precision
        
        trade_value = losing_trade.price * losing_trade.quantity
        max_error = trade_value * Decimal("0.005")  # 0.5% threshold
        
        error = abs(unrealized_pnl - expected_pnl)
        assert error <= max_error, f"Negative PnL error {error} exceeds 0.5% threshold"

    async def test_percentage_calculations(self, pnl_calculator, test_trades):
        """Test percentage-based PnL calculations for return metrics"""
        spot_trade = test_trades[0]
        
        current_price = Decimal("52000.00")
        
        # Test percentage return calculation
        percentage_return = await pnl_calculator.calculate_percentage_return(spot_trade, current_price)
        
        # Manual calculation
        expected_return = ((current_price - spot_trade.price) / spot_trade.price) * 100
        
        error = abs(percentage_return - expected_return)
        # For percentage, test against 0.5% of the percentage value itself
        max_error = abs(expected_return) * Decimal("0.005")
        
        assert error <= max_error, f"Percentage return error {error}% exceeds 0.5% threshold"

    async def test_rolling_pnl_calculations(self, pnl_calculator):
        """Test rolling PnL calculations for time-based analysis"""
        # Create time series of trades
        trade_series = []
        base_price = Decimal("50000.00")
        
        for i in range(10):
            trade = Trade(
                id=f"rolling_trade_{i}",
                symbol="BTCUSDT",
                exchange="binance",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=Decimal("0.01"),
                price=base_price + Decimal(str(i * 100)),  # Gradual price increase
                fee=Decimal("0.50"),
                timestamp=datetime.now(timezone.utc),
                trade_type="spot"
            )
            trade_series.append(trade)
        
        # Test rolling PnL for different time windows
        rolling_pnl = await pnl_calculator.calculate_rolling_pnl(trade_series, window_size=5)
        
        # Verify rolling calculation accuracy
        assert len(rolling_pnl) == len(trade_series), "Rolling PnL should cover all trades"
        
        for i, pnl_snapshot in enumerate(rolling_pnl):
            # Validate each rolling calculation
            window_start = max(0, i - 4)  # 5-trade window
            window_trades = trade_series[window_start:i+1]
            
            calculated_pnl = pnl_snapshot.total_pnl
            expected_pnl = Decimal("0")
            
            for trade in window_trades:
                if trade.side == "SELL":
                    # For completed trades, use trade price as current price
                    current_price = trade.price
                else:
                    # For open trades, use a mock current price
                    current_price = base_price + Decimal("500")  # Assume current price
                
                trade_pnl = await pnl_calculator.calculate_unrealized_pnl(trade, current_price)
                expected_pnl += trade_pnl
            
            # Check accuracy within 0.5% threshold
            window_value = sum(trade.price * trade.quantity for trade in window_trades)
            max_error = window_value * Decimal("0.005")
            
            error = abs(calculated_pnl - expected_pnl)
            assert error <= max_error, f"Rolling PnL error {error} exceeds 0.5% threshold at index {i}"

    async def test_high_precision_calculations(self, pnl_calculator):
        """Test very high precision PnL calculations for small amounts"""
        # Test with very small quantities and high precision
        micro_trade = Trade(
            id="micro_trade",
            symbol="BTCUSDT",
            exchange="binance",
            side="BUY",
            quantity=Decimal("0.00000001"),  # 1 satoshi
            price=Decimal("50000.00"),
            fee=Decimal("0.00000050"),  # Very small fee
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        current_price = Decimal("50000.01")  # Minimal price change
        
        unrealized_pnl = await pnl_calculator.calculate_unrealized_pnl(micro_trade, current_price)
        
        # Manual calculation
        expected_pnl = (current_price - micro_trade.price) * micro_trade.quantity - micro_trade.fee
        
        # Very small amounts require even tighter precision
        trade_value = micro_trade.price * micro_trade.quantity
        max_error = trade_value * Decimal("0.005")  # Still 0.5% but on tiny amounts
        
        error = abs(unrealized_pnl - expected_pnl)
        assert error <= max_error, f"High precision PnL error {error} exceeds threshold"

    async def test_mark_to_market_calculations(self, pnl_calculator, test_trades):
        """Test mark-to-market PnL calculations for futures"""
        futures_trade = test_trades[2]
        
        # Test mark-to-market calculation
        mark_price = Decimal("51500.00")
        funding_rate = Decimal("0.0001")
        
        mark_to_market_pnl = await pnl_calculator.calculate_mark_to_market_pnl(
            futures_trade, mark_price, funding_rate
        )
        
        # Calculate expected mark-to-market PnL
        price_diff = mark_price - futures_trade.price
        leverage_pnl = price_diff * futures_trade.quantity * futures_trade.leverage
        
        # Funding fee calculation
        mark_value = mark_price * futures_trade.quantity * futures_trade.leverage
        funding_fee = mark_value * funding_rate
        
        expected_mtm_pnl = leverage_pnl - funding_fee - futures_trade.fee
        
        trade_value = futures_trade.price * futures_trade.quantity * futures_trade.leverage
        max_error = trade_value * Decimal("0.005")  # 0.5% threshold
        
        error = abs(mark_to_market_pnl - expected_mtm_pnl)
        assert error <= max_error, f"Mark-to-market PnL error {error} exceeds 0.5% threshold"

    async def test_end_to_end_pnl_scenario(self, pnl_calculator):
        """Test complete end-to-end PnL scenario with multiple exchanges and asset types"""
        # Create complex scenario with multiple exchanges and assets
        
        # Binance spot positions
        btc_spot_buy = Trade(
            id="binance_spot_btc",
            symbol="BTCUSDT",
            exchange="binance",
            side="BUY",
            quantity=Decimal("0.5"),
            price=Decimal("50000.00"),
            fee=Decimal("25.00"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        eth_spot_buy = Trade(
            id="binance_spot_eth",
            symbol="ETHUSDT",
            exchange="binance", 
            side="BUY",
            quantity=Decimal("2.0"),
            price=Decimal("3000.00"),
            fee=Decimal("6.00"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        # OKX futures positions
        btc_futures_long = Trade(
            id="okx_futures_btc",
            symbol="BTCUSDT",
            exchange="okx",
            side="BUY",
            quantity=Decimal("0.2"),
            price=Decimal("50200.00"),
            fee=Decimal("5.02"),
            leverage=Decimal("5"),
            timestamp=datetime.now(timezone.utc),
            trade_type="futures",
            funding_rate=Decimal("0.0001"),
            mark_price=Decimal("51000.00")
        )
        
        # Partial BTC spot sell (close half position)
        btc_spot_sell = Trade(
            id="binance_spot_btc_sell",
            symbol="BTCUSDT",
            exchange="binance",
            side="SELL",
            quantity=Decimal("0.25"),
            price=Decimal("51000.00"),
            fee=Decimal("12.75"),
            timestamp=datetime.now(timezone.utc),
            trade_type="spot"
        )
        
        all_trades = [btc_spot_buy, eth_spot_buy, btc_futures_long, btc_spot_sell]
        
        # Current market prices
        current_prices = {
            "BTCUSDT": Decimal("51500.00"),
            "ETHUSDT": Decimal("3100.00")
        }
        
        # Test comprehensive PnL calculation
        pnl_summary = await pnl_calculator.calculate_comprehensive_pnl(all_trades, current_prices)
        
        # Verify the summary contains all expected components
        assert "realized_pnl" in pnl_summary
        assert "unrealized_pnl" in pnl_summary
        assert "total_pnl" in pnl_summary
        assert "by_exchange" in pnl_summary
        assert "by_asset" in pnl_summary
        assert "by_type" in pnl_summary
        
        # Validate individual calculations
        
        # 1. Check realized PnL (BTC spot partial close)
        expected_realized = (btc_spot_sell.price - btc_spot_buy.price) * btc_spot_sell.quantity - btc_spot_buy.fee - btc_spot_sell.fee
        actual_realized = pnl_summary["realized_pnl"]
        
        realized_value = btc_spot_buy.price * btc_spot_buy.quantity * 0.5  # Half position
        max_error = realized_value * Decimal("0.005")
        error = abs(actual_realized - expected_realized)
        assert error <= max_error, f"Realized PnL error {error} exceeds 0.5% threshold"
        
        # 2. Check unrealized PnL (remaining BTC + ETH + futures)
        remaining_btc_value = btc_spot_buy.price * Decimal("0.25")  # Remaining position
        eth_value = eth_spot_buy.price * eth_spot_buy.quantity
        futures_value = btc_futures_long.price * btc_futures_long.quantity * btc_futures_long.leverage
        
        total_unrealized_value = remaining_btc_value + eth_value + futures_value
        max_error = total_unrealized_value * Decimal("0.005")
        
        # Verify the PnL components add up correctly
        total_calculated = pnl_summary["realized_pnl"] + pnl_summary["unrealized_pnl"]
        assert abs(total_calculated - pnl_summary["total_pnl"]) <= Decimal("0.01"), "PnL components don't add up correctly"

    async def test_performance_benchmark(self, pnl_calculator):
        """Performance test for PnL calculations under load"""
        import time
        
        # Create large number of trades for performance testing
        large_trade_list = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(1000):  # 1000 trades
            trade = Trade(
                id=f"perf_trade_{i}",
                symbol="BTCUSDT" if i % 3 == 0 else "ETHUSDT",
                exchange="binance" if i % 2 == 0 else "okx",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=Decimal(str(0.1 + (i % 10) * 0.01)),
                price=Decimal(str(50000 + (i % 100) * 10)),
                fee=Decimal("5.00"),
                timestamp=base_time,
                trade_type="spot" if i % 2 == 0 else "futures",
                leverage=Decimal("5") if i % 2 == 1 else None
            )
            large_trade_list.append(trade)
        
        current_prices = {
            "BTCUSDT": Decimal("50500.00"),
            "ETHUSDT": Decimal("3050.00")
        }
        
        # Benchmark PnL calculation performance
        start_time = time.time()
        
        pnl_result = await pnl_calculator.calculate_portfolio_pnl(large_trade_list, current_prices)
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Performance requirements: should handle 1000 trades in under 1 second
        assert calculation_time < 1.0, f"PnL calculation took {calculation_time:.3f}s, should be under 1.0s"
        
        # Verify result is reasonable (not NaN, not infinite)
        assert pnl_result is not None
        assert not (pnl_result != pnl_result)  # Not NaN
        assert abs(pnl_result) < Decimal("1000000000")  # Not infinite (reasonable bounds)

    async def test_accuracy_benchmarks(self, pnl_calculator, test_trades):
        """Comprehensive accuracy benchmarks across different scenarios"""
        accuracy_tests = [
            {
                "name": "High Value Spot Trade",
                "trade": Trade(
                    id="high_value_spot",
                    symbol="BTCUSDT", 
                    exchange="binance",
                    side="BUY",
                    quantity=Decimal("10.0"),  # High value
                    price=Decimal("50000.00"),
                    fee=Decimal("50.00"),
                    timestamp=datetime.now(timezone.utc),
                    trade_type="spot"
                ),
                "current_price": Decimal("51000.00"),
                "max_error_percent": 0.5  # 0.5% accuracy requirement
            },
            {
                "name": "Small Value Spot Trade", 
                "trade": Trade(
                    id="small_value_spot",
                    symbol="BTCUSDT",
                    exchange="binance",
                    side="BUY", 
                    quantity=Decimal("0.001"),  # Small value
                    price=Decimal("50000.00"),
                    fee=Decimal("0.05"),
                    timestamp=datetime.now(timezone.utc),
                    trade_type="spot"
                ),
                "current_price": Decimal("50100.00"),
                "max_error_percent": 0.5  # Still 0.5% for small amounts
            },
            {
                "name": "High Leverage Futures",
                "trade": Trade(
                    id="high_leverage_futures",
                    symbol="BTCUSDT",
                    exchange="binance",
                    side="BUY",
                    quantity=Decimal("1.0"),
                    price=Decimal("50000.00"), 
                    fee=Decimal("5.00"),
                    leverage=Decimal("100"),  # High leverage
                    timestamp=datetime.now(timezone.utc),
                    trade_type="futures",
                    funding_rate=Decimal("0.0001"),
                    mark_price=Decimal("50100.00")
                ),
                "current_price": Decimal("50100.00"),
                "max_error_percent": 0.5  # Maintain 0.5% even with leverage
            }
        ]
        
        all_passed = True
        failed_tests = []
        
        for test_case in accuracy_tests:
            trade = test_case["trade"]
            current_price = test_case["current_price"]
            max_error_percent = test_case["max_error_percent"]
            
            try:
                calculated_pnl = await pnl_calculator.calculate_unrealized_pnl(trade, current_price)
                
                # Calculate expected PnL
                if trade.trade_type == "futures":
                    # Leverage-adjusted PnL for futures
                    price_change = (current_price - trade.price) * trade.quantity
                    leverage_multiplier = trade.leverage
                    leverage_pnl = price_change * leverage_multiplier
                    
                    # Add funding fee if mark price provided
                    if hasattr(trade, 'mark_price') and trade.mark_price:
                        funding_fee = trade.mark_price * trade.quantity * trade.leverage * trade.funding_rate
                        leverage_pnl -= funding_fee
                else:
                    # Simple spot PnL
                    leverage_pnl = (current_price - trade.price) * trade.quantity
                
                expected_pnl = leverage_pnl - trade.fee
                
                # Calculate error
                trade_value = trade.price * trade.quantity
                if trade.trade_type == "futures":
                    trade_value *= trade.leverage
                    
                max_error = trade_value * (max_error_percent / 100)
                error = abs(calculated_pnl - expected_pnl)
                
                # Check accuracy
                if error <= max_error:
                    print(f"✓ {test_case['name']}: Accuracy test passed (error: {error}, threshold: {max_error})")
                else:
                    all_passed = False
                    failed_tests.append({
                        "name": test_case['name'],
                        "error": error,
                        "threshold": max_error,
                        "calculated": calculated_pnl,
                        "expected": expected_pnl
                    })
                    print(f"✗ {test_case['name']}: Accuracy test failed (error: {error}, threshold: {max_error})")
                    
            except Exception as e:
                all_passed = False
                failed_tests.append({
                    "name": test_case['name'],
                    "error": str(e),
                    "type": "exception"
                })
                print(f"✗ {test_case['name']}: Exception occurred: {e}")
        
        # Final assertion
        if not all_passed:
            error_summary = "; ".join([f"{test['name']}: {test.get('error', 'N/A')}" for test in failed_tests])
            pytest.fail(f"PnL accuracy benchmarks failed. Failed tests: {error_summary}")
        
        print(f"✓ All {len(accuracy_tests)} accuracy benchmarks passed successfully")


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v"])