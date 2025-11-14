#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDE数据访问助手 - 简化版
为IDE提供简单易用的数据访问接口
"""

import json
import os
import glob
from datetime import datetime

class IDEDATAHelper:
    """IDE数据访问助手"""
    
    def __init__(self, project_path=None):
        self.project_path = project_path or os.getcwd()
        self.okx_data = None
        self.binance_data = None
        self.load_all_data()
    
    def find_latest_file(self, pattern):
        """查找最新的匹配文件"""
        files = glob.glob(os.path.join(self.project_path, pattern))
        return max(files) if files else None
    
    def load_okx_data(self):
        """加载OKX数据"""
        okx_file = self.find_latest_file("okx_market_data_*.json")
        if not okx_file:
            return None
        
        try:
            with open(okx_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换数据格式
            trading_pairs = []
            
            # 检查是否是摘要格式
            if 'SPOT_tickers' in data:
                # 处理摘要格式
                for item in data['SPOT_tickers']:
                    if 'instId' in item:
                        inst_id = item['instId']
                        base_ccy = item.get('instId', '').split('-')[0] if '-' in inst_id else ''
                        quote_ccy = item.get('instId', '').split('-')[1] if '-' in inst_id else ''
                        
                        trading_pairs.append({
                            'symbol': inst_id,
                            'base': base_ccy,
                            'quote': quote_ccy,
                            'type': 'spot',
                            'tick_size': '',
                            'lot_size': '',
                            'min_size': ''
                        })
                
                for item in data.get('SWAP_tickers', []):
                    if 'instId' in item:
                        inst_id = item['instId']
                        base_ccy = item.get('instId', '').split('-')[0] if '-' in inst_id else ''
                        quote_ccy = item.get('instId', '').split('-')[1] if '-' in inst_id else ''
                        
                        trading_pairs.append({
                            'symbol': inst_id,
                            'base': base_ccy,
                            'quote': quote_ccy,
                            'type': 'swap',
                            'tick_size': '',
                            'lot_size': '',
                            'min_size': ''
                        })
            else:
                # 处理标准格式
                # 处理现货
                for item in data.get('instruments_spot', []):
                    if item.get('state') == 'live':  # 只包含活跃的交易对
                        trading_pairs.append({
                            'symbol': item.get('instId', ''),
                            'base': item.get('baseCcy', ''),
                            'quote': item.get('quoteCcy', ''),
                            'type': 'spot',
                            'tick_size': item.get('tickSz', ''),
                            'lot_size': item.get('lotSz', ''),
                            'min_size': item.get('minSz', '')
                        })
                
                # 处理合约
                for item in data.get('instruments_swap', []):
                    if item.get('state') == 'live':
                        trading_pairs.append({
                            'symbol': item.get('instId', ''),
                            'base': item.get('baseCcy', ''),
                            'quote': item.get('quoteCcy', ''),
                            'type': 'swap',
                            'tick_size': item.get('tickSz', ''),
                            'lot_size': item.get('lotSz', ''),
                            'min_size': item.get('minSz', '')
                        })
                
                # 如果没有找到数据，尝试原始格式
                if not trading_pairs:
                    # 可能是原始数据格式，直接处理
                    if 'data' in data:
                        for item in data['data']:
                            if item.get('state') == 'live':
                                trading_pairs.append({
                                    'symbol': item.get('instId', ''),
                                    'base': item.get('baseCcy', ''),
                                    'quote': item.get('quoteCcy', ''),
                                    'type': 'spot',
                                    'tick_size': item.get('tickSz', ''),
                                    'lot_size': item.get('lotSz', ''),
                                    'min_size': item.get('minSz', '')
                                })
            
            return {
                'exchange': 'okx',
                'file': okx_file,
                'total_pairs': len(trading_pairs),
                'trading_pairs': trading_pairs,
                'last_update': data.get('system_time', {}).get('ts', '') or data.get('summary', {}).get('collected_at', '')
            }
            
        except Exception as e:
            print(f"加载OKX数据失败: {e}")
            return None
    
    def load_binance_data(self):
        """加载币安数据"""
        binance_file = self.find_latest_file("binance_market_data_*.json")
        if not binance_file:
            return None
        
        try:
            with open(binance_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换数据格式
            trading_pairs = []
            
            # 检查是否是摘要格式
            if 'top_volume_symbols' in data:
                # 处理摘要格式
                for item in data['top_volume_symbols']:
                    if 'symbol' in item:
                        symbol = item['symbol']
                        # 尝试从symbol中解析base和quote
                        if len(symbol) >= 6:
                            # 常见的币安交易对格式
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
                        
                        trading_pairs.append({
                            'symbol': symbol,
                            'base': base,
                            'quote': quote,
                            'type': 'spot',
                            'status': 'TRADING'
                        })
            else:
                # 处理标准格式
                symbols = data.get('exchange_info', {}).get('symbols', [])
                
                for item in symbols:
                    if item.get('status') == 'TRADING':  # 只包含活跃的交易对
                        trading_pairs.append({
                            'symbol': item.get('symbol', ''),
                            'base': item.get('baseAsset', ''),
                            'quote': item.get('quoteAsset', ''),
                            'type': 'spot',
                            'status': item.get('status', '')
                        })
                
                # 如果没有找到数据，尝试原始格式
                if not trading_pairs:
                    # 可能是原始数据格式，直接处理
                    if 'data' in data:
                        for item in data['data']:
                            if item.get('status') == 'TRADING':
                                trading_pairs.append({
                                    'symbol': item.get('symbol', ''),
                                    'base': item.get('baseAsset', ''),
                                    'quote': item.get('quoteAsset', ''),
                                    'type': 'spot',
                                    'status': item.get('status', '')
                                })
            
            return {
                'exchange': 'binance',
                'file': binance_file,
                'total_pairs': len(trading_pairs),
                'trading_pairs': trading_pairs,
                'last_update': data.get('exchange_info', {}).get('serverTime', '') or data.get('collection_time', '')
            }
            
        except Exception as e:
            print(f"加载币安数据失败: {e}")
            return None
    
    def load_all_data(self):
        """加载所有数据"""
        self.okx_data = self.load_okx_data()
        self.binance_data = self.load_binance_data()
    
    def get_okx_pairs(self, base_currency=None):
        """获取OKX交易对"""
        if not self.okx_data:
            return []
        
        pairs = self.okx_data['trading_pairs']
        
        if base_currency:
            pairs = [p for p in pairs if p['base'].upper() == base_currency.upper()]
        
        return pairs
    
    def get_binance_pairs(self, base_currency=None):
        """获取币安交易对"""
        if not self.binance_data:
            return []
        
        pairs = self.binance_data['trading_pairs']
        
        if base_currency:
            pairs = [p for p in pairs if p['base'].upper() == base_currency.upper()]
        
        return pairs
    
    def search_pairs(self, keyword, exchange=None):
        """搜索交易对"""
        results = {}
        
        if exchange is None or exchange.lower() == 'okx':
            okx_pairs = self.get_okx_pairs()
            okx_matches = [p for p in okx_pairs if keyword.upper() in p['symbol'].upper()]
            if okx_matches:
                results['okx'] = okx_matches
        
        if exchange is None or exchange.lower() == 'binance':
            binance_pairs = self.get_binance_pairs()
            binance_matches = [p for p in binance_pairs if keyword.upper() in p['symbol'].upper()]
            if binance_matches:
                results['binance'] = binance_matches
        
        return results
    
    def get_common_pairs(self):
        """获取两个交易所的共同交易对"""
        if not self.okx_data or not self.binance_data:
            return []
        
        okx_symbols = set(p['symbol'] for p in self.okx_data['trading_pairs'])
        binance_symbols = set(p['symbol'] for p in self.binance_data['trading_pairs'])
        
        common_symbols = okx_symbols.intersection(binance_symbols)
        
        # 获取详细信息
        common_pairs = []
        for symbol in common_symbols:
            okx_pair = next((p for p in self.okx_data['trading_pairs'] if p['symbol'] == symbol), None)
            binance_pair = next((p for p in self.binance_data['trading_pairs'] if p['symbol'] == symbol), None)
            
            if okx_pair and binance_pair:
                common_pairs.append({
                    'symbol': symbol,
                    'base': okx_pair['base'],
                    'quote': okx_pair['quote'],
                    'okx': okx_pair,
                    'binance': binance_pair
                })
        
        return common_pairs
    
    def get_statistics(self):
        """获取统计信息"""
        stats = {
            'okx': {
                'total': self.okx_data['total_pairs'] if self.okx_data else 0,
                'file': self.okx_data['file'] if self.okx_data else None,
                'last_update': self.okx_data['last_update'] if self.okx_data else None
            },
            'binance': {
                'total': self.binance_data['total_pairs'] if self.binance_data else 0,
                'file': self.binance_data['file'] if self.binance_data else None,
                'last_update': self.binance_data['last_update'] if self.binance_data else None
            },
            'common_pairs': len(self.get_common_pairs())
        }
        
        return stats
    
    def print_summary(self):
        """打印摘要信息"""
        stats = self.get_statistics()
        
        print("="*50)
        print("📊 OKX & 币安数据访问助手")
        print("="*50)
        
        print(f"\n🔶 OKX 交易所:")
        print(f"  📈 总交易对: {stats['okx']['total']:,}")
        if stats['okx']['file']:
            print(f"  📁 数据文件: {os.path.basename(stats['okx']['file'])}")
        
        print(f"\n🔶 币安交易所:")
        print(f"  📈 总交易对: {stats['binance']['total']:,}")
        if stats['binance']['file']:
            print(f"  📁 数据文件: {os.path.basename(stats['binance']['file'])}")
        
        print(f"\n🔄 共同交易对: {stats['common_pairs']}")
        
        return stats

# 全局实例
helper = IDEDATAHelper()

def get_okx_pairs(base=None):
    """获取OKX交易对 - IDE快捷函数"""
    return helper.get_okx_pairs(base)

def get_binance_pairs(base=None):
    """获取币安交易对 - IDE快捷函数"""
    return helper.get_binance_pairs(base)

def search_pairs(keyword, exchange=None):
    """搜索交易对 - IDE快捷函数"""
    return helper.search_pairs(keyword, exchange)

def get_common_pairs():
    """获取共同交易对 - IDE快捷函数"""
    return helper.get_common_pairs()

def get_statistics():
    """获取统计信息 - IDE快捷函数"""
    return helper.get_statistics()

def print_summary():
    """打印摘要 - IDE快捷函数"""
    return helper.print_summary()

# 快速测试
if __name__ == "__main__":
    print("🚀 IDE数据访问助手测试...")
    
    # 打印摘要
    stats = print_summary()
    
    # 搜索示例
    print(f"\n🔍 BTC相关交易对:")
    btc_results = search_pairs("BTC")
    
    for exchange, pairs in btc_results.items():
        print(f"  {exchange.upper()}: {len(pairs)} 个")
        for pair in pairs[:3]:  # 显示前3个
            print(f"    - {pair['symbol']} ({pair['base']}/{pair['quote']})")
    
    # 共同交易对示例
    print(f"\n🔄 共同交易对 (前5个):")
    common = get_common_pairs()
    for pair in common[:5]:
        print(f"  - {pair['symbol']} ({pair['base']}/{pair['quote']})")
    
    print(f"\n✅ 数据访问助手已就绪！")
    print(f"💡 在IDE中直接调用: get_okx_pairs(), get_binance_pairs(), search_pairs()")