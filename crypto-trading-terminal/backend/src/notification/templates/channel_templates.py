"""
渠道特定模板
为不同通知渠道优化的模板配置
"""

from typing import Dict, List

# 弹窗通知模板
POPUP_TEMPLATES = {
    'price_alert': {
        'title': '价格预警 - {condition_name}',
        'message': '{priority_emoji} 交易对: {result_value}\n详情: {result_details}\n时间: {trigger_time_datetime}',
        'max_length': 200,
        'priority_levels': {
            1: {'icon': 'ℹ️', 'style': 'info'},
            2: {'icon': '✅', 'style': 'success'},
            3: {'icon': '⚠️', 'style': 'warning'},
            4: {'icon': '🔴', 'style': 'error'},
            5: {'icon': '🆘', 'style': 'critical'}
        }
    },
    'volume_alert': {
        'title': '成交量预警 - {condition_name}',
        'message': '📊 交易对: {result_value}\n成交量: {result_details}\n时间: {trigger_time_datetime}',
        'max_length': 150,
        'priority_levels': {
            1: {'icon': 'ℹ️', 'style': 'info'},
            2: {'icon': '📊', 'style': 'success'},
            3: {'icon': '⚡', 'style': 'warning'},
            4: {'icon': '🚨', 'style': 'error'},
            5: {'icon': '🆘', 'style': 'critical'}
        }
    },
    'technical_alert': {
        'title': '技术指标预警 - {condition_name}',
        'message': '📈 交易对: {result_value}\n指标: {result_details}\n时间: {trigger_time_datetime}',
        'max_length': 150,
        'priority_levels': {
            1: {'icon': '📊', 'style': 'info'},
            2: {'icon': '📈', 'style': 'success'},
            3: {'icon': '🔔', 'style': 'warning'},
            4: {'icon': '⚡', 'style': 'error'},
            5: {'icon': '🆘', 'style': 'critical'}
        }
    },
    'emergency_alert': {
        'title': '紧急预警 - {condition_name}',
        'message': '🚨 {result_details}\n时间: {trigger_time_datetime}',
        'max_length': 100,
        'priority_levels': {
            3: {'icon': '⚠️', 'style': 'warning'},
            4: {'icon': '🚨', 'style': 'error'},
            5: {'icon': '🆘', 'style': 'critical'}
        }
    }
}

# 桌面通知模板
DESKTOP_TEMPLATES = {
    'price_alert': {
        'title': '价格预警: {condition_name}',
        'body': '交易对: {result_value}\n详情: {result_details}\n时间: {trigger_time_datetime}',
        'urgency': 'normal',
        'timeout': 5000,
        'categories': ['price.trading'],
        'default_actions': ['view_details', 'dismiss']
    },
    'volume_alert': {
        'title': '成交量预警: {condition_name}',
        'body': '交易对: {result_value}\n成交量: {result_details}\n时间: {trigger_time_datetime}',
        'urgency': 'normal',
        'timeout': 4000,
        'categories': ['volume.trading'],
        'default_actions': ['view_details', 'dismiss']
    },
    'technical_alert': {
        'title': '技术指标预警: {condition_name}',
        'body': '交易对: {result_value}\n指标: {result_details}\n时间: {trigger_time_datetime}',
        'urgency': 'normal',
        'timeout': 6000,
        'categories': ['technical.analysis'],
        'default_actions': ['view_chart', 'dismiss']
    },
    'emergency_alert': {
        'title': '紧急预警: {condition_name}',
        'body': '{result_details}\n时间: {trigger_time_datetime}',
        'urgency': 'critical',
        'timeout': 0,  # 不自动关闭
        'categories': ['system.emergency'],
        'default_actions': ['acknowledge', 'details']
    }
}

# Telegram通知模板
TELEGRAM_TEMPLATES = {
    'price_alert': {
        'format': 'markdown',
        'template': '''🚨 *价格预警* - {condition_name}

📊 *交易对*: `{result_value}`
📈 *详情*: {result_details}
⏰ *时间*: {trigger_time_datetime}
{priority_emoji} *优先级*: {priority}/5

📋 *事件ID*: `{event_id}`''',
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    },
    'volume_alert': {
        'format': 'markdown',
        'template': '''📊 *成交量预警* - {condition_name}

📈 *交易对*: `{result_value}`
⚡ *成交量*: {result_details}
⏰ *时间*: {trigger_time_datetime}
{priority_emoji} *优先级*: {priority}/5

📋 *事件ID*: `{event_id}`''',
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    },
    'technical_alert': {
        'format': 'markdown',
        'template': '''📈 *技术指标预警* - {condition_name}

📊 *交易对*: `{result_value}`
🔍 *指标*: {result_details}
⏰ *时间*: {trigger_time_datetime}
{priority_emoji} *优先级*: {priority}/5

📋 *事件ID*: `{event_id}`''',
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    },
    'market_alert': {
        'format': 'markdown',
        'template': '''🌍 *市场预警* - {condition_name}

📈 *交易对*: `{result_value}`
🔍 *详情*: {result_details}
⏰ *时间*: {trigger_time_datetime}
{priority_emoji} *优先级*: {priority}/5

📋 *事件ID*: `{event_id}`''',
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    },
    'emergency_alert': {
        'format': 'markdown',
        'template': '''🚨 *紧急预警* - {condition_name}

⚠️ *详情*: {result_details}
⏰ *时间*: {trigger_time_datetime}
🆘 *优先级*: {priority}/5 (紧急)

📋 *事件ID*: `{event_id}`

*请立即关注此预警！*''',
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
}

# 邮件通知模板
EMAIL_TEMPLATES = {
    'price_alert': {
        'subject': '{priority_emoji} 价格预警 - {condition_name}',
        'html_template': '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .content { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }
                .alert-info { background: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 10px 0; }
                .priority { display: inline-block; padding: 5px 10px; border-radius: 15px; 
                           background: {priority_color}; color: white; font-size: 12px; }
                .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🔔 价格预警通知</h2>
                <h3>{condition_name}</h3>
            </div>
            
            <div class="content">
                <div class="alert-info">
                    <h4>📊 预警详情</h4>
                    <p><strong>交易对:</strong> <span class="priority">{result_value}</span></p>
                    <p><strong>预警详情:</strong> {result_details}</p>
                    <p><strong>触发时间:</strong> {trigger_time_datetime}</p>
                    <p><strong>优先级:</strong> <span class="priority">{priority_text}</span> ({priority}/5)</p>
                    <p><strong>状态:</strong> {'✅ 条件满足' if result_satisfied else '❌ 条件不满足'}</p>
                </div>
            </div>
            
            <div class="footer">
                <p>此邮件由加密货币交易终端自动发送</p>
                <p>事件ID: {event_id} | 发送时间: {send_time}</p>
            </div>
        </body>
        </html>
        ''',
        'text_template': '''
价格预警通知 - {condition_name}

预警详情:
- 交易对: {result_value}
- 预警详情: {result_details}
- 触发时间: {trigger_time_datetime}
- 优先级: {priority_text} ({priority}/5)
- 状态: {status_text}

事件ID: {event_id}
发送时间: {send_time}

此邮件由加密货币交易终端自动发送
        '''
    },
    'volume_alert': {
        'subject': '📊 成交量预警 - {condition_name}',
        'html_template': '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                          color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .content { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }
                .alert-info { background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 10px 0; }
                .priority { display: inline-block; padding: 5px 10px; border-radius: 15px; 
                           background: #ff9800; color: white; font-size: 12px; }
                .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 成交量预警通知</h2>
                <h3>{condition_name}</h3>
            </div>
            
            <div class="content">
                <div class="alert-info">
                    <h4>📈 成交量详情</h4>
                    <p><strong>交易对:</strong> <span class="priority">{result_value}</span></p>
                    <p><strong>成交量详情:</strong> {result_details}</p>
                    <p><strong>触发时间:</strong> {trigger_time_datetime}</p>
                    <p><strong>优先级:</strong> <span class="priority">{priority_text}</span> ({priority}/5)</p>
                </div>
            </div>
            
            <div class="footer">
                <p>事件ID: {event_id} | 发送时间: {send_time}</p>
            </div>
        </body>
        </html>
        ''',
        'text_template': '''
成交量预警通知 - {condition_name}

成交量详情:
- 交易对: {result_value}
- 成交量详情: {result_details}
- 触发时间: {trigger_time_datetime}
- 优先级: {priority_text} ({priority}/5)

事件ID: {event_id}
发送时间: {send_time}
        '''
    },
    'technical_alert': {
        'subject': '📈 技术指标预警 - {condition_name}',
        'html_template': '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                          color: #333; padding: 20px; border-radius: 10px; text-align: center; }
                .content { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }
                .alert-info { background: #f3e5f5; padding: 15px; border-left: 4px solid #9c27b0; margin: 10px 0; }
                .priority { display: inline-block; padding: 5px 10px; border-radius: 15px; 
                           background: #9c27b0; color: white; font-size: 12px; }
                .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📈 技术指标预警通知</h2>
                <h3>{condition_name}</h3>
            </div>
            
            <div class="content">
                <div class="alert-info">
                    <h4>🔍 技术指标详情</h4>
                    <p><strong>交易对:</strong> <span class="priority">{result_value}</span></p>
                    <p><strong>指标详情:</strong> {result_details}</p>
                    <p><strong>触发时间:</strong> {trigger_time_datetime}</p>
                    <p><strong>优先级:</strong> <span class="priority">{priority_text}</span> ({priority}/5)</p>
                </div>
            </div>
            
            <div class="footer">
                <p>事件ID: {event_id} | 发送时间: {send_time}</p>
            </div>
        </body>
        </html>
        ''',
        'text_template': '''
技术指标预警通知 - {condition_name}

技术指标详情:
- 交易对: {result_value}
- 指标详情: {result_details}
- 触发时间: {trigger_time_datetime}
- 优先级: {priority_text} ({priority}/5)

事件ID: {event_id}
发送时间: {send_time}
        '''
    },
    'emergency_alert': {
        'subject': '🚨 紧急预警 - {condition_name}',
        'html_template': '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                          color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .content { margin: 20px 0; padding: 20px; background: #ffebee; border-radius: 5px; }
                .alert-critical { background: #ffcdd2; padding: 20px; border-left: 6px solid #f44336; margin: 15px 0; 
                                animation: pulse 2s infinite; }
                @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); } 
                                  70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); } 
                                  100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); } }
                .priority { display: inline-block; padding: 8px 15px; border-radius: 20px; 
                           background: #f44336; color: white; font-size: 14px; font-weight: bold; }
                .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 紧急预警通知</h2>
                <h3>{condition_name}</h3>
            </div>
            
            <div class="content">
                <div class="alert-critical">
                    <h4>⚠️ 紧急情况详情</h4>
                    <p><strong>紧急描述:</strong> {result_details}</p>
                    <p><strong>触发时间:</strong> {trigger_time_datetime}</p>
                    <p><strong>优先级:</strong> <span class="priority">紧急 ({priority}/5)</span></p>
                    <p><strong>状态:</strong> 需要立即处理</p>
                </div>
            </div>
            
            <div class="footer">
                <p>⚠️ 请立即关注此紧急预警！</p>
                <p>事件ID: {event_id} | 发送时间: {send_time}</p>
            </div>
        </body>
        </html>
        ''',
        'text_template': '''
🚨 紧急预警通知 - {condition_name}

紧急情况详情:
- 紧急描述: {result_details}
- 触发时间: {trigger_time_datetime}
- 优先级: 紧急 ({priority}/5)
- 状态: 需要立即处理

⚠️ 请立即关注此紧急预警！

事件ID: {event_id}
发送时间: {send_time}
        '''
    }
}

# Webhook通知模板
WEBHOOK_TEMPLATES = {
    'default': {
        'format': 'json',
        'template': {
            'event_type': 'trading_alert',
            'condition_name': '{condition_name}',
            'result': {
                'value': '{result_value}',
                'details': '{result_details}',
                'satisfied': '{result_satisfied}'
            },
            'timestamp': '{trigger_time_datetime}',
            'priority': '{priority}',
            'event_id': '{event_id}',
            'metadata': '{metadata}'
        }
    },
    'slack': {
        'format': 'json',
        'template': {
            'channel': '#trading-alerts',
            'username': 'CryptoTradingBot',
            'icon_emoji': ':chart_with_upwards_trend:',
            'attachments': [
                {
                    'color': '{priority_color}',
                    'title': '{condition_name}',
                    'fields': [
                        {'title': '交易对', 'value': '{result_value}', 'short': True},
                        {'title': '优先级', 'value': '{priority_text}', 'short': True},
                        {'title': '详情', 'value': '{result_details}', 'short': False}
                    ],
                    'footer': 'Crypto Trading Terminal',
                    'ts': '{timestamp_unix}'
                }
            ]
        }
    },
    'discord': {
        'format': 'json',
        'template': {
            'embeds': [
                {
                    'title': '🚨 {condition_name}',
                    'description': '{result_details}',
                    'color': '{priority_color_int}',
                    'fields': [
                        {
                            'name': '📊 交易对',
                            'value': '{result_value}',
                            'inline': True
                        },
                        {
                            'name': '⏰ 时间',
                            'value': '{trigger_time_datetime}',
                            'inline': True
                        },
                        {
                            'name': '⚡ 优先级',
                            'value': '{priority_text} ({priority}/5)',
                            'inline': True
                        }
                    ],
                    'footer': {
                        'text': 'Crypto Trading Terminal | Event ID: {event_id}'
                    },
                    'timestamp': '{trigger_time_iso}'
                }
            ]
        }
    }
}

# 模板配置
TEMPLATE_CONFIGS = {
    'max_template_length': 1000,
    'default_timeout': 5000,
    'encoding': 'utf-8',
    'escape_html': True,
    'allow_markdown': True,
    'channel_specific_rules': {
        'popup': {'max_length': 200, 'allow_html': False},
        'desktop': {'max_length': 300, 'allow_html': False},
        'telegram': {'max_length': 4096, 'allow_markdown': True},
        'email': {'max_length': 10000, 'allow_html': True},
        'webhook': {'max_length': 5000, 'allow_json': True}
    }
}
