"""
通知模板引擎
处理模板渲染、变量替换和格式化
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from string import Template
import logging

from ...conditions.condition_engine import TriggerEvent

logger = logging.getLogger(__name__)


class TemplateEngine:
    """模板引擎核心类"""
    
    def __init__(self):
        self.custom_templates: Dict[str, str] = {}
        self.template_variables: Dict[str, Any] = {}
        self.formatters: Dict[str, callable] = {}
        
        # 注册内置格式化器
        self._register_builtin_formatters()
    
    def _register_builtin_formatters(self):
        """注册内置格式化器"""
        self.formatters.update({
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'datetime': lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, datetime) else str(x),
            'short_datetime': lambda x: x.strftime('%m-%d %H:%M') if isinstance(x, datetime) else str(x),
            'currency': lambda x: f"${float(x):,.2f}" if x else "N/A",
            'percentage': lambda x: f"{float(x):.2f}%" if x else "N/A",
            'round': lambda x, n=2: round(float(x), int(n)) if x else "N/A",
            'absolute': lambda x: abs(float(x)) if x else "N/A",
            'positive_negative': lambda x: f"+{x}" if float(x) > 0 else str(x),
            'emoji_priority': self._get_priority_emoji,
            'color_priority': self._get_priority_color,
            'status_text': self._get_status_text,
            'truncate': lambda x, n=50: str(x)[:int(n)] + '...' if len(str(x)) > int(n) else str(x),
        })
    
    def register_template(self, name: str, template: str):
        """注册自定义模板"""
        self.custom_templates[name] = template
        logger.info(f"已注册模板: {name}")
    
    def unregister_template(self, name: str):
        """注销模板"""
        if name in self.custom_templates:
            del self.custom_templates[name]
            logger.info(f"已注销模板: {name}")
    
    def register_formatter(self, name: str, formatter: callable):
        """注册自定义格式化器"""
        self.formatters[name] = formatter
        logger.info(f"已注册格式化器: {name}")
    
    def render_template(self, template: str, variables: Dict[str, Any], 
                       template_type: str = 'default') -> str:
        """渲染模板"""
        try:
            # 预处理变量
            processed_vars = self._preprocess_variables(variables)
            
            # 渲染模板
            if template_type == 'python_template':
                return self._render_python_template(template, processed_vars)
            elif template_type == 'json_template':
                return self._render_json_template(template, processed_vars)
            else:
                return self._render_simple_template(template, processed_vars)
                
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return f"模板渲染错误: {template}"
    
    def render_trigger_event(self, template_name: str, trigger_event: TriggerEvent,
                           channel_type: str = 'default') -> str:
        """渲染触发事件"""
        # 获取模板
        template = self._get_template_by_name(template_name, channel_type)
        
        # 准备变量
        variables = self._prepare_trigger_variables(trigger_event)
        
        # 渲染模板
        return self.render_template(template, variables, template_type='python_template')
    
    def _preprocess_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """预处理变量"""
        processed = {}
        
        for key, value in variables.items():
            if isinstance(value, datetime):
                processed[f"{key}_datetime"] = value.strftime('%Y-%m-%d %H:%M:%S')
                processed[f"{key}_short"] = value.strftime('%m-%d %H:%M')
                processed[f"{key}_time"] = value.strftime('%H:%M:%S')
                processed[f"{key}_date"] = value.strftime('%Y-%m-%d')
            elif isinstance(value, (int, float)):
                processed[f"{key}_formatted"] = self._format_number(value)
            else:
                processed[key] = value
        
        return processed
    
    def _render_simple_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染简单模板（Python Template）"""
        try:
            string_template = Template(template)
            return string_template.safe_substitute(variables)
        except Exception as e:
            logger.error(f"简单模板渲染失败: {e}")
            return template
    
    def _render_python_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染Python模板（支持格式化器）"""
        try:
            # 提取格式化器调用
            formatter_calls = re.findall(r'\|(\w+)(?:\(([^)]*)\))?', template)
            
            # 替换格式化器调用
            rendered_template = template
            for formatter_name, params in formatter_calls:
                if formatter_name in self.formatters:
                    if params:
                        # 处理带参数的格式化器
                        rendered_template = rendered_template.replace(
                            f"|{formatter_name}({params})",
                            f"__formatter_result_{formatter_name}__"
                        )
                    else:
                        # 处理无参数的格式化器
                        rendered_template = rendered_template.replace(
                            f"|{formatter_name}",
                            f"__formatter_result_{formatter_name}__"
                        )
            
            # 应用格式化器
            for formatter_name, params in formatter_calls:
                if formatter_name in self.formatters:
                    try:
                        formatter = self.formatters[formatter_name]
                        if params:
                            # 解析参数
                            param_values = [variables.get(p.strip()) for p in params.split(',')]
                            result = formatter(*param_values)
                        else:
                            # 获取格式化对象（通常是当前模板的主要变量）
                            format_obj = self._get_format_object(variables)
                            result = formatter(format_obj)
                        
                        rendered_template = rendered_template.replace(
                            f"__formatter_result_{formatter_name}__",
                            str(result)
                        )
                    except Exception as e:
                        logger.warning(f"格式化器 {formatter_name} 执行失败: {e}")
                        rendered_template = rendered_template.replace(
                            f"__formatter_result_{formatter_name}__",
                            "N/A"
                        )
            
            # 最终渲染
            string_template = Template(rendered_template)
            return string_template.safe_substitute(variables)
            
        except Exception as e:
            logger.error(f"Python模板渲染失败: {e}")
            return template
    
    def _render_json_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染JSON模板"""
        try:
            template_data = json.loads(template)
            return json.dumps(template_data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.error(f"JSON模板解析失败: {e}")
            return template
    
    def _get_format_object(self, variables: Dict[str, Any]):
        """获取格式化的主要对象"""
        # 优先使用价格，然后是值，最后是详细信息
        for key in ['price', 'value', 'current_value', 'details_value']:
            if key in variables:
                return variables[key]
        return variables.get('result_value', 'N/A')
    
    def _prepare_trigger_variables(self, trigger_event: TriggerEvent) -> Dict[str, Any]:
        """准备触发事件变量"""
        variables = {
            # 基础信息
            'condition_id': trigger_event.condition_id,
            'condition_name': trigger_event.condition_name,
            'event_id': trigger_event.event_id,
            
            # 结果信息
            'result_value': trigger_event.result.value,
            'result_details': trigger_event.result.details,
            'result_satisfied': trigger_event.result.satisfied,
            
            # 时间信息
            'timestamp': trigger_event.timestamp,
            'trigger_time': trigger_event.timestamp,
            
            # 优先级信息
            'priority': trigger_event.priority,
            'priority_text': self._get_priority_text(trigger_event.priority),
            
            # 上下文信息
            'context_strategy': trigger_event.context.strategy.value,
            'context_id': trigger_event.context.evaluation_id,
        }
        
        # 添加元数据
        if trigger_event.metadata:
            variables.update(trigger_event.metadata)
        
        # 添加格式化信息
        variables.update({
            'status_text': self._get_status_text(trigger_event.result.satisfied),
            'priority_emoji': self._get_priority_emoji(trigger_event.priority),
            'priority_color': self._get_priority_color(trigger_event.priority),
        })
        
        return variables
    
    def _get_template_by_name(self, template_name: str, channel_type: str) -> str:
        """根据名称获取模板"""
        # 先查找自定义模板
        if template_name in self.custom_templates:
            return self.custom_templates[template_name]
        
        # 使用内置模板
        return self._get_builtin_template(template_name, channel_type)
    
    def _get_builtin_template(self, template_name: str, channel_type: str) -> str:
        """获取内置模板"""
        # 这里可以根据需要从预构建模板中获取
        # 返回默认模板
        return "🔔 $condition_name: $result_details ($trigger_time_datetime)"
    
    def _format_number(self, value: Union[int, float]) -> str:
        """格式化数字"""
        if value >= 1e9:
            return f"{value/1e9:.2f}B"
        elif value >= 1e6:
            return f"{value/1e6:.2f}M"
        elif value >= 1e3:
            return f"{value/1e3:.2f}K"
        else:
            return f"{value:.2f}"
    
    def _get_priority_emoji(self, priority: int) -> str:
        """获取优先级表情符号"""
        emojis = {1: "🔵", 2: "🟢", 3: "🟡", 4: "🟠", 5: "🔴"}
        return emojis.get(priority, "⚪")
    
    def _get_priority_color(self, priority: int) -> str:
        """获取优先级颜色"""
        colors = {1: "blue", 2: "green", 3: "yellow", 4: "orange", 5: "red"}
        return colors.get(priority, "gray")
    
    def _get_priority_text(self, priority: int) -> str:
        """获取优先级文本"""
        texts = {1: "低优先级", 2: "普通", 3: "高优先级", 4: "重要", 5: "紧急"}
        return texts.get(priority, f"优先级{priority}")
    
    def _get_status_text(self, satisfied: bool) -> str:
        """获取状态文本"""
        return "条件满足" if satisfied else "条件不满足"
    
    def validate_template(self, template: str, template_type: str = 'default') -> Dict[str, Any]:
        """验证模板"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if template_type in ['python_template', 'simple']:
                # 检查Python模板语法
                string_template = Template(template)
                # 尝试渲染空变量
                test_render = string_template.safe_substitute({})
                
                # 检查未定义的变量
                placeholder_pattern = r'\$(\w+)'
                placeholders = re.findall(placeholder_pattern, template)
                undefined_vars = []
                
                for placeholder in placeholders:
                    if placeholder not in ['condition_name', 'result_details', 'trigger_time']:
                        undefined_vars.append(placeholder)
                
                if undefined_vars:
                    result['warnings'].append(f"未识别的变量: {', '.join(undefined_vars)}")
                
            elif template_type == 'json_template':
                # 检查JSON模板
                json.loads(template)
                
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"模板语法错误: {str(e)}")
        
        return result


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_engine: TemplateEngine = None):
        self.template_engine = template_engine or TemplateEngine()
        self.template_categories = {
            'price': ['price_alert', 'price_change', 'price_target'],
            'volume': ['volume_spike', 'volume_anomaly'],
            'technical': ['rsi_signal', 'macd_signal', 'ma_crossover'],
            'time': ['market_open', 'market_close', 'session_change'],
            'market': ['price_breakout', 'trend_change', 'volatility_spike'],
            'emergency': ['connection_lost', 'critical_error', 'system_alert']
        }
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """获取分类下的模板"""
        template_names = self.template_categories.get(category, [])
        templates = []
        
        for name in template_names:
            template_info = self.get_template_info(name)
            if template_info:
                templates.append(template_info)
        
        return templates
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取模板信息"""
        # 这里可以根据需要返回模板的详细信息
        # 包括描述、变量、示例等
        return {
            'name': template_name,
            'description': f"{template_name} 模板",
            'variables': ['condition_name', 'result_details', 'trigger_time'],
            'example': "示例渲染结果"
        }
    
    def create_custom_template(self, name: str, template: str, 
                             description: str = "", category: str = "custom") -> bool:
        """创建自定义模板"""
        try:
            # 验证模板
            validation = self.template_engine.validate_template(template)
            if not validation['valid']:
                raise ValueError(f"模板无效: {', '.join(validation['errors'])}")
            
            # 注册模板
            self.template_engine.register_template(name, template)
            
            # 添加到分类
            if category not in self.template_categories:
                self.template_categories[category] = []
            if name not in self.template_categories[category]:
                self.template_categories[category].append(name)
            
            logger.info(f"已创建自定义模板: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建自定义模板失败: {e}")
            return False
    
    def list_templates(self, category: str = None) -> Dict[str, List[str]]:
        """列出所有模板"""
        if category:
            return {category: self.template_categories.get(category, [])}
        else:
            return self.template_categories.copy()
    
    def export_templates(self) -> Dict[str, Any]:
        """导出模板配置"""
        return {
            'custom_templates': self.template_engine.custom_templates,
            'categories': self.template_categories,
            'exported_at': datetime.now().isoformat()
        }
    
    def import_templates(self, template_data: Dict[str, Any]) -> bool:
        """导入模板配置"""
        try:
            # 导入自定义模板
            for name, template in template_data.get('custom_templates', {}).items():
                self.template_engine.register_template(name, template)
            
            # 导入分类
            categories = template_data.get('categories', {})
            for category, templates in categories.items():
                if category not in self.template_categories:
                    self.template_categories[category] = []
                self.template_categories[category].extend(templates)
            
            logger.info("模板配置导入成功")
            return True
            
        except Exception as e:
            logger.error(f"模板配置导入失败: {e}")
            return False