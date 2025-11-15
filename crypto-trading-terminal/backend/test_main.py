"""
基础测试文件 - 确保CI流水线能够正常运行
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """测试根路径端点"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "status" in data

def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "crypto-trading-backend"

def test_markets_endpoint():
    """测试市场数据端点"""
    response = client.get("/api/markets")
    assert response.status_code == 200
    data = response.json()
    assert "markets" in data
    assert len(data["markets"]) > 0

@pytest.mark.asyncio
async def test_websocket_connection():
    """测试WebSocket连接"""
    from main import ConnectionManager
    from fastapi import WebSocket
    
    manager = ConnectionManager()
    
    # 模拟WebSocket连接
    class MockWebSocket:
        def __init__(self):
            self.accepted = False
            self.sent_messages = []
            
        async def accept(self):
            self.accepted = True
            
        async def send_text(self, message):
            self.sent_messages.append(message)
            
    mock_ws = MockWebSocket()
    await manager.connect(mock_ws)
    assert manager.active_connections == [mock_ws]
    
    await manager.send_personal_message("test", mock_ws)
    assert "test" in mock_ws.sent_messages