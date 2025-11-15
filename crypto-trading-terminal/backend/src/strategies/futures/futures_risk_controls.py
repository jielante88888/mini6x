"""
合约杠杆交易风险控制系统
提供专门针对合约交易的风险控制、保证金监控和强平保护功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Callable

from .base_futures_strategy import (
    FuturesMarketData, FuturesPosition, FuturesRiskLevel,
    ValidationException, RiskManagementException
)
from .leverage_manager import PositionMetrics


class LiquidationProtection:
    """强平保护机制"""
    
    def __init__(self):
        self.protection_levels = {
            'buffer_ratio': Decimal('0.05'),  # 5%缓冲
            'early_warning_ratio': Decimal('0.1'),  # 10%预警
            'emergency_ratio': Decimal('0.15'),  # 15%紧急
        }
        
        self.actions = {
            'early_warning': 'reduce_position',
            'emergency': 'close_position',
            'critical': 'emergency_close'
        }
    
    def calculate_protection_thresholds(
        self,
        liquidation_price: Decimal,
        current_price: Decimal,
        position_direction: str,  # 'long' or 'short'
    ) -> Dict[str, Decimal]:
        """计算保护阈值"""
        try:
            if liquidation_price == 0 or current_price == 0:
                return {
                    'early_warning': Decimal('0'),
                    'emergency': Decimal('0'),
                    'buffer_zone': Decimal('0')
                }
            
            if position_direction == 'long':
                # 多头：保护阈值在强平价上方
                early_warning = liquidation_price * (1 + self.protection_levels['early_warning_ratio'])
                emergency = liquidation_price * (1 + self.protection_levels['emergency_ratio'])
                buffer_zone = liquidation_price * (1 + self.protection_levels['buffer_ratio'])
            else:
                # 空头：保护阈值在强平价下方
                early_warning = liquidation_price * (1 - self.protection_levels['early_warning_ratio'])
                emergency = liquidation_price * (1 - self.protection_levels['emergency_ratio'])
                buffer_zone = liquidation_price * (1 - self.protection_levels['buffer_ratio'])
            
            return {
                'early_warning': early_warning,
                'emergency': emergency,
                'buffer_zone': buffer_zone,
                'liquidation_price': liquidation_price,
                'current_price': current_price
            }
            
        except Exception as e:
            logging.error(f"计算保护阈值失败: {e}")
            return {
                'early_warning': Decimal('0'),
                'emergency': Decimal('0'),
                'buffer_zone': Decimal('0')
            }
    
    def get_protection_action(
        self,
        current_price: Decimal,
        thresholds: Dict[str, Decimal],
        position_direction: str,
    ) -> Tuple[str, str, Decimal]:
        """获取保护行动"""
        try:
            early_warning = thresholds['early_warning']
            emergency = thresholds['emergency']
            
            if position_direction == 'long':
                # 多头：价格越低风险越大
                if current_price <= thresholds['emergency']:
                    return 'critical', 'emergency_close', self.protection_levels['emergency_ratio']
                elif current_price <= thresholds['early_warning']:
                    return 'high', 'reduce_position', self.protection_levels['early_warning_ratio']
                else:
                    return 'normal', 'monitor', Decimal('0')
            else:
                # 空头：价格越高风险越大
                if current_price >= thresholds['emergency']:
                    return 'critical', 'emergency_close', self.protection_levels['emergency_ratio']
                elif current_price >= thresholds['early_warning']:
                    return 'high', 'reduce_position', self.protection_levels['early_warning_ratio']
                else:
                    return 'normal', 'monitor', Decimal('0')
                    
        except Exception as e:
            logging.error(f"获取保护行动失败: {e}")
            return 'unknown', 'monitor', Decimal('0')


class MarginManager:
    """保证金管理器"""
    
    def __init__(self):
        self.margin_thresholds = {
            'maintenance_margin': Decimal('0.005'),  # 0.5%维持保证金
            'initial_margin': Decimal('0.01'),       # 1%初始保证金
            'warning_margin': Decimal('1.2'),        # 120%保证金比例预警
            'danger_margin': Decimal('1.1'),         # 110%保证金比例危险
            'critical_margin': Decimal('1.05'),      # 105%保证金比例临界
        }
    
    def calculate_margin_requirements(
        self,
        position_value: Decimal,
        leverage: Decimal,
        contract_type: str = 'perpetual'
    ) -> Dict[str, Decimal]:
        """计算保证金要求"""
        try:
            # 计算保证金比例
            initial_margin_ratio = self.margin_thresholds['initial_margin']
            maintenance_margin_ratio = self.margin_thresholds['maintenance_margin']
            
            # 永续合约和交割合约的保证金计算略有不同
            if contract_type.lower() == 'perpetual':
                initial_margin = position_value / leverage
                maintenance_margin = position_value / leverage * maintenance_margin_ratio
            else:
                # 交割合约
                initial_margin = position_value * initial_margin_ratio
                maintenance_margin = position_value * maintenance_margin_ratio
            
            return {
                'initial_margin': initial_margin,
                'maintenance_margin': maintenance_margin,
                'initial_margin_ratio': initial_margin_ratio,
                'maintenance_margin_ratio': maintenance_margin_ratio,
                'effective_leverage': position_value / initial_margin if initial_margin > 0 else Decimal('0')
            }
            
        except Exception as e:
            logging.error(f"计算保证金要求失败: {e}")
            return {
                'initial_margin': Decimal('0'),
                'maintenance_margin': Decimal('0'),
                'initial_margin_ratio': Decimal('0'),
                'maintenance_margin_ratio': Decimal('0'),
                'effective_leverage': Decimal('0')
            }
    
    def assess_margin_risk(
        self,
        margin_level: Decimal,
        unrealized_pnl: Decimal,
        wallet_balance: Decimal
    ) -> Dict[str, Any]:
        """评估保证金风险"""
        try:
            risk_level = 'LOW'
            action = 'hold'
            warning_message = ""
            
            if margin_level < self.margin_thresholds['critical_margin']:
                risk_level = 'CRITICAL'
                action = 'emergency_close'
                warning_message = f"保证金比例过低: {margin_level:.3f} (低于 {self.margin_thresholds['critical_margin']:.1%})"
            
            elif margin_level < self.margin_thresholds['danger_margin']:
                risk_level = 'HIGH'
                action = 'close_position'
                warning_message = f"保证金比例危险: {margin_level:.3f} (低于 {self.margin_thresholds['danger_margin']:.1%})"
            
            elif margin_level < self.margin_thresholds['warning_margin']:
                risk_level = 'MEDIUM'
                action = 'reduce_position'
                warning_message = f"保证金比例偏低: {margin_level:.3f} (低于 {self.margin_thresholds['warning_margin']:.1%})"
            
            # 额外的风险评估
            if unrealized_pnl < -wallet_balance * Decimal('0.2'):  # 亏损超过钱包余额20%
                if risk_level not in ['CRITICAL', 'HIGH']:
                    risk_level = 'HIGH'
                    action = 'reduce_position'
                warning_message += " 亏损过大，建议减仓"
            
            return {
                'risk_level': risk_level,
                'action': action,
                'margin_level': margin_level,
                'warning_message': warning_message,
                'margin_thresholds': self.margin_thresholds
            }
            
        except Exception as e:
            logging.error(f"评估保证金风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'action': 'hold',
                'margin_level': Decimal('0'),
                'warning_message': f"风险评估失败: {e}"
            }
    
    def calculate_safe_position_size(
        self,
        wallet_balance: Decimal,
        current_price: Decimal,
        leverage: Decimal,
        risk_tolerance: Decimal = Decimal('0.02'),  # 2%最大风险
        margin_buffer: Decimal = Decimal('0.1')     # 10%保证金缓冲
    ) -> Decimal:
        """计算安全仓位大小"""
        try:
            # 计算最大允许的保证金使用量
            max_margin_usage = wallet_balance * (1 - margin_buffer) * risk_tolerance
            
            # 计算最大仓位价值
            max_position_value = max_margin_usage * leverage
            
            # 计算最大合约数量
            max_quantity = max_position_value / current_price
            
            logging.debug(
                f"安全仓位计算: 钱包={wallet_balance}, "
                f"价格={current_price}, 杠杆={leverage}, "
                f"最大数量={max_quantity}"
            )
            
            return max_quantity
            
        except Exception as e:
            logging.error(f"计算安全仓位大小失败: {e}")
            return Decimal('0')


class FuturesRiskController:
    """合约风险控制器"""
    
    def __init__(
        self,
        symbol: str,
        user_id: int,
        account_id: int,
        config: Dict[str, Any] = None
    ):
        self.symbol = symbol
        self.user_id = user_id
        self.account_id = account_id
        self.config = config or {}
        
        # 初始化风险组件
        self.liquidation_protection = LiquidationProtection()
        self.margin_manager = MarginManager()
        
        # 风险状态
        self.risk_state = {
            'last_check': None,
            'current_risk_level': FuturesRiskLevel.LOW,
            'warning_count': 0,
            'critical_events': [],
            'margin_calls': [],
        }
        
        # 回调函数
        self.risk_alert_callback: Optional[Callable] = None
        self.auto_close_callback: Optional[Callable] = None
        
        self.logger = logging.getLogger(f"futures_risk_controller.{symbol}")
    
    async def assess_position_risk(
        self,
        position: FuturesPosition,
        market_data: FuturesMarketData,
        wallet_balance: Decimal,
        available_balance: Decimal,
    ) -> Dict[str, Any]:
        """评估仓位风险"""
        try:
            # 创建仓位指标
            position_metrics = PositionMetrics(
                symbol=self.symbol,
                position=position,
                wallet_balance=wallet_balance,
                total_balance=wallet_balance + position.unrealized_pnl,
                available_balance=available_balance
            )
            
            # 强平风险评估
            liquidation_assessment = self._assess_liquidation_risk(
                position, market_data, position_metrics
            )
            
            # 保证金风险评估
            margin_assessment = self.margin_manager.assess_margin_risk(
                position_metrics.margin_ratio,
                position.unrealized_pnl,
                wallet_balance
            )
            
            # 杠杆风险评估
            leverage_assessment = self._assess_leverage_risk(position, position_metrics)
            
            # 波动性风险评估
            volatility_assessment = self._assess_volatility_risk(market_data)
            
            # 资金费率风险评估
            funding_rate_assessment = self._assess_funding_rate_risk(market_data)
            
            # 综合风险评估
            comprehensive_risk = self._calculate_comprehensive_risk(
                liquidation_assessment,
                margin_assessment,
                leverage_assessment,
                volatility_assessment,
                funding_rate_assessment
            )
            
            # 更新风险状态
            self._update_risk_state(comprehensive_risk)
            
            return {
                'symbol': self.symbol,
                'timestamp': datetime.now(),
                'risk_level': comprehensive_risk['risk_level'],
                'overall_score': comprehensive_risk['score'],
                'recommendations': comprehensive_risk['recommendations'],
                'detailed_assessments': {
                    'liquidation': liquidation_assessment,
                    'margin': margin_assessment,
                    'leverage': leverage_assessment,
                    'volatility': volatility_assessment,
                    'funding_rate': funding_rate_assessment,
                },
                'position_metrics': {
                    'margin_ratio': float(position_metrics.margin_ratio),
                    'effective_leverage': float(position_metrics.leverage_effective),
                    'liquidation_distance': float(position_metrics.liquidation_distance),
                    'unrealized_pnl_pct': float(position_metrics.unrealized_pnl_pct),
                },
                'market_conditions': {
                    'funding_rate': float(market_data.funding_rate),
                    'volatility': float(market_data.implied_volatility or Decimal('0')),
                    'price_change_24h': float(market_data.price_change_24h),
                }
            }
            
        except Exception as e:
            self.logger.error(f"评估仓位风险失败: {e}")
            return {
                'symbol': self.symbol,
                'timestamp': datetime.now(),
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }
    
    async def execute_risk_controls(
        self,
        risk_assessment: Dict[str, Any],
        current_positions: List[FuturesPosition],
        market_data: FuturesMarketData,
    ) -> List[Dict[str, Any]]:
        """执行风险控制措施"""
        try:
            executed_actions = []
            risk_level = risk_assessment['risk_level']
            
            # 根据风险等级执行相应措施
            if risk_level == 'CRITICAL':
                # 紧急情况：立即平仓
                actions = await self._execute_emergency_close(
                    current_positions, market_data, risk_assessment
                )
                executed_actions.extend(actions)
                
            elif risk_level == 'HIGH':
                # 高风险：减仓或平仓
                actions = await self._execute_high_risk_actions(
                    current_positions, market_data, risk_assessment
                )
                executed_actions.extend(actions)
                
            elif risk_level == 'MEDIUM':
                # 中风险：警告和监控
                actions = await self._execute_medium_risk_actions(
                    current_positions, market_data, risk_assessment
                )
                executed_actions.extend(actions)
            
            # 发送风险警告
            if risk_level in ['HIGH', 'CRITICAL'] and self.risk_alert_callback:
                await self._safe_callback(
                    self.risk_alert_callback,
                    risk_assessment,
                    executed_actions
                )
            
            return executed_actions
            
        except Exception as e:
            self.logger.error(f"执行风险控制失败: {e}")
            return []
    
    async def check_margin_call_conditions(
        self,
        position_metrics: PositionMetrics,
        market_data: FuturesMarketData,
    ) -> Optional[Dict[str, Any]]:
        """检查追加保证金条件"""
        try:
            margin_ratio = position_metrics.margin_ratio
            
            # 追加保证金阈值
            margin_call_threshold = Decimal('1.1')  # 110%
            
            if margin_ratio < margin_call_threshold:
                # 计算需要的追加保证金
                required_margin = position_metrics.margin_used
                current_margin = position_metrics.total_balance
                additional_margin_needed = required_margin - current_margin
                
                if additional_margin_needed > 0:
                    margin_call = {
                        'symbol': self.symbol,
                        'type': 'margin_call',
                        'severity': 'critical' if margin_ratio < Decimal('1.05') else 'high',
                        'margin_ratio': float(margin_ratio),
                        'additional_margin_required': float(additional_margin_needed),
                        'timestamp': datetime.now(),
                        'liquidation_price': float(position_metrics.position.liquidation_price or 0),
                        'current_price': float(market_data.current_price),
                    }
                    
                    # 记录保证金调用
                    self.risk_state['margin_calls'].append(margin_call)
                    
                    # 保持记录在合理范围内
                    if len(self.risk_state['margin_calls']) > 50:
                        self.risk_state['margin_calls'] = self.risk_state['margin_calls'][-25:]
                    
                    return margin_call
            
            return None
            
        except Exception as e:
            self.logger.error(f"检查追加保证金条件失败: {e}")
            return None
    
    async def calculate_risk_limits(
        self,
        wallet_balance: Decimal,
        leverage: Decimal,
        risk_tolerance: Decimal,
        market_conditions: Dict[str, Any] = None,
    ) -> Dict[str, Decimal]:
        """计算风险限制"""
        try:
            base_max_position = self.margin_manager.calculate_safe_position_size(
                wallet_balance, 
                Decimal('1'),  # 标准化计算
                leverage,
                risk_tolerance
            )
            
            # 根据市场条件调整
            if market_conditions:
                volatility = market_conditions.get('volatility', Decimal('0'))
                funding_rate = abs(market_conditions.get('funding_rate', Decimal('0')))
                
                # 波动性调整
                volatility_adjustment = max(Decimal('0.5'), Decimal('1') - volatility * 10)
                
                # 资金费率调整
                funding_adjustment = max(Decimal('0.7'), Decimal('1') - funding_rate * 100)
                
                # 综合调整
                final_adjustment = volatility_adjustment * funding_adjustment
                base_max_position *= final_adjustment
            
            return {
                'max_position_size': base_max_position,
                'max_order_size': base_max_position * Decimal('0.1'),  # 单笔订单不超过仓位的10%
                'max_daily_loss': wallet_balance * risk_tolerance,
                'max_leverage': min(leverage, Decimal('20')),  # 最大20倍杠杆
                'margin_requirement': wallet_balance * Decimal('0.1'),  # 10%保证金预留
            }
            
        except Exception as e:
            self.logger.error(f"计算风险限制失败: {e}")
            return {
                'max_position_size': Decimal('0'),
                'max_order_size': Decimal('0'),
                'max_daily_loss': Decimal('0'),
                'max_leverage': Decimal('1'),
                'margin_requirement': Decimal('0'),
            }
    
    def _assess_liquidation_risk(
        self,
        position: FuturesPosition,
        market_data: FuturesMarketData,
        position_metrics: PositionMetrics,
    ) -> Dict[str, Any]:
        """评估强平风险"""
        try:
            if not position.liquidation_price or position.quantity == 0:
                return {
                    'risk_level': 'LOW',
                    'liquidation_distance': Decimal('100'),
                    'protection_thresholds': {},
                    'action': 'monitor'
                }
            
            position_direction = 'long' if position.quantity > 0 else 'short'
            
            # 计算保护阈值
            thresholds = self.liquidation_protection.calculate_protection_thresholds(
                position.liquidation_price,
                market_data.current_price,
                position_direction
            )
            
            # 获取保护行动
            protection_action, action_type, buffer_ratio = self.liquidation_protection.get_protection_action(
                market_data.current_price,
                thresholds,
                position_direction
            )
            
            return {
                'risk_level': protection_action,
                'liquidation_distance': position_metrics.liquidation_distance,
                'liquidation_price': position.liquidation_price,
                'protection_thresholds': thresholds,
                'suggested_action': action_type,
                'buffer_ratio': buffer_ratio,
                'position_direction': position_direction
            }
            
        except Exception as e:
            self.logger.error(f"评估强平风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'liquidation_distance': Decimal('0'),
                'error': str(e)
            }
    
    def _assess_leverage_risk(
        self,
        position: FuturesPosition,
        position_metrics: PositionMetrics,
    ) -> Dict[str, Any]:
        """评估杠杆风险"""
        try:
            effective_leverage = position_metrics.leverage_effective
            leverage_ratio = effective_leverage / position.leverage if position.leverage > 0 else Decimal('0')
            
            risk_level = 'LOW'
            action = 'hold'
            
            if leverage_ratio > Decimal('1.5'):
                risk_level = 'CRITICAL'
                action = 'reduce_leverage'
            elif leverage_ratio > Decimal('1.2'):
                risk_level = 'HIGH'
                action = 'monitor_leverage'
            elif leverage_ratio > Decimal('1.1'):
                risk_level = 'MEDIUM'
                action = 'review_position'
            
            return {
                'risk_level': risk_level,
                'effective_leverage': effective_leverage,
                'leverage_ratio': leverage_ratio,
                'suggested_action': action,
                'target_leverage_reduction': max(Decimal('1'), effective_leverage * Decimal('0.8'))
            }
            
        except Exception as e:
            self.logger.error(f"评估杠杆风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }
    
    def _assess_volatility_risk(
        self,
        market_data: FuturesMarketData,
    ) -> Dict[str, Any]:
        """评估波动性风险"""
        try:
            volatility = market_data.implied_volatility or Decimal('0')
            price_change_24h = abs(market_data.price_change_24h)
            
            risk_level = 'LOW'
            action = 'hold'
            
            # 基于隐含波动率评估
            if volatility > Decimal('0.1'):  # 10%
                risk_level = 'HIGH'
                action = 'reduce_position_size'
            elif volatility > Decimal('0.05'):  # 5%
                risk_level = 'MEDIUM'
                action = 'monitor_volatility'
            
            # 基于价格变化评估
            if price_change_24h > Decimal('0.2'):  # 20%
                if risk_level == 'LOW':
                    risk_level = 'MEDIUM'
                    action = 'monitor_price_movement'
            
            return {
                'risk_level': risk_level,
                'implied_volatility': volatility,
                'price_change_24h': price_change_24h,
                'suggested_action': action,
                'volatility_threshold': Decimal('0.05')
            }
            
        except Exception as e:
            self.logger.error(f"评估波动性风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }
    
    def _assess_funding_rate_risk(
        self,
        market_data: FuturesMarketData,
    ) -> Dict[str, Any]:
        """评估资金费率风险"""
        try:
            funding_rate = market_data.funding_rate
            funding_rate_abs = abs(funding_rate)
            
            risk_level = 'LOW'
            action = 'hold'
            
            if funding_rate_abs > Decimal('0.001'):  # 0.1%
                risk_level = 'MEDIUM'
                action = 'monitor_funding_rate'
            elif funding_rate_abs > Decimal('0.002'):  # 0.2%
                risk_level = 'HIGH'
                action = 'consider_position_adjustment'
            
            return {
                'risk_level': risk_level,
                'funding_rate': funding_rate,
                'funding_rate_abs': funding_rate_abs,
                'suggested_action': action,
                'next_settlement_time': market_data.next_funding_time,
                'funding_rate_threshold': Decimal('0.001')
            }
            
        except Exception as e:
            self.logger.error(f"评估资金费率风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }
    
    def _calculate_comprehensive_risk(
        self,
        liquidation_assessment: Dict[str, Any],
        margin_assessment: Dict[str, Any],
        leverage_assessment: Dict[str, Any],
        volatility_assessment: Dict[str, Any],
        funding_rate_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算综合风险"""
        try:
            # 风险等级权重
            risk_weights = {
                'CRITICAL': 10,
                'HIGH': 7,
                'MEDIUM': 4,
                'LOW': 1,
                'UNKNOWN': 0
            }
            
            # 计算加权风险分数
            total_weight = 0
            risk_score = 0
            
            assessments = [
                liquidation_assessment,
                margin_assessment,
                leverage_assessment,
                volatility_assessment,
                funding_rate_assessment
            ]
            
            for assessment in assessments:
                risk_level = assessment.get('risk_level', 'LOW')
                weight = risk_weights.get(risk_level, 0)
                risk_score += weight
                total_weight += 1
            
            # 归一化风险分数
            normalized_score = risk_score / total_weight if total_weight > 0 else 0
            
            # 确定综合风险等级
            if normalized_score >= 8:
                comprehensive_risk_level = 'CRITICAL'
                recommendations = ['立即平仓', '降低杠杆', '增加保证金']
            elif normalized_score >= 5:
                comprehensive_risk_level = 'HIGH'
                recommendations = ['减仓', '监控风险', '准备资金']
            elif normalized_score >= 3:
                comprehensive_risk_level = 'MEDIUM'
                recommendations = ['密切监控', '考虑调整', '保持警惕']
            else:
                comprehensive_risk_level = 'LOW'
                recommendations = ['继续监控', '保持当前策略']
            
            return {
                'risk_level': comprehensive_risk_level,
                'score': normalized_score,
                'recommendations': recommendations,
                'component_scores': {
                    'liquidation': risk_weights.get(liquidation_assessment.get('risk_level', 'LOW'), 0),
                    'margin': risk_weights.get(margin_assessment.get('risk_level', 'LOW'), 0),
                    'leverage': risk_weights.get(leverage_assessment.get('risk_level', 'LOW'), 0),
                    'volatility': risk_weights.get(volatility_assessment.get('risk_level', 'LOW'), 0),
                    'funding_rate': risk_weights.get(funding_rate_assessment.get('risk_level', 'LOW'), 0),
                }
            }
            
        except Exception as e:
            self.logger.error(f"计算综合风险失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'score': 0,
                'recommendations': ['风险评估失败'],
                'error': str(e)
            }
    
    def _update_risk_state(self, comprehensive_risk: Dict[str, Any]):
        """更新风险状态"""
        self.risk_state['last_check'] = datetime.now()
        self.risk_state['current_risk_level'] = FuturesRiskLevel(comprehensive_risk['risk_level'].lower())
        
        risk_level = comprehensive_risk['risk_level']
        if risk_level in ['HIGH', 'CRITICAL']:
            self.risk_state['warning_count'] += 1
            
            # 记录严重事件
            if risk_level == 'CRITICAL':
                self.risk_state['critical_events'].append({
                    'timestamp': datetime.now(),
                    'risk_level': risk_level,
                    'score': comprehensive_risk['score']
                })
                
                # 保持事件记录在合理范围内
                if len(self.risk_state['critical_events']) > 20:
                    self.risk_state['critical_events'] = self.risk_state['critical_events'][-10:]
    
    async def _execute_emergency_close(
        self,
        positions: List[FuturesPosition],
        market_data: FuturesMarketData,
        risk_assessment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """执行紧急平仓"""
        actions = []
        
        for position in positions:
            if position.quantity != 0:
                action = {
                    'type': 'emergency_close',
                    'symbol': position.symbol,
                    'position_quantity': float(position.quantity),
                    'action_side': 'SELL' if position.quantity > 0 else 'BUY',
                    'reason': risk_assessment['risk_level'],
                    'timestamp': datetime.now()
                }
                actions.append(action)
        
        self.logger.warning(f"执行紧急平仓: {len(actions)} 个仓位")
        return actions
    
    async def _execute_high_risk_actions(
        self,
        positions: List[FuturesPosition],
        market_data: FuturesMarketData,
        risk_assessment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """执行高风险操作"""
        actions = []
        
        # 建议减仓50%
        for position in positions:
            if position.quantity != 0:
                reduce_quantity = abs(position.quantity) * Decimal('0.5')
                
                action = {
                    'type': 'reduce_position',
                    'symbol': position.symbol,
                    'original_quantity': float(position.quantity),
                    'reduce_quantity': float(reduce_quantity),
                    'action_side': 'SELL' if position.quantity > 0 else 'BUY',
                    'reason': 'high_risk_reduction',
                    'timestamp': datetime.now()
                }
                actions.append(action)
        
        self.logger.info(f"执行高风险操作: 减仓 {len(actions)} 个仓位")
        return actions
    
    async def _execute_medium_risk_actions(
        self,
        positions: List[FuturesPosition],
        market_data: FuturesMarketData,
        risk_assessment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """执行中等风险操作"""
        actions = []
        
        # 添加监控和警告
        for position in positions:
            action = {
                'type': 'risk_warning',
                'symbol': position.symbol,
                'position_quantity': float(position.quantity),
                'warning_message': '中等风险：建议密切监控',
                'timestamp': datetime.now()
            }
            actions.append(action)
        
        return actions
    
    async def _safe_callback(self, callback: Callable, *args):
        """安全执行回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.logger.error(f"回调函数执行失败: {e}")
    
    def set_risk_alert_callback(self, callback: Callable):
        """设置风险警告回调"""
        self.risk_alert_callback = callback
    
    def set_auto_close_callback(self, callback: Callable):
        """设置自动平仓回调"""
        self.auto_close_callback = callback
    
    def get_risk_state(self) -> Dict[str, Any]:
        """获取风险状态"""
        return self.risk_state.copy()
    
    def reset_risk_state(self):
        """重置风险状态"""
        self.risk_state = {
            'last_check': None,
            'current_risk_level': FuturesRiskLevel.LOW,
            'warning_count': 0,
            'critical_events': [],
            'margin_calls': [],
        }
        self.logger.info("风险状态已重置")


class RiskMonitoringService:
    """风险监控服务"""
    
    def __init__(self):
        self.controllers: Dict[str, FuturesRiskController] = {}
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitoring_interval = 30  # 秒
        
        self.logger = logging.getLogger("risk_monitoring_service")
    
    def register_controller(self, controller: FuturesRiskController):
        """注册风险控制器"""
        key = f"{controller.user_id}_{controller.account_id}_{controller.symbol}"
        self.controllers[key] = controller
        self.logger.info(f"注册风险控制器: {key}")
    
    def unregister_controller(self, user_id: int, account_id: int, symbol: str):
        """注销风险控制器"""
        key = f"{user_id}_{account_id}_{symbol}"
        if key in self.controllers:
            del self.controllers[key]
            self.logger.info(f"注销风险控制器: {key}")
    
    async def start_monitoring(self):
        """启动风险监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("启动风险监控服务")
    
    async def stop_monitoring(self):
        """停止风险监控"""
        self.monitoring_active = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("停止风险监控服务")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # 这里可以添加自动风险检查逻辑
                # 例如：定期检查所有注册的控制器
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"风险监控循环错误: {e}")
    
    async def execute_global_risk_check(
        self,
        user_positions: Dict[str, List[FuturesPosition]],
        market_data: Dict[str, FuturesMarketData],
        user_balances: Dict[str, Dict[str, Decimal]],
    ) -> Dict[str, Any]:
        """执行全局风险检查"""
        try:
            total_risk_assessment = {
                'timestamp': datetime.now(),
                'total_users': len(user_positions),
                'total_positions': 0,
                'high_risk_positions': 0,
                'critical_risk_positions': 0,
                'margin_calls': 0,
                'overall_risk_score': Decimal('0'),
                'recommendations': []
            }
            
            for user_id_str, positions in user_positions.items():
                user_id = int(user_id_str.split('_')[0])
                
                for position in positions:
                    symbol = position.symbol
                    account_id = 1  # 简化处理
                    
                    # 获取市场数据和余额
                    market_info = market_data.get(symbol)
                    balance_info = user_balances.get(user_id_str, {})
                    
                    if market_info and balance_info:
                        # 创建风险控制器（如果不存在）
                        controller_key = f"{user_id}_{account_id}_{symbol}"
                        if controller_key not in self.controllers:
                            controller = FuturesRiskController(
                                symbol=symbol,
                                user_id=user_id,
                                account_id=account_id
                            )
                            self.register_controller(controller)
                        
                        # 执行风险评估
                        controller = self.controllers[controller_key]
                        risk_assessment = await controller.assess_position_risk(
                            position,
                            market_info,
                            balance_info.get('wallet_balance', Decimal('0')),
                            balance_info.get('available_balance', Decimal('0'))
                        )
                        
                        # 更新统计
                        total_risk_assessment['total_positions'] += 1
                        
                        risk_level = risk_assessment['risk_level']
                        if risk_level == 'HIGH':
                            total_risk_assessment['high_risk_positions'] += 1
                        elif risk_level == 'CRITICAL':
                            total_risk_assessment['critical_risk_positions'] += 1
                        
                        # 检查保证金调用
                        position_metrics = type('obj', (object,), {
                            'margin_ratio': Decimal(str(risk_assessment['position_metrics']['margin_ratio'])),
                            'total_balance': balance_info.get('wallet_balance', Decimal('0')),
                            'margin_used': Decimal('0')  # 简化处理
                        })()
                        
                        margin_call = await controller.check_margin_call_conditions(
                            position_metrics, market_info
                        )
                        
                        if margin_call:
                            total_risk_assessment['margin_calls'] += 1
            
            # 计算整体风险评分
            if total_risk_assessment['total_positions'] > 0:
                risk_score = (
                    total_risk_assessment['high_risk_positions'] * 5 +
                    total_risk_assessment['critical_risk_positions'] * 10 +
                    total_risk_assessment['margin_calls'] * 8
                ) / total_risk_assessment['total_positions']
                
                total_risk_assessment['overall_risk_score'] = Decimal(str(risk_score))
                
                # 生成建议
                if risk_score > 7:
                    total_risk_assessment['recommendations'].append('全局风险过高，建议暂停新交易')
                elif risk_score > 4:
                    total_risk_assessment['recommendations'].append('风险较高，建议加强监控')
                
                total_risk_assessment['recommendations'].append(f'当前监控 {total_risk_assessment["total_positions"]} 个仓位')
            
            return total_risk_assessment
            
        except Exception as e:
            self.logger.error(f"执行全局风险检查失败: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'total_positions': 0,
                'overall_risk_score': Decimal('0')
            }
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """获取监控统计"""
        return {
            'active_controllers': len(self.controllers),
            'monitoring_active': self.monitoring_active,
            'controllers': list(self.controllers.keys())
        }