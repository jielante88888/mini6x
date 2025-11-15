"""
通知模板系统
提供预构建的消息模板和自定义模板功能
"""

from .template_engine import TemplateEngine, TemplateManager
from .prebuilt_templates import (
    PRICE_ALERT_TEMPLATE,
    VOLUME_ALERT_TEMPLATE,
    TECHNICAL_ALERT_TEMPLATE,
    TIME_BASED_ALERT_TEMPLATE,
    MARKET_ALERT_TEMPLATE,
    EMERGENCY_ALERT_TEMPLATE
)
from .channel_templates import (
    POPUP_TEMPLATES,
    DESKTOP_TEMPLATES,
    TELEGRAM_TEMPLATES,
    EMAIL_TEMPLATES
)

__all__ = [
    'TemplateEngine',
    'TemplateManager',
    'PRICE_ALERT_TEMPLATE',
    'VOLUME_ALERT_TEMPLATE', 
    'TECHNICAL_ALERT_TEMPLATE',
    'TIME_BASED_ALERT_TEMPLATE',
    'MARKET_ALERT_TEMPLATE',
    'EMERGENCY_ALERT_TEMPLATE',
    'POPUP_TEMPLATES',
    'DESKTOP_TEMPLATES',
    'TELEGRAM_TEMPLATES',
    'EMAIL_TEMPLATES'
]
