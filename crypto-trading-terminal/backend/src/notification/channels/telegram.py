"""
Telegram通知渠道
处理Telegram Bot API通知发送
"""

import asyncio
import json
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlencode

from ..notify_manager import NotificationMessage, DeliveryStatus, DeliveryRecord


class TelegramNotificationChannel:
    """Telegram通知渠道处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = "telegram"
        self.enabled = self.config.get("enabled", False)  # 默认禁用，需要配置
        
        # Telegram配置
        self.bot_token = self.config.get("bot_token")
        self.chat_id = self.config.get("chat_id")
        self.api_base_url = self.config.get("api_base_url", "https://api.telegram.org")
        self.parse_mode = self.config.get("parse_mode", "Markdown")  # Markdown, HTML
        self.disable_web_page_preview = self.config.get("disable_web_page_preview", True)
        self.disable_notification = self.config.get("disable_notification", False)
        
        # 发送配置
        self.timeout = self.config.get("timeout", 30)  # 秒
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)  # 秒
        
        # 统计数据
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "rate_limited": 0,
            "last_used": None
        }
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        self.config_valid = bool(self.bot_token and self.chat_id)
        
        if not self.config_valid:
            print("⚠️ Telegram配置不完整，需要bot_token和chat_id")
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送Telegram通知"""
        try:
            if not self.enabled or not self.config_valid:
                return False
            
            # 更新统计数据
            self.stats["total_sent"] += 1
            self.stats["last_used"] = datetime.now()
            
            # 构建消息内容
            formatted_message = self._format_message(message)
            
            # 发送消息
            for attempt in range(self.max_retries):
                try:
                    success = await self._send_telegram_message(
                        text=formatted_message,
                        chat_id=self.chat_id
                    )
                    
                    if success:
                        self.stats["successful"] += 1
                        print(f"Telegram通知发送成功: {message.message_id}")
                        return True
                    else:
                        if attempt < self.max_retries - 1:
                            print(f"Telegram发送失败，第{attempt + 1}次重试...")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            self.stats["failed"] += 1
                            print(f"Telegram通知发送失败: {message.message_id}")
                
                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        print(f"Telegram发送超时，第{attempt + 1}次重试...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        self.stats["failed"] += 1
                        print(f"Telegram通知发送超时: {message.message_id}")
                        return False
                
                except Exception as e:
                    if "429" in str(e):  # 速率限制
                        self.stats["rate_limited"] += 1
                        print(f"Telegram速率限制: {str(e)}")
                        await asyncio.sleep(self.retry_delay * 2)  # 延迟重试
                    elif attempt < self.max_retries - 1:
                        print(f"Telegram发送异常，第{attempt + 1}次重试: {str(e)}")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        self.stats["failed"] += 1
                        print(f"Telegram通知发送异常: {str(e)}")
                        return False
            
            return False
            
        except Exception as e:
            self.stats["failed"] += 1
            print(f"Telegram通知异常: {str(e)}")
            return False
    
    def _format_message(self, message: NotificationMessage) -> str:
        """格式化Telegram消息"""
        # 根据优先级选择模板
        if message.priority.value in ["urgent", "critical"]:
            template = self._get_urgent_template()
        elif message.priority.value == "high":
            template = self._get_high_priority_template()
        else:
            template = self._get_normal_template()
        
        # 填充模板变量
        return template.format(
            title=message.title,
            content=message.content,
            timestamp=message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            priority_emoji=self._get_priority_emoji(message.priority.value),
            priority_text=self._get_priority_text(message.priority.value),
            message_id=message.message_id,
            channel=message.channel.value
        )
    
    def _get_urgent_template(self) -> str:
        """获取紧急消息模板"""
        return """🚨 *紧急预警* - {title}

⚠️ *详情*: {content}
⏰ *时间*: {timestamp}
🆘 *优先级*: {priority_text}

📋 *消息ID*: `{message_id}`
🔔 *渠道*: {channel}

*请立即关注此预警！*"""
    
    def _get_high_priority_template(self) -> str:
        """获取高优先级消息模板"""
        return """⚠️ *重要预警* - {title}

📊 *详情*: {content}
⏰ *时间*: {timestamp}
{priority_emoji} *优先级*: {priority_text}

📋 *消息ID*: `{message_id}`"""
    
    def _get_normal_template(self) -> str:
        """获取普通消息模板"""
        return """📢 *通知* - {title}

📝 *详情*: {content}
⏰ *时间*: {timestamp}
{priority_emoji} *优先级*: {priority_text}

📋 *消息ID*: `{message_id}`"""
    
    def _get_priority_emoji(self, priority: str) -> str:
        """获取优先级表情符号"""
        mapping = {
            "low": "🔵",
            "normal": "✅",
            "high": "⚠️",
            "urgent": "🔴",
            "critical": "🆘"
        }
        return mapping.get(priority, "📢")
    
    def _get_priority_text(self, priority: str) -> str:
        """获取优先级文本"""
        mapping = {
            "low": "低优先级",
            "normal": "普通",
            "high": "高优先级", 
            "urgent": "紧急",
            "critical": "关键"
        }
        return mapping.get(priority, "普通")
    
    async def _send_telegram_message(self, text: str, chat_id: str) -> bool:
        """发送Telegram消息"""
        try:
            url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
            
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": self.disable_web_page_preview,
                "disable_notification": self.disable_notification
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("ok", False)
                    else:
                        response_text = await response.text()
                        print(f"Telegram API错误: {response.status} - {response_text}")
                        return False
                        
        except Exception as e:
            print(f"Telegram发送异常: {str(e)}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        if not self.config_valid:
            return {
                "status": "error",
                "message": "Telegram配置不完整",
                "config_valid": False,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # 发送测试消息
            test_message = NotificationMessage(
                message_id="test_connection",
                channel="telegram",
                title="连接测试",
                content="Telegram通知渠道连接测试",
                priority="normal",
                timestamp=datetime.now()
            )
            
            success = await self.send_notification(test_message)
            
            if success:
                return {
                    "status": "success",
                    "message": "Telegram连接正常",
                    "config_valid": True,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": "Telegram发送测试失败",
                    "config_valid": True,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Telegram连接测试异常: {str(e)}",
                "config_valid": True,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_me(self) -> Dict[str, Any]:
        """获取Bot信息"""
        if not self.config_valid:
            return {"error": "配置不完整"}
        
        try:
            url = f"{self.api_base_url}/bot{self.bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"API错误: {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}
    
    def is_enabled(self) -> bool:
        """检查渠道是否启用"""
        return self.enabled and self.config_valid
    
    def enable(self):
        """启用渠道"""
        if self.config_valid:
            self.enabled = True
            print("Telegram通知渠道已启用")
        else:
            print("Telegram配置不完整，无法启用")
    
    def disable(self):
        """禁用渠道"""
        self.enabled = False
        print("Telegram通知渠道已禁用")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        success_rate = 0
        if self.stats["total_sent"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_sent"]) * 100
        
        return {
            "channel": self.name,
            "enabled": self.enabled,
            "config_valid": self.config_valid,
            "stats": self.stats.copy(),
            "success_rate": round(success_rate, 2),
            "rate_limit_percentage": round(
                (self.stats["rate_limited"] / max(self.stats["total_sent"], 1)) * 100, 2
            ),
            "config": {
                "chat_id": self.chat_id,
                "parse_mode": self.parse_mode,
                "timeout": self.timeout,
                "max_retries": self.max_retries
            }
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        
        # 更新相关属性
        self.bot_token = config.get("bot_token", self.bot_token)
        self.chat_id = config.get("chat_id", self.chat_id)
        self.api_base_url = config.get("api_base_url", self.api_base_url)
        self.parse_mode = config.get("parse_mode", self.parse_mode)
        self.disable_web_page_preview = config.get("disable_web_page_preview", self.disable_web_page_preview)
        self.timeout = config.get("timeout", self.timeout)
        self.max_retries = config.get("max_retries", self.max_retries)
        self.enabled = config.get("enabled", self.enabled)
        
        # 重新验证配置
        self._validate_config()
        
        print("Telegram配置已更新")
    
    def cleanup(self):
        """清理资源"""
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "rate_limited": 0,
            "last_used": None
        }
        print("Telegram通知渠道已清理")
    
    def setup_instructions(self) -> str:
        """获取Telegram Bot设置说明"""
        return """
Telegram通知渠道设置步骤：

1. 创建Telegram Bot：
   - 搜索 @BotFather
   - 发送 /newbot 命令
   - 按提示创建Bot并获取 Bot Token

2. 获取Chat ID：
   - 将Bot添加到你的群聊或私聊
   - 发送消息给Bot
   - 访问：https://api.telegram.org/bot[TOKEN]/getUpdates
   - 从响应中获取Chat ID

3. 配置参数：
   - bot_token: 你的Bot Token
   - chat_id: 你的Chat ID
   - parse_mode: "Markdown" 或 "HTML" (可选)
   - disable_web_page_preview: true/false (可选)

4. 测试连接：
   - 使用test_connection()方法测试
"""


# 工具函数
def create_telegram_channel(config: Optional[Dict[str, Any]] = None) -> TelegramNotificationChannel:
    """创建Telegram通知渠道实例"""
    return TelegramNotificationChannel(config)


def get_telegram_templates() -> Dict[str, Dict[str, Any]]:
    """获取Telegram消息模板"""
    return {
        "price_alert": {
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "template": "🚨 *价格预警* - {title}\n\n📊 *交易对*: `{content}`\n⏰ *时间*: {timestamp}"
        },
        "volume_alert": {
            "parse_mode": "Markdown", 
            "disable_web_page_preview": True,
            "template": "📊 *成交量预警* - {title}\n\n📈 *成交量*: {content}\n⏰ *时间*: {timestamp}"
        },
        "technical_alert": {
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "template": "📈 *技术指标预警* - {title}\n\n🔍 *指标*: {content}\n⏰ *时间*: {timestamp}"
        },
        "emergency_alert": {
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "template": "🚨 *紧急预警* - {title}\n\n⚠️ *详情*: {content}\n⏰ *时间*: {timestamp}\n\n*请立即关注！*"
        }
    }


if __name__ == "__main__":
    # 测试Telegram通知渠道
    import asyncio
    
    async def test_telegram_channel():
        print("测试Telegram通知渠道...")
        
        # 需要配置的参数
        config = {
            "enabled": False,  # 需要先配置token和chat_id
            "bot_token": "YOUR_BOT_TOKEN",
            "chat_id": "YOUR_CHAT_ID",
            "parse_mode": "Markdown",
            "timeout": 30
        }
        
        channel = create_telegram_channel(config)
        print(f"配置有效: {channel.config_valid}")
        
        if channel.config_valid:
            # 测试连接
            test_result = await channel.test_connection()
            print(f"连接测试: {test_result}")
            
            # 获取Bot信息
            bot_info = await channel.get_me()
            print(f"Bot信息: {bot_info}")
        
        # 显示设置说明
        print("\n" + channel.setup_instructions())
        
        stats = channel.get_statistics()
        print(f"统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    asyncio.run(test_telegram_channel())