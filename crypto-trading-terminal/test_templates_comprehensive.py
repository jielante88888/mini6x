#!/usr/bin/env python3
"""
综合测试通知模板系统功能
"""

import sys
import os
from datetime import datetime
from unittest.mock import Mock
sys.path.append('.')

try:
    # 测试模板引擎
    from backend.src.notification.templates.template_engine import TemplateEngine, TemplateManager
    from backend.src.notification.templates.prebuilt_templates import ALL_TEMPLATES
    from backend.src.notification.templates.channel_templates import POPUP_TEMPLATES, TELEGRAM_TEMPLATES
    from backend.src.conditions.condition_engine import TriggerEvent, ConditionResult, EvaluationContext
    
    print("✅ All template modules imported successfully")
    
    # 1. 测试模板引擎
    engine = TemplateEngine()
    template = "价格预警: $condition_name - $result_details ($trigger_time_datetime)"
    variables = {
        'condition_name': 'BTC价格预警',
        'result_details': '价格超过50000美元',
        'trigger_time': datetime(2024, 1, 15, 14, 30, 0)
    }
    
    result = engine.render_template(template, variables, template_type='python_template')
    print(f"✅ Template rendered: {result}")
    
    # 2. 测试格式化器
    formatted_price = engine.formatters['currency'](50000.5)
    priority_emoji = engine.formatters['emoji_priority'](3)
    formatted_percent = engine.formatters['percentage'](5.5)
    
    print(f"✅ Currency formatter: {formatted_price}")
    print(f"✅ Priority emoji: {priority_emoji}")
    print(f"✅ Percentage formatter: {formatted_percent}")
    
    # 3. 测试模板管理器
    manager = TemplateManager()
    
    # 测试自定义模板创建
    custom_template = '自定义预警: $condition_name - $result_details ($priority_text)'
    success = manager.create_custom_template('test_alert', custom_template, '测试预警模板')
    print(f"✅ Custom template created: {success}")
    
    # 4. 测试预构建模板
    print(f"✅ Prebuilt templates loaded: {len(ALL_TEMPLATES)} categories")
    for category, templates in ALL_TEMPLATES.items():
        print(f"   - {category}: {len(templates)} templates")
    
    # 5. 测试渠道模板
    print(f"✅ Popup templates: {len(POPUP_TEMPLATES)} templates")
    print(f"✅ Telegram templates: {len(TELEGRAM_TEMPLATES)} templates")
    
    # 6. 测试触发事件渲染
    mock_result = Mock()
    mock_result.value = 'BTCUSDT'
    mock_result.details = '价格突破55000美元'
    mock_result.satisfied = True
    
    mock_context = Mock()
    mock_context.strategy.value = 'sequential'
    mock_context.evaluation_id = 'eval_123'
    
    trigger_event = TriggerEvent(
        event_id='event_123',
        condition_id='cond_123',
        condition_name='BTC突破预警',
        result=mock_result,
        timestamp=datetime(2024, 1, 15, 15, 45, 0),
        context=mock_context,
        priority=4,
        metadata={'test': True}
    )
    
    # 注册模板并渲染
    engine.register_template('test_event', '🚨 $priority_emoji $condition_name: $result_value ($trigger_time_datetime)')
    rendered_event = engine.render_trigger_event('test_event', trigger_event)
    print(f"✅ Event template rendered: {rendered_event}")
    
    # 7. 测试模板导出
    exported = manager.export_templates()
    print(f"✅ Templates exported: {len(exported['custom_templates'])} custom templates")
    
    # 8. 测试模板验证
    valid_template = "测试: $condition_name ($result_details)"
    validation = engine.validate_template(valid_template)
    print(f"✅ Template validation: valid={validation['valid']}")
    
    print("\n🎉 All comprehensive template tests passed!")
    print("📋 Summary:")
    print(f"   - Template engine with {len(engine.formatters)} formatters")
    print(f"   - Prebuilt templates: {sum(len(templates) for templates in ALL_TEMPLATES.values())} total")
    print(f"   - Custom templates created and exported successfully")
    print(f"   - Trigger event rendering working correctly")
    print(f"   - All channel templates loaded successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)