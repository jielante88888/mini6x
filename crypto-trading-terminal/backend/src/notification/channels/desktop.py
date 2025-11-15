"""
Desktop notification channel
Handles system desktop notifications
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import platform
import sys

from ..notify_manager import NotificationMessage, DeliveryStatus, DeliveryRecord


class DesktopNotificationChannel:
    """Desktop notification channel handler"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = "desktop"
        self.enabled = self.config.get("enabled", True)
        
        # Desktop notification config
        self.timeout = self.config.get("timeout", 5000)  # milliseconds
        self.urgency = self.config.get("urgency", "normal")  # low, normal, critical
        self.category = self.config.get("category", "trading")
        self.app_name = self.config.get("app_name", "Crypto Trading Terminal")
        self.icon_path = self.config.get("icon_path", None)
        
        # Statistics
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None
        }
        
        # System detection
        self.system = self._detect_system()
        self.available = self._check_availability()
        
        # Priority mapping
        self.priority_mapping = {
            "low": "low",
            "normal": "normal", 
            "high": "normal",
            "urgent": "critical",
            "critical": "critical"
        }
    
    def _detect_system(self) -> str:
        """Detect operating system"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    def _check_availability(self) -> bool:
        """Check desktop notification availability"""
        try:
            if self.system == "linux":
                # Check if notify-send is available
                result = subprocess.run(
                    ["which", "notify-send"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            elif self.system in ["windows", "macos"]:
                # Assume notification is available on these systems
                return True
            else:
                return False
        except Exception:
            return False
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send desktop notification"""
        try:
            if not self.enabled or not self.available:
                return False
            
            # Update statistics
            self.stats["total_sent"] += 1
            self.stats["last_used"] = datetime.now()
            
            # Process message content
            title = self._format_title(message)
            body = self._format_body(message)
            
            # Send notification based on system
            success = False
            if self.system == "linux":
                success = await self._send_linux_notification(title, body, message)
            elif self.system == "windows":
                success = await self._send_windows_notification(title, body, message)
            elif self.system == "macos":
                success = await self._send_macos_notification(title, body, message)
            else:
                print(f"Unsupported system: {self.system}")
                success = False
            
            if success:
                self.stats["successful"] += 1
                print(f"Desktop notification sent successfully: {message.message_id}")
            else:
                self.stats["failed"] += 1
                print(f"Desktop notification failed: {message.message_id}")
            
            return success
            
        except Exception as e:
            self.stats["failed"] += 1
            print(f"Desktop notification error: {str(e)}")
            return False
    
    def _format_title(self, message: NotificationMessage) -> str:
        """Format notification title"""
        return f"{self.app_name}: {message.title}"
    
    def _format_body(self, message: NotificationMessage) -> str:
        """Format notification body"""
        # Format message content
        body = message.content.strip()
        
        # Add timestamp
        time_str = message.timestamp.strftime("%H:%M:%S")
        body = f"{body}\nTime: {time_str}"
        
        # Add priority info
        priority_text = {
            "low": "Low Priority",
            "normal": "Normal",
            "high": "High Priority",
            "urgent": "Urgent",
            "critical": "Critical"
        }.get(message.priority.value, "Normal")
        
        body = f"{body}\nPriority: {priority_text}"
        
        return body
    
    async def _send_linux_notification(self, title: str, body: str, message: NotificationMessage) -> bool:
        """Send Linux desktop notification"""
        try:
            # Build notify-send command
            urgency = self.priority_mapping.get(message.priority.value, "normal")
            timeout_ms = self.timeout
            
            cmd = [
                "notify-send",
                "-u", urgency,  # Urgency
                "-t", str(timeout_ms),  # Timeout
                "-c", self.category,  # Category
                "-a", self.app_name,  # App name
                title,
                body
            ]
            
            # Add icon if specified
            if self.icon_path:
                cmd.extend(["-i", self.icon_path])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                print(f"notify-send error: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"Linux desktop notification failed: {str(e)}")
            return False
    
    async def _send_windows_notification(self, title: str, body: str, message: NotificationMessage) -> bool:
        """Send Windows desktop notification"""
        try:
            # For Windows, we can use win10toast library or other methods
            # Here we use a simulated implementation
            
            print(f"Windows desktop notification:")
            print(f"  Title: {title}")
            print(f"  Body: {body}")
            
            # Simulate async processing
            await asyncio.sleep(0.1)
            
            # Real implementation should use:
            # import win10toast
            # toaster = win1010toast.ToastNotifier()
            # toaster.show_toast(title, body, duration=self.timeout/1000)
            
            return True
            
        except Exception as e:
            print(f"Windows desktop notification failed: {str(e)}")
            return False
    
    async def _send_macos_notification(self, title: str, body: str, message: NotificationMessage) -> bool:
        """Send macOS desktop notification"""
        try:
            # On macOS, use osascript or third-party libraries
            print(f"macOS desktop notification:")
            print(f"  Title: {title}")
            print(f"  Body: {body}")
            
            # Simulate async processing
            await asyncio.sleep(0.1)
            
            # Real implementation should use:
            # import pync
            # pync.notify(body, title=title, sound="default")
            
            return True
            
        except Exception as e:
            print(f"macOS desktop notification failed: {str(e)}")
            return False
    
    def is_enabled(self) -> bool:
        """Check if channel is enabled"""
        return self.enabled and self.available
    
    def enable(self):
        """Enable channel"""
        if self.available:
            self.enabled = True
            print("Desktop notification channel enabled")
        else:
            print("Desktop notification not available, cannot enable")
    
    def disable(self):
        """Disable channel"""
        self.enabled = False
        print("Desktop notification channel disabled")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        success_rate = 0
        if self.stats["total_sent"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_sent"]) * 100
        
        return {
            "channel": self.name,
            "enabled": self.enabled,
            "available": self.available,
            "system": self.system,
            "stats": self.stats.copy(),
            "success_rate": round(success_rate, 2),
            "config": {
                "timeout": self.timeout,
                "urgency": self.urgency,
                "category": self.category,
                "app_name": self.app_name
            }
        }
    
    def update_config(self, config: Dict[str, Any]):
        """Update configuration"""
        self.config.update(config)
        
        # Update related attributes
        self.timeout = config.get("timeout", self.timeout)
        self.urgency = config.get("urgency", self.urgency)
        self.category = config.get("category", self.category)
        self.app_name = config.get("app_name", self.app_name)
        self.icon_path = config.get("icon_path", self.icon_path)
        self.enabled = config.get("enabled", self.enabled)
        
        # Recheck availability
        self.available = self._check_availability()
        
        print("Desktop notification configuration updated")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection"""
        if not self.available:
            return {
                "status": "error",
                "message": f"Desktop notification not available on {self.system}",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "message": f"Desktop notification available on {self.system}",
            "system": self.system,
            "timestamp": datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "last_used": None
        }
        print("Desktop notification channel cleaned up")


# Utility functions
def create_desktop_channel(config: Optional[Dict[str, Any]] = None) -> DesktopNotificationChannel:
    """Create desktop notification channel instance"""
    return DesktopNotificationChannel(config)


def get_desktop_templates() -> Dict[str, Dict[str, Any]]:
    """Get desktop notification templates"""
    return {
        "price_alert": {
            "category": "trading.price",
            "urgency": "normal",
            "timeout": 5000,
            "actions": ["view_details", "dismiss"]
        },
        "volume_alert": {
            "category": "trading.volume", 
            "urgency": "normal",
            "timeout": 4000,
            "actions": ["view_details", "dismiss"]
        },
        "technical_alert": {
            "category": "trading.technical",
            "urgency": "normal", 
            "timeout": 6000,
            "actions": ["view_chart", "dismiss"]
        },
        "emergency_alert": {
            "category": "system.emergency",
            "urgency": "critical",
            "timeout": 0,  # Don't auto-close
            "actions": ["acknowledge", "details"]
        }
    }


if __name__ == "__main__":
    # Test desktop notification channel
    import asyncio
    
    async def test_desktop_channel():
        print("Testing desktop notification channel...")
        
        config = {
            "enabled": True,
            "timeout": 5000,
            "urgency": "normal",
            "category": "trading",
            "app_name": "Crypto Trading Terminal"
        }
        
        channel = create_desktop_channel(config)
        
        print(f"System: {channel.system}")
        print(f"Available: {channel.available}")
        
        if channel.available:
            message = NotificationMessage(
                message_id="test_456",
                channel="desktop", 
                title="Test Notification",
                content="This is a desktop notification test",
                priority="normal",
                timestamp=datetime.now()
            )
            
            success = await channel.send_notification(message)
            print(f"Test result: {'success' if success else 'failed'}")
        
        stats = channel.get_statistics()
        print(f"Statistics: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    asyncio.run(test_desktop_channel())