"""
弹窗通知渠道
处理浏览器弹窗通知功能
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp

from ..notify_manager import NotificationMessage, DeliveryStatus, DeliveryRecord


class PopupNotificationChannel:
    """弹窗通知渠道处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = "popup"
        self.enabled = self.config.get("enabled", True)
        
        # 弹窗配置
        self.max_length = self.config.get("max_length", 200)
        self.display_duration = self.config.get("display_duration", 5000)  # 毫秒
        self.allow_html = self.config.get("allow_html", False)
        self.position = self.config.get("position", "top-right")  # top-left, top-right, bottom-left, bottom-right
        
        # 统计数据
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None
        }
        
        # 弹窗样式配置
        self.styles = {
            "low": {"color": "#2196F3", "icon": "ℹ️"},
            "normal": {"color": "#4CAF50", "icon": "✅"},
            "high": {"color": "#FF9800", "icon": "⚠️"},
            "urgent": {"color": "#F44336", "icon": "🔴"},
            "critical": {"color": "#9C27B0", "icon": "🆘"}
        }
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送弹窗通知"""
        try:
            if not self.enabled:
                return False
            
            # 更新统计数据
            self.stats["total_sent"] += 1
            self.stats["last_used"] = datetime.now()
            
            # 处理消息内容
            title = self._format_title(message)
            content = self._format_content(message)
            
            # 限制长度
            if len(content) > self.max_length:
                content = content[:self.max_length - 3] + "..."
            
            # 生成弹窗配置
            popup_config = {
                "title": title,
                "body": content,
                "icon": self._get_icon_for_priority(message.priority.value),
                "tag": message.message_id,
                "requireInteraction": message.priority.value in ["urgent", "critical"],
                "silent": message.priority.value == "low",
                "data": {
                    "message_id": message.message_id,
                    "channel": self.name,
                    "timestamp": message.timestamp.isoformat(),
                    "priority": message.priority.value
                }
            }
            
            # 添加操作按钮（针对高优先级消息）
            if message.priority.value in ["high", "urgent", "critical"]:
                popup_config["actions"] = [
                    {"action": "view", "title": "查看详情"},
                    {"action": "dismiss", "title": "关闭"}
                ]
            
            # 模拟弹窗发送（在实际应用中，这里会调用浏览器的Notification API）
            success = await self._simulate_popup_display(popup_config)
            
            if success:
                self.stats["successful"] += 1
                print(f"弹窗通知发送成功: {message.message_id}")
            else:
                self.stats["failed"] += 1
                print(f"弹窗通知发送失败: {message.message_id}")
            
            return success
            
        except Exception as e:
            self.stats["failed"] += 1
            print(f"弹窗通知异常: {str(e)}")
            return False
    
    def _format_title(self, message: NotificationMessage) -> str:
        """格式化标题"""
        return f"{message.title}"
    
    def _format_content(self, message: NotificationMessage) -> str:
        """格式化内容"""
        # 移除多余空格和换行
        content = message.content.strip()
        content = content.replace('\n', ' | ')
        
        # 添加时间信息
        time_str = message.timestamp.strftime("%H:%M:%S")
        content = f"{content} ({time_str})"
        
        return content
    
    def _get_icon_for_priority(self, priority: str) -> str:
        """根据优先级获取图标"""
        priority_config = self.styles.get(priority, self.styles["normal"])
        return priority_config["icon"]
    
    async def _simulate_popup_display(self, config: Dict[str, Any]) -> bool:
        """模拟弹窗显示（在实际应用中替换为真实实现）"""
        try:
            # 在真实环境中，这里会调用：
            # - Web浏览器的 Notification API
            # - 或者移动端的原生通知API
            
            print(f"显示弹窗通知:")
            print(f"  标题: {config['title']}")
            print(f"  内容: {config['body']}")
            print(f"  图标: {config['icon']}")
            print(f"  标签: {config['tag']}")
            
            # 模拟异步处理
            await asyncio.sleep(0.1)
            
            # 在真实环境中，这里应该：
            # 1. 请求浏览器通知权限
            # 2. 创建Notification对象
            # 3. 处理用户交互
            # 4. 跟踪显示状态
            
            return True
            
        except Exception as e:
            print(f"弹窗显示失败: {str(e)}")
            return False
    
    def is_enabled(self) -> bool:
        """检查渠道是否启用"""
        return self.enabled
    
    def enable(self):
        """启用渠道"""
        self.enabled = True
        print("弹窗通知渠道已启用")
    
    def disable(self):
        """禁用渠道"""
        self.enabled = False
        print("弹窗通知渠道已禁用")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        success_rate = 0
        if self.stats["total_sent"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_sent"]) * 100
        
        return {
            "channel": self.name,
            "enabled": self.enabled,
            "stats": self.stats.copy(),
            "success_rate": round(success_rate, 2),
            "config": {
                "max_length": self.max_length,
                "display_duration": self.display_duration,
                "position": self.position
            }
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        
        # 更新相关属性
        self.max_length = config.get("max_length", self.max_length)
        self.display_duration = config.get("display_duration", self.display_duration)
        self.position = config.get("position", self.position)
        self.enabled = config.get("enabled", self.enabled)
        
        print("弹窗通知配置已更新")
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接（对于弹窗通知，总是返回成功）"""
        return {
            "status": "success",
            "message": "弹窗通知渠道可用",
            "timestamp": datetime.now().isoformat()
        }
    
    def cleanup(self):
        """清理资源"""
        # 清理统计数据
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None
        }
        print("弹窗通知渠道已清理")


# 工具函数
def create_popup_channel(config: Optional[Dict[str, Any]] = None) -> PopupNotificationChannel:
    """创建弹窗通知渠道实例"""
    return PopupNotificationChannel(config)


def get_popup_templates() -> Dict[str, Dict[str, Any]]:
    """获取弹窗模板"""
    return {
        "price_alert": {
            "title": "价格预警",
            "priority_levels": {
                1: {"icon": "ℹ️", "style": "info"},
                2: {"icon": "✅", "style": "success"},
                3: {"icon": "⚠️", "style": "warning"},
                4: {"icon": "🔴", "style": "error"},
                5: {"icon": "🆘", "style": "critical"}
            }
        },
        "volume_alert": {
            "title": "成交量预警",
            "priority_levels": {
                1: {"icon": "ℹ️", "style": "info"},
                2: {"icon": "📊", "style": "success"},
                3: {"icon": "⚡", "style": "warning"},
                4: {"icon": "🚨", "style": "error"},
                5: {"icon": "🆘", "style": "critical"}
            }
        },
        "technical_alert": {
            "title": "技术指标预警",
            "priority_levels": {
                1: {"icon": "📊", "style": "info"},
                2: {"icon": "📈", "style": "success"},
                3: {"icon": "🔔", "style": "warning"},
                4: {"icon": "⚡", "style": "error"},
                5: {"icon": "🆘", "style": "critical"}
            }
        },
        "emergency_alert": {
            "title": "紧急预警",
            "priority_levels": {
                3: {"icon": "⚠️", "style": "warning"},
                4: {"icon": "🚨", "style": "error"},
                5: {"icon": "🆘", "style": "critical"}
            }
        }
    }


if __name__ == "__main__":
    # 测试弹窗通知渠道
    import asyncio
    
    async def test_popup_channel():
        print("测试弹窗通知渠道...")
        
        # 创建渠道实例
        config = {
            "enabled": True,
            "max_length": 150,
            "display_duration": 5000,
            "position": "top-right"
        }
        
        channel = create_popup_channel(config)
        
        # 创建测试消息
        message = NotificationMessage(
            message_id="test_123",
            channel="popup",
            title="测试通知",
            content="这是一个测试弹窗通知",
            priority="normal",
            timestamp=datetime.now()
        )
        
        # 发送测试通知
        success = await channel.send_notification(message)
        print(f"测试结果: {'成功' if success else '失败'}")
        
        # 获取统计信息
        stats = channel.get_statistics()
        print(f"统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    asyncio.run(test_popup_channel())