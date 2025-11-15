"""
邮件通知渠道
处理SMTP邮件发送功能
"""

import asyncio
import smtplib
import ssl
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, format_datetime
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..notify_manager import NotificationMessage, DeliveryStatus, DeliveryRecord


class EmailNotificationChannel:
    """邮件通知渠道处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = "email"
        self.enabled = self.config.get("enabled", False)  # 默认禁用，需要配置
        
        # 邮件服务器配置
        self.smtp_server = self.config.get("smtp_server")
        self.smtp_port = self.config.get("smtp_port", 587)  # 默认587 (STARTTLS)
        self.username = self.config.get("username")
        self.password = self.config.get("password")
        self.use_tls = self.config.get("use_tls", True)
        self.use_ssl = self.config.get("use_ssl", False)
        
        # 邮件内容配置
        self.from_name = self.config.get("from_name", "Crypto Trading Terminal")
        self.from_email = self.config.get("from_email", self.username)
        self.recipients = self.config.get("recipients", [])
        self.subject_prefix = self.config.get("subject_prefix", "[Crypto Alert]")
        self.reply_to = self.config.get("reply_to")
        
        # 内容配置
        self.include_html = self.config.get("include_html", True)
        self.include_text = self.config.get("include_text", True)
        self.max_content_length = self.config.get("max_content_length", 10000)
        
        # 统计数据
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None,
            "bytes_sent": 0
        }
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        required_fields = ["smtp_server", "username", "password", "recipients"]
        self.config_valid = all(self.config.get(field) for field in required_fields)
        
        if not self.config_valid:
            print("⚠️ 邮件配置不完整，需要smtp_server, username, password, recipients")
        
        # 验证收件人格式
        if isinstance(self.recipients, str):
            self.recipients = [self.recipients]
        elif not isinstance(self.recipients, list):
            self.recipients = []
        
        # 验证SMTP端口
        if self.smtp_port not in [25, 465, 587, 2525]:
            print(f"⚠️ 非标准SMTP端口: {self.smtp_port}")
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        try:
            if not self.enabled or not self.config_valid:
                return False
            
            # 更新统计数据
            self.stats["total_sent"] += 1
            self.stats["last_used"] = datetime.now()
            
            # 构建邮件内容
            subject = self._build_subject(message)
            html_body, text_body = self._build_email_body(message)
            
            # 限制内容长度
            html_body, text_body = self._limit_content_length(html_body, text_body)
            
            # 发送邮件
            for attempt in range(3):  # 最多重试3次
                try:
                    success = await self._send_email(
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body
                    )
                    
                    if success:
                        self.stats["successful"] += 1
                        self.stats["bytes_sent"] += len(html_body.encode('utf-8'))
                        print(f"邮件通知发送成功: {message.message_id}")
                        return True
                    else:
                        if attempt < 2:
                            print(f"邮件发送失败，第{attempt + 1}次重试...")
                            await asyncio.sleep(2)  # 2秒后重试
                        else:
                            self.stats["failed"] += 1
                            print(f"邮件通知发送失败: {message.message_id}")
                
                except Exception as e:
                    if attempt < 2:
                        print(f"邮件发送异常，第{attempt + 1}次重试: {str(e)}")
                        await asyncio.sleep(2)
                    else:
                        self.stats["failed"] += 1
                        print(f"邮件通知发送异常: {str(e)}")
                        return False
            
            return False
            
        except Exception as e:
            self.stats["failed"] += 1
            print(f"邮件通知异常: {str(e)}")
            return False
    
    def _build_subject(self, message: NotificationMessage) -> str:
        """构建邮件主题"""
        # 根据优先级调整主题前缀
        priority_prefix = {
            "low": "[信息]",
            "normal": "",
            "high": "[重要]",
            "urgent": "[紧急]",
            "critical": "[紧急]"
        }.get(message.priority.value, "")
        
        prefix = f"{self.subject_prefix} {priority_prefix}".strip()
        return f"{prefix} {message.title}" if prefix else message.title
    
    def _build_email_body(self, message: NotificationMessage) -> tuple[str, str]:
        """构建邮件正文"""
        # HTML版本
        html_body = self._build_html_body(message)
        
        # 文本版本
        text_body = self._build_text_body(message)
        
        return html_body, text_body
    
    def _build_html_body(self, message: NotificationMessage) -> str:
        """构建HTML邮件正文"""
        # 根据优先级选择颜色主题
        color_theme = self._get_color_theme(message.priority.value)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{message.title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .email-container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, {color_theme['primary']}, {color_theme['secondary']});
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 30px 20px;
                }}
                .alert-info {{
                    background: {color_theme['background']};
                    border-left: 4px solid {color_theme['accent']};
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .field {{
                    margin: 10px 0;
                }}
                .field-label {{
                    font-weight: 600;
                    color: #555;
                    display: inline-block;
                    min-width: 100px;
                }}
                .field-value {{
                    background: #f8f9fa;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    border: 1px solid #e9ecef;
                }}
                .priority {{
                    display: inline-block;
                    padding: 6px 12px;
                    background: {color_theme['accent']};
                    color: white;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-top: 1px solid #e9ecef;
                }}
                .timestamp {{
                    color: #888;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>{message.title}</h1>
                </div>
                
                <div class="content">
                    <div class="alert-info">
                        <div class="field">
                            <span class="field-label">消息ID:</span>
                            <span class="field-value">{message.message_id}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">优先级:</span>
                            <span class="priority">{self._get_priority_text(message.priority.value)}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">详情:</span>
                            <div style="margin-top: 10px; padding: 12px; background: white; border-radius: 4px; border: 1px solid #e9ecef;">
                                {message.content.replace(chr(10), '<br>')}
                            </div>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">时间:</span>
                            <span class="timestamp">{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</span>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>此邮件由 <strong>Crypto Trading Terminal</strong> 自动发送</p>
                    <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_text_body(self, message: NotificationMessage) -> str:
        """构建纯文本邮件正文"""
        lines = [
            "=" * 60,
            f"    {message.title.upper()}",
            "=" * 60,
            "",
            f"消息ID: {message.message_id}",
            f"优先级: {self._get_priority_text(message.priority.value)}",
            "",
            "详情:",
            "-" * 40,
            message.content,
            "",
            "时间:",
            "-" * 40,
            message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "",
            "=" * 60,
            "此邮件由 Crypto Trading Terminal 自动发送",
            f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60
        ]
        
        return "\n".join(lines)
    
    def _get_color_theme(self, priority: str) -> Dict[str, str]:
        """获取颜色主题"""
        themes = {
            "low": {
                "primary": "#6c757d",
                "secondary": "#495057", 
                "accent": "#6c757d",
                "background": "#f8f9fa"
            },
            "normal": {
                "primary": "#28a745",
                "secondary": "#20c997",
                "accent": "#28a745", 
                "background": "#f8fff9"
            },
            "high": {
                "primary": "#fd7e14",
                "secondary": "#e55100",
                "accent": "#fd7e14",
                "background": "#fff8f0"
            },
            "urgent": {
                "primary": "#dc3545",
                "secondary": "#c82333",
                "accent": "#dc3545",
                "background": "#fff5f5"
            },
            "critical": {
                "primary": "#6f42c1",
                "secondary": "#5a32a3", 
                "accent": "#6f42c1",
                "background": "#f8f5ff"
            }
        }
        return themes.get(priority, themes["normal"])
    
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
    
    def _limit_content_length(self, html_body: str, text_body: str) -> tuple[str, str]:
        """限制内容长度"""
        if len(html_body) > self.max_content_length:
            html_body = html_body[:self.max_content_length-100] + "...</body></html>"
        
        if len(text_body) > self.max_content_length:
            text_body = text_body[:self.max_content_length-50] + "\n\n... (内容已截断)"
        
        return html_body, text_body
    
    async def _send_email(self, subject: str, html_body: str, text_body: str) -> bool:
        """发送邮件"""
        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            
            # 设置邮件头
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = subject
            msg['Date'] = format_datetime(datetime.now())
            msg['X-Mailer'] = 'Crypto Trading Terminal'
            
            # 添加回复地址
            if self.reply_to:
                msg['Reply-To'] = self.reply_to
            
            # 添加纯文本版本
            if self.include_text:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # 添加HTML版本
            if self.include_html:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # 发送邮件
            if self.use_ssl:
                # SSL连接 (端口 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg)
            else:
                # TLS连接 (端口 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    server.login(self.username, self.password)
                    server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {str(e)}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        if not self.config_valid:
            return {
                "status": "error",
                "message": "邮件配置不完整",
                "config_valid": False,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # 发送测试邮件
            test_message = NotificationMessage(
                message_id="test_connection",
                channel="email",
                title="连接测试",
                content="这是一封邮件通知渠道连接测试邮件",
                priority="normal",
                timestamp=datetime.now()
            )
            
            success = await self.send_notification(test_message)
            
            if success:
                return {
                    "status": "success",
                    "message": "邮件连接正常",
                    "config_valid": True,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error", 
                    "message": "邮件发送测试失败",
                    "config_valid": True,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"邮件连接测试异常: {str(e)}",
                "config_valid": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def is_enabled(self) -> bool:
        """检查渠道是否启用"""
        return self.enabled and self.config_valid
    
    def enable(self):
        """启用渠道"""
        if self.config_valid:
            self.enabled = True
            print("邮件通知渠道已启用")
        else:
            print("邮件配置不完整，无法启用")
    
    def disable(self):
        """禁用渠道"""
        self.enabled = False
        print("邮件通知渠道已禁用")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        success_rate = 0
        if self.stats["total_sent"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_sent"]) * 100
        
        avg_size = 0
        if self.stats["successful"] > 0:
            avg_size = self.stats["bytes_sent"] / self.stats["successful"]
        
        return {
            "channel": self.name,
            "enabled": self.enabled,
            "config_valid": self.config_valid,
            "stats": self.stats.copy(),
            "success_rate": round(success_rate, 2),
            "average_email_size": round(avg_size, 2),
            "config": {
                "smtp_server": self.smtp_server,
                "smtp_port": self.smtp_port,
                "use_tls": self.use_tls,
                "use_ssl": self.use_ssl,
                "from_name": self.from_name,
                "recipients_count": len(self.recipients)
            }
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        
        # 更新相关属性
        self.smtp_server = config.get("smtp_server", self.smtp_server)
        self.smtp_port = config.get("smtp_port", self.smtp_port)
        self.username = config.get("username", self.username)
        self.password = config.get("password", self.password)
        self.use_tls = config.get("use_tls", self.use_tls)
        self.use_ssl = config.get("use_ssl", self.use_ssl)
        self.from_name = config.get("from_name", self.from_name)
        self.from_email = config.get("from_email", self.from_email)
        self.recipients = config.get("recipients", self.recipients)
        self.subject_prefix = config.get("subject_prefix", self.subject_prefix)
        self.enabled = config.get("enabled", self.enabled)
        
        # 重新验证配置
        self._validate_config()
        
        print("邮件配置已更新")
    
    def cleanup(self):
        """清理资源"""
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None,
            "bytes_sent": 0
        }
        print("邮件通知渠道已清理")
    
    def get_smtp_config_examples(self) -> Dict[str, Dict[str, Any]]:
        """获取常用SMTP配置示例"""
        return {
            "Gmail": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False,
                "note": "需要开启两步验证并生成应用专用密码"
            },
            "Outlook": {
                "smtp_server": "smtp-mail.outlook.com", 
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False,
                "note": "使用您的Outlook账户"
            },
            "QQ邮箱": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False,
                "note": "需要在QQ邮箱中开启SMTP服务"
            },
            "163邮箱": {
                "smtp_server": "smtp.163.com",
                "smtp_port": 587,
                "use_tls": True,
                "use_ssl": False,
                "note": "需要在163邮箱中开启SMTP服务"
            },
            "SSL连接": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 465,
                "use_tls": False,
                "use_ssl": True,
                "note": "使用SSL加密连接"
            }
        }


# 工具函数
def create_email_channel(config: Optional[Dict[str, Any]] = None) -> EmailNotificationChannel:
    """创建邮件通知渠道实例"""
    return EmailNotificationChannel(config)


if __name__ == "__main__":
    # 测试邮件通知渠道
    import asyncio
    
    async def test_email_channel():
        print("测试邮件通知渠道...")
        
        # 邮件配置示例
        config = {
            "enabled": False,  # 需要先配置真实的SMTP信息
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "your_email@gmail.com",
            "password": "your_app_password",
            "recipients": ["recipient@example.com"],
            "from_name": "Crypto Trading Terminal",
            "subject_prefix": "[Crypto Alert]",
            "include_html": True,
            "include_text": True
        }
        
        channel = create_email_channel(config)
        print(f"配置有效: {channel.config_valid}")
        
        # 显示SMTP配置示例
        print("\n常用SMTP配置示例:")
        examples = channel.get_smtp_config_examples()
        for provider, example in examples.items():
            print(f"\n{provider}:")
            for key, value in example.items():
                print(f"  {key}: {value}")
        
        if channel.config_valid:
            # 测试连接
            test_result = await channel.test_connection()
            print(f"连接测试: {test_result}")
        
        stats = channel.get_statistics()
        print(f"统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    asyncio.run(test_email_channel())