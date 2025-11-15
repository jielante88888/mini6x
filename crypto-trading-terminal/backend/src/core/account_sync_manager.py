"""
多交易所账户余额同步管理器
统一管理币安和OKX交易所的账户余额同步
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import time

from ..storage.models.account_models import (
    Account, AccountBalance, ExchangeType, AccountType, account_manager
)
from ..adapters.binance.spot import BinanceSpotAdapter
from ..adapters.binance.futures import BinanceFuturesAdapter
from ..adapters.okx.spot import OKXSpotAdapter
from ..adapters.okx.futures import OKXFuturesAdapter
from ..core.exceptions import SyncException, ValidationException


class AccountSyncStatus:
    """同步状态"""
    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分成功


class AccountBalanceSyncManager:
    """账户余额同步管理器"""
    
    def __init__(self):
        self.exchange_adapters = {
            ExchangeType.BINANCE: {
                AccountType.SPOT: BinanceSpotAdapter(),
                AccountType.FUTURES: BinanceFuturesAdapter(),
                AccountType.MARGIN: BinanceSpotAdapter()  # 使用现货适配器
            },
            ExchangeType.OKX: {
                AccountType.SPOT: OKXSpotAdapter(),
                AccountType.FUTURES: OKXFuturesAdapter(),
                AccountType.MARGIN: OKXSpotAdapter()  # 使用现货适配器
            }
        }
        
        self.sync_status: Dict[str, str] = {}  # account_id -> status
        self.last_sync_times: Dict[str, datetime] = {}  # account_id -> last_sync_time
        self.sync_errors: Dict[str, List[str]] = {}  # account_id -> errors
        
        self.logger = logging.getLogger(__name__)
        
        # 同步配置
        self.sync_interval = 30  # 30秒同步间隔
        self.retry_attempts = 3
        self.timeout_seconds = 30
    
    async def sync_account_balance(
        self,
        account_id: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """同步指定账户余额"""
        try:
            self.logger.info(f"开始同步账户余额: {account_id}")
            
            # 获取账户信息
            account = await account_manager.get_account(account_id)
            if not account:
                raise ValidationException(f"账户不存在: {account_id}")
            
            # 检查是否需要同步
            if not force_sync and self._should_skip_sync(account_id):
                return {
                    'account_id': account_id,
                    'status': 'skipped',
                    'reason': 'sync_too_recent',
                    'last_sync': self.last_sync_times.get(account_id).isoformat() if self.last_sync_times.get(account_id) else None
                }
            
            # 设置同步状态
            self.sync_status[account_id] = AccountSyncStatus.SYNCING
            sync_start_time = time.time()
            
            # 获取相应的交易所适配器
            adapter = self._get_exchange_adapter(account.exchange, account.account_type)
            if not adapter:
                raise ValidationException(f"不支持的交易所或账户类型: {account.exchange.value} {account.account_type.value}")
            
            # 执行同步
            sync_result = await self._sync_with_adapter(adapter, account)
            
            # 更新账户余额
            success_count = await self._update_account_balances(account, sync_result)
            
            # 更新同步状态
            sync_duration = time.time() - sync_start_time
            self._update_sync_status(account_id, success_count, sync_result, sync_duration)
            
            self.logger.info(f"账户余额同步完成: {account_id}, 耗时: {sync_duration:.2f}秒")
            
            return {
                'account_id': account_id,
                'status': self.sync_status.get(account_id),
                'synced_balances': success_count,
                'total_exchange_balances': len(sync_result),
                'sync_duration': sync_duration,
                'last_sync': datetime.now().isoformat(),
                'errors': self.sync_errors.get(account_id, [])
            }
            
        except Exception as e:
            self.logger.error(f"同步账户余额失败: {account_id}, 错误: {e}")
            self.sync_status[account_id] = AccountSyncStatus.FAILED
            self._add_sync_error(account_id, str(e))
            raise SyncException(f"同步账户余额失败: {e}")
    
    async def sync_user_all_accounts(
        self,
        user_id: int,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """同步用户所有账户余额"""
        try:
            self.logger.info(f"开始同步用户所有账户余额: {user_id}")
            
            # 获取用户所有账户
            user_accounts = await account_manager.get_user_accounts(user_id)
            if not user_accounts:
                return {
                    'user_id': user_id,
                    'total_accounts': 0,
                    'successful_syncs': 0,
                    'failed_syncs': 0,
                    'results': []
                }
            
            # 并行同步所有账户
            sync_tasks = []
            for account in user_accounts:
                task = asyncio.create_task(
                    self.sync_account_balance(account.account_id, force_sync)
                )
                sync_tasks.append((account.account_id, task))
            
            # 收集结果
            results = []
            successful_syncs = 0
            failed_syncs = 0
            
            for account_id, task in sync_tasks:
                try:
                    result = await task
                    results.append(result)
                    
                    if result['status'] == AccountSyncStatus.SUCCESS:
                        successful_syncs += 1
                    else:
                        failed_syncs += 1
                        
                except Exception as e:
                    self.logger.error(f"账户同步异常: {account_id}, 错误: {e}")
                    results.append({
                        'account_id': account_id,
                        'status': AccountSyncStatus.FAILED,
                        'error': str(e)
                    })
                    failed_syncs += 1
            
            self.logger.info(f"用户账户余额同步完成: {user_id}, 成功: {successful_syncs}, 失败: {failed_syncs}")
            
            return {
                'user_id': user_id,
                'total_accounts': len(user_accounts),
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'success_rate': successful_syncs / len(user_accounts) * 100 if user_accounts else 0,
                'results': results,
                'sync_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"同步用户所有账户余额失败: {user_id}, 错误: {e}")
            raise SyncException(f"同步用户所有账户余额失败: {e}")
    
    async def sync_all_user_accounts(self) -> Dict[str, Any]:
        """同步所有用户的所有账户（管理员功能）"""
        try:
            self.logger.info("开始同步所有用户的所有账户")
            
            # 获取所有账户
            all_accounts = list(account_manager.accounts.values())
            unique_users = set(account.user_id for account in all_accounts)
            
            # 按用户分组并行同步
            sync_tasks = []
            for user_id in unique_users:
                task = asyncio.create_task(self.sync_user_all_accounts(user_id))
                sync_tasks.append((user_id, task))
            
            # 收集结果
            user_results = {}
            total_successful = 0
            total_failed = 0
            
            for user_id, task in sync_tasks:
                try:
                    result = await task
                    user_results[user_id] = result
                    total_successful += result['successful_syncs']
                    total_failed += result['failed_syncs']
                except Exception as e:
                    self.logger.error(f"用户账户同步失败: {user_id}, 错误: {e}")
                    user_results[user_id] = {
                        'user_id': user_id,
                        'status': 'failed',
                        'error': str(e)
                    }
                    total_failed += 1
            
            total_accounts = sum(len(account_manager.get_user_accounts(user_id)) for user_id in unique_users)
            
            self.logger.info(f"全量账户余额同步完成, 总账户: {total_accounts}, 成功: {total_successful}, 失败: {total_failed}")
            
            return {
                'total_users': len(unique_users),
                'total_accounts': total_accounts,
                'successful_syncs': total_successful,
                'failed_syncs': total_failed,
                'success_rate': total_successful / total_accounts * 100 if total_accounts else 0,
                'user_results': user_results,
                'sync_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"全量账户余额同步失败: {e}")
            raise SyncException(f"全量账户余额同步失败: {e}")
    
    async def get_sync_status(self, account_id: str) -> Dict[str, Any]:
        """获取账户同步状态"""
        account = await account_manager.get_account(account_id)
        if not account:
            return {'error': '账户不存在'}
        
        return {
            'account_id': account_id,
            'sync_status': self.sync_status.get(account_id, AccountSyncStatus.IDLE),
            'last_sync_time': self.last_sync_times.get(account_id).isoformat() if self.last_sync_times.get(account_id) else None,
            'errors': self.sync_errors.get(account_id, []),
            'account_info': {
                'exchange': account.exchange.value,
                'account_type': account.account_type.value,
                'is_active': account.is_active,
                'total_balance_usdt': float(account.total_balance_usdt)
            }
        }
    
    async def start_periodic_sync(self, user_id: Optional[int] = None):
        """启动定期同步"""
        async def sync_worker():
            while True:
                try:
                    if user_id:
                        # 同步指定用户
                        await self.sync_user_all_accounts(user_id, force_sync=False)
                    else:
                        # 同步所有用户
                        await self.sync_all_user_accounts()
                    
                    # 等待下次同步
                    await asyncio.sleep(self.sync_interval)
                    
                except Exception as e:
                    self.logger.error(f"定期同步异常: {e}")
                    await asyncio.sleep(60)  # 异常时等待1分钟再试
        
        # 启动后台同步任务
        sync_task = asyncio.create_task(sync_worker())
        self.logger.info(f"启动定期同步任务 (用户: {user_id or '所有'})")
        return sync_task
    
    def _should_skip_sync(self, account_id: str) -> bool:
        """检查是否应该跳过同步"""
        last_sync = self.last_sync_times.get(account_id)
        if not last_sync:
            return False
        
        # 检查是否在同步间隔内
        time_since_last_sync = datetime.now() - last_sync
        return time_since_last_sync.total_seconds() < self.sync_interval
    
    def _get_exchange_adapter(self, exchange: ExchangeType, account_type: AccountType):
        """获取交易所适配器"""
        return self.exchange_adapters.get(exchange, {}).get(account_type)
    
    async def _sync_with_adapter(self, adapter, account: Account) -> List[Dict[str, Any]]:
        """使用适配器执行同步"""
        try:
            # 设置API配置（从环境或配置获取）
            api_key = self._get_api_key(account.exchange)
            api_secret = self._get_api_secret(account.exchange)
            
            if not api_key or not api_secret:
                raise ValidationException(f"未配置{account.exchange.value}的API密钥")
            
            # 重试机制
            for attempt in range(self.retry_attempts):
                try:
                    # 根据账户类型获取余额
                    if account.account_type == AccountType.SPOT:
                        # 现货账户余额
                        balance_data = await adapter.get_account_info(
                            api_key=api_key,
                            api_secret=api_secret,
                            testnet=account.testnet_mode
                        )
                        
                        # 转换为统一格式
                        unified_balances = []
                        if 'balances' in balance_data:
                            for balance in balance_data['balances']:
                                unified_balances.append({
                                    'symbol': balance['asset'],
                                    'free': Decimal(balance['free']),
                                    'locked': Decimal(balance['locked'])
                                })
                        
                        return unified_balances
                        
                    elif account.account_type == AccountType.FUTURES:
                        # 合约账户余额
                        futures_data = await adapter.get_account_info(
                            api_key=api_key,
                            api_secret=api_secret,
                            testnet=account.testnet_mode
                        )
                        
                        # 转换为统一格式
                        unified_balances = []
                        if 'assets' in futures_data:
                            for asset in futures_data['assets']:
                                unified_balances.append({
                                    'symbol': asset['asset'],
                                    'free': Decimal(asset['availableBalance']),
                                    'locked': Decimal(asset['walletBalance']) - Decimal(asset['availableBalance'])
                                })
                        
                        return unified_balances
                    
                except Exception as e:
                    self.logger.warning(f"同步尝试 {attempt + 1} 失败: {e}")
                    if attempt == self.retry_attempts - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
            return []
            
        except Exception as e:
            self.logger.error(f"使用适配器同步失败: {e}")
            raise SyncException(f"交易所API同步失败: {e}")
    
    async def _update_account_balances(
        self,
        account: Account,
        sync_result: List[Dict[str, Any]]
    ) -> int:
        """更新账户余额"""
        success_count = 0
        
        for balance_data in sync_result:
            try:
                symbol = balance_data['symbol']
                free_balance = balance_data['free']
                locked_balance = balance_data['locked']
                
                # 更新账户余额
                account.add_balance(symbol, free_balance, locked_balance)
                success_count += 1
                
            except Exception as e:
                self.logger.error(f"更新余额失败 {symbol}: {e}")
                self._add_sync_error(account.account_id, f"更新{symbol}余额失败: {e}")
        
        return success_count
    
    def _update_sync_status(
        self,
        account_id: str,
        success_count: int,
        sync_result: List[Dict[str, Any]],
        sync_duration: float
    ):
        """更新同步状态"""
        self.last_sync_times[account_id] = datetime.now()
        
        total_count = len(sync_result)
        if success_count == total_count and total_count > 0:
            self.sync_status[account_id] = AccountSyncStatus.SUCCESS
        elif success_count > 0:
            self.sync_status[account_id] = AccountSyncStatus.PARTIAL
        else:
            self.sync_status[account_id] = AccountSyncStatus.FAILED
        
        self.logger.debug(
            f"同步状态更新: {account_id}, "
            f"状态: {self.sync_status[account_id]}, "
            f"成功: {success_count}/{total_count}, "
            f"耗时: {sync_duration:.2f}秒"
        )
    
    def _add_sync_error(self, account_id: str, error: str):
        """添加同步错误"""
        if account_id not in self.sync_errors:
            self.sync_errors[account_id] = []
        
        self.sync_errors[account_id].append({
            'timestamp': datetime.now().isoformat(),
            'error': error
        })
        
        # 保持错误记录在合理范围内
        if len(self.sync_errors[account_id]) > 50:
            self.sync_errors[account_id] = self.sync_errors[account_id][-25:]
    
    def _get_api_key(self, exchange: ExchangeType) -> Optional[str]:
        """获取API密钥"""
        # 从环境变量或配置获取
        env_keys = {
            ExchangeType.BINANCE: 'BINANCE_API_KEY',
            ExchangeType.OKX: 'OKX_API_KEY',
        }
        
        import os
        return os.getenv(env_keys.get(exchange))
    
    def _get_api_secret(self, exchange: ExchangeType) -> Optional[str]:
        """获取API密钥"""
        # 从环境变量或配置获取
        env_secrets = {
            ExchangeType.BINANCE: 'BINANCE_API_SECRET',
            ExchangeType.OKX: 'OKX_API_SECRET',
        }
        
        import os
        return os.getenv(env_secrets.get(exchange))
    
    async def get_sync_metrics(self) -> Dict[str, Any]:
        """获取同步指标"""
        try:
            total_accounts = len(account_manager.accounts)
            active_syncs = len([status for status in self.sync_status.values() if status == AccountSyncStatus.SYNCING])
            successful_syncs = len([status for status in self.sync_status.values() if status == AccountSyncStatus.SUCCESS])
            failed_syncs = len([status for status in self.sync_status.values() if status == AccountSyncStatus.FAILED])
            
            # 计算成功率
            success_rate = (successful_syncs / total_accounts * 100) if total_accounts > 0 else 0
            
            # 计算平均同步时间
            sync_durations = []
            for account_id in self.last_sync_times:
                # 这里应该从数据库或缓存获取同步时间
                # 简化处理，使用时间戳差值
                last_sync = self.last_sync_times[account_id]
                sync_duration = (datetime.now() - last_sync).total_seconds()
                if sync_duration < self.sync_interval:  # 最近同步的
                    sync_durations.append(sync_duration)
            
            avg_sync_duration = sum(sync_durations) / len(sync_durations) if sync_durations else 0
            
            return {
                'total_accounts': total_accounts,
                'active_syncs': active_syncs,
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'success_rate': success_rate,
                'avg_sync_duration': avg_sync_duration,
                'sync_interval': self.sync_interval,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取同步指标失败: {e}")
            return {'error': str(e)}


# 全局同步管理器实例
sync_manager = AccountBalanceSyncManager()