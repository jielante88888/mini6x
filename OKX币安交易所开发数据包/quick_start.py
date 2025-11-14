#!/usr/bin/env python3
"""
OKX和币安数据包快速开始测试脚本
"""

import os
import json
import sys

def test_data_access():
    """测试数据访问功能"""
    print("🚀 OKX和币安数据包快速测试")
    print("=" * 50)
    
    # 检查数据文件
    categories = ['okx_data', 'binance_data', 'unified_data', 'scripts', 'documentation']
    
    for category in categories:
        if os.path.exists(category):
            files = os.listdir(category)
            print(f"📁 {category}: {len(files)} 个文件")
            for f in files[:3]:  # 显示前3个文件
                print(f"  - {f}")
            if len(files) > 3:
                print(f"  ... 还有 {len(files) - 3} 个文件")
        else:
            print(f"❌ {category}: 目录不存在")
    
    print("\n📊 数据文件详情:")
    
    # 检查OKX数据
    if os.path.exists('okx_data'):
        okx_files = [f for f in os.listdir('okx_data') if f.endswith('.json')]
        if okx_files:
            latest_okx = sorted(okx_files)[-1]
            print(f"✅ OKX最新数据文件: {latest_okx}")
    
    # 检查币安数据
    if os.path.exists('binance_data'):
        binance_files = [f for f in os.listdir('binance_data') if f.endswith('.json')]
        if binance_files:
            latest_binance = sorted(binance_files)[-1]
            print(f"✅ 币安最新数据文件: {latest_binance}")
    
    # 检查统一数据
    if os.path.exists('unified_data'):
        unified_files = [f for f in os.listdir('unified_data') if f.endswith('.json')]
        if unified_files:
            print(f"✅ 统一数据文件: {unified_files[0]}")
    
    print("\n🎯 下一步建议:")
        print("1. 运行 scripts/ 目录下的访问脚本")
        print("2. 查看 documentation/ 目录下的使用说明")
        print("3. 根据需求选择合适的IDE集成方式")
        print("4. 开始您的量化交易或数据分析项目！")

if __name__ == "__main__":
    test_data_access()