"""
账户余额同步合约测试
测试多交易所账户余额同步的准确性、实时性和稳定性
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import logging

# 模拟交易所API响应数据
MOCK_BINANCE_SPOT_BALANCE = {
    "balances": [
        {"asset": "USDT", "free": "1000.0", "locked": "0.0"},
        {"asset": "BTC", "free": "0.05", "locked": "0.0"},
        {"asset": "ETH", "free": "2.0", "locked": "0.0"},
    ],
    "canTrade": True,
    "canWithdraw": True,
    "canDeposit": True
}

MOCK_BINANCE_FUTURES_BALANCE = {
    "assets": [
        {"asset": "USDT", "walletBalance": "1000.0", "unrealizedProfit": "10.5"},
        {"asset": "BTC", "walletBalance": "0.0", "unrealizedProfit": "-0.001"}
    ],
    "canTrade": True,
    "canWithdraw": True,
    "maxWithdrawAmount": "999.0"
}

MOCK_OKX_SPOT_BALANCE = {
    "data": [{
        "ccy": "USDT",
        "bal": "995.5",
        "frozenBal": "0.0",
        "availBal": "995.5"
    }]
}

MOCK_OKX_FUTURES_BALANCE = {
    "data": [{
        "ccy": "USDT",
        "availBal": "1005.0",
        "bal": "1015.5",
        "posIm": "10.0",
        "posMgn": "10.0"
    }]
}


class TestAccountBalanceSynchronization:
    """账户余额同步测试类"""
    
    @pytest.fixture
    def mock_exchange_apis(self):
        """模拟交易所API"""
        mock_binance_spot = AsyncMock()
        mock_binance_futures = AsyncMock()
        mock_okx_spot = AsyncMock()
        mock_okx_futures = AsyncMock()
        
        # 设置模拟响应
        mock_binance_spot.get_account_info.return_value = MOCK_BINANCE_SPOT_BALANCE
        mock_binance_futures.get_account_info.return_value = MOCK_BINANCE_FUTURES_BALANCE
        mock_okx_spot.get_account_info.return_value = MOCK_OKX_SPOT_BALANCE
        mock_okx_futures.get_account_info.return_value = MOCK_OKX_FUTURES_BALANCE
        
        return {
            'binance_spot': mock_binance_spot,
            'binance_futures': mock_binance_futures,
            'okx_spot': mock_okx_spot,
            'okx_futures': mock_okx_futures
        }
    
    @pytest.fixture
    def account_sync_manager(self, mock_exchange_apis):
        """创建账户同步管理器"""
        from backend.src.core.account_sync import AccountSyncManager
        return AccountSyncManager(mock_exchange_apis)
    
    @pytest.mark.asyncio
    async def test_single_exchange_balance_sync(self, account_sync_manager, mock_exchange_apis):
        """测试单交易所余额同步"""
        # 测试币安现货账户同步
        result = await account_sync_manager.sync_binance_spot_account(1, 1)
        
        assert result is not None
        assert 'balances' in result
        assert 'USDT' in result['balances']
        
        # 验证余额数据准确性
        usdt_balance = result['balances']['USDT']
        assert usdt_balance['available'] == Decimal('1000.0')
        assert usdt_balance['locked'] == Decimal('0.0')
        assert usdt_balance['total'] == Decimal('1000.0')
        
        # 验证其他币种
        btc_balance = result['balances']['BTC']
        assert btc_balance['available'] == Decimal('0.05')
        
        # 验证API调用
        mock_exchange_apis['binance_spot'].get_account_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_binance_futures_balance_sync(self, account_sync_manager, mock_exchange_apis):
        """测试币安期货账户同步"""
        result = await account_sync_manager.sync_binance_futures_account(1, 1)
        
        assert result is not None
        assert 'assets' in result
        
        # 验证USDT余额
        usdt_balance = result['assets']['USDT']
        assert usdt_balance['wallet_balance'] == Decimal('1000.0')
        assert usdt_balance['unrealized_pnl'] == Decimal('10.5')
        assert usdt_balance['total_balance'] == Decimal('1010.5')
        
        # 验证持仓保证金信息
        assert 'margin_balance' in usdt_balance
        assert usdt_balance['available_balance'] == Decimal('990.0')  # wallet_balance - unrealized_pnl
        
        mock_exchange_apis['binance_futures'].get_account_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_okx_balance_sync(self, account_sync_manager, mock_exchange_apis):
        """测试OKX账户同步"""
        # 测试OKX现货
        spot_result = await account_sync_manager.sync_okx_spot_account(1, 1)
        assert spot_result is not None
        assert 'USDT' in spot_result['balances']
        assert spot_result['balances']['USDT']['available'] == Decimal('995.5')
        
        # 测试OKX期货
        futures_result = await account_sync_manager.sync_okx_futures_account(1, 1)
        assert futures_result is not None
        assert 'USDT' in futures_result['assets']
        assert futures_result['assets']['USDT']['available_balance'] == Decimal('1005.0')
        assert futures_result['assets']['USDT']['total_balance'] == Decimal('1015.5')
        
        # 验证API调用
        mock_exchange_apis['okx_spot'].get_account_info.assert_called_once()
        mock_exchange_apis['okx_futures'].get_account_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_exchange_balance_consolidation(self, account_sync_manager):
        """测试多交易所余额合并"""
        # 合并所有交易所余额
        result = await account_sync_manager.consolidate_all_accounts(1, 1)
        
        assert result is not None
        assert 'user_id' in result
        assert 'account_id' in result
        assert 'total_balances' in result
        assert 'exchange_balances' in result
        
        # 验证总余额计算
        total_balances = result['total_balances']
        assert 'USDT' in total_balances
        assert 'BTC' in total_balances
        assert 'ETH' in total_balances
        
        # 验证各交易所余额明细
        exchange_balances = result['exchange_balances']
        assert 'binance_spot' in exchange_balances
        assert 'binance_futures' in exchange_balances
        assert 'okx_spot' in exchange_balances
        assert 'okx_futures' in exchange_balances
    
    @pytest.mark.asyncio
    async def test_balance_sync_data_accuracy(self, account_sync_manager, mock_exchange_apis):
        """测试余额同步数据准确性"""
        # 执行同步
        result = await account_sync_manager.sync_and_validate_balances(1, 1)
        
        # 验证数据结构完整性
        assert 'sync_time' in result
        assert 'balances' in result
        assert 'validation' in result
        
        # 验证余额数据精度（保留到小数点后8位）
        for currency, balance_data in result['balances'].items():
            assert isinstance(balance_data['available'], Decimal)
            assert isinstance(balance_data['total'], Decimal)
            
            # 检查精度
            assert balance_data['available'] == balance_data['available'].quantize(Decimal('0.00000001'))
            assert balance_data['total'] == balance_data['total'].quantize(Decimal('0.00000001'))
        
        # 验证校验结果
        validation = result['validation']
        assert validation['data_integrity'] is True
        assert validation['precision_check'] is True
        assert validation['completeness_check'] is True
    
    @pytest.mark.asyncio
    async def test_balance_sync_latency(self, account_sync_manager, mock_exchange_apis):
        """测试余额同步延迟"""
        start_time = datetime.now()
        
        # 执行单次同步
        result = await account_sync_manager.sync_single_account('binance_spot', 1, 1)
        
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds()
        
        # 验证延迟要求（≤1秒）
        assert latency <= 1.0
        assert result is not None
        
        # 测试多账户同步延迟
        start_time = datetime.now()
        result = await account_sync_manager.consolidate_all_accounts(1, 1)
        end_time = datetime.now()
        total_latency = (end_time - start_time).total_seconds()
        
        # 验证多账户同步延迟（≤3秒）
        assert total_latency <= 3.0
    
    @pytest.mark.asyncio
    async def test_concurrent_balance_sync(self, account_sync_manager):
        """测试并发余额同步"""
        # 并发执行多个同步任务
        tasks = [
            account_sync_manager.sync_binance_spot_account(1, 1),
            account_sync_manager.sync_binance_futures_account(1, 1),
            account_sync_manager.sync_okx_spot_account(1, 1),
            account_sync_manager.sync_okx_futures_account(1, 1),
        ]
        
        start_time = datetime.now()
        results = await asyncio.gather(*tasks)
        end_time = datetime.now()
        
        concurrent_latency = (end_time - start_time).total_seconds()
        
        # 验证并发同步时间（应该比串行快）
        assert len(results) == 4
        assert all(result is not None for result in results)
        assert concurrent_latency <= 2.0  # 并发应该在2秒内完成
        
        # 验证结果一致性
        for i, result in enumerate(results):
            assert result is not None
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_balance_sync_error_handling(self, account_sync_manager, mock_exchange_apis):
        """测试余额同步错误处理"""
        # 模拟API错误
        mock_exchange_apis['binance_spot'].get_account_info.side_effect = Exception("API Error")
        
        # 执行同步并验证错误处理
        result = await account_sync_manager.sync_binance_spot_account(1, 1)
        
        # 应该返回错误信息而不是抛出异常
        assert result is not None
        assert 'error' in result
        assert result['error'] is not None
    
    @pytest.mark.asyncio
    async def test_balance_sync_fallback_mechanism(self, account_sync_manager, mock_exchange_apis):
        """测试余额同步回退机制"""
        # 模拟一个API失败但其他API正常
        mock_exchange_apis['binance_futures'].get_account_info.side_effect = Exception("API Unavailable")
        
        # 执行合并同步
        result = await account_sync_manager.consolidate_all_accounts(1, 1)
        
        # 验证部分成功的结果
        assert result is not None
        assert 'partial_success' in result
        assert result['partial_success'] is True
        
        # 验证可用的交易所数据
        exchange_balances = result['exchange_balances']
        assert 'binance_spot' in exchange_balances
        assert 'okx_spot' in exchange_balances
        assert 'okx_futures' in exchange_balances
        # 期货数据应该缺失
        assert 'binance_futures' not in exchange_balances
    
    @pytest.mark.asyncio
    async def test_balance_data_caching(self, account_sync_manager, mock_exchange_apis):
        """测试余额数据缓存机制"""
        # 首次获取
        result1 = await account_sync_manager.sync_binance_spot_account(1, 1)
        
        # 验证API被调用
        assert mock_exchange_apis['binance_spot'].get_account_info.call_count == 1
        
        # 再次获取（应该使用缓存）
        result2 = await account_sync_manager.sync_binance_spot_account(1, 1)
        
        # 验证缓存机制工作（API调用次数不应该增加）
        assert mock_exchange_apis['binance_spot'].get_account_info.call_count == 1
        
        # 验证缓存数据一致性
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_balance_sync_real_time_monitoring(self, account_sync_manager):
        """测试实时余额监控"""
        # 开始实时监控
        monitoring_task = asyncio.create_task(
            account_sync_manager.start_real_time_monitoring(1, 1, interval=0.1)
        )
        
        # 等待一些监控数据
        await asyncio.sleep(0.5)
        
        # 停止监控
        monitoring_task.cancel()
        
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证监控数据
        monitoring_data = account_sync_manager.get_monitoring_data()
        assert monitoring_data is not None
        assert len(monitoring_data) > 0
    
    @pytest.mark.asyncio
    async def test_balance_sync_performance_benchmark(self, account_sync_manager):
        """测试余额同步性能基准"""
        # 执行多次同步并统计性能
        sync_times = []
        
        for _ in range(10):
            start_time = datetime.now()
            await account_sync_manager.sync_and_validate_balances(1, 1)
            end_time = datetime.now()
            
            sync_time = (end_time - start_time).total_seconds()
            sync_times.append(sync_time)
        
        # 验证性能统计
        avg_time = sum(sync_times) / len(sync_times)
        max_time = max(sync_times)
        min_time = min(sync_times)
        
        # 性能要求
        assert avg_time <= 0.5  # 平均延迟≤500ms
        assert max_time <= 1.0  # 最大延迟≤1秒
        assert min_time >= 0.01  # 最小延迟≥10ms
        
        print(f"性能统计: 平均={avg_time:.3f}s, 最大={max_time:.3f}s, 最小={min_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_balance_sync_consistency_across_exchanges(self, account_sync_manager):
        """测试跨交易所余额一致性"""
        # 获取所有交易所余额
        balances = await account_sync_manager.get_all_exchange_balances(1, 1)
        
        # 验证数据一致性
        for exchange_name, exchange_data in balances.items():
            assert exchange_data is not None
            assert len(exchange_data) > 0
            
            # 验证每种货币的数据结构
            for currency, amount in exchange_data.items():
                assert isinstance(amount, Decimal)
                assert amount >= 0  # 余额不能为负数
        
        # 验证不同交易所的相同货币总额
        total_usdt = sum(
            balances[exchange].get('USDT', Decimal('0')) 
            for exchange in balances
        )
        
        assert total_usdt > 0  # 总USDT余额应该大于0


class TestAccountDataIntegrity:
    """账户数据完整性测试"""
    
    @pytest.mark.asyncio
    async def test_decimal_precision_validation(self):
        """测试Decimal精度验证"""
        from backend.src.core.account_sync import DecimalValidator
        
        validator = DecimalValidator()
        
        # 测试有效精度
        valid_amount = Decimal("1000.12345678")
        assert validator.validate_precision(valid_amount, 8) is True
        
        # 测试无效精度
        invalid_amount = Decimal("1000.123456789")
        assert validator.validate_precision(invalid_amount, 8) is False
        
        # 测试零值
        zero_amount = Decimal("0")
        assert validator.validate_precision(zero_amount, 8) is True
    
    @pytest.mark.asyncio
    async def test_balance_reconciliation(self):
        """测试余额对账"""
        from backend.src.core.account_sync import BalanceReconciliator
        
        reconciliator = BalanceReconciliator()
        
        # 模拟不同的余额数据源
        source1 = {'USDT': Decimal('1000.0'), 'BTC': Decimal('0.1')}
        source2 = {'USDT': Decimal('1000.0'), 'BTC': Decimal('0.1')}
        source3 = {'USDT': Decimal('999.9'), 'BTC': Decimal('0.11')}
        
        # 验证相同数据源对账
        assert reconciliator.reconcile_balances(source1, source2) is True
        
        # 验证不同数据源对账
        assert reconciliator.reconcile_balances(source1, source3) is False
    
    @pytest.mark.asyncio
    async def test_sync_timestamp_validation(self):
        """测试同步时间戳验证"""
        from backend.src.core.account_sync import SyncTimestampValidator
        
        validator = SyncTimestampValidator()
        
        # 验证有效时间戳
        valid_timestamp = datetime.now() - timedelta(seconds=30)
        assert validator.validate_timestamp(valid_timestamp, max_age_seconds=60) is True
        
        # 验证过期时间戳
        expired_timestamp = datetime.now() - timedelta(seconds=90)
        assert validator.validate_timestamp(expired_timestamp, max_age_seconds=60) is False


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])