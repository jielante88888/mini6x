"""
预构建通知模板
提供常用的通知模板配置
"""

from typing import Dict, List

# 价格相关模板
PRICE_ALERT_TEMPLATE = {
    'name': 'price_alert',
    'description': '价格预警模板',
    'templates': {
        'default': '🔔 价格预警: $condition_name 触发，价格 $result_value|upper ($result_details)',
        'detailed': '🚨 价格预警详情\n交易对: $result_value\n预警条件: $condition_name\n触发时间: $trigger_time_datetime\n详细信息: $result_details',
        'simple': '💰 $condition_name: $result_value ($trigger_time_datetime)',
        'urgent': '🔥 紧急价格预警: $condition_name\n当前价格: $result_value\n变化详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 3
}

PRICE_CHANGE_TEMPLATE = {
    'name': 'price_change',
    'description': '价格变化模板',
    'templates': {
        'default': '📈 价格变化: $condition_name 触发，新价格 $result_value|currency (变化: $result_details)',
        'detailed': '📊 价格变化详情\n交易对: $result_value\n变化描述: $result_details\n触发时间: $trigger_time_datetime\n优先级: $priority_text ($priority/5)',
        'simple': '💹 $condition_name: $result_value ($trigger_time_datetime)'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

# 成交量相关模板
VOLUME_ALERT_TEMPLATE = {
    'name': 'volume_alert',
    'description': '成交量预警模板',
    'templates': {
        'default': '📊 成交量预警: $condition_name 触发，成交量 $result_value|upper ($result_details)',
        'detailed': '📈 成交量预警详情\n交易对: $result_value\n成交量描述: $result_details\n触发时间: $trigger_time_datetime\n状态: $status_text',
        'simple': '📊 $condition_name: $result_value ($trigger_time_datetime)',
        'spike': '⚡ 成交量激增: $condition_name\n当前成交量: $result_value\n异常描述: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

VOLUME_SPIKE_TEMPLATE = {
    'name': 'volume_spike',
    'description': '成交量激增模板',
    'templates': {
        'default': '⚡ 成交量激增: $condition_name 触发，当前成交量 $result_value|upper ($result_details)',
        'detailed': '🚀 成交量激增详情\n交易对: $result_value\n激增描述: $result_details\n触发时间: $trigger_time_datetime\n优先级: $priority_text',
        'urgent': '🚨 紧急成交量激增: $condition_name\n当前成交量: $result_value|upper\n激增详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 3
}

# 技术指标相关模板
TECHNICAL_ALERT_TEMPLATE = {
    'name': 'technical_alert',
    'description': '技术指标预警模板',
    'templates': {
        'default': '📈 技术指标预警: $condition_name 触发，指标值 $result_value (详情: $result_details)',
        'detailed': '📊 技术指标预警详情\n交易对: $result_value\n指标描述: $result_details\n触发时间: $trigger_time_datetime\n状态: $status_text',
        'rsi': '📈 RSI指标预警: $condition_name\n当前RSI: $result_value\n信号详情: $result_details\n时间: $trigger_time_datetime',
        'macd': '📊 MACD指标预警: $condition_name\n当前MACD: $result_value\n信号详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

RSI_SIGNAL_TEMPLATE = {
    'name': 'rsi_signal',
    'description': 'RSI信号模板',
    'templates': {
        'default': '📈 RSI信号: $condition_name 触发，当前RSI $result_value (详情: $result_details)',
        'overbought': '🔴 RSI超买信号: $condition_name\n当前RSI: $result_value\n超买详情: $result_details\n时间: $trigger_time_datetime',
        'oversold': '🟢 RSI超卖信号: $condition_name\n当前RSI: $result_value\n超卖详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

MACD_SIGNAL_TEMPLATE = {
    'name': 'macd_signal',
    'description': 'MACD信号模板',
    'templates': {
        'default': '📊 MACD信号: $condition_name 触发，MACD值 $result_value (详情: $result_details)',
        'bullish': '📈 MACD金叉信号: $condition_name\n当前MACD: $result_value\n金叉详情: $result_details\n时间: $trigger_time_datetime',
        'bearish': '📉 MACD死叉信号: $condition_name\n当前MACD: $result_value\n死叉详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

# 时间相关模板
TIME_BASED_ALERT_TEMPLATE = {
    'name': 'time_alert',
    'description': '时间预警模板',
    'templates': {
        'default': '⏰ 时间预警: $condition_name 触发 ($result_details) - $trigger_time_datetime',
        'market_open': '🌅 市场开盘: $condition_name 触发 ($result_details) - $trigger_time_datetime',
        'market_close': '🌇 市场收盘: $condition_name 触发 ($result_details) - $trigger_time_datetime',
        'trading_session': '📈 交易时段切换: $condition_name 触发 ($result_details) - $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 1
}

# 市场相关模板
MARKET_ALERT_TEMPLATE = {
    'name': 'market_alert',
    'description': '市场预警模板',
    'templates': {
        'default': '🌍 市场预警: $condition_name 触发 ($result_details) - $trigger_time_datetime',
        'breakout': '🚀 价格突破: $condition_name 触发，突破价格 $result_value (详情: $result_details)',
        'trend_change': '🔄 趋势变化: $condition_name 触发，趋势信息 $result_value (详情: $result_details)',
        'volatility': '⚡ 波动率变化: $condition_name 触发，波动信息 $result_value (详情: $result_details)'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 3
}

PRICE_BREAKOUT_TEMPLATE = {
    'name': 'price_breakout',
    'description': '价格突破模板',
    'templates': {
        'default': '🚀 价格突破: $condition_name 触发，突破价格 $result_value (详情: $result_details)',
        'bullish': '📈 向上突破: $condition_name\n突破价格: $result_value\n突破详情: $result_details\n时间: $trigger_time_datetime',
        'bearish': '📉 向下突破: $condition_name\n突破价格: $result_value\n突破详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 4
}

TREND_CHANGE_TEMPLATE = {
    'name': 'trend_change',
    'description': '趋势变化模板',
    'templates': {
        'default': '🔄 趋势变化: $condition_name 触发，趋势信息 $result_value (详情: $result_details)',
        'bullish': '📈 趋势转多: $condition_name\n当前趋势: $result_value\n变化详情: $result_details\n时间: $trigger_time_datetime',
        'bearish': '📉 趋势转空: $condition_name\n当前趋势: $result_value\n变化详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 3
}

VOLATILITY_TEMPLATE = {
    'name': 'volatility_alert',
    'description': '波动率预警模板',
    'templates': {
        'default': '⚡ 波动率预警: $condition_name 触发，波动信息 $result_value (详情: $result_details)',
        'high': '🌪️ 高波动率: $condition_name\n当前波动: $result_value\n波动详情: $result_details\n时间: $trigger_time_datetime',
        'low': '😴 低波动率: $condition_name\n当前波动: $result_value\n波动详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_value', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 2
}

# 紧急情况模板
EMERGENCY_ALERT_TEMPLATE = {
    'name': 'emergency_alert',
    'description': '紧急预警模板',
    'templates': {
        'default': '🚨 紧急预警: $condition_name 触发 ($result_details) - $trigger_time_datetime',
        'critical': '🆘 关键错误: $condition_name\n错误详情: $result_details\n时间: $trigger_time_datetime',
        'system': '🔧 系统异常: $condition_name\n异常信息: $result_details\n时间: $trigger_time_datetime',
        'connection': '📡 连接异常: $condition_name\n连接信息: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 5
}

# 通用系统模板
SYSTEM_ALERT_TEMPLATE = {
    'name': 'system_alert',
    'description': '系统预警模板',
    'templates': {
        'default': '🔧 系统消息: $condition_name ($result_details) - $trigger_time_datetime',
        'info': 'ℹ️ 系统信息: $condition_name\n信息详情: $result_details\n时间: $trigger_time_datetime',
        'warning': '⚠️ 系统警告: $condition_name\n警告详情: $result_details\n时间: $trigger_time_datetime',
        'error': '❌ 系统错误: $condition_name\n错误详情: $result_details\n时间: $trigger_time_datetime'
    },
    'variables': ['condition_name', 'result_details', 'trigger_time', 'priority'],
    'default_priority': 3
}

# 模板集合
ALL_TEMPLATES = {
    'price': {
        'price_alert': PRICE_ALERT_TEMPLATE,
        'price_change': PRICE_CHANGE_TEMPLATE,
        'price_breakout': PRICE_BREAKOUT_TEMPLATE
    },
    'volume': {
        'volume_alert': VOLUME_ALERT_TEMPLATE,
        'volume_spike': VOLUME_SPIKE_TEMPLATE
    },
    'technical': {
        'technical_alert': TECHNICAL_ALERT_TEMPLATE,
        'rsi_signal': RSI_SIGNAL_TEMPLATE,
        'macd_signal': MACD_SIGNAL_TEMPLATE
    },
    'time': {
        'time_alert': TIME_BASED_ALERT_TEMPLATE
    },
    'market': {
        'market_alert': MARKET_ALERT_TEMPLATE,
        'trend_change': TREND_CHANGE_TEMPLATE,
        'volatility_alert': VOLATILITY_TEMPLATE
    },
    'emergency': {
        'emergency_alert': EMERGENCY_ALERT_TEMPLATE,
        'system_alert': SYSTEM_ALERT_TEMPLATE
    }
}

# 模板使用示例
TEMPLATE_EXAMPLES = {
    'price_alert': {
        'input': {
            'condition_name': 'BTC价格预警',
            'result_value': 'BTCUSDT',
            'result_details': '价格超过50,000美元',
            'trigger_time': '2024-01-15 14:30:00',
            'priority': 3
        },
        'output': '🔔 价格预警: BTC价格预警 触发，价格 BTCUSDT (价格超过50,000美元)'
    },
    'volume_spike': {
        'input': {
            'condition_name': 'ETH成交量激增',
            'result_value': '2,500,000',
            'result_details': '成交量比平均值高出300%',
            'trigger_time': '2024-01-15 14:30:00',
            'priority': 4
        },
        'output': '⚡ 成交量激增: ETH成交量激增 触发，当前成交量 2,500,000 (成交量比平均值高出300%)'
    }
}

# 模板变量说明
TEMPLATE_VARIABLES = {
    'condition_name': '条件名称',
    'result_value': '结果值（通常为交易对或数值）',
    'result_details': '结果详情描述',
    'trigger_time': '触发时间',
    'priority': '优先级数值',
    'priority_text': '优先级文本',
    'status_text': '状态文本',
    'priority_emoji': '优先级表情符号',
    'result_satisfied': '条件是否满足'
}

# 格式化器说明
FORMATTERS = {
    'upper': '转换为大写',
    'lower': '转换为小写',
    'capitalize': '首字母大写',
    'title': '标题格式',
    'datetime': '格式化日期时间',
    'short_datetime': '简短日期时间格式',
    'currency': '货币格式',
    'percentage': '百分比格式',
    'round': '四舍五入',
    'absolute': '绝对值',
    'positive_negative': '正负号格式化',
    'emoji_priority': '优先级表情符号',
    'color_priority': '优先级颜色',
    'status_text': '状态文本',
    'truncate': '字符串截断'
}