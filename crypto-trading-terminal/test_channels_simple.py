#!/usr/bin/env python3
"""
简单测试通知渠道功能
"""

import sys
import os
from datetime import datetime
sys.path.append('.')

try:
    from backend.src.notification.channels.popup import PopupNotificationChannel, create_popup_channel
    from backend.src.notification.channels.desktop import DesktopNotificationChannel, create_desktop_channel
    from backend.src.notification.channels.telegram import TelegramNotificationChannel, create_telegram_channel
    from backend.src.notification.channels.email import EmailNotificationChannel, create_email_channel
    
    print("✅ 所有通知渠道模块导入成功")
    
    # 1. 测试弹窗通知渠道
    print("\n🔔 测试弹窗通知渠道...")
    popup_config = {"enabled": True, "max_length": 150}
    popup_channel = create_popup_channel(popup_config)
    print(f"✅ 弹窗渠道创建成功 - 启用状态: {popup_channel.enabled}")
    
    # 2. 测试桌面通知渠道
    print("\n🖥️ 测试桌面通知渠道...")
    desktop_config = {"enabled": True, "timeout": 5000}
    desktop_channel = create_desktop_channel(desktop_config)
    print(f"✅ 桌面渠道创建成功")
    print(f"   系统: {desktop_channel.system}, 可用性: {desktop_channel.available}")
    
    # 3. 测试Telegram通知渠道
    print("\n📱 测试Telegram通知渠道...")
    telegram_config = {"enabled": False, "bot_token": "test", "chat_id": "test"}
    telegram_channel = create_telegram_channel(telegram_config)
    print(f"✅ Telegram渠道创建成功 - 配置有效: {telegram_channel.config_valid}")
    
    # 4. 测试邮件通知渠道
    print("\n📧 测试邮件通知渠道...")
    email_config = {"enabled": False, "smtp_server": "smtp.gmail.com", "username": "test@test.com", "password": "test", "recipients": ["test@test.com"]}
    email_channel = create_email_channel(email_config)
    print(f"✅ 邮件渠道创建成功 - 配置有效: {email_channel.config_valid}")
    
    # 5. 获取统计信息
    print("\n📊 渠道统计信息:")
    for name, channel in [("弹窗", popup_channel), ("桌面", desktop_channel), ("Telegram", telegram_channel), ("邮件", email_channel)]:
        stats = channel.get_statistics()
        print(f"{name}渠道: 启用={stats['enabled']}, 发送={stats['stats']['total_sent']}")
    
    print("\n🎉 通知渠道测试完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()