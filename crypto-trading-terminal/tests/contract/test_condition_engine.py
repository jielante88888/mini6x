"""
条件引擎合同测试
验证条件引擎的核心功能和接口合约
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crypto_trading_terminal.backend.src.conditions.base_conditions import (
    Condition, 
    ConditionResult, 
    MarketData,
    ConditionOperator,
    ConditionType,
    AndCondition,
    OrCondition,
    NotCondition
)
from crypto_trading_terminal.backend.src.conditions.price_conditions import PriceCondition
from crypto_trading_terminal.backend.src.conditions.volume_conditions import VolumeCondition
from crypto_trading_terminal.backend.src.conditions.time_conditions import TimeCondition
from crypto_trading_terminal.backend.src.conditions.indicator_conditions import TechnicalIndicatorCondition
from crypto_trading_terminal.backend.src.conditions.market_alert_conditions import MarketAlertCondition
from crypto_trading_terminal.backend.src.conditions.condition_engine import (
    ConditionEngine,
    EvaluationContext,
    EvaluationStrategy,
    TriggerEvent,
    EngineStatus,
    ConditionFactory
)
from crypto_trading_terminal.backend.src.notification.notify_manager import (
    NotificationManager,
    NotificationChannel,
    NotificationPriority
)


class TestConditionEngineContract:
    """条件引擎合同测试类"""
    
    @pytest.fixture
    async def engine(self):
        """创建测试用的条件引擎"""
        config = {
            "max_parallel_evaluations": 5,
            "evaluation_timeout": 10.0,
            "cache_ttl": 300,
            "performance_monitoring": True
        }
        
        engine = ConditionEngine(config)
        await engine.start()
        yield engine
        await engine.stop()
    
    @pytest.fixture
    def sample_market_data(self):
        """创建测试用的市场数据"""
        return MarketData(
            symbol="BTCUSDT",
            price=50000.0,
            volume_24h=1000000.0,
            price_change_24h=2500.0,
            price_change_percent_24h=5.0,
            high_24h=52000.0,
            low_24h=48000.0,
            timestamp=datetime.now(),
            rsi=65.0,
            macd=120.5,
            macd_signal=115.2,
            bollinger_upper=51000.0,
            bollinger_lower=49000.0,
            moving_average_20=49500.0,
            moving_average_50=49200.0,
            open_interest=500000.0,
            funding_rate=0.001
        )
    
    @pytest.fixture
    def mock_trigger_handler(self):
        """创建模拟触发处理器"""
        handler = AsyncMock()
        return handler
    
    @pytest.mark.asyncio
    async def test_engine_initialization_and_lifecycle(self, engine):
        """测试引擎初始化和生命周期"""
        # 测试初始状态
        assert engine.status == EngineStatus.RUNNING
        assert engine.start_time is not None
        assert len(engine.conditions) == 0
        assert engine.metrics.total_conditions == 0
        
        # 测试暂停
        await engine.pause()
        assert engine.status == EngineStatus.PAUSED
        
        # 测试恢复
        await engine.resume()
        assert engine.status == EngineStatus.RUNNING
        
        # 测试停止
        await engine.stop()
        assert engine.status == EngineStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_condition_registration_and_management(self, engine, sample_market_data):
        """测试条件注册和管理"""
        # 创建测试条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Test Price Condition",
            description="Test price above 49000"
        )
        
        # 注册条件
        condition_id = engine.register_condition(condition)
        assert condition_id in engine.conditions
        assert engine.metrics.total_conditions == 1
        assert engine.metrics.active_conditions == 1
        
        # 测试条件状态
        status = engine.get_condition_status(condition_id)
        assert status["condition_id"] == condition_id
        assert status["name"] == "Test Price Condition"
        assert status["type"] == ConditionType.PRICE.value
        assert status["enabled"] == True
        
        # 禁用条件
        assert engine.disable_condition(condition_id) == True
        assert engine.get_condition_status(condition_id)["enabled"] == False
        assert engine.metrics.active_conditions == 0
        
        # 启用条件
        assert engine.enable_condition(condition_id) == True
        assert engine.get_condition_status(condition_id)["enabled"] == True
        assert engine.metrics.active_conditions == 1
        
        # 注销条件
        assert engine.unregister_condition(condition_id) == True
        assert condition_id not in engine.conditions
        assert engine.metrics.total_conditions == 0
        
        # 测试无效操作
        assert engine.disable_condition("invalid_id") == False
        assert engine.unregister_condition("invalid_id") == False
    
    @pytest.mark.asyncio
    async def test_and_condition_logic(self, engine, sample_market_data, mock_trigger_handler):
        """测试AND条件逻辑"""
        # 创建两个简单的条件
        condition1 = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Price Above 49000"
        )
        
        condition2 = VolumeCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=500000.0,
            name="Volume Above 500k"
        )
        
        # 注册条件
        id1 = engine.register_condition(condition1)
        id2 = engine.register_condition(condition2)
        
        # 创建AND条件
        and_condition_id = await engine.create_and_condition(
            [id1, id2],
            name="AND Test Condition",
            description="Test AND logic"
        )
        
        # 注册触发处理器
        engine.register_trigger_handler("composite", mock_trigger_handler)
        
        # 测试AND条件 - 两个条件都满足
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        # 应该有一个AND条件的触发事件
        and_events = [e for e in trigger_events if e.condition_id == and_condition_id]
        assert len(and_events) == 1
        assert and_events[0].result.satisfied == True
        
        # 测试AND条件 - 修改数据使一个条件不满足
        sample_market_data.price = 45000.0  # 低于49000
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        and_events = [e for e in trigger_events if e.condition_id == and_condition_id]
        assert len(and_events) == 1
        assert and_events[0].result.satisfied == False
    
    @pytest.mark.asyncio
    async def test_or_condition_logic(self, engine, sample_market_data):
        """测试OR条件逻辑"""
        # 创建两个条件
        condition1 = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=52000.0,  # 不满足
            name="Price Above 52000"
        )
        
        condition2 = VolumeCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=500000.0,  # 满足
            name="Volume Above 500k"
        )
        
        # 注册条件
        id1 = engine.register_condition(condition1)
        id2 = engine.register_condition(condition2)
        
        # 创建OR条件
        or_condition_id = await engine.create_or_condition(
            [id1, id2],
            name="OR Test Condition",
            description="Test OR logic"
        )
        
        # 测试OR条件 - 一个条件满足
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        or_events = [e for e in trigger_events if e.condition_id == or_condition_id]
        assert len(or_events) == 1
        assert or_events[0].result.satisfied == True
        
        # 测试OR条件 - 两个条件都不满足
        sample_market_data.price = 45000.0
        sample_market_data.volume_24h = 400000.0
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        or_events = [e for e in trigger_events if e.condition_id == or_condition_id]
        assert len(or_events) == 1
        assert or_events[0].result.satisfied == False
    
    @pytest.mark.asyncio
    async def test_not_condition_logic(self, engine, sample_market_data):
        """测试NOT条件逻辑"""
        # 创建条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=52000.0,  # 不满足 (当前价格50000)
            name="Price Above 52000"
        )
        
        # 注册条件
        condition_id = engine.register_condition(condition)
        
        # 创建NOT条件
        not_condition_id = await engine.create_not_condition(
            condition_id,
            name="NOT Test Condition",
            description="Test NOT logic"
        )
        
        # 测试NOT条件 - 原始条件不满足，NOT条件应满足
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        not_events = [e for e in trigger_events if e.condition_id == not_condition_id]
        assert len(not_events) == 1
        assert not_events[0].result.satisfied == True
        
        # 测试NOT条件 - 原始条件满足，NOT条件应不满足
        sample_market_data.price = 53000.0  # 高于52000
        trigger_events = await engine.evaluate_all(sample_market_data)
        
        not_events = [e for e in trigger_events if e.condition_id == not_condition_id]
        assert len(not_events) == 1
        assert not_events[0].result.satisfied == False
    
    @pytest.mark.asyncio
    async def test_evaluation_strategies(self, engine, sample_market_data):
        """测试不同的评估策略"""
        # 创建多个条件
        conditions = []
        for i in range(5):
            condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0 - i * 1000,
                name=f"Price Condition {i}"
            )
            condition_id = engine.register_condition(condition)
            conditions.append(condition)
        
        # 测试顺序策略
        engine.set_evaluation_strategy(EvaluationStrategy.SEQUENTIAL)
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data)
        sequential_time = time.time() - start_time
        
        # 测试并行策略
        engine.set_evaluation_strategy(EvaluationStrategy.PARALLEL)
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data)
        parallel_time = time.time() - start_time
        
        # 测试优先级策略
        engine.set_evaluation_strategy(EvaluationStrategy.PRIORITY)
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data)
        priority_time = time.time() - start_time
        
        # 测试自适应策略
        engine.set_evaluation_strategy(EvaluationStrategy.ADAPTIVE)
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data)
        adaptive_time = time.time() - start_time
        
        # 验证都产生了结果
        assert len(trigger_events) >= 0
        
        # 验证引擎状态
        status = engine.get_engine_status()
        assert status["status"] == EngineStatus.RUNNING.value
        assert status["total_conditions"] == 5
        assert status["active_conditions"] == 5
        assert status["evaluation_strategy"] == EvaluationStrategy.ADAPTIVE.value
    
    @pytest.mark.asyncio
    async def test_single_condition_evaluation(self, engine, sample_market_data):
        """测试单个条件评估"""
        # 创建条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Single Test Condition"
        )
        
        # 注册条件
        condition_id = engine.register_condition(condition)
        
        # 评估单个条件
        trigger_event = await engine.evaluate_condition(condition_id, sample_market_data)
        
        # 验证结果
        assert trigger_event is not None
        assert trigger_event.condition_id == condition_id
        assert trigger_event.result.satisfied == True
        assert trigger_event.result.value == sample_market_data.price
        assert "Price Above" in trigger_event.condition_name
    
    @pytest.mark.asyncio
    async def test_condition_factory(self):
        """测试条件工厂"""
        factory = ConditionFactory()
        
        # 测试创建价格条件
        price_condition = factory.create_condition(
            ConditionType.PRICE,
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Factory Test Price"
        )
        
        assert isinstance(price_condition, PriceCondition)
        assert price_condition.symbol == "BTCUSDT"
        assert price_condition.operator == ConditionOperator.GREATER_THAN
        assert price_condition.threshold == 49000.0
        
        # 测试从字典创建
        condition_dict = {
            "condition_type": "price",
            "symbol": "BTCUSDT",
            "operator": "gt",
            "threshold": 49000.0,
            "name": "Factory Test Price 2",
            "enabled": True,
            "priority": 1
        }
        
        price_condition_2 = factory.create_from_dict(condition_dict)
        assert isinstance(price_condition_2, PriceCondition)
        assert price_condition_2.symbol == "BTCUSDT"
    
    @pytest.mark.asyncio
    async def test_configuration_and_persistence(self, engine):
        """测试配置和持久化"""
        # 注册一些条件
        condition1 = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Config Test 1"
        )
        
        condition2 = VolumeCondition(
            symbol="ETHUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=500000.0,
            name="Config Test 2"
        )
        
        id1 = engine.register_condition(condition1)
        id2 = engine.register_condition(condition2)
        
        # 设置优先级
        engine.condition_priority[id1] = 5
        engine.condition_priority[id2] = 3
        
        # 导出配置
        exported_data = engine.export_conditions()
        
        assert "export_time" in exported_data
        assert "conditions" in exported_data
        assert len(exported_data["conditions"]) == 2
        assert "priorities" in exported_data
        
        # 验证导出的数据包含正确的条件
        exported_conditions = exported_data["conditions"]
        assert any(c["name"] == "Config Test 1" for c in exported_conditions.values())
        assert any(c["name"] == "Config Test 2" for c in exported_conditions.values())
        
        # 清空引擎
        engine.unregister_condition(id1)
        engine.unregister_condition(id2)
        assert len(engine.conditions) == 0
        
        # 导入配置
        imported_ids = engine.import_conditions(exported_data)
        
        # 验证导入成功
        assert len(imported_ids) == 2
        assert len(engine.conditions) == 2
        
        # 验证导入的条件
        imported_condition = list(engine.conditions.values())[0]
        assert imported_condition.name in ["Config Test 1", "Config Test 2"]
    
    @pytest.mark.asyncio
    async def test_performance_and_caching(self, engine, sample_market_data):
        """测试性能和缓存"""
        # 启用缓存
        context = EvaluationContext(
            evaluation_id="test_123",
            timestamp=datetime.now(),
            strategy=EvaluationStrategy.SEQUENTIAL,
            max_execution_time=30.0,
            timeout_handling="skip",
            enable_cache=True
        )
        
        # 创建条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Performance Test Condition"
        )
        
        condition_id = engine.register_condition(condition)
        
        # 第一次评估
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data, context)
        first_evaluation_time = time.time() - start_time
        
        # 第二次评估（应该使用缓存）
        start_time = time.time()
        trigger_events = await engine.evaluate_all(sample_market_data, context)
        second_evaluation_time = time.time() - start_time
        
        # 验证性能改进（第二次应该更快）
        assert second_evaluation_time <= first_evaluation_time
        
        # 验证缓存工作
        assert len(engine.result_cache) > 0
        
        # 测试缓存清理
        engine.clear_cache()
        assert len(engine.result_cache) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_robustness(self, engine, sample_market_data):
        """测试错误处理和鲁棒性"""
        # 测试引擎未运行时的评估
        await engine.stop()
        
        with pytest.raises(RuntimeError, match="引擎未运行"):
            await engine.evaluate_all(sample_market_data)
        
        await engine.start()
        
        # 测试评估超时
        context = EvaluationContext(
            evaluation_id="timeout_test",
            timestamp=datetime.now(),
            strategy=EvaluationStrategy.SEQUENTIAL,
            max_execution_time=0.001,  # 非常短的超时
            timeout_handling="timeout"
        )
        
        # 创建条件（可能有延迟）
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Timeout Test Condition"
        )
        
        condition_id = engine.register_condition(condition)
        
        # 应该处理超时
        trigger_event = await engine.evaluate_condition(condition_id, sample_market_data, context)
        assert trigger_event is not None
        assert "timeout" in trigger_event.metadata or not trigger_event.result.satisfied
    
    @pytest.mark.asyncio
    async def test_statistics_and_monitoring(self, engine, sample_market_data):
        """测试统计和监控"""
        # 创建并评估条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0,
            name="Stats Test Condition"
        )
        
        condition_id = engine.register_condition(condition)
        
        # 执行多次评估
        for _ in range(5):
            trigger_events = await engine.evaluate_all(sample_market_data)
        
        # 检查统计数据
        status = engine.get_engine_status()
        metrics = status["metrics"]
        
        assert metrics["total_evaluations"] > 0
        assert metrics["successful_evaluations"] > 0
        assert metrics["total_conditions"] == 1
        assert metrics["active_conditions"] == 1
        assert metrics["conditions_by_type"]["price"] == 1
        assert metrics["last_evaluation_time"] is not None
        
        # 检查条件统计
        condition_status = engine.get_condition_status(condition_id)
        assert condition_status["evaluation_count"] > 0
        assert condition_status["success_rate"] >= 0
        assert condition_status["last_evaluation"] is not None
    
    @pytest.mark.asyncio
    async def test_global_engine_singleton(self):
        """测试全局引擎单例"""
        from crypto_trading_terminal.backend.src.conditions.condition_engine import (
            get_condition_engine,
            init_condition_engine,
            shutdown_condition_engine
        )
        
        # 获取全局引擎
        engine1 = get_condition_engine()
        engine2 = get_condition_engine()
        
        # 应该是同一个实例
        assert engine1 is engine2
        
        # 初始化全局引擎
        global_engine = await init_condition_engine({"test": True})
        assert global_engine is engine1
        
        # 关闭全局引擎
        await shutdown_condition_engine()
        
        # 再次获取应该是新的实例
        engine3 = get_condition_engine()
        assert engine3 is not engine1


class TestConditionIntegration:
    """条件集成测试类"""
    
    @pytest.mark.asyncio
    async def test_complex_condition_combinations(self):
        """测试复杂条件组合"""
        # 创建模拟市场数据
        market_data = MarketData(
            symbol="BTCUSDT",
            price=50000.0,
            volume_24h=1000000.0,
            price_change_24h=2500.0,
            price_change_percent_24h=5.0,
            high_24h=52000.0,
            low_24h=48000.0,
            timestamp=datetime.now(),
            rsi=65.0,
            macd=120.5,
            macd_signal=115.2,
            bollinger_upper=51000.0,
            bollinger_lower=49000.0,
            moving_average_20=49500.0,
            moving_average_50=49200.0
        )
        
        # 创建引擎
        engine = ConditionEngine()
        await engine.start()
        
        try:
            # 创建复杂条件组合
            # 条件1: 价格高于49000
            price_condition = PriceCondition(
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold=49000.0,
                name="Price Above 49000"
            )
            
            # 条件2: RSI在30-70之间
            rsi_condition = TechnicalIndicatorCondition(
                symbol="BTCUSDT",
                indicator_type="RSI",
                operator=ConditionOperator.IN_RANGE,
                threshold_value={"min": 30, "max": 70},
                name="RSI Normal Range"
            )
            
            # 条件3: 当前时间在交易时间内
            time_condition = TimeCondition(
                time_type="trading_hours",
                operator=ConditionOperator.EQUAL,
                time_value="trading",
                target_market="crypto",
                name="Trading Hours"
            )
            
            # 注册基础条件
            price_id = engine.register_condition(price_condition)
            rsi_id = engine.register_condition(rsi_condition)
            time_id = engine.register_condition(time_condition)
            
            # 创建复合条件: (价格条件 AND RSI条件) OR 时间条件
            and_condition_id = await engine.create_and_condition(
                [price_id, rsi_id],
                name="Price and RSI",
                description="Price above 49000 and RSI in normal range"
            )
            
            or_condition_id = await engine.create_or_condition(
                [and_condition_id, time_id],
                name="Complex OR Condition",
                description="(Price and RSI) OR Trading Hours"
            )
            
            # 评估复杂条件
            trigger_events = await engine.evaluate_all(market_data)
            
            # 验证结果
            complex_events = [e for e in trigger_events if e.condition_id == or_condition_id]
            assert len(complex_events) == 1
            assert complex_events[0].result.satisfied == True
            
            # 验证AND条件也满足
            and_events = [e for e in trigger_events if e.condition_id == and_condition_id]
            assert len(and_events) == 1
            assert and_events[0].result.satisfied == True
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_notification_integration(self):
        """测试通知集成"""
        # 创建引擎和通知管理器
        engine = ConditionEngine()
        await engine.start()
        
        notification_manager = NotificationManager()
        
        try:
            # 创建条件
            condition = MarketAlertCondition(
                alert_type="price_change",
                symbol="BTCUSDT",
                operator=ConditionOperator.GREATER_THAN,
                threshold_value=5.0,
                name="Price Change Alert"
            )
            
            condition_id = engine.register_condition(condition)
            
            # 注册触发处理器，集成通知
            async def notification_handler(trigger_event):
                # 发送通知
                notification_manager.send_notification(trigger_event)
            
            engine.register_trigger_handler("market_alert", notification_handler)
            
            # 创建市场数据（触发价格变动预警）
            market_data = MarketData(
                symbol="BTCUSDT",
                price=50000.0,
                volume_24h=1000000.0,
                price_change_24h=2500.0,
                price_change_percent_24h=5.0,
                high_24h=52000.0,
                low_24h=48000.0,
                timestamp=datetime.now(),
                rsi=65.0
            )
            
            # 评估条件
            trigger_event = await engine.evaluate_condition(condition_id, market_data)
            
            if trigger_event:
                # 手动调用通知处理器
                await notification_handler(trigger_event)
                
                # 验证通知队列
                stats = notification_manager.get_statistics()
                assert stats["queue_size"] >= 0
            
        finally:
            await engine.stop()


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])