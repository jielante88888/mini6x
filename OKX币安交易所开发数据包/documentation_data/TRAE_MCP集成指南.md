# 🚀 TRAE IDE集成指南

## 概述

本指南帮助您在TRAE IDE中集成OKX和币安数据访问功能。

## 📋 集成步骤

### 1. 配置MCP服务器

在TRAE设置中添加MCP服务器配置：

```json
{
  "mcp_servers": {
    "crypto_trading_data": {
      "command": "python",
      "args": ["-m", "trader_mcp_server"],
      "env": {
        "PYTHONPATH": ".",
        "DATA_DIR": "./"
      }
    }
  }
}
```

### 2. 使用Spec-Kit工作流

在TRAE中使用以下命令：

```bash
# 创建数据访问项目
specify init crypto-data-access --ai claude

# 创建数据访问任务
specify create-task "集成OKX和币安数据访问"
```

### 3. 在TRAE中使用数据访问

```python
# 在TRAE Python控制台中
import trader_mcp_client

# 获取OKX数据
okx_data = trader_mcp_client.get_okx_pairs()

# 搜索交易对
search_results = trader_mcp_client.search_trading_pairs("BTC")

# 获取统计信息
stats = trader_mcp_client.get_market_stats()
```

## 🎯 常用操作

### 数据查询
```python
# 获取所有OKX交易对
okx_pairs = trader_mcp_client.get_okx_pairs()

# 获取BTC相关交易对
btc_pairs = trader_mcp_client.get_okx_pairs("BTC")

# 搜索USDT交易对
usdt_results = trader_mcp_client.search_trading_pairs("USDT")
```

### 市场分析
```python
# 获取共同交易对
common_pairs = trader_mcp_client.get_common_pairs()

# 获取市场统计
market_stats = trader_mcp_client.get_market_stats()

# 分析套利机会
arbitrage = trader_mcp_client.find_arbitrage_opportunities()
```

## 🔧 故障排除

### MCP服务器连接问题
1. 检查Python环境
2. 验证数据文件存在
3. 检查网络连接

### 数据加载问题
1. 验证数据文件格式
2. 检查文件路径
3. 确认数据文件完整性

## 📈 高级功能

### 实时数据监控
```python
# 设置价格监控
trader_mcp_client.setup_price_monitor(["BTC-USDT", "ETH-USDT"])
```

### 自动化交易信号
```python
# 获取交易信号
signals = trader_mcp_client.get_trading_signals()
```

## 💡 最佳实践

1. **缓存数据**：使用TRAE的缓存机制
2. **错误处理**：添加完善的错误处理
3. **性能优化**：使用异步处理
4. **数据验证**：定期验证数据完整性

---

**注意**：确保MCP服务器正在运行，数据文件存在且格式正确。
