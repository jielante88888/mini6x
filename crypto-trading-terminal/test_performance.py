#!/usr/bin/env python3
"""
简单的性能测试运行器
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_basic_functionality():
    """测试基本功能"""
    try:
        from backend.src.conditions.base_conditions import MarketData, ConditionOperator
        from backend.src.conditions.price_conditions import PriceCondition, PriceType
        from backend.src.conditions.condition_engine import ConditionEngine
        
        print("✓ 所有必要的模块导入成功")
        
        # 创建测试数据
        market_data = MarketData(
            symbol="BTCUSDT",
            price=50000.0,
            volume_24h=1000000.0,
            price_change_24h=2500.0,
            price_change_percent_24h=5.0,
            high_24h=52000.0,
            low_24h=48000.0,
            timestamp=None
        )
        
        if market_data.timestamp is None:
            from datetime import datetime
            market_data.timestamp = datetime.now()
        
        print("✓ 市场数据创建成功")
        
        # 创建条件引擎
        engine = ConditionEngine()
        print("✓ 条件引擎创建成功")
        
        # 启动引擎
        await engine.start()
        print("✓ 条件引擎启动成功")
        
        # 创建条件
        condition = PriceCondition(
            symbol="BTCUSDT",
            price_type=PriceType.CURRENT_PRICE,  # 需要指定价格类型
            operator=ConditionOperator.GREATER_THAN,
            threshold=49000.0
        )
        
        condition_id = engine.register_condition(condition)
        print(f"✓ 条件注册成功，ID: {condition_id}")
        
        # 测试评估
        trigger_events = await engine.evaluate_all(market_data)
        print(f"✓ 条件评估成功，触发事件数量: {len(trigger_events)}")
        
        # 停止引擎
        await engine.stop()
        print("✓ 条件引擎停止成功")
        
        print("\n所有基本功能测试通过！性能测试T057可以运行。")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_basic_functionality())
    if success:
        print("\n🎉 性能测试准备就绪！")
        sys.exit(0)
    else:
        print("\n💥 需要修复问题后才能运行性能测试")
        sys.exit(1)
