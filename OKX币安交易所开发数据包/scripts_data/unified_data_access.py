# 🚀 OKX & 币安交易所统一数据访问脚本
# 版本: v1.0
# 最后更新: 2025-10-04

import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime

class UnifiedExchangeDataAccess:
    """
    OKX和币安交易所统一数据访问类
    提供快速、统一的数据访问接口
    """
    
    def __init__(self, data_dir: str = "."):
        """
        初始化统一数据访问
        
        Args:
            data_dir: 数据文件目录，默认为当前目录
        """
        self.data_dir = data_dir
        self.exchanges = ['okx', 'binance']
        self.data_cache = {}
        
        # 数据文件映射
        self.data_files = {
            'okx': {
                'market_data': 'okx_market_data_20251004_041754.json',
                'market_summary': 'okx_market_data_20251004_041754_summary.json',
                'api_docs': 'okx_api_documentation_20251004_041908.json',
                'development_config': 'okx_development_config_20251004_042051.json',
                'development_guide': 'okx_development_guide_20251004_042051.md'
            },
            'binance': {
                'market_data': 'binance_market_data_20251004_043616.json',
                'market_summary': 'binance_market_data_20251004_043616_summary.json',
                'api_docs': 'binance_api_documentation_20251004_043720.json',
                'api_docs_reference': 'binance_api_documentation_20251004_043720_reference.json'
            }
        }
    
    def load_json_data(self, file_path: str) -> Optional[Dict]:
        """加载JSON数据文件"""
        try:
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️ 文件不存在: {file_path}")
                return None
        except Exception as e:
            print(f"❌ 加载文件失败 {file_path}: {e}")
            return None
    
    def get_exchange_info(self, exchange: str) -> Dict:
        """获取交易所基本信息"""
        if exchange.lower() not in self.exchanges:
            return {'error': f'不支持的交易所: {exchange}'}
        
        # 获取市场数据摘要
        summary_file = self.data_files[exchange.lower()].get('market_summary')
        if summary_file:
            summary_data = self.load_json_data(summary_file)
            if summary_data:
                return {
                    'exchange': exchange.upper(),
                    'status': 'active',
                    'total_symbols': summary_data.get('total_symbols', 0),
                    'spot_symbols': summary_data.get('spot_symbols', 0),
                    'futures_symbols': summary_data.get('futures_symbols', 0),
                    'last_updated': summary_data.get('timestamp', 'unknown')
                }
        
        # 如果没有摘要，从市场数据计算
        market_data = self.get_market_data(exchange)
        if market_data and 'data' in market_data:
            symbols = market_data['data']
            return {
                'exchange': exchange.upper(),
                'status': 'active',
                'total_symbols': len(symbols),
                'spot_symbols': len([s for s in symbols if 'SPOT' in str(s.get('symbol', '')).upper()]),
                'futures_symbols': len([s for s in symbols if 'SWAP' in str(s.get('symbol', '')).upper() or 'FUTURES' in str(s.get('symbol', '')).upper()]),
                'last_updated': datetime.now().isoformat()
            }
        
        return {'error': f'无法获取 {exchange} 的信息'}
    
    def get_market_data(self, exchange: str) -> Optional[Dict]:
        """获取交易所市场数据"""
        if exchange.lower() not in self.exchanges:
            return None
        
        cache_key = f"{exchange.lower()}_market_data"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        market_file = self.data_files[exchange.lower()].get('market_data')
        if market_file:
            data = self.load_json_data(market_file)
            self.data_cache[cache_key] = data
            return data
        
        return None
    
    def get_all_symbols(self, exchange: str) -> List[str]:
        """获取所有交易对符号"""
        market_data = self.get_market_data(exchange)
        if not market_data:
            return []
        
        symbols = []
        if exchange.lower() == 'okx':
            # OKX数据结构
            if 'data' in market_data and isinstance(market_data['data'], list):
                for item in market_data['data']:
                    if isinstance(item, dict) and 'instId' in item:
                        symbols.append(item['instId'])
        elif exchange.lower() == 'binance':
            # 币安数据结构
            if 'symbols' in market_data and isinstance(market_data['symbols'], list):
                for item in market_data['symbols']:
                    if isinstance(item, dict) and 'symbol' in item:
                        symbols.append(item['symbol'])
        
        return sorted(list(set(symbols)))
    
    def get_spot_symbols(self, exchange: str) -> List[str]:
        """获取现货交易对"""
        market_data = self.get_market_data(exchange)
        if not market_data:
            return []
        
        symbols = []
        if exchange.lower() == 'okx':
            if 'data' in market_data and isinstance(market_data['data'], list):
                for item in market_data['data']:
                    if isinstance(item, dict) and 'instId' in item and item.get('instType') == 'SPOT':
                        symbols.append(item['instId'])
        elif exchange.lower() == 'binance':
            if 'symbols' in market_data and isinstance(market_data['symbols'], list):
                for item in market_data['symbols']:
                    if isinstance(item, dict) and 'symbol' in item and item.get('status') == 'TRADING':
                        symbols.append(item['symbol'])
        
        return sorted(list(set(symbols)))
    
    def get_futures_symbols(self, exchange: str) -> List[str]:
        """获取合约交易对"""
        market_data = self.get_market_data(exchange)
        if not market_data:
            return []
        
        symbols = []
        if exchange.lower() == 'okx':
            if 'data' in market_data and isinstance(market_data['data'], list):
                for item in market_data['data']:
                    if isinstance(item, dict) and 'instId' in item and item.get('instType') in ['SWAP', 'FUTURES']:
                        symbols.append(item['instId'])
        elif exchange.lower() == 'binance':
            if 'symbols' in market_data and isinstance(market_data['symbols'], list):
                for item in market_data['symbols']:
                    if isinstance(item, dict) and 'symbol' in item and item.get('contractType'):
                        symbols.append(item['symbol'])
        
        return sorted(list(set(symbols)))
    
    def search_symbols(self, exchange: str, query: str) -> List[str]:
        """搜索交易对"""
        all_symbols = self.get_all_symbols(exchange)
        query = query.upper()
        return [s for s in all_symbols if query in s.upper()]
    
    def get_symbol_info(self, exchange: str, symbol: str) -> Optional[Dict]:
        """获取特定交易对信息"""
        market_data = self.get_market_data(exchange)
        if not market_data:
            return None
        
        if exchange.lower() == 'okx':
            if 'data' in market_data and isinstance(market_data['data'], list):
                for item in market_data['data']:
                    if isinstance(item, dict) and item.get('instId') == symbol:
                        return item
        elif exchange.lower() == 'binance':
            if 'symbols' in market_data and isinstance(market_data['symbols'], list):
                for item in market_data['symbols']:
                    if isinstance(item, dict) and item.get('symbol') == symbol:
                        return item
        
        return None
    
    def compare_exchanges(self) -> Dict:
        """比较两个交易所的数据"""
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'exchanges': {}
        }
        
        for exchange in self.exchanges:
            comparison['exchanges'][exchange.upper()] = self.get_exchange_info(exchange)
        
        # 添加对比统计
        okx_symbols = set(self.get_all_symbols('okx'))
        binance_symbols = set(self.get_all_symbols('binance'))
        
        comparison['statistics'] = {
            'okx_total_symbols': len(okx_symbols),
            'binance_total_symbols': len(binance_symbols),
            'common_symbols': len(okx_symbols & binance_symbols),
            'okx_unique_symbols': len(okx_symbols - binance_symbols),
            'binance_unique_symbols': len(binance_symbols - okx_symbols)
        }
        
        return comparison
    
    def get_quick_stats(self) -> Dict:
        """获取快速统计信息"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'exchanges': {}
        }
        
        for exchange in self.exchanges:
            info = self.get_exchange_info(exchange)
            symbols = self.get_all_symbols(exchange)
            spot_symbols = self.get_spot_symbols(exchange)
            futures_symbols = self.get_futures_symbols(exchange)
            
            stats['exchanges'][exchange.upper()] = {
                'total_symbols': len(symbols),
                'spot_symbols': len(spot_symbols),
                'futures_symbols': len(futures_symbols),
                'sample_symbols': symbols[:5] if symbols else [],
                'status': info.get('status', 'unknown')
            }
        
        return stats
    
    def export_unified_data(self, output_file: str = "unified_exchange_data.json"):
        """导出统一数据"""
        unified_data = {
            'metadata': {
                'version': '1.0',
                'generated_at': datetime.now().isoformat(),
                'exchanges': self.exchanges,
                'description': 'OKX和币安交易所统一数据'
            },
            'data': {}
        }
        
        for exchange in self.exchanges:
            unified_data['data'][exchange.upper()] = {
                'exchange_info': self.get_exchange_info(exchange),
                'all_symbols': self.get_all_symbols(exchange),
                'spot_symbols': self.get_spot_symbols(exchange),
                'futures_symbols': self.get_futures_symbols(exchange),
                'market_data': self.get_market_data(exchange)
            }
        
        unified_data['comparison'] = self.compare_exchanges()
        unified_data['quick_stats'] = self.get_quick_stats()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 统一数据已导出到: {output_file}")
        return unified_data

def main():
    """主函数 - 演示统一数据访问"""
    print("🚀 启动OKX & 币安统一数据访问...")
    
    # 创建统一数据访问实例
    data_access = UnifiedExchangeDataAccess()
    
    # 获取快速统计
    print("\n📊 快速统计:")
    quick_stats = data_access.get_quick_stats()
    for exchange, stats in quick_stats['exchanges'].items():
        print(f"  {exchange}: {stats['total_symbols']} 交易对 "
              f"(现货: {stats['spot_symbols']}, 合约: {stats['futures_symbols']})")
        print(f"    示例: {', '.join(stats['sample_symbols'])}")
    
    # 交易所对比
    print("\n🔍 交易所对比:")
    comparison = data_access.compare_exchanges()
    stats = comparison['statistics']
    print(f"  共同交易对: {stats['common_symbols']}")
    print(f"  OKX独有: {stats['okx_unique_symbols']}")
    print(f"  币安独有: {stats['binance_unique_symbols']}")
    
    # 搜索示例
    print("\n🔎 搜索示例 (BTC相关):")
    for exchange in ['okx', 'binance']:
        btc_symbols = data_access.search_symbols(exchange, 'BTC')
        print(f"  {exchange.upper()}: {len(btc_symbols)} 个BTC相关交易对")
        if btc_symbols:
            print(f"    {', '.join(btc_symbols[:5])}{'...' if len(btc_symbols) > 5 else ''}")
    
    # 导出统一数据
    print("\n💾 导出统一数据...")
    unified_data = data_access.export_unified_data("unified_exchange_data_20251004.json")
    
    print(f"\n✅ 统一数据访问演示完成！")
    print(f"📁 数据文件总数: {len(os.listdir('.'))} 个")
    print(f"🎯 可用功能: 数据查询、交易对搜索、交易所对比、数据导出")

if __name__ == "__main__":
    main()