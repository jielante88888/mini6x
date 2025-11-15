#!/usr/bin/env python3
"""
简单测试脚本，验证通知模板系统功能
"""

import sys
import os
sys.path.append('.')

try:
    from backend.src.notification.templates.template_engine import TemplateEngine
    print("✅ Template engine imported successfully")
    
    # 创建模板引擎实例
    engine = TemplateEngine()
    print(f"✅ Template engine initialized with {len(engine.formatters)} formatters")
    
    # 测试简单模板渲染
    template = "价格预警: $condition_name - $result_details"
    variables = {
        'condition_name': 'BTC价格预警',
        'result_details': '价格超过50000美元'
    }
    
    result = engine.render_template(template, variables)
    print(f"✅ Simple template rendered: {result}")
    
    # 测试格式化器
    formatted_price = engine.formatters['currency'](50000.5)
    print(f"✅ Currency formatter: {formatted_price}")
    
    priority_emoji = engine.formatters['emoji_priority'](3)
    print(f"✅ Priority emoji: {priority_emoji}")
    
    print("\n🎉 All basic functionality tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()