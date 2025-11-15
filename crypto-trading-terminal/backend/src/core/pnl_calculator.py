"""
实时盈亏计算服务
统一计算现货和合约持仓的实时盈亏，支持多种计算模式和高级功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum

from ..storage.models.account_models import (
    Position, PnLRecord, PnLType, Account, account_manager
)
from ..storage.models.account_models import PositionType, PnLSummary
from ..core.exceptions import ValidationException, CalculationException


class PnLCalculationMode(Enum):
    """盈亏计算模式"""
    BASIC = "basic"              # 基础计算
    MARK_TO_MARKET = "m2m"       # 逐日盯市
    REALIZED_ONLY = "realized"   # 仅已实现盈亏
    UNREALIZED_ONLY = "unrealized"  # 仅未实现盈亏
    COMPREHENSIVE = "comprehensive"  # 综合计算


class PnLCalculationConfig:
    """盈亏计算配置"""
    
    def __init__(self):
        # 计算精度设置
        self.price_precision = Decimal('0.01')  # 价格精度
        self.pnl_precision = Decimal('0.0001')  # PnL精度
        
        # 风险控制设置
        self.max_leverage_warning = Decimal('20')  # 最大杠杆警告
        self.min_margin_level = Decimal('1.1')     # 最小保证金水平
        
        # 性能设置
        self.cache_ttl_seconds = 30  # 缓存TTL
        self.batch_size = 100        # 批处理大小
        
        # 成本计算
        self.include_commission = True
        self.include_funding_fee = True
        self.include_slippage = False  # 滑点成本


class RealTimePnLCalculator:
    """实时盈亏计算器"""
    
    def __init__(self, config: PnLCalculationConfig = None):
        self.config = config or PnLCalculationConfig()
        self.market_prices: Dict[str, Decimal] = {}  # 实时价格缓存
        self.last_calculation: Dict[str, datetime] = {}  # 最后计算时间
        
        self.logger = logging.getLogger(__name__)
    
    async def calculate_position_pnl(
        self,
        position: Position,
        current_price: Optional[Decimal] = None,
        calculation_mode: PnLCalculationMode = PnLCalculationMode.COMPREHENSIVE
    ) -> Dict[str, Any]:
        """计算单个持仓的盈亏"""
        try:
            # 获取当前价格
            if current_price is None:
                current_price = await self._get_current_price(position.symbol)
            
            if current_price is None or current_price <= 0:
                raise ValidationException(f"无效的价格: {position.symbol} {current_price}")
            
            # 根据持仓类型选择计算方法
            if position.position_type == PositionType.SPOT:
                result = await self._calculate_spot_pnl(position, current_price, calculation_mode)
            else:
                result = await self._calculate_futures_pnl(position, current_price, calculation_mode)
            
            # 添加通用信息
            result.update({
                'position_id': position.position_id,
                'symbol': position.symbol,
                'calculation_time': datetime.now().isoformat(),
                'calculation_mode': calculation_mode.value,
                'current_price': float(current_price)
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算持仓盈亏失败 {position.position_id}: {e}")
            raise CalculationException(f"计算持仓盈亏失败: {e}")
    
    async def _calculate_spot_pnl(
        self,
        position: Position,
        current_price: Decimal,
        mode: PnLCalculationMode
    ) -> Dict[str, Any]:
        """计算现货持仓盈亏"""
        try:
            # 基础计算
            quantity = abs(position.quantity)
            entry_price = position.entry_price
            
            if quantity == 0:
                return self._empty_position_result(position, current_price)
            
            # 计算持仓价值
            position_value = quantity * current_price
            cost_basis = quantity * entry_price
            
            # 计算未实现盈亏
            if position.quantity > 0:  # 多头
                unrealized_pnl = (current_price - entry_price) * quantity
            else:  # 空头（如果支持）
                unrealized_pnl = (entry_price - current_price) * quantity
            
            # 计算百分比
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else Decimal('0')
            
            # 计算已实现盈亏（如果有交易记录）
            realized_pnl = position.realized_pnl
            
            # 计算总盈亏
            total_pnl = unrealized_pnl + realized_pnl
            
            # 根据计算模式调整结果
            if mode == PnLCalculationMode.REALIZED_ONLY:
                display_unrealized_pnl = Decimal('0')
            elif mode == PnLCalculationMode.UNREALIZED_ONLY:
                display_unrealized_pnl = unrealized_pnl
                realized_pnl = Decimal('0')
            else:  # BASIC, M2M, COMPREHENSIVE
                display_unrealized_pnl = unrealized_pnl
            
            # 计算净盈亏（扣除费用）
            total_fees = position.commission_paid
            net_pnl = total_pnl - total_fees
            
            # 计算ROI
            roi_pct = (net_pnl / cost_basis * 100) if cost_basis > 0 else Decimal('0')
            
            return {
                'position_quantity': float(position.quantity),
                'entry_price': float(entry_price),
                'current_price': float(current_price),
                'position_value': float(position_value),
                'cost_basis': float(cost_basis),
                'unrealized_pnl': float(display_unrealized_pnl),
                'realized_pnl': float(realized_pnl),
                'total_pnl': float(total_pnl),
                'net_pnl': float(net_pnl),
                'total_fees': float(total_fees),
                'unrealized_pnl_pct': float(unrealized_pnl_pct),
                'roi_pct': float(roi_pct),
                'calculation_details': {
                    'quantity': float(quantity),
                    'side': position.side,
                    'commission_included': self.config.include_commission,
                    'slippage_included': self.config.include_slippage
                }
            }
            
        except Exception as e:
            self.logger.error(f"计算现货持仓盈亏失败: {e}")
            raise CalculationException(f"计算现货持仓盈亏失败: {e}")
    
    async def _calculate_futures_pnl(
        self,
        position: Position,
        current_price: Decimal,
        mode: PnLCalculationMode
    ) -> Dict[str, Any]:
        """计算合约持仓盈亏"""
        try:
            quantity = position.quantity
            entry_price = position.entry_price
            leverage = position.leverage
            contract_value = position.contract_value
            
            if quantity == 0:
                return self._empty_position_result(position, current_price)
            
            # 基础合约计算
            nominal_value = abs(quantity) * current_price * contract_value
            cost_basis = abs(quantity) * entry_price * contract_value
            
            # 计算未实现盈亏
            if position.side == "LONG":
                unrealized_pnl = (current_price - entry_price) * quantity * contract_value
            else:  # SHORT
                unrealized_pnl = (entry_price - current_price) * abs(quantity) * contract_value
            
            # 计算已实现盈亏
            realized_pnl = position.realized_pnl
            
            # 计算保证金相关指标
            margin_used = position.margin_used
            effective_leverage = nominal_value / margin_used if margin_used > 0 else Decimal('0')
            
            # 计算杠杆调整后的收益率
            if margin_used > 0:
                leverage_roi = (unrealized_pnl / margin_used * 100) if margin_used > 0 else Decimal('0')
                effective_roi = leverage_roi  # 杠杆效应已包含在margin_used中
            else:
                leverage_roi = Decimal('0')
                effective_roi = Decimal('0')
            
            # 计算资金费率影响
            funding_fee = position.funding_fee
            funding_rate_impact = Decimal('0')  # 需要从市场数据获取实际资金费率
            
            # 计算滑点成本（如果启用）
            slippage_cost = Decimal('0')
            if self.config.include_slippage:
                # 简化计算：假设0.01%的滑点
                slippage_cost = nominal_value * Decimal('0.0001')
            
            # 总费用
            total_fees = position.commission_paid + funding_fee + slippage_cost
            
            # 计算保证金水平
            if margin_used > 0:
                margin_level = (margin_used + unrealized_pnl) / margin_used if (margin_used + unrealized_pnl) >= 0 else Decimal('0')
            else:
                margin_level = Decimal('0')
            
            # 强平价格（估算）
            liquidation_price = self._estimate_liquidation_price(position, current_price)
            
            # 根据计算模式调整结果
            if mode == PnLCalculationMode.REALIZED_ONLY:
                display_unrealized_pnl = Decimal('0')
                display_funding_fee = Decimal('0')
            elif mode == PnLCalculationMode.UNREALIZED_ONLY:
                display_unrealized_pnl = unrealized_pnl
                display_funding_fee = funding_rate_impact
                realized_pnl = Decimal('0')
            else:  # BASIC, M2M, COMPREHENSIVE
                display_unrealized_pnl = unrealized_pnl
                display_funding_fee = funding_rate_impact
            
            # 总盈亏
            total_pnl = display_unrealized_pnl + realized_pnl - display_funding_fee
            net_pnl = total_pnl - total_fees
            
            # 计算回报率
            if cost_basis > 0:
                pnl_percentage = total_pnl / cost_basis * 100
            else:
                pnl_percentage = Decimal('0')
            
            return {
                'position_quantity': float(position.quantity),
                'entry_price': float(entry_price),
                'current_price': float(current_price),
                'nominal_value': float(nominal_value),
                'cost_basis': float(cost_basis),
                'unrealized_pnl': float(display_unrealized_pnl),
                'realized_pnl': float(realized_pnl),
                'funding_fee': float(display_funding_fee),
                'total_pnl': float(total_pnl),
                'net_pnl': float(net_pnl),
                'total_fees': float(total_fees),
                'slippage_cost': float(slippage_cost),
                'margin_used': float(margin_used),
                'effective_leverage': float(effective_leverage),
                'margin_level': float(margin_level),
                'leverage_roi_pct': float(leverage_roi),
                'pnl_percentage': float(pnl_percentage),
                'liquidation_price': float(liquidation_price) if liquidation_price else None,
                'calculation_details': {
                    'contract_value': float(contract_value),
                    'side': position.side,
                    'leverage': float(leverage),
                    'funding_rate_included': self.config.include_funding_fee,
                    'commission_included': self.config.include_commission,
                    'slippage_included': self.config.include_slippage
                }
            }
            
        except Exception as e:
            self.logger.error(f"计算合约持仓盈亏失败: {e}")
            raise CalculationException(f"计算合约持仓盈亏失败: {e}")
    
    def _empty_position_result(self, position: Position, current_price: Decimal) -> Dict[str, Any]:
        """空持仓结果"""
        return {
            'position_quantity': 0.0,
            'position_value': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': float(position.realized_pnl),
            'total_pnl': float(position.realized_pnl),
            'net_pnl': float(position.realized_pnl - position.commission_paid),
            'total_fees': float(position.commission_paid),
            'current_price': float(current_price),
            'calculation_details': {'note': 'empty_position'}
        }
    
    def _estimate_liquidation_price(self, position: Position, current_price: Decimal) -> Optional[Decimal]:
        """估算强平价格"""
        try:
            if position.position_type == PositionType.FUTURES and position.liquidation_price:
                return position.liquidation_price
            
            # 估算强平价格（简化计算）
            margin_ratio = self.config.min_margin_level  # 使用配置的最小保证金比例
            maintenance_margin_rate = Decimal('0.005')  # 0.5%维持保证金率
            
            if position.side == "LONG":
                # 多头强平价 = 入场价 * (1 - 维持保证金率 * 杠杆)
                liquidation_price = position.entry_price * (1 - maintenance_margin_rate * position.leverage)
            else:
                # 空头强平价 = 入场价 * (1 + 维持保证金率 * 杠杆)
                liquidation_price = position.entry_price * (1 + maintenance_margin_rate * position.leverage)
            
            return liquidation_price
            
        except Exception as e:
            self.logger.warning(f"估算强平价格失败: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """获取当前价格（从缓存或API）"""
        try:
            # 检查缓存
            if symbol in self.market_prices:
                last_update = self.last_calculation.get(symbol)
                if last_update and (datetime.now() - last_update).total_seconds() < self.config.cache_ttl_seconds:
                    return self.market_prices[symbol]
            
            # TODO: 从市场数据服务获取实时价格
            # 这里需要实现市场数据获取逻辑
            # 示例返回模拟价格
            price = self.market_prices.get(symbol, Decimal('100'))
            
            # 更新缓存
            self.market_prices[symbol] = price
            self.last_calculation[symbol] = datetime.now()
            
            return price
            
        except Exception as e:
            self.logger.error(f"获取当前价格失败 {symbol}: {e}")
            return None
    
    async def calculate_portfolio_pnl(
        self,
        account_id: str,
        current_prices: Optional[Dict[str, Decimal]] = None,
        mode: PnLCalculationMode = PnLCalculationMode.COMPREHENSIVE
    ) -> Dict[str, Any]:
        """计算投资组合盈亏"""
        try:
            # 获取账户的所有持仓
            positions = await account_manager.get_account_positions(account_id)
            
            if not positions:
                return {
                    'account_id': account_id,
                    'total_positions': 0,
                    'total_pnl': 0.0,
                    'net_pnl': 0.0,
                    'positions': []
                }
            
            # 批量计算每个持仓的盈亏
            position_results = []
            total_unrealized_pnl = Decimal('0')
            total_realized_pnl = Decimal('0')
            total_fees = Decimal('0')
            total_margin_used = Decimal('0')
            total_position_value = Decimal('0')
            
            for position in positions:
                # 获取或使用提供当前价格
                current_price = None
                if current_prices:
                    current_price = current_prices.get(position.symbol)
                elif position.symbol in self.market_prices:
                    current_price = self.market_prices[position.symbol]
                
                try:
                    result = await self.calculate_position_pnl(position, current_price, mode)
                    position_results.append(result)
                    
                    # 累加统计数据
                    total_unrealized_pnl += Decimal(str(result['unrealized_pnl']))
                    total_realized_pnl += Decimal(str(result['realized_pnl']))
                    total_fees += Decimal(str(result['total_fees']))
                    total_position_value += Decimal(str(result.get('position_value', 0)))
                    
                    # 合约持仓的保证金
                    if position.position_type == PositionType.FUTURES:
                        total_margin_used += Decimal(str(result.get('margin_used', 0)))
                    
                except Exception as e:
                    self.logger.error(f"计算持仓盈亏失败 {position.position_id}: {e}")
                    # 添加错误信息到结果
                    position_results.append({
                        'position_id': position.position_id,
                        'symbol': position.symbol,
                        'error': str(e)
                    })
            
            # 计算投资组合指标
            net_pnl = total_unrealized_pnl + total_realized_pnl - total_fees
            portfolio_roi = (net_pnl / total_position_value * 100) if total_position_value > 0 else Decimal('0')
            
            # 计算风险指标
            risk_metrics = self._calculate_portfolio_risk_metrics(position_results)
            
            return {
                'account_id': account_id,
                'total_positions': len(positions),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'total_realized_pnl': float(total_realized_pnl),
                'total_fees': float(total_fees),
                'total_pnl': float(total_unrealized_pnl + total_realized_pnl),
                'net_pnl': float(net_pnl),
                'total_position_value': float(total_position_value),
                'total_margin_used': float(total_margin_used),
                'portfolio_roi_pct': float(portfolio_roi),
                'risk_metrics': risk_metrics,
                'positions': position_results,
                'calculation_time': datetime.now().isoformat(),
                'calculation_mode': mode.value
            }
            
        except Exception as e:
            self.logger.error(f"计算投资组合盈亏失败 {account_id}: {e}")
            raise CalculationException(f"计算投资组合盈亏失败: {e}")
    
    def _calculate_portfolio_risk_metrics(self, position_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算投资组合风险指标"""
        try:
            # 提取成功的计算结果
            valid_results = [r for r in position_results if 'error' not in r]
            
            if not valid_results:
                return {'risk_level': 'UNKNOWN'}
            
            # 计算分散度
            symbols = [r['symbol'] for r in valid_results]
            unique_symbols = len(set(symbols))
            diversification_score = unique_symbols / len(valid_results) if valid_results else 0
            
            # 计算盈亏分布
            profitable_positions = len([r for r in valid_results if r.get('unrealized_pnl', 0) > 0])
            losing_positions = len([r for r in valid_results if r.get('unrealized_pnl', 0) < 0])
            
            # 计算集中度风险
            position_values = [r.get('position_value', 0) for r in valid_results]
            max_position_value = max(position_values) if position_values else 0
            total_position_value = sum(position_values)
            concentration_risk = (max_position_value / total_position_value) if total_position_value > 0 else 0
            
            # 风险等级评估
            risk_score = 0
            if concentration_risk > 0.5:  # 50%以上集中在单一持仓
                risk_score += 30
            if losing_positions > profitable_positions:  # 亏损持仓多于盈利持仓
                risk_score += 20
            if diversification_score < 0.3:  # 分散度低
                risk_score += 20
            
            if risk_score >= 70:
                risk_level = 'HIGH'
            elif risk_score >= 40:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'diversification_score': diversification_score,
                'profitable_positions': profitable_positions,
                'losing_positions': losing_positions,
                'concentration_risk': concentration_risk,
                'max_position_concentration_pct': concentration_risk * 100
            }
            
        except Exception as e:
            self.logger.error(f"计算投资组合风险指标失败: {e}")
            return {'risk_level': 'ERROR', 'error': str(e)}
    
    async def create_pnl_record(
        self,
        account_id: str,
        position_id: str,
        pnl_type: PnLType,
        calculation_result: Dict[str, Any]
    ) -> PnLRecord:
        """创建盈亏记录"""
        try:
            # 获取持仓信息
            positions = await account_manager.get_account_positions(account_id)
            position = next((p for p in positions if p.position_id == position_id), None)
            
            if not position:
                raise ValidationException(f"持仓不存在: {position_id}")
            
            # 创建盈亏记录
            record = await account_manager.create_pnl_record(
                account_id=account_id,
                symbol=position.symbol,
                pnl_type=pnl_type,
                pnl_amount=Decimal(str(calculation_result.get('total_pnl', 0))),
                period_start=datetime.now() - timedelta(hours=1),  # 最近1小时
                period_end=datetime.now(),
                position_id=position_id,
                quantity=Decimal(str(abs(position.quantity))),
                entry_price=Decimal(str(position.entry_price)),
                exit_price=Decimal(str(calculation_result.get('current_price', 0))),
                commission=Decimal(str(calculation_result.get('total_fees', 0))),
                funding_fee=Decimal(str(calculation_result.get('funding_fee', 0))),
                pnl_percentage=Decimal(str(calculation_result.get('pnl_percentage', 0)))
            )
            
            return record
            
        except Exception as e:
            self.logger.error(f"创建盈亏记录失败: {e}")
            raise CalculationException(f"创建盈亏记录失败: {e}")
    
    async def get_performance_summary(
        self,
        account_id: str,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """获取性能汇总"""
        try:
            period_start = datetime.now() - timedelta(hours=period_hours)
            period_end = datetime.now()
            
            # 获取时间段内的盈亏记录
            pnl_summary = await account_manager.get_pnl_summary(
                account_id=account_id,
                period_start=period_start,
                period_end=period_end,
                period_type="custom"
            )
            
            # 获取当前投资组合状态
            portfolio_result = await self.calculate_portfolio_pnl(account_id)
            
            # 合并信息
            performance_summary = {
                'account_id': account_id,
                'period_hours': period_hours,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'total_trades': pnl_summary.total_trades,
                'total_pnl': float(pnl_summary.total_pnl),
                'win_rate': float(pnl_summary.win_rate),
                'profit_factor': float(pnl_summary.profit_factor),
                'total_return_pct': float(pnl_summary.total_return_pct),
                'performance_grade': pnl_summary.get_performance_grade(),
                'current_portfolio': {
                    'total_unrealized_pnl': portfolio_result['total_unrealized_pnl'],
                    'total_position_value': portfolio_result['total_position_value'],
                    'portfolio_roi_pct': portfolio_result['portfolio_roi_pct'],
                    'total_positions': portfolio_result['total_positions']
                },
                'last_updated': datetime.now().isoformat()
            }
            
            return performance_summary
            
        except Exception as e:
            self.logger.error(f"获取性能汇总失败 {account_id}: {e}")
            raise CalculationException(f"获取性能汇总失败: {e}")
    
    async def batch_calculate_pnl(
        self,
        position_ids: List[str],
        current_prices: Optional[Dict[str, Decimal]] = None,
        mode: PnLCalculationMode = PnLCalculationMode.COMPREHENSIVE
    ) -> Dict[str, List[Dict[str, Any]]]:
        """批量计算多个持仓的盈亏"""
        try:
            results = []
            errors = []
            
            # 分批处理
            for i in range(0, len(position_ids), self.config.batch_size):
                batch = position_ids[i:i + self.config.batch_size]
                
                # 并行计算当前批次
                batch_tasks = []
                for position_id in batch:
                    task = self._calculate_single_position_batch(position_id, current_prices, mode)
                    batch_tasks.append(task)
                
                # 等待批次完成
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 处理结果
                for j, result in enumerate(batch_results):
                    position_id = batch[j]
                    if isinstance(result, Exception):
                        errors.append({
                            'position_id': position_id,
                            'error': str(result)
                        })
                    else:
                        results.append(result)
                
                # 批次间暂停，避免过载
                if i + self.config.batch_size < len(position_ids):
                    await asyncio.sleep(0.1)
            
            return {
                'results': results,
                'errors': errors,
                'total_processed': len(position_ids),
                'successful': len(results),
                'failed': len(errors),
                'processing_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"批量计算盈亏失败: {e}")
            raise CalculationException(f"批量计算盈亏失败: {e}")
    
    async def _calculate_single_position_batch(
        self,
        position_id: str,
        current_prices: Optional[Dict[str, Decimal]],
        mode: PnLCalculationMode
    ) -> Dict[str, Any]:
        """批量计算单个持仓（内部方法）"""
        # 获取持仓
        position = account_manager.positions.get(position_id)
        if not position:
            raise ValidationException(f"持仓不存在: {position_id}")
        
        # 获取价格
        current_price = None
        if current_prices:
            current_price = current_prices.get(position.symbol)
        
        # 计算盈亏
        return await self.calculate_position_pnl(position, current_price, mode)


# 全局PnL计算器实例
pnl_calculator = RealTimePnLCalculator()