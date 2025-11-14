#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX & 币安交易所数据获取快速启动器
为 IDE 提供一键式数据获取和验证功能
"""

import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path

class DataQuickLauncher:
    """数据获取快速启动器"""
    
    def __init__(self, project_path=None):
        self.project_path = project_path or os.getcwd()
        self.data_files = {}
        self.exchanges = ['okx', 'binance']
        
    def scan_data_files(self):
        """扫描项目中的数据文件"""
        print("🔍 扫描数据文件中...")
        
        for exchange in self.exchanges:
            pattern = os.path.join(self.project_path, f"{exchange}_*.json")
            files = glob.glob(pattern)
            
            self.data_files[exchange] = {
                'market_data': [],
                'api_docs': [],
                'other': []
            }
            
            for file in files:
                filename = os.path.basename(file)
                if 'market_data' in filename:
                    self.data_files[exchange]['market_data'].append(file)
                elif 'api_documentation' in filename or 'api_docs' in filename:
                    self.data_files[exchange]['api_docs'].append(file)
                else:
                    self.data_files[exchange]['other'].append(file)
        
        # 统一数据文件
        unified_pattern = os.path.join(self.project_path, "unified_exchange_data_*.json")
        unified_files = glob.glob(unified_pattern)
        self.data_files['unified'] = unified_files
        
        print("✅ 数据文件扫描完成")
        return self.data_files
    
    def validate_data_file(self, filepath):
        """验证数据文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # OKX 数据格式验证
            if 'instruments_spot' in data or 'instruments_swap' in data:
                # OKX 格式
                spot_pairs = data.get('instruments_spot', [])
                swap_pairs = data.get('instruments_swap', [])
                total_pairs = len(spot_pairs) + len(swap_pairs)
                
                if total_pairs == 0:
                    return False, "OKX数据: 交易对为空"
                
                # 检查第一个交易对
                if spot_pairs:
                    first_pair = spot_pairs[0]
                    if 'instId' not in first_pair:
                        return False, "OKX数据: 缺少instId字段"
                
                return True, "OKX数据有效"
            
            # 币安数据格式验证
            elif 'exchange_info' in data and 'symbols' in data['exchange_info']:
                # 币安格式
                symbols = data['exchange_info']['symbols']
                if not isinstance(symbols, list):
                    return False, "币安数据: symbols格式错误"
                
                if len(symbols) == 0:
                    return False, "币安数据: 交易对为空"
                
                # 检查第一个交易对
                if symbols:
                    first_symbol = symbols[0]
                    if 'symbol' not in first_symbol:
                        return False, "币安数据: 缺少symbol字段"
                
                return True, "币安数据有效"
            
            # 统一数据格式验证
            elif 'exchanges' in data:
                exchanges = data['exchanges']
                if 'okx' in exchanges and 'binance' in exchanges:
                    return True, "统一数据有效"
                else:
                    return False, "统一数据: 缺少交易所数据"
            
            else:
                return False, "未知数据格式"
            
        except FileNotFoundError:
            return False, "文件不存在"
        except json.JSONDecodeError:
            return False, "JSON解析错误"
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def get_quick_stats(self):
        """获取快速统计信息"""
        stats = {}
        
        for exchange in self.exchanges:
            exchange_stats = {
                'total_pairs': 0,
                'spot_pairs': 0,
                'swap_pairs': 0,
                'valid_files': 0,
                'latest_file': None,
                'file_count': 0
            }
            
            market_files = self.data_files.get(exchange, {}).get('market_data', [])
            
            for file in market_files:
                exchange_stats['file_count'] += 1
                is_valid, message = self.validate_data_file(file)
                
                if is_valid:
                    exchange_stats['valid_files'] += 1
                    
                    # 获取最新文件
                    if not exchange_stats['latest_file'] or file > exchange_stats['latest_file']:
                        exchange_stats['latest_file'] = file
                    
                    # 统计交易对数量
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # OKX 格式
                            if 'instruments_spot' in data or 'instruments_swap' in data:
                                spot_pairs = data.get('instruments_spot', [])
                                swap_pairs = data.get('instruments_swap', [])
                                exchange_stats['spot_pairs'] += len(spot_pairs)
                                exchange_stats['swap_pairs'] += len(swap_pairs)
                                exchange_stats['total_pairs'] += len(spot_pairs) + len(swap_pairs)
                            
                            # 币安格式
                            elif 'exchange_info' in data and 'symbols' in data['exchange_info']:
                                symbols = data['exchange_info']['symbols']
                                exchange_stats['total_pairs'] += len(symbols)
                                # 简单区分现货和合约（基于symbol命名规则）
                                spot_count = len([s for s in symbols if not s['symbol'].endswith(('USDT', 'BUSD', 'USDC')) or len(s['symbol']) <= 10])
                                exchange_stats['spot_pairs'] += spot_count
                                exchange_stats['swap_pairs'] += len(symbols) - spot_count
                    
                    except Exception as e:
                        print(f"统计 {file} 时出错: {e}")
            
            stats[exchange] = exchange_stats
        
        # 统一数据文件统计
        unified_files = self.data_files.get('unified', [])
        stats['unified'] = {
            'file_count': len(unified_files),
            'latest_file': max(unified_files) if unified_files else None
        }
        
        return stats
    
    def display_status(self):
        """显示数据状态"""
        print("\n" + "="*60)
        print("📊 OKX & 币安数据获取快速启动器")
        print("="*60)
        
        # 扫描数据文件
        self.scan_data_files()
        stats = self.get_quick_stats()
        
        print(f"\n📁 项目路径: {self.project_path}")
        print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # OKX 状态
        print(f"\n🔶 OKX 交易所:")
        okx_stats = stats['okx']
        print(f"  📈 总交易对: {okx_stats['total_pairs']:,}")
        print(f"     现货: {okx_stats['spot_pairs']:,}")
        print(f"     合约: {okx_stats['swap_pairs']:,}")
        print(f"  📋 数据文件: {okx_stats['file_count']} 个")
        print(f"  ✅ 有效文件: {okx_stats['valid_files']} 个")
        if okx_stats['latest_file']:
            print(f"  🆕 最新数据: {os.path.basename(okx_stats['latest_file'])}")
        
        # 币安状态
        print(f"\n🔶 币安交易所:")
        binance_stats = stats['binance']
        print(f"  📈 总交易对: {binance_stats['total_pairs']:,}")
        print(f"     现货: {binance_stats['spot_pairs']:,}")
        print(f"     合约: {binance_stats['swap_pairs']:,}")
        print(f"  📋 数据文件: {binance_stats['file_count']} 个")
        print(f"  ✅ 有效文件: {binance_stats['valid_files']} 个")
        if binance_stats['latest_file']:
            print(f"  🆕 最新数据: {os.path.basename(binance_stats['latest_file'])}")
        
        # 统一数据
        print(f"\n🔶 统一数据:")
        unified_stats = stats['unified']
        print(f"  📋 文件数量: {unified_stats['file_count']} 个")
        if unified_stats['latest_file']:
            print(f"  🆕 最新文件: {os.path.basename(unified_stats['latest_file'])}")
        
        return stats
    
    def get_recommended_actions(self, stats):
        """获取推荐操作"""
        actions = []
        
        # 检查是否需要重新获取数据
        for exchange in self.exchanges:
            exchange_stats = stats[exchange]
            if exchange_stats['total_pairs'] == 0:
                actions.append(f"🔄 需要重新获取 {exchange.upper()} 数据")
            elif exchange_stats['valid_files'] == 0:
                actions.append(f"⚠️  {exchange.upper()} 数据文件损坏，需要重新获取")
        
        # 检查统一数据
        if stats['unified']['file_count'] == 0:
            actions.append("🔄 建议生成统一数据文件")
        
        # 检查开发工具
        required_tools = [
            'unified_data_access.py',
            'quick_start_tool.py',
            'ide_code_snippets.py'
        ]
        
        for tool in required_tools:
            if not os.path.exists(os.path.join(self.project_path, tool)):
                actions.append(f"📥 缺少开发工具: {tool}")
        
        return actions
    
    def run_data_validation(self):
        """运行数据验证"""
        print("\n🔍 运行数据验证...")
        
        validation_results = {}
        
        for exchange in self.exchanges:
            print(f"\n📋 验证 {exchange.upper()} 数据:")
            market_files = self.data_files.get(exchange, {}).get('market_data', [])
            
            exchange_results = {
                'total_files': len(market_files),
                'valid_files': 0,
                'invalid_files': 0,
                'errors': []
            }
            
            for file in market_files:
                filename = os.path.basename(file)
                is_valid, message = self.validate_data_file(file)
                
                if is_valid:
                    exchange_results['valid_files'] += 1
                    print(f"  ✅ {filename}: 有效")
                else:
                    exchange_results['invalid_files'] += 1
                    exchange_results['errors'].append(f"{filename}: {message}")
                    print(f"  ❌ {filename}: {message}")
            
            validation_results[exchange] = exchange_results
        
        return validation_results
    
    def generate_quick_access_script(self):
        """生成快速访问脚本"""
        script_content = '''#!/usr/bin/env python3
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
            return json.load(f)
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
    print("\\n📊 市场概览:")
    for exchange, info in overview['exchanges'].items():
        print(f"  {exchange.upper()}: {info['total_pairs']} 交易对")
    
    # 搜索示例
    print("\\n🔍 BTC 交易对搜索:")
    btc_results = search_trading_pairs("BTC")
    for exchange, pairs in btc_results.items():
        print(f"  {exchange.upper()}: {len(pairs)} 个BTC相关交易对")
        for pair in pairs[:3]:  # 显示前3个
            print(f"    - {pair.get('symbol', 'N/A')}")
'''
        
        script_path = os.path.join(self.project_path, 'quick_data_access.py')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"✅ 快速访问脚本已生成: {script_path}")
        return script_path

def main():
    """主函数"""
    launcher = DataQuickLauncher()
    
    # 显示状态
    stats = launcher.display_status()
    
    # 获取推荐操作
    actions = launcher.get_recommended_actions(stats)
    
    if actions:
        print(f"\n⚡ 推荐操作:")
        for action in actions:
            print(f"  {action}")
    else:
        print(f"\n✅ 所有数据状态正常！")
    
    # 运行数据验证
    validation_results = launcher.run_data_validation()
    
    # 生成快速访问脚本
    print(f"\n🔧 生成快速访问脚本...")
    script_path = launcher.generate_quick_access_script()
    
    print(f"\n🎉 快速启动器运行完成！")
    print(f"📁 项目路径: {launcher.project_path}")
    print(f"📝 快速访问脚本: {os.path.basename(script_path)}")
    
    # 显示下一步操作
    print(f"\n📋 下一步操作:")
    print(f"  1. 运行快速访问脚本: python {os.path.basename(script_path)}")
    print(f"  2. 使用统一数据访问: python unified_data_access.py")
    print(f"  3. 查看 IDE 指南: IDE快速数据获取指南.md")
    
    return stats, validation_results

if __name__ == "__main__":
    main()