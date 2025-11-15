"""
Simple test for OKX Spot adapter connection and basic functionality
"""

import asyncio
import sys
import os

# Add the path to the backend source
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_path)

async def test_okx_spot_adapter():
    """测试OKX现货适配器的基本功能"""
    
    try:
        # 直接导入适配器
        from src.adapters.okx.spot import OKXSpotAdapter
        from src.adapters.base import MarketData, OrderBook, Trade
        
        print("✅ 成功导入OKX现货适配器")
        
        # 创建适配器实例
        adapter = OKXSpotAdapter(is_testnet=True)
        print("✅ 成功创建OKX现货适配器实例")
        
        # 测试连接
        print("🔄 测试连接到OKX API...")
        connected = await adapter.connect()
        
        if connected:
            print("✅ 成功连接到OKX API")
            
            # 测试健康检查
            print("🔄 执行健康检查...")
            health = await adapter.health_check()
            print(f"✅ 健康检查结果: {health.get('status', 'unknown')}")
            
            # 测试获取BTC价格 (注意：OKX使用不同的交易对格式)
            print("🔄 获取BTC-USDT价格...")
            try:
                ticker = await adapter.get_spot_ticker("BTC-USDT")
                print(f"✅ BTC-USDT价格: ${ticker.current_price}")
                print(f"   24h涨跌幅: {ticker.price_change_percent}%")
                print(f"   24h成交量: {ticker.volume_24h}")
            except Exception as e:
                print(f"❌ 获取BTC-USDT价格失败: {e}")
            
            # 测试获取订单簿
            print("🔄 获取BTC-USDT订单簿...")
            try:
                order_book = await adapter.get_spot_order_book("BTC-USDT", limit=10)
                print(f"✅ 订单簿获取成功")
                print(f"   买盘数量: {len(order_book.bids)}")
                print(f"   卖盘数量: {len(order_book.asks)}")
            except Exception as e:
                print(f"❌ 获取订单簿失败: {e}")
            
            # 测试获取交易记录
            print("🔄 获取BTC-USDT交易记录...")
            try:
                trades = await adapter.get_spot_trades("BTC-USDT", limit=5)
                print(f"✅ 交易记录获取成功: {len(trades)}条记录")
            except Exception as e:
                print(f"❌ 获取交易记录失败: {e}")
            
        else:
            print("❌ 无法连接到OKX API")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理连接
        if 'adapter' in locals():
            await adapter.disconnect()
            print("🔄 已断开连接")


async def test_adapter_factory_okx():
    """测试OKX适配器工厂功能"""
    
    try:
        from src.adapters.base import ExchangeAdapterFactory
        
        print("\n🔄 测试OKX适配器工厂...")
        
        # 注册适配器（通过装饰器自动注册）
        exchanges = ExchangeAdapterFactory.get_supported_exchanges()
        print(f"✅ 支持的交易所: {exchanges}")
        
        # 测试创建OKX适配器
        okx_spot = ExchangeAdapterFactory.create_adapter(
            "okx", 
            is_testnet=True
        )
        print(f"✅ 成功创建OKX现货适配器: {okx_spot.exchange_name}")
        
        # 测试创建OKX期货适配器
        okx_futures = ExchangeAdapterFactory.create_adapter(
            "okx_futures", 
            is_testnet=True
        )
        print(f"✅ 成功创建OKX期货适配器: {okx_futures.exchange_name}")
        
    except Exception as e:
        print(f"❌ OKX工厂测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("🚀 开始OKX现货适配器测试")
    print("=" * 50)
    
    # 测试基本适配器功能
    await test_okx_spot_adapter()
    
    # 测试适配器工厂
    await test_adapter_factory_okx()
    
    print("\n" + "=" * 50)
    print("🏁 OKX测试完成")


if __name__ == "__main__":
    asyncio.run(main())