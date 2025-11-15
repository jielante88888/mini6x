#!/usr/bin/env python3
"""验证T085测试模块导入"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_import():
    try:
        from tests.integration.test_strategy_performance import TestStrategyPerformanceIntegration
        print("✅ T085策略性能集成测试模块导入成功")
        
        # 检查测试类
        test_instance = TestStrategyPerformanceIntegration()
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        print(f"📋 发现 {len(test_methods)} 个测试方法")
        
        for method in test_methods[:10]:  # 显示前10个
            print(f"  - {method}")
        
        if len(test_methods) > 10:
            print(f"  ... 还有 {len(test_methods) - 10} 个方法")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)