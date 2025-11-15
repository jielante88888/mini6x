"""
合约杠杆管理器
提供动态杠杆管理、风险控制和保证金监控功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from .base_futures_strategy import (
    FuturesMarketData, FuturesPosition, OrderSide, OrderType,
    PositionSide, ValidationException, FuturesRiskLevel, LeverageMode
)


class LeverageConfig:
    """杠杆配置"""
    def __init__(
        self,
        symbol: str,
        max_leverage: Decimal,
        min_leverage: Decimal = Decimal('1'),
        leverage_step: Decimal = Decimal('1'),
        auto_leverage_enabled: bool = True,
        risk_based_adjustment: bool = True,
        volatility_threshold: Decimal = Decimal('0.05'),
        margin_ratio_threshold: Decimal = Decimal('1.2'),
        max_position_leverage: Decimal = Decimal('10'),
    ):
        self.symbol = symbol
        self.max_leverage = max_leverage
        self.min_leverage = min_leverage
        self.leverage_step = leverage_step
        self.auto_leverage_enabled = auto_leverage_enabled
        self.risk_based_adjustment = risk_based_adjustment
        self.volatility_threshold = volatility_threshold
        self.margin_ratio_threshold = margin_ratio_threshold
        self.max_position_leverage = max_position_leverage
        
        # 验证配置
        if min_leverage > max_leverage:
            raise ValidationException("最小杠杆不能大于最大杠杆")
        
        if leverage_step <= 0:
            raise ValidationException("杠杆调整步长必须大于0")


class PositionMetrics:
    """仓位指标"""
    def __init__(
        self,
        symbol: str,
        position: FuturesPosition,
        wallet_balance: Decimal,
        total_balance: Decimal,
        available_balance: Decimal,
    ):
        self.symbol = symbol
        self.position = position
        self.wallet_balance = wallet_balance
        self.total_balance = total_balance
        self.available_balance = available_balance
        
        # 计算各项指标
        self.position_value = abs(position.quantity) * position.average_price
        self.unrealized_pnl_pct = self._calculate_unrealized_pnl_percentage()
        self.margin_used = position.margin_used or Decimal('0')
        self.margin_ratio = self._calculate_margin_ratio()
        self.leverage_effective = self._calculate_effective_leverage()
        self.liquidation_distance = self._calculate_liquidation_distance()
        
    def _calculate_unrealized_pnl_percentage(self) -> Decimal:
        """计算未实现盈亏百分比"""
        if self.position_value == 0:
            return Decimal('0')
        
        return self.position.unrealized_pnl / self.position_value
    
    def _calculate_margin_ratio(self) -> Decimal:
        """计算保证金比例（强平保护）"""
        if self.margin_used == 0:
            return Decimal('999')  # 无仓位时设为高值
        
        effective_balance = self.total_balance + self.position.unrealized_pnl
        return effective_balance / self.margin_used
    
    def _calculate_effective_leverage(self) -> Decimal:
        """计算实际杠杆"""
        if self.margin_used == 0:
            return Decimal('0')
        
        return self.position_value / self.margin_used
    
    def _calculate_liquidation_distance(self) -> Decimal:
        """计算到强平价格的距离百分比"""
        if not self.position.liquidation_price or self.position.quantity == 0:
            return Decimal('100')
        
        if self.position.quantity > 0:  # 多头
            distance = (self.position.liquidation_price - self.position.average_price) / self.position.average_price
        else:  # 空头
            distance = (self.position.average_price - self.position.liquidation_price) / self.position.average_price
        
        return abs(distance)
    
    def get_risk_level(self) -> FuturesRiskLevel:
        """获取风险等级"""
        if self.margin_ratio < Decimal('1.05'):  # 105%
            return FuturesRiskLevel.CRITICAL
        elif self.margin_ratio < Decimal('1.1'):  # 110%
            return FuturesRiskLevel.HIGH
        elif self.margin_ratio < Decimal('1.2'):  # 120%
            return FuturesRiskLevel.MEDIUM
        else:
            return FuturesRiskLevel.LOW
    
    def should_reduce_position(self) -> bool:
        """判断是否应该减仓"""
        return (self.margin_ratio < Decimal('1.15') or  # 保证金比例过低
                self.liquidation_distance < Decimal('0.05') or  # 距离强平5%以内
                self.unrealized_pnl_pct < Decimal('-0.1'))  # 亏损超过10%
    
    def should_close_position(self) -> bool:
        """判断是否应该平仓"""
        return (self.margin_ratio < Decimal('1.08') or  # 保证金比例极低
                self.liquidation_distance < Decimal('0.02') or  # 距离强平2%以内
                self.unrealized_pnl_pct < Decimal('-0.2'))  # 亏损超过20%


class LeverageManager:
    """杠杆管理器"""
    
    def __init__(self, config: LeverageConfig):
        self.config = config
        self.logger = logging.getLogger(f"leverage_manager.{config.symbol}")
        
        # 杠杆状态追踪
        self.current_leverage = config.min_leverage
        self.leverage_history: List[Dict[str, Any]] = []
        self.risk_events: List[Dict[str, Any]] = []
        
        # 监控参数
        self.check_interval = 30  # 秒
        self.risk_monitor_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        # 回调函数
        self.leverage_change_callback: Optional[callable] = None
        self.risk_alert_callback: Optional[callable] = None
    
    async def start_monitoring(self):
        """启动风险监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.risk_monitor_task = asyncio.create_task(self._risk_monitoring_loop())
        self.logger.info(f"启动杠杆监控: {self.config.symbol}")
    
    async def stop_monitoring(self):
        """停止风险监控"""
        self.is_monitoring = False
        
        if self.risk_monitor_task and not self.risk_monitor_task.done():
            self.risk_monitor_task.cancel()
            try:
                await self.risk_monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"停止杠杆监控: {self.config.symbol}")
    
    async def calculate_optimal_leverage(
        self,
        position_metrics: PositionMetrics,
        market_data: FuturesMarketData,
        volatility: Decimal = None,
    ) -> Decimal:
        """计算最优杠杆"""
        try:
            # 基础杠杆
            base_leverage = self.config.min_leverage
            
            # 根据市场波动性调整
            if volatility:
                volatility_adjustment = self._calculate_volatility_adjustment(volatility)
            else:
                volatility_adjustment = self._estimate_volatility(market_data)
            
            # 根据保证金比例调整
            margin_adjustment = self._calculate_margin_adjustment(position_metrics)
            
            # 根据未实现盈亏调整
            pnl_adjustment = self._calculate_pnl_adjustment(position_metrics)
            
            # 综合调整
            final_leverage = base_leverage * (1 + volatility_adjustment + margin_adjustment + pnl_adjustment)
            
            # 限制在允许范围内
            final_leverage = max(
                self.config.min_leverage,
                min(final_leverage, self.config.max_leverage, self.config.max_position_leverage)
            )
            
            # 按步长调整
            final_leverage = self._round_to_step(final_leverage)
            
            self.logger.debug(
                f"计算最优杠杆: 基础={base_leverage}, "
                f"波动性={volatility_adjustment:.3f}, "
                f"保证金={margin_adjustment:.3f}, "
                f"盈亏={pnl_adjustment:.3f}, "
                f"最终={final_leverage}"
            )
            
            return final_leverage
            
        except Exception as e:
            self.logger.error(f"计算最优杠杆失败: {e}")
            return self.config.min_leverage
    
    async def adjust_leverage(
        self,
        current_leverage: Decimal,
        target_leverage: Decimal,
        position_metrics: PositionMetrics,
        market_data: FuturesMarketData,
    ) -> Dict[str, Any]:
        """调整杠杆"""
        try:
            if abs(target_leverage - current_leverage) < self.config.leverage_step:
                return {
                    'action': 'no_change',
                    'reason': '杠杆变化小于步长',
                    'old_leverage': current_leverage,
                    'new_leverage': current_leverage
                }
            
            # 检查是否允许调整
            adjustment_check = await self._check_leverage_adjustment(position_metrics, target_leverage)
            if not adjustment_check['allowed']:
                return {
                    'action': 'rejected',
                    'reason': adjustment_check['reason'],
                    'old_leverage': current_leverage,
                    'new_leverage': current_leverage
                }
            
            # 记录杠杆变更
            leverage_change = {
                'timestamp': datetime.now(),
                'old_leverage': current_leverage,
                'new_leverage': target_leverage,
                'reason': adjustment_check.get('reason', '优化调整'),
                'position_metrics': {
                    'margin_ratio': float(position_metrics.margin_ratio),
                    'unrealized_pnl_pct': float(position_metrics.unrealized_pnl_pct),
                    'liquidation_distance': float(position_metrics.liquidation_distance),
                    'risk_level': position_metrics.get_risk_level().value
                },
                'market_data': {
                    'price': float(market_data.current_price),
                    'funding_rate': float(market_data.funding_rate),
                    'volatility': float(market_data.implied_volatility or Decimal('0'))
                }
            }
            
            self.leverage_history.append(leverage_change)
            self.current_leverage = target_leverage
            
            # 保持历史记录在合理范围内
            if len(self.leverage_history) > 100:
                self.leverage_history = self.leverage_history[-50:]
            
            # 触发回调
            if self.leverage_change_callback:
                await self._safe_callback(
                    self.leverage_change_callback,
                    leverage_change
                )
            
            self.logger.info(
                f"杠杆调整: {current_leverage} -> {target_leverage}, "
                f"原因: {leverage_change['reason']}"
            )
            
            return {
                'action': 'adjusted',
                'reason': leverage_change['reason'],
                'old_leverage': current_leverage,
                'new_leverage': target_leverage,
                'change_details': leverage_change
            }
            
        except Exception as e:
            self.logger.error(f"调整杠杆失败: {e}")
            return {
                'action': 'error',
                'reason': str(e),
                'old_leverage': current_leverage,
                'new_leverage': current_leverage
            }
    
    async def check_risk_and_recommend_action(
        self,
        position_metrics: PositionMetrics,
        market_data: FuturesMarketData,
    ) -> Dict[str, Any]:
        """检查风险并推荐行动"""
        try:
            risk_level = position_metrics.get_risk_level()
            recommendations = []
            
            # 检查各项风险指标
            if position_metrics.should_close_position():
                recommendations.append({
                    'action': 'close_position',
                    'priority': 'critical',
                    'reason': '仓位风险过高，建议立即平仓',
                    'risk_factors': ['margin_ratio_low', 'liquidation_close', 'large_loss']
                })
            
            elif position_metrics.should_reduce_position():
                recommendations.append({
                    'action': 'reduce_position',
                    'priority': 'high',
                    'reason': '风险偏高，建议减仓',
                    'risk_factors': ['margin_ratio_warning', 'position_size_large']
                })
            
            # 检查杠杆风险
            if position_metrics.leverage_effective > self.config.max_position_leverage:
                recommendations.append({
                    'action': 'reduce_leverage',
                    'priority': 'medium',
                    'reason': '杠杆过高，建议降低杠杆',
                    'risk_factors': ['leverage_too_high']
                })
            
            # 检查资金费率风险
            if abs(market_data.funding_rate) > Decimal('0.001'):  # 0.1%
                recommendations.append({
                    'action': 'monitor_funding_rate',
                    'priority': 'low',
                    'reason': f'资金费率较高: {market_data.funding_rate:.4f}',
                    'risk_factors': ['high_funding_rate']
                })
            
            # 生成综合建议
            if not recommendations:
                action_recommendation = 'hold'
                priority = 'low'
                reason = '风险水平正常，无需特殊操作'
            elif any(r['priority'] == 'critical' for r in recommendations):
                action_recommendation = 'emergency_close'
                priority = 'critical'
                reason = '紧急情况：立即平仓'
            elif any(r['priority'] == 'high' for r in recommendations):
                action_recommendation = 'reduce_exposure'
                priority = 'high'
                reason = '高风险：建议减仓或降低杠杆'
            else:
                action_recommendation = 'monitor'
                priority = 'medium'
                reason = '中等风险：持续监控'
            
            return {
                'risk_level': risk_level.value,
                'action': action_recommendation,
                'priority': priority,
                'reason': reason,
                'detailed_recommendations': recommendations,
                'position_metrics': {
                    'margin_ratio': float(position_metrics.margin_ratio),
                    'leverage_effective': float(position_metrics.leverage_effective),
                    'unrealized_pnl_pct': float(position_metrics.unrealized_pnl_pct),
                    'liquidation_distance': float(position_metrics.liquidation_distance),
                },
                'market_conditions': {
                    'funding_rate': float(market_data.funding_rate),
                    'volatility': float(market_data.implied_volatility or Decimal('0')),
                    'price_change_24h': float(market_data.price_change_24h)
                }
            }
            
        except Exception as e:
            self.logger.error(f"风险检查失败: {e}")
            return {
                'risk_level': 'unknown',
                'action': 'hold',
                'priority': 'low',
                'reason': f'风险检查错误: {e}'
            }
    
    async def calculate_position_size_limit(
        self,
        leverage: Decimal,
        wallet_balance: Decimal,
        market_price: Decimal,
        risk_level: Decimal = Decimal('0.02'),  # 2%最大风险
    ) -> Decimal:
        """计算仓位大小限制"""
        try:
            # 计算最大保证金使用量
            max_margin_usage = wallet_balance * risk_level
            
            # 计算最大仓位价值
            max_position_value = max_margin_usage * leverage
            
            # 计算最大合约数量
            max_quantity = max_position_value / market_price
            
            self.logger.debug(
                f"仓位大小限制: 杠杆={leverage}, "
                f"钱包余额={wallet_balance}, "
                f"价格={market_price}, "
                f"最大数量={max_quantity}"
            )
            
            return max_quantity
            
        except Exception as e:
            self.logger.error(f"计算仓位大小限制失败: {e}")
            return Decimal('0')
    
    def _calculate_volatility_adjustment(self, volatility: Decimal) -> Decimal:
        """计算波动性调整"""
        if volatility > self.config.volatility_threshold:
            # 波动性过高，降低杠杆
            return -min((volatility / self.config.volatility_threshold - 1) * 0.3, 0.5)
        else:
            # 波动性适中，可以适当增加杠杆
            return min((self.config.volatility_threshold - volatility) / self.config.volatility_threshold * 0.2, 0.1)
    
    def _calculate_margin_adjustment(self, position_metrics: PositionMetrics) -> Decimal:
        """计算保证金调整"""
        margin_ratio = position_metrics.margin_ratio
        
        if margin_ratio < Decimal('1.15'):  # 115%
            # 保证金比例很低，大幅降低杠杆
            return -0.4
        elif margin_ratio < Decimal('1.3'):  # 130%
            # 保证金比例偏低，降低杠杆
            return -0.2
        elif margin_ratio > Decimal('2.0'):  # 200%
            # 保证金比例很充足，可以增加杠杆
            return 0.1
        else:
            # 保证金比例正常
            return 0
    
    def _calculate_pnl_adjustment(self, position_metrics: PositionMetrics) -> Decimal:
        """计算盈亏调整"""
        unrealized_pnl_pct = position_metrics.unrealized_pnl_pct
        
        if unrealized_pnl_pct < Decimal('-0.1'):  # 亏损10%
            # 大幅亏损，降低杠杆
            return -0.3
        elif unrealized_pnl_pct < Decimal('-0.05'):  # 亏损5%
            # 小幅亏损，适度降低杠杆
            return -0.1
        elif unrealized_pnl_pct > Decimal('0.1'):  # 盈利10%
            # 大幅盈利，可以适当增加杠杆
            return 0.1
        else:
            # 盈亏正常
            return 0
    
    def _estimate_volatility(self, market_data: FuturesMarketData) -> Decimal:
        """估算波动性"""
        # 简化的波动性估算：基于24小时价格变化
        if market_data.previous_close and market_data.previous_close > 0:
            price_change = abs(market_data.price_change_24h) / market_data.previous_close
            return price_change
        
        # 如果没有历史数据，返回默认值
        return Decimal('0.02')  # 2%
    
    def _round_to_step(self, leverage: Decimal) -> Decimal:
        """按步长调整杠杆"""
        steps = int(leverage / self.config.leverage_step)
        return steps * self.config.leverage_step
    
    async def _check_leverage_adjustment(
        self,
        position_metrics: PositionMetrics,
        target_leverage: Decimal,
    ) -> Dict[str, Any]:
        """检查杠杆调整是否允许"""
        # 检查杠杆范围
        if target_leverage < self.config.min_leverage or target_leverage > self.config.max_leverage:
            return {
                'allowed': False,
                'reason': f'目标杠杆 {target_leverage} 超出允许范围 [{self.config.min_leverage}, {self.config.max_leverage}]'
            }
        
        # 检查强平风险
        if position_metrics.leverage_effective > Decimal('1.5') and target_leverage > position_metrics.leverage_effective:
            return {
                'allowed': False,
                'reason': f'增加杠杆风险过高: 当前有效杠杆 {position_metrics.leverage_effective}'
            }
        
        # 检查保证金比例
        if position_metrics.margin_ratio < Decimal('1.2') and target_leverage > self.current_leverage:
            return {
                'allowed': False,
                'reason': '保证金比例偏低，不允许增加杠杆'
            }
        
        return {'allowed': True, 'reason': '杠杆调整通过检查'}
    
    async def _risk_monitoring_loop(self):
        """风险监控循环"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.check_interval)
                
                # 这里可以添加自动风险检查和杠杆调整逻辑
                # 实际实现中需要获取当前仓位和市场数据
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"风险监控错误: {e}")
    
    async def _safe_callback(self, callback: callable, *args):
        """安全执行回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.logger.error(f"回调函数执行失败: {e}")
    
    def set_leverage_change_callback(self, callback: callable):
        """设置杠杆变更回调"""
        self.leverage_change_callback = callback
    
    def set_risk_alert_callback(self, callback: callable):
        """设置风险警告回调"""
        self.risk_alert_callback = callback
    
    def get_leverage_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取杠杆变更历史"""
        return self.leverage_history[-limit:] if self.leverage_history else []
    
    def get_risk_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取风险事件历史"""
        return self.risk_events[-limit:] if self.risk_events else []


class DynamicLeverageManager:
    """动态杠杆管理器（支持多策略）"""
    
    def __init__(self):
        self.leverage_managers: Dict[str, LeverageManager] = {}
        self.global_settings = {
            'max_total_exposure': Decimal('1.0'),  # 最大总敞口
            'correlation_check': True,  # 相关性检查
            'emergency_stop': False,   # 紧急停止
        }
        self.logger = logging.getLogger("dynamic_leverage_manager")
    
    async def register_strategy(
        self,
        symbol: str,
        strategy_id: str,
        leverage_config: LeverageConfig,
        current_leverage: Decimal = None,
    ) -> bool:
        """注册策略杠杆配置"""
        try:
            if symbol not in self.leverage_managers:
                self.leverage_managers[symbol] = {}
            
            if strategy_id in self.leverage_managers[symbol]:
                self.logger.warning(f"策略 {strategy_id} 已存在，将更新配置")
            
            manager = LeverageManager(leverage_config)
            if current_leverage:
                manager.current_leverage = current_leverage
            
            self.leverage_managers[symbol][strategy_id] = manager
            
            self.logger.info(f"注册策略杠杆管理: {symbol}/{strategy_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册策略失败: {e}")
            return False
    
    async def unregister_strategy(self, symbol: str, strategy_id: str) -> bool:
        """注销策略"""
        try:
            if symbol in self.leverage_managers and strategy_id in self.leverage_managers[symbol]:
                manager = self.leverage_managers[symbol][strategy_id]
                await manager.stop_monitoring()
                del self.leverage_managers[symbol][strategy_id]
                
                if not self.leverage_managers[symbol]:
                    del self.leverage_managers[symbol]
                
                self.logger.info(f"注销策略杠杆管理: {symbol}/{strategy_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"注销策略失败: {e}")
            return False
    
    async def get_global_risk_assessment(self) -> Dict[str, Any]:
        """获取全局风险评估"""
        try:
            total_exposure = Decimal('0')
            total_strategies = 0
            high_risk_strategies = 0
            risk_distributions = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
            
            # 汇总各策略的风险
            for symbol, strategies in self.leverage_managers.items():
                for strategy_id, manager in strategies.items():
                    total_strategies += 1
                    
                    # 简化的风险评估（实际需要具体数据）
                    risk_level = 'LOW'  # 这里应该从实际PositionMetrics获取
                    risk_distributions[risk_level] += 1
                    
                    if risk_level in ['HIGH', 'CRITICAL']:
                        high_risk_strategies += 1
            
            # 计算风险指标
            high_risk_ratio = Decimal(str(high_risk_strategies)) / Decimal(str(total_strategies)) if total_strategies > 0 else Decimal('0')
            
            return {
                'total_strategies': total_strategies,
                'total_exposure': float(total_exposure),
                'high_risk_strategies': high_risk_strategies,
                'high_risk_ratio': float(high_risk_ratio),
                'risk_distribution': risk_distributions,
                'emergency_stop': self.global_settings['emergency_stop'],
                'assessment_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"全局风险评估失败: {e}")
            return {
                'total_strategies': 0,
                'total_exposure': 0,
                'high_risk_strategies': 0,
                'error': str(e)
            }
    
    async def emergency_stop_all(self):
        """紧急停止所有策略"""
        try:
            self.global_settings['emergency_stop'] = True
            
            for symbol, strategies in self.leverage_managers.items():
                for strategy_id, manager in strategies:
                    await manager.stop_monitoring()
            
            self.logger.warning("执行紧急停止：所有策略已停止")
            
        except Exception as e:
            self.logger.error(f"紧急停止失败: {e}")
    
    async def resume_all(self):
        """恢复所有策略"""
        try:
            self.global_settings['emergency_stop'] = False
            
            for symbol, strategies in self.leverage_managers.items():
                for strategy_id, manager in strategies:
                    await manager.start_monitoring()
            
            self.logger.info("恢复所有策略监控")
            
        except Exception as e:
            self.logger.error(f"恢复策略失败: {e}")