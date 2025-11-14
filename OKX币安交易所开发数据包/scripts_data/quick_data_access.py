#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的快速数据访问脚本
为 IDE 提供便捷的数据访问接口
"""

import json
import glob
import os
from datetime import datetime

def get_latest_data_file(exchange, data_type='market_data'):
    """获取最新的数据文件"""
    pattern = f"{exchange}_{data_type}_*.json"
    files = glob.glob(pattern)
    return max(files) if files else None

def load_exchange_data(exchange):
    """加载交易所数据"""
    latest_file = get_latest_data_file(exchange)
    if not latest_file:
        return None
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # OKX 数据格式转换
            if 'instruments_spot' in data or 'instruments_swap' in data:
                # 转换为统一格式
                trading_pairs = []
                
                # 处理现货
                for item in data.get('instruments_spot', []):
                    trading_pairs.append({
                        'symbol': item.get('instId', ''),
                        'base_currency': item.get('baseCcy', ''),
                        'quote_currency': item.get('quoteCcy', ''),
                        'type': 'spot',
                        'state': item.get('state', ''),
                        'tick_size': item.get('tickSz', ''),
                        'lot_size': item.get('lotSz', ''),
                        'min_size': item.get('minSz', '')
                    })
                
                # 处理合约
                for item in data.get('instruments_swap', []):
                    trading_pairs.append({
                        'symbol': item.get('instId', ''),
                        'base_currency': item.get('baseCcy', ''),
                        'quote_currency': item.get('quoteCcy', ''),
                        'type': 'swap',
                        'state': item.get('state', ''),
                        'tick_size': item.get('tickSz', ''),
                        'lot_size': item.get('lotSz', ''),
                        'min_size': item.get('minSz', '')
                    })
                
                return {
                    'exchange': 'okx',
                    'timestamp': data.get('system_time', {}).get('ts', ''),
                    'trading_pairs': trading_pairs
                }
            
            # 币安数据格式转换
            elif 'exchange_info' in data and 'symbols' in data['exchange_info']:
                symbols = data['exchange_info']['symbols']
                trading_pairs = []
                
                for item in symbols:
                    trading_pairs.append({
                        'symbol': item.get('symbol', ''),
                        'base_currency': item.get('baseAsset', ''),
                        'quote_currency': item.get('quoteAsset', ''),
                        'type': 'spot' if 'SPOT' in item.get('permissions', []) else 'other',
                        'status': item.get('status', ''),
                        'filters': item.get('filters', [])
                    })
                
                return {
                    'exchange': 'binance',
                    'timestamp': data.get('exchange_info', {}).get('serverTime', ''),
                    'trading_pairs': trading_pairs
                }
            
            # 如果已经是统一格式
            else:
                return data
                
    except Exception as e:
        print(f"加载 {exchange} 数据失败: {e}")
        return None

def get_quick_market_overview():
    """获取快速市场概览"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'exchanges': {}
    }
    
    for exchange in ['okx', 'binance']:
        data = load_exchange_data(exchange)
        if data:
            pairs = data.get('trading_pairs', [])
            result['exchanges'][exchange] = {
                'total_pairs': len(pairs),
                'data_file': get_latest_data_file(exchange),
                'last_update': data.get('timestamp', 'N/A')
            }
    
    return result

def search_trading_pairs(keyword, exchange=None):
    """搜索交易对"""
    results = {}
    
    exchanges = [exchange] if exchange else ['okx', 'binance']
    
    for ex in exchanges:
        data = load_exchange_data(ex)
        if data:
            pairs = data.get('trading_pairs', [])
            matches = [p for p in pairs if keyword.upper() in p.get('symbol', '').upper()]
            results[ex] = matches
    
    return results

# 快速测试
if __name__ == "__main__":
    print("🚀 快速数据访问测试...")
    
    # 市场概览
    overview = get_quick_market_overview()
    print("\n📊 市场概览:")
    for exchange, info in overview['exchanges'].items():
        print(f"  {exchange.upper()}: {info['total_pairs']} 交易对")
    
    # 搜索示例
    print("\n🔍 BTC 交易对搜索:")
    btc_results = search_trading_pairs("BTC")
    for exchange, pairs in btc_results.items():
        print(f"  {exchange.upper()}: {len(pairs)} 个BTC相关交易对")
        for pair in pairs[:3]:  # 显示前3个
            print(f"    - {pair.get('symbol', 'N/A')}")
