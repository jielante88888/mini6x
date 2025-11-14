#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDE快速访问脚本 - 简化版
为IDE提供一键式数据访问功能
"""

import json
import os
import glob
from datetime import datetime

def load_okx_pairs():
    """加载OKX交易对 - 从摘要文件"""
    okx_file = "okx_market_data_20251004_041754_summary.json"
    if not os.path.exists(okx_file):
        return []
    
    try:
        with open(okx_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pairs = []
        
        # 从SPOT_tickers获取现货
        for item in data.get('SPOT_tickers', []):
            if 'instId' in item:
                inst_id = item['instId']
                base = inst_id.split('-')[0] if '-' in inst_id else ''
                quote = inst_id.split('-')[1] if '-' in inst_id else ''
                pairs.append({
                    'symbol': inst_id,
                    'base': base,
                    'quote': quote,
                    'type': 'spot',
                    'last_price': item.get('last', ''),
                    'price_change_24h': item.get('open24h', '') and item.get('last', '') and 
                        f"{((float(item['last']) - float(item['open24h'])) / float(item['open24h']) * 100):.2f}%" or '0%'
                })
        
        # 从SWAP_tickers获取合约
        for item in data.get('SWAP_tickers', []):
            if 'instId' in item:
                inst_id = item['instId']
                base = inst_id.split('-')[0] if '-' in inst_id else ''
                quote = inst_id.split('-')[1] if '-' in inst_id else ''
                pairs.append({
                    'symbol': inst_id,
                    'base': base,
                    'quote': quote,
                    'type': 'swap',
                    'last_price': item.get('last', ''),
                    'price_change_24h': item.get('open24h', '') and item.get('last', '') and 
                        f"{((float(item['last']) - float(item['open24h'])) / float(item['open24h']) * 100):.2f}%" or '0%'
                })
        
        return pairs
        
    except Exception as e:
        print(f"加载OKX数据失败: {e}")
        return []

def load_binance_pairs():
    """加载币安交易对 - 从摘要文件"""
    binance_file = "binance_market_data_20251004_043616_summary.json"
    if not os.path.exists(binance_file):
        return []
    
    try:
        with open(binance_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pairs = []
        
        # 从top_volume_symbols获取交易对
        for item in data.get('top_volume_symbols', []):
            if 'symbol' in item:
                symbol = item['symbol']
                
                # 解析base和quote
                if len(symbol) >= 6:
                    if symbol.endswith('USDT'):
                        base = symbol[:-4]
                        quote = 'USDT'
                    elif symbol.endswith('BUSD'):
                        base = symbol[:-4]
                        quote = 'BUSD'
                    elif symbol.endswith('BTC'):
                        base = symbol[:-3]
                        quote = 'BTC'
                    elif symbol.endswith('ETH'):
                        base = symbol[:-3]
                        quote = 'ETH'
                    elif symbol.endswith('BNB'):
                        base = symbol[:-3]
                        quote = 'BNB'
                    else:
                        # 其他情况，尝试分割
                        base = symbol[:len(symbol)//2]
                        quote = symbol[len(symbol)//2:]
                else:
                    base = symbol
                    quote = ''
                
                pairs.append({
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'type': 'spot',
                    'last_price': item.get('last_price', ''),
                    'price_change_24h': item.get('price_change_24h', '0') + '%'
                })
        
        return pairs
        
    except Exception as e:
        print(f"加载币安数据失败: {e}")
        return []

def search_pairs(keyword, exchange=None):
    """搜索交易对"""
    results = {}
    
    if exchange is None or exchange.lower() == 'okx':
        okx_pairs = load_okx_pairs()
        okx_matches = [p for p in okx_pairs if keyword.upper() in p['symbol'].upper()]
        if okx_matches:
            results['okx'] = okx_matches
    
    if exchange is None or exchange.lower() == 'binance':
        binance_pairs = load_binance_pairs()
        binance_matches = [p for p in binance_pairs if keyword.upper() in p['symbol'].upper()]
        if binance_matches:
            results['binance'] = binance_matches
    
    return results

def get_common_pairs():
    """获取共同交易对"""
    okx_pairs = load_okx_pairs()
    binance_pairs = load_binance_pairs()
    
    okx_symbols = set(p['symbol'] for p in okx_pairs)
    binance_symbols = set(p['symbol'] for p in binance_pairs)
    
    common_symbols = okx_symbols.intersection(binance_symbols)
    
    common_pairs = []
    for symbol in common_symbols:
        okx_pair = next((p for p in okx_pairs if p['symbol'] == symbol), None)
        binance_pair = next((p for p in binance_pairs if p['symbol'] == symbol), None)
        
        if okx_pair and binance_pair:
            common_pairs.append({
                'symbol': symbol,
                'base': okx_pair['base'],
                'quote': okx_pair['quote'],
                'okx_price': okx_pair.get('last_price', ''),
                'binance_price': binance_pair.get('last_price', ''),
                'price_diff': ''
            })
    
    return common_pairs

def get_statistics():
    """获取统计信息"""
    okx_pairs = load_okx_pairs()
    binance_pairs = load_binance_pairs()
    common_pairs = get_common_pairs()
    
    return {
        'okx': {
            'total': len(okx_pairs),
            'spot': len([p for p in okx_pairs if p['type'] == 'spot']),
            'swap': len([p for p in okx_pairs if p['type'] == 'swap'])
        },
        'binance': {
            'total': len(binance_pairs),
            'spot': len([p for p in binance_pairs if p['type'] == 'spot'])
        },
        'common_pairs': len(common_pairs)
    }

def print_summary():
    """打印摘要信息"""
    stats = get_statistics()
    
    print("="*50)
    print("📊 OKX & 币安数据快速访问")
    print("="*50)
    
    print(f"\n🔶 OKX 交易所:")
    print(f"  📈 总交易对: {stats['okx']['total']:,}")
    print(f"  📈 现货: {stats['okx']['spot']:,}")
    print(f"  📈 合约: {stats['okx']['swap']:,}")
    
    print(f"\n🔶 币安交易所:")
    print(f"  📈 总交易对: {stats['binance']['total']:,}")
    print(f"  📈 现货: {stats['binance']['spot']:,}")
    
    print(f"\n🔄 共同交易对: {stats['common_pairs']}")
    
    return stats

# 快速访问函数
def okx(base=None):
    """快速获取OKX交易对"""
    pairs = load_okx_pairs()
    if base:
        pairs = [p for p in pairs if p['base'].upper() == base.upper()]
    return pairs

def binance(base=None):
    """快速获取币安交易对"""
    pairs = load_binance_pairs()
    if base:
        pairs = [p for p in pairs if p['base'].upper() == base.upper()]
    return pairs

def search(keyword, exchange=None):
    """快速搜索交易对"""
    return search_pairs(keyword, exchange)

def common():
    """快速获取共同交易对"""
    return get_common_pairs()

def stats():
    """快速获取统计信息"""
    return get_statistics()

# 主要功能演示
if __name__ == "__main__":
    print("🚀 IDE快速访问脚本测试...")
    
    # 打印摘要
    stats = print_summary()
    
    # 搜索示例
    print(f"\n🔍 BTC相关交易对:")
    btc_results = search("BTC")
    
    for exchange, pairs in btc_results.items():
        print(f"  {exchange.upper()}: {len(pairs)} 个")
        for pair in pairs[:3]:  # 显示前3个
            print(f"    - {pair['symbol']} ({pair['base']}/{pair['quote']}) 价格: {pair.get('last_price', 'N/A')}")
    
    # 共同交易对示例
    print(f"\n🔄 共同交易对 (前5个):")
    common_pairs = common()
    for pair in common_pairs[:5]:
        print(f"  - {pair['symbol']} ({pair['base']}/{pair['quote']})")
    
    print(f"\n✅ 快速访问脚本已就绪！")
    print(f"💡 在IDE中直接调用: okx(), binance(), search(), common(), stats()")
    print(f"💡 示例: okx('BTC') - 获取OKX中BTC相关的交易对")