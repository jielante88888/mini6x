# 🚀 OKX和币安交易所开发数据快速访问工具包

## 📋 项目概述

本项目为OKX和币安交易所提供了完整的数据访问解决方案，支持Visual Studio Community 2022和TRAE IDE集成，帮助开发者快速获取和分析交易数据。

## 🎯 功能特性

### ✅ 核心功能
- **多交易所支持**: OKX和币安交易所数据访问
- **统一数据格式**: 标准化的交易对数据结构
- **智能搜索**: 支持按货币代码搜索交易对
- **市场统计**: 实时统计交易对数量和分布
- **套利分析**: 跨交易所价格差异分析
- **IDE集成**: 深度集成VS和TRAE开发环境

### 📊 数据覆盖
- **OKX交易所**: 926个交易对（671现货/255合约）
- **币安交易所**: 3327个交易对（3266现货/61合约）
- **共同交易对**: 多交易所共有的交易对识别

## 📁 文件结构

```
OKX/
├── 数据获取快速启动器.py          # 数据验证和快速启动
├── quick_data_access.py           # 基础数据访问脚本
├── IDE数据访问助手.py              # 完整版IDE数据助手
├── IDE快速访问脚本.py              # 简化版快速访问
├── unified_data_access.py         # 统一数据访问接口
├── TRAE_MCP配置.py                # TRAE MCP服务器配置
├── trader_mcp_server.py           # MCP服务器实现
├── IDE使用说明.md                 # 详细使用指南
├── IDE代码片段.xml                # VS代码片段
├── TRAE_MCP集成指南.md            # TRAE集成指南
├── README.md                      # 项目说明
└── trader_mcp_config.json         # MCP配置
```

## 🚀 快速开始

### 1. 基础使用（推荐）

```python
# 导入快速访问脚本
import IDE快速访问脚本 as data

# 获取所有交易对
okx_pairs = data.okx()           # OKX交易对
binance_pairs = data.binance()   # 币安交易对

# 搜索特定货币
btc_results = data.search("BTC")  # 搜索BTC相关交易对

# 获取统计信息
stats = data.stats()              # 市场统计信息

# 获取共同交易对
common = data.common()            # 两个交易所都有的交易对
```

### 2. 高级使用

```python
# 使用完整版数据助手
import IDE数据访问助手 as helper

# 获取全局实例统计
helper.print_summary()

# 搜索交易对
results = helper.search_pairs("USDT")

# 获取特定交易所数据
okx_btc = helper.get_okx_pairs("BTC")
binance_eth = helper.get_binance_pairs("ETH")
```

### 3. 命令行使用

```bash
# 运行快速访问测试
python IDE快速访问脚本.py

# 运行数据助手测试
python IDE数据访问助手.py

# 验证数据文件
python 数据获取快速启动器.py
```

## 🛠️ IDE集成

### Visual Studio Community 2022

#### 代码片段使用
1. 导入 `IDE代码片段.xml` 到VS代码片段管理器
2. 使用快捷方式：
   - `okxdata` + Tab: 插入OKX数据访问代码
   - `bnbdata` + Tab: 插入币安数据访问代码
   - `searchpairs` + Tab: 插入交易对搜索代码
   - `marketstats` + Tab: 插入市场统计代码
   - `arbitrage` + Tab: 插入套利分析代码

#### 智能感知
- 完整的函数参数提示
- 返回类型说明
- 使用示例展示

### TRAE IDE

#### MCP服务器集成
1. 运行配置生成器：
   ```bash
   python TRAE_MCP配置.py
   ```

2. 在TRAE中配置MCP服务器：
   ```json
   {
     "mcp_servers": {
       "crypto_trading_data": {
         "command": "python",
         "args": ["-m", "trader_mcp_server"]
       }
     }
   }
   ```

3. 使用Spec-Kit工作流：
   ```
   /specify 创建数据访问和分析任务
   ```

#### 直接调用
```python
# 在TRAE Python控制台
import IDE快速访问脚本 as data
data.okx()  # 获取OKX数据
data.search("BTC")  # 搜索BTC交易对
```

## 📊 数据结构

### 交易对信息
```python
{
    'symbol': 'BTC-USDT',           # 交易对符号
    'base': 'BTC',                  # 基础货币
    'quote': 'USDT',                # 计价货币
    'type': 'spot',                 # 类型: spot/swap
    'last_price': '43250.50',       # 最新价格
    'price_change_24h': '2.5%',     # 24小时涨跌幅
    'volume_24h': '1234567.89',     # 24小时交易量
    'exchange': 'OKX'               # 交易所
}
```

### 统计信息
```python
{
    'okx': {
        'total': 926,               # 总交易对数
        'spot': 671,                # 现货交易对
        'swap': 255                 # 合约交易对
    },
    'binance': {
        'total': 3327,              # 总交易对数
        'spot': 3266,               # 现货交易对
        'futures': 61               # 合约交易对
    },
    'common_pairs': 45              # 共同交易对数
}
```

## 🔍 使用示例

### 1. 套利机会发现
```python
import IDE快速访问脚本 as data

# 获取共同交易对
common_pairs = data.common()

# 分析价格差异
arbitrage_opportunities = []
for pair in common_pairs:
    if pair.get('okx_price') and pair.get('binance_price'):
        okx_price = float(pair['okx_price'])
        binance_price = float(pair['binance_price'])
        price_diff = abs(okx_price - binance_price) / min(okx_price, binance_price) * 100
        
        if price_diff > 1.0:  # 价格差异大于1%
            arbitrage_opportunities.append({
                'symbol': pair['symbol'],
                'price_diff': price_diff,
                'okx_price': okx_price,
                'binance_price': binance_price
            })

# 按价格差异排序
arbitrage_opportunities.sort(key=lambda x: x['price_diff'], reverse=True)
```

### 2. 市场覆盖分析
```python
# 获取统计信息
stats = data.stats()

# 分析市场覆盖
print("市场覆盖分析:")
print(f"OKX总交易对: {stats['okx']['total']}")
print(f"币安总交易对: {stats['binance']['total']}")
print(f"共同交易对: {stats['common_pairs']}")
print(f"OKX独特交易对: {stats['okx']['total'] - stats['common_pairs']}")
print(f"币安独特交易对: {stats['binance']['total'] - stats['common_pairs']}")
```

### 3. 价格监控
```python
def monitor_price(symbol, duration=60):
    """监控指定交易对价格变化"""
    print(f"=== 监控 {symbol} 价格变化 ===")
    
    # 获取当前价格
    all_pairs = data.search(symbol)
    
    for exchange, pairs in all_pairs.items():
        print(f"\n{exchange} {symbol} 交易对:")
        for pair in pairs:
            price = pair.get('last_price', 'N/A')
            change = pair.get('price_change_24h', 'N/A')
            print(f"  - {pair['symbol']}: {price} (24h: {change})")

# 监控BTC和ETH
monitor_price("BTC")
monitor_price("ETH")
```

## 🔧 故障排除

### 常见问题

1. **数据文件找不到**
   - 确保数据文件在当前目录
   - 检查文件名格式是否正确
   - 运行数据验证脚本

2. **交易对数量为0**
   - 验证数据文件是否包含有效数据
   - 检查数据文件格式是否支持
   - 重新运行数据获取脚本

3. **搜索无结果**
   - 确认关键词拼写正确
   - 尝试使用大写关键词
   - 检查数据文件完整性

### 调试方法

```python
# 启用调试模式
import IDE快速访问脚本 as data

# 检查数据文件
print("当前目录文件:")
import os
for f in os.listdir('.'):
    if 'market_data' in f:
        print(f"  - {f}")

# 手动加载数据验证
okx_pairs = data.load_okx_pairs()
binance_pairs = data.load_binance_pairs()
print(f"OKX: {len(okx_pairs)} 个交易对")
print(f"币安: {len(binance_pairs)} 个交易对")
```

## 🚀 扩展开发

### 自定义分析
基于现有框架，您可以轻松扩展：

- **技术指标计算**: RSI、MACD、布林带等
- **机器学习模型**: 价格预测、趋势识别
- **自动化交易**: 基于规则的自动交易
- **实时监控**: 价格告警和通知
- **历史回测**: 策略回测和优化

### 数据源扩展
支持添加新的交易所：

1. 实现数据加载函数
2. 添加格式转换逻辑
3. 更新统计计算
4. 集成到现有框架

## 📈 性能优化

### 大数据处理
- 使用生成器减少内存占用
- 实现数据分页加载
- 添加缓存机制
- 支持异步处理

### 实时更新
- 定时数据刷新
- 增量数据更新
- 变化检测和通知

## 📚 相关文档

- [IDE使用说明](IDE使用说明.md) - 详细的IDE集成指南
- [TRAE_MCP集成指南](TRAE_MCP集成指南.md) - TRAE MCP服务器集成
- [Spec-Kit工作流](https://github.com/spec-kit/spec-kit) - 规范驱动开发

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目：

1. Fork项目仓库
2. 创建功能分支
3. 提交您的修改
4. 创建Pull Request

## 📄 许可证

MIT License - 详见LICENSE文件

## 🆘 支持

如有问题，请：

1. 查看故障排除部分
2. 检查相关文档
3. 提交Issue报告

---

**💡 提示**: 本项目遵循Spec-Kit工作流进行规范驱动开发，确保代码质量和可维护性。

**🎯 总结**: 这是一个功能完整的交易所数据访问工具包，支持多种IDE环境，提供了丰富的数据分析和套利功能，非常适合量化交易和数据分析工作。