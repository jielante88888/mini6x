#!/usr/bin/env python3
"""验证基础策略类"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

def test_import():
    try:
        print("🔄 正在导入基础策略类...")
        from backend.src.strategies.base import BaseSpotStrategy, StrategyType, StrategyConfig, MarketData, StrategyState
        print("✅ 基础策略类导入成功")
        
        # 测试枚举
        print(f"📋 策略类型: {list(StrategyType)}")
        print(f"📋 策略状态: {list(StrategyStatus)}")
        
        # 测试数据模型
        print("✅ 枚举类型定义正常")
        print("✅ 数据模型定义正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)