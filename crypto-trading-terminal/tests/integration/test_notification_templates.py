"""
通知模板系统集成测试
测试模板引擎、预构建模板和渠道特定模板的功能
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from backend.src.notification.templates.template_engine import TemplateEngine, TemplateManager
from backend.src.notification.templates.prebuilt_templates import ALL_TEMPLATES, TEMPLATE_VARIABLES
from backend.src.notification.templates.channel_templates import (
    POPUP_TEMPLATES, DESKTOP_TEMPLATES, TELEGRAM_TEMPLATES, EMAIL_TEMPLATES
)
from backend.src.conditions.condition_engine import TriggerEvent, ConditionResult, EvaluationContext


class TestTemplateEngine:
    """测试模板引擎核心功能"""
    
    @pytest.fixture
    def template_engine(self):
        return TemplateEngine()
    
    def test_template_engine_initialization(self, template_engine):
        """测试模板引擎初始化"""
        assert template_engine is not None
        assert len(template_engine.formatters) > 0
        assert 'upper' in template_engine.formatters
        assert 'datetime' in template_engine.formatters
        assert 'currency' in template_engine.formatters
        assert 'percentage' in template_engine.formatters
    
    def test_register_template(self, template_engine):
        """测试模板注册"""
        template_content = "测试模板: $condition_name ($trigger_time)"
        template_engine.register_template('test_template', template_content)
        
        assert 'test_template' in template_engine.custom_templates
        assert template_engine.custom_templates['test_template'] == template_content
    
    def test_render_simple_template(self, template_engine):
        """测试简单模板渲染"""
        template_content = "预警: $condition_name - $result_details"
        variables = {
            'condition_name': '价格预警',
            'result_details': '价格超过50000美元'
        }
        
        result = template_engine.render_template(template_content, variables)
        expected = "预警: 价格预警 - 价格超过50000美元"
        
        assert result == expected
    
    def test_render_python_template_with_formatters(self, template_engine):
        """测试Python模板渲染（含格式化器）"""
        template_content = "价格: $price_value|upper ($trigger_time|short_datetime)"
        variables = {
            'price_value': 'btcusdt',
            'trigger_time': datetime(2024, 1, 15, 14, 30, 0)
        }
        
        result = template_engine.render_template(template_content, variables, template_type='python_template')
        expected_contains = ['BTCUSDT', '01-15 14:30']
        
        for expected in expected_contains:
            assert expected in result
    
    def test_render_trigger_event(self, template_engine):
        """测试触发事件渲染"""
        # 创建模拟触发事件
        mock_result = Mock()
        mock_result.value = 'BTCUSDT'
        mock_result.details = '价格超过50000美元'
        mock_result.satisfied = True
        
        mock_context = Mock()
        mock_context.strategy.value = 'sequential'
        mock_context.evaluation_id = 'eval_123'
        
        trigger_event = TriggerEvent(
            condition_id='cond_123',
            condition_name='BTC价格预警',
            result=mock_result,
            timestamp=datetime(2024, 1, 15, 14, 30, 0),
            priority=3,
            context=mock_context
        )
        
        template_content = "$priority_emoji $condition_name: $result_value ($trigger_time_datetime)"
        template_engine.register_template('test_event', template_content)
        
        result = template_engine.render_trigger_event('test_event', trigger_event)
        expected_contains = ['🟡', 'BTC价格预警', 'BTCUSDT', '2024-01-15 14:30:00']
        
        for expected in expected_contains:
            assert expected in result
    
    def test_validate_template(self, template_engine):
        """测试模板验证"""
        # 有效模板
        valid_template = "预警: $condition_name - $result_details"
        validation = template_engine.validate_template(valid_template)
        assert validation['valid'] is True
        
        # 包含格式化器的模板
        formatter_template = "价格: $price|upper ($time|datetime)"
        validation = template_engine.validate_template(formatter_template)
        assert validation['valid'] is True
    
    def test_formatters(self, template_engine):
        """测试格式化器功能"""
        # 测试upper格式化器
        result = template_engine.formatters['upper']('btcusdt')
        assert result == 'BTCUSDT'
        
        # 测试currency格式化器
        result = template_engine.formatters['currency'](50000.5)
        assert '$50,000.50' in result
        
        # 测试percentage格式化器
        result = template_engine.formatters['percentage'](5.5)
        assert '5.50%' in result
        
        # 测试priority_emoji格式化器
        result = template_engine.formatters['emoji_priority'](3)
        assert result == '🟡'
        
        # 测试priority_color格式化器
        result = template_engine.formatters['color_priority'](5)
        assert result == 'red'


class TestTemplateManager:
    """测试模板管理器"""
    
    @pytest.fixture
    def template_manager(self):
        return TemplateManager()
    
    def test_get_templates_by_category(self, template_manager):
        """测试按分类获取模板"""
        price_templates = template_manager.get_templates_by_category('price')
        assert isinstance(price_templates, list)
        assert len(price_templates) > 0
    
    def test_get_template_info(self, template_manager):
        """测试获取模板信息"""
        info = template_manager.get_template_info('price_alert')
        assert info is not None
        assert 'name' in info
        assert 'description' in info
        assert 'variables' in info
    
    def test_create_custom_template(self, template_manager):
        """测试创建自定义模板"""
        success = template_manager.create_custom_template(
            'custom_price_alert',
            '自定义价格预警: $condition_name - $result_details',
            '自定义价格预警模板',
            'custom'
        )
        assert success is True
        
        # 验证模板已创建
        categories = template_manager.list_templates()
        assert 'custom' in categories
        assert 'custom_price_alert' in categories['custom']
    
    def test_export_import_templates(self, template_manager):
        """测试模板导出和导入"""
        # 创建一个自定义模板
        template_manager.create_custom_template(
            'export_test_template',
            '导出测试模板: $condition_name',
            '用于测试导出功能的模板'
        )
        
        # 导出模板
        exported_data = template_manager.export_templates()
        assert 'custom_templates' in exported_data
        assert 'export_test_template' in exported_data['custom_templates']
        
        # 创建新管理器并导入
        new_manager = TemplateManager()
        import_success = new_manager.import_templates(exported_data)
        assert import_success is True
        
        # 验证导入成功
        assert 'export_test_template' in new_manager.template_engine.custom_templates


class TestPrebuiltTemplates:
    """测试预构建模板"""
    
    def test_all_templates_structure(self):
        """测试所有预构建模板的结构"""
        assert isinstance(ALL_TEMPLATES, dict)
        
        # 检查每个分类
        for category, templates in ALL_TEMPLATES.items():
            assert isinstance(templates, dict)
            
            for template_name, template_config in templates.items():
                # 检查模板配置结构
                assert 'name' in template_config
                assert 'description' in template_config
                assert 'templates' in template_config
                assert 'variables' in template_config
                assert 'default_priority' in template_config
                
                # 检查模板内容
                assert isinstance(template_config['templates'], dict)
                assert len(template_config['templates']) > 0
                assert isinstance(template_config['variables'], list)
    
    def test_template_variables_coverage(self):
        """测试模板变量覆盖"""
        expected_vars = ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority']
        
        for category, templates in ALL_TEMPLATES.items():
            for template_config in templates.values():
                template_vars = template_config['variables']
                for expected_var in expected_vars:
                    assert expected_var in template_vars, f"Missing {expected_var} in {category}"


class TestChannelTemplates:
    """测试渠道特定模板"""
    
    def test_popup_templates_structure(self):
        """测试弹窗模板结构"""
        for template_name, config in POPUP_TEMPLATES.items():
            assert 'title' in config
            assert 'message' in config
            assert 'max_length' in config
            assert 'priority_levels' in config
            
            # 检查优先级级别
            assert isinstance(config['priority_levels'], dict)
            for priority, level_config in config['priority_levels'].items():
                assert 'icon' in level_config
                assert 'style' in level_config
    
    def test_telegram_templates_structure(self):
        """测试Telegram模板结构"""
        for template_name, config in TELEGRAM_TEMPLATES.items():
            assert 'format' in config
            assert 'template' in config
            assert 'parse_mode' in config
            
            # 检查模板内容
            template_content = config['template']
            assert '{condition_name}' in template_content
            assert '{result_value}' in template_content
            assert '{result_details}' in template_content
            assert '{trigger_time_datetime}' in template_content
    
    def test_email_templates_structure(self):
        """测试邮件模板结构"""
        for template_name, config in EMAIL_TEMPLATES.items():
            assert 'subject' in config
            assert 'html_template' in config
            assert 'text_template' in config
            
            # 检查HTML模板结构
            html_template = config['html_template']
            assert '<!DOCTYPE html>' in html_template
            assert '<style>' in html_template
            assert '{condition_name}' in html_template
    
    def test_desktop_templates_structure(self):
        """测试桌面通知模板结构"""
        for template_name, config in DESKTOP_TEMPLATES.items():
            assert 'title' in config
            assert 'body' in config
            assert 'urgency' in config
            assert 'timeout' in config
            assert 'categories' in config
            assert 'default_actions' in config


class TestTemplateIntegration:
    """测试模板系统集成"""
    
    @pytest.fixture
    def template_manager(self):
        return TemplateManager()
    
    def test_full_template_workflow(self, template_manager):
        """测试完整模板工作流"""
        # 1. 创建自定义模板
        custom_template = '''
        自定义价格预警
        交易对: $result_value
        预警条件: $condition_name
        详情: $result_details
        触发时间: $trigger_time_datetime
        优先级: $priority_text ($priority/5)
        '''
        
        success = template_manager.create_custom_template(
            'custom_price_alert',
            custom_template,
            '自定义价格预警模板',
            'custom'
        )
        assert success is True
        
        # 2. 渲染模板
        mock_result = Mock()
        mock_result.value = 'BTCUSDT'
        mock_result.details = '价格突破55000美元'
        mock_result.satisfied = True
        
        mock_context = Mock()
        mock_context.strategy.value = 'sequential'
        mock_context.evaluation_id = 'eval_456'
        
        trigger_event = TriggerEvent(
            condition_id='cond_456',
            condition_name='BTC突破预警',
            result=mock_result,
            timestamp=datetime(2024, 1, 15, 15, 45, 0),
            priority=4,
            context=mock_context
        )
        
        rendered = template_manager.template_engine.render_trigger_event(
            'custom_price_alert', 
            trigger_event
        )
        
        # 3. 验证渲染结果
        assert 'BTC突破预警' in rendered
        assert 'BTCUSDT' in rendered
        assert '价格突破55000美元' in rendered
        assert '2024-01-15 15:45:00' in rendered
        assert '重要' in rendered  # 优先级4对应的文本
    
    def test_formatter_chaining(self, template_manager):
        """测试格式化器链式调用"""
        template_content = '价格: $symbol|upper (变化: $change|percentage)'
        template_manager.template_engine.register_template('test_chain', template_content)
        
        variables = {
            'symbol': 'btcusdt',
            'change': 5.5  # 5.5%
        }
        
        result = template_manager.template_engine.render_template(
            template_content, 
            variables, 
            template_type='python_template'
        )
        
        assert 'BTCUSDT' in result
        assert '5.50%' in result
    
    def test_template_error_handling(self, template_manager):
        """测试模板错误处理"""
        # 测试无效模板
        invalid_template = '预警: $undefined_var ($trigger_time_datetime)'
        validation = template_manager.template_engine.validate_template(invalid_template)
        # 应该通过验证，只是会有警告
        assert validation['valid'] is True
        
        # 测试格式错误的模板
        malformed_template = '预警: $condition_name (未关闭的括号'
        validation = template_manager.template_engine.validate_template(malformed_template)
        # 这应该通过验证，因为Template.safe_substitute是安全的
        
        # 测试实际渲染时的错误处理
        variables = {'condition_name': '测试'}
        result = template_manager.template_engine.render_template(malformed_template, variables)
        assert '测试' in result  # 应该正常渲染已定义的变量
    
    def test_template_performance(self, template_manager):
        """测试模板性能"""
        template_content = '复杂模板: $condition_name - $result_value - $trigger_time|datetime - $priority_text'
        
        # 创建大量触发事件
        mock_result = Mock()
        mock_result.value = 'ETHUSDT'
        mock_result.details = '成交量异常'
        mock_result.satisfied = True
        
        mock_context = Mock()
        mock_context.strategy.value = 'parallel'
        mock_context.evaluation_id = 'perf_test'
        
        trigger_events = []
        for i in range(100):
            event = TriggerEvent(
                condition_id=f'cond_{i}',
                condition_name=f'测试条件{i}',
                result=mock_result,
                timestamp=datetime.now(),
                priority=(i % 5) + 1,
                context=mock_context
            )
            trigger_events.append(event)
        
        # 渲染所有事件（模拟性能测试）
        template_manager.template_engine.register_template('perf_test_template', template_content)
        
        start_time = datetime.now()
        for event in trigger_events:
            template_manager.template_engine.render_trigger_event('perf_test_template', event)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        # 100个模板应该在合理时间内完成（少于5秒）
        assert processing_time < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])