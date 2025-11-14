# OKX专业交易工具开发配置文档

## 项目概述

- **项目名称**: OKX专业交易工具开发套件
- **版本**: 1.0.0
- **描述**: 基于欧易交易所API的专业交易工具开发套件
- **创建时间**: 2025-10-04T04:20:51.456997
- **数据源**: OKX官方API

## 交易对配置

### 现货交易对 (671个)
- **USDT-SGD**: USDT/SGD
- **USDC-SGD**: USDC/SGD
- **BTC-AUD**: BTC/AUD
- **ETH-AUD**: ETH/AUD
- **SOL-AUD**: SOL/AUD
- **XRP-AUD**: XRP/AUD
- **TRUMP-AUD**: TRUMP/AUD
- **USDT-AUD**: USDT/AUD
- **USDC-AUD**: USDC/AUD
- **BTC-AED**: BTC/AED
- ... 还有 661 个交易对

### 永续合约 (255个)
- **BTC-USD-SWAP**: 标的BTC-USD, 结算货币BTC
- **ETH-USD-SWAP**: 标的ETH-USD, 结算货币ETH
- **SOL-USD-SWAP**: 标的SOL-USD, 结算货币SOL
- **SOL-USD_UM-SWAP**: 标的SOL-USD, 结算货币USD
- **DOGE-USD-SWAP**: 标的DOGE-USD, 结算货币DOGE

### 交割合约 (23个)
- **BTC-USD-251010**: 到期日1760083200000
- **BTC-USD-251017**: 到期日1760688000000
- **BTC-USD-251031**: 到期日1761897600000
- **BTC-USD-251128**: 到期日1764316800000
- **BTC-USD-251226**: 到期日1766736000000

## API端点配置

### REST API
- **基础URL**: https://www.okx.com
- **公开端点**: 市场数据、交易产品信息等
- **私有端点**: 账户信息、交易下单等（需要API密钥）

### WebSocket API
- **公开连接**: wss://ws.okx.com:8443/ws/v5/public
- **私有连接**: wss://ws.okx.com:8443/ws/v5/private

## 开发环境配置

### 环境变量
```bash
# 开发环境
OKX_API_KEY=your_demo_api_key
OKX_SECRET_KEY=your_demo_secret_key
OKX_PASSPHRASE=your_demo_passphrase

# 生产环境  
OKX_PROD_API_KEY=your_production_api_key
OKX_PROD_SECRET_KEY=your_production_secret_key
OKX_PROD_PASSPHRASE=your_production_passphrase
```

### 安装依赖
```bash
pip install aiohttp asyncio python-socketio
```

## 使用示例

请参考生成的配置文件和示例数据进行开发。

## 数据收集时间
- 市场数据: 2025-10-04T04:17:54.229479
- API文档: 2025-10-04T04:19:08.969738

## 注意事项
1. 请妥善保管API密钥，不要提交到代码仓库
2. 遵守OKX API的频率限制
3. 在生产环境中启用适当的风险控制
4. 定期更新交易对配置信息
