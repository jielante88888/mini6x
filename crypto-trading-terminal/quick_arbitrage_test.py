#!/usr/bin/env python3
"""
套利策略快速验证测试
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

from decimal import Decimal
from datetime import datetime

from strategies.spot.arbitrage import (
    ArbitrageStrategy, 
    ExchangeName, 
    ExchangePrice
)
from strategies.base import (
    StrategyConfig, 
    StrategyType, 
    MarketData
)

async def quick_test():
    """快速功能验证"""
    print("🔍 开始套利策略快速验证...")
    
    try:
        # 创建配置
        config = StrategyConfig(
            strategy_id="quick_test",
            strategy_type=StrategyType.ARBITRAGE,
            user_id=1,
            account_id=1,
            symbol="BTCUSDT",
            base_quantity=Decimal('0.001'),
            arbitrage_threshold=Decimal('0.01')
        )
        
        # 创建策略
        strategy = ArbitrageStrategy(config)
        
        # 初始化
        await strategy.initialize()
        print("✅ 策略初始化成功")
        
        # 启动
        await strategy.start()
        print("✅ 策略启动成功")
        
        # 添加价格数据
        strategy.update_exchange_price(ExchangeName.BINANCE, {
            'symbol': 'BTCUSDT',
            'bid_price': '50000',
            'ask_price': '50100',
            'fee_rate': '0.001'
        })
        
        strategy.update_exchange_price(ExchangeName.OKX, {
            'symbol': 'BTCUSDT',
            'bid_price': '50200',
            'ask_price': '50300',
            'fee_rate': '0.001'
        })
        
        # 创建市场数据
        market_data = MarketData(
            symbol="BTCUSDT",
            current_price=Decimal('50200'),
            bid_price=Decimal('50100'),
            ask_price=Decimal('50300'),
            volume_24h=Decimal('1000000'),
            price_change_24h=Decimal('0.02'),
            timestamp=datetime.now()
        )
        
        # 处理市场数据
        await strategy.process_market_data(market_data)
        print("✅ 市场数据处理成功")
        
        # 获取订单
        orders = await strategy.get_next_orders(market_data)
        print(f"✅ 生成订单: {len(orders)} 个")
        
        # 获取状态
        status = strategy.get_arbitrage_status()
        print(f"✅ 策略状态: 活跃机会{status['active_opportunities']}, 监控交易所{status['total_exchanges_monitored']}")
        
        # 停止策略
        await strategy.stop()
        print("✅ 策略停止成功")
        
        print("\n🎉 套利策略快速验证通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(quick_test())
    exit(0 if result else 1)