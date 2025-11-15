"""
资金费率套利策略
利用永续合约资金费率的周期性结算特性进行套利交易
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from .base_futures_strategy import (
    BaseFuturesStrategy, FuturesMarketData, FuturesOrderRequest, 
    FuturesOrderResult, FuturesPosition, OrderType, OrderSide,
    PositionSide, ValidationException, FuturesStrategyConfig,
    FuturesStrategyType
)


class FundingRateAnalysis:
    """资金费率分析器"""
    
    def __init__(self):
        self.funding_rate_history: List[Dict[str, Any]] = []
        self.predictions: List[Dict[str, Any]] = []
        
    def add_funding_rate_data(
        self,
        symbol: str,
        funding_rate: Decimal,
        predicted_rate: Decimal,
        settlement_time: datetime,
        market_price: Decimal,
        spot_price: Optional[Decimal] = None,
    ):
        """添加资金费率数据"""
        data_point = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'funding_rate': funding_rate,
            'predicted_rate': predicted_rate,
            'settlement_time': settlement_time,
            'market_price': market_price,
            'spot_price': spot_price,
            'is_positive': funding_rate > 0,
            'abs_rate': abs(funding_rate)
        }
        
        self.funding_rate_history.append(data_point)
        
        # 保持历史数据在合理范围内
        if len(self.funding_rate_history) > 200:
            self.funding_rate_history = self.funding_rate_history[-100:]
    
    def analyze_funding_pattern(self, symbol: str, lookback_periods: int = 50) -> Dict[str, Any]:
        """分析资金费率模式"""
        if not self.funding_rate_history:
            return {'pattern': 'no_data', 'prediction': Decimal('0')}
        
        # 获取指定币种的历史数据
        symbol_data = [
            data for data in self.funding_rate_history[-lookback_periods:]
            if data['symbol'] == symbol
        ]
        
        if len(symbol_data) < 10:
            return {'pattern': 'insufficient_data', 'prediction': Decimal('0')}
        
        # 分析费率趋势
        rates = [data['funding_rate'] for data in symbol_data]
        avg_rate = sum(rates) / Decimal(str(len(rates)))
        rate_volatility = self._calculate_volatility(rates)
        
        # 分析极值
        positive_rates = [r for r in rates if r > 0]
        negative_rates = [r for r in rates if r < 0]
        
        avg_positive = sum(positive_rates) / Decimal(str(len(positive_rates))) if positive_rates else Decimal('0')
        avg_negative = sum(negative_rates) / Decimal(str(len(negative_rates))) if negative_rates else Decimal('0')
        
        # 预测下一期费率
        prediction = self._predict_next_rate(rates)
        
        # 判断模式
        pattern = self._classify_funding_pattern(rates, avg_rate, rate_volatility)
        
        return {
            'pattern': pattern,
            'current_avg': avg_rate,
            'volatility': rate_volatility,
            'positive_avg': avg_positive,
            'negative_avg': avg_negative,
            'prediction': prediction,
            'confidence': self._calculate_prediction_confidence(symbol_data),
            'data_points': len(symbol_data)
        }
    
    def calculate_arbitrage_opportunity(
        self,
        symbol: str,
        current_rate: Decimal,
        next_settlement_time: datetime,
        current_price: Decimal,
        spot_price: Optional[Decimal] = None,
        min_profit_threshold: Decimal = Decimal('0.0001'),  # 0.01%
        max_holding_period: int = 24,  # 小时
    ) -> Dict[str, Any]:
        """计算套利机会"""
        try:
            # 获取市场分析
            analysis = self.analyze_funding_pattern(symbol)
            
            if analysis['pattern'] == 'no_data' or analysis['pattern'] == 'insufficient_data':
                return {
                    'opportunity': False,
                    'reason': '数据不足',
                    'potential_profit': Decimal('0'),
                    'risk_level': 'unknown'
                }
            
            # 计算套利机会评分
            opportunity_score = self._calculate_opportunity_score(
                current_rate, analysis['prediction'], analysis['volatility']
            )
            
            # 计算潜在收益
            potential_profit = self._calculate_potential_profit(
                current_rate, current_price, min_profit_threshold
            )
            
            # 计算风险评估
            risk_assessment = self._assess_arbitrage_risk(
                current_rate, analysis['volatility'], analysis['confidence']
            )
            
            # 计算时间敏感性
            time_sensitivity = self._calculate_time_sensitivity(next_settlement_time)
            
            # 综合评估
            if (opportunity_score > 0.7 and 
                potential_profit >= min_profit_threshold and
                risk_assessment['level'] in ['LOW', 'MEDIUM']):
                
                strategy = self._determine_arbitrage_strategy(
                    current_rate, analysis['prediction']
                )
                
                return {
                    'opportunity': True,
                    'strategy': strategy,
                    'potential_profit': potential_profit,
                    'risk_level': risk_assessment['level'],
                    'confidence': analysis['confidence'],
                    'time_sensitivity': time_sensitivity,
                    'suggested_position_size': risk_assessment['suggested_size'],
                    'expected_duration': self._estimate_holding_period(current_rate, analysis['prediction']),
                    'analysis': analysis,
                    'opportunity_score': opportunity_score
                }
            else:
                return {
                    'opportunity': False,
                    'reason': self._determine_no_opportunity_reason(
                        opportunity_score, potential_profit, risk_assessment
                    ),
                    'potential_profit': potential_profit,
                    'risk_level': risk_assessment['level'],
                    'analysis': analysis
                }
                
        except Exception as e:
            return {
                'opportunity': False,
                'reason': f'分析失败: {e}',
                'potential_profit': Decimal('0'),
                'risk_level': 'unknown'
            }
    
    def _calculate_volatility(self, rates: List[Decimal]) -> Decimal:
        """计算费率波动性"""
        if len(rates) < 2:
            return Decimal('0')
        
        mean_rate = sum(rates) / Decimal(str(len(rates)))
        variance = sum((rate - mean_rate) ** 2 for rate in rates) / Decimal(str(len(rates) - 1))
        
        return variance.sqrt()
    
    def _predict_next_rate(self, rates: List[Decimal]) -> Decimal:
        """预测下一期资金费率"""
        if len(rates) < 3:
            return sum(rates) / Decimal(str(len(rates))) if rates else Decimal('0')
        
        # 简单的线性回归预测
        n = len(rates)
        x_values = list(range(n))
        
        # 计算斜率和截距
        sum_x = sum(x_values)
        sum_y = sum(float(rate) for rate in rates)
        sum_xy = sum(x * float(rate) for x, rate in zip(x_values, rates))
        sum_x2 = sum(x * x for x in x_values)
        
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
            
            # 预测下一期
            next_x = n
            predicted = Decimal(str(slope * next_x + intercept))
            
            return predicted
        except ZeroDivisionError:
            # 如果无法计算线性回归，使用移动平均
            return sum(rates[-3:]) / Decimal('3')
    
    def _classify_funding_pattern(self, rates: List[Decimal], avg_rate: Decimal, volatility: Decimal) -> str:
        """分类资金费率模式"""
        if not rates:
            return 'no_data'
        
        # 分析费率分布
        positive_rates = [r for r in rates if r > 0]
        negative_rates = [r for r in rates if r < 0]
        
        positive_ratio = len(positive_rates) / len(rates)
        negative_ratio = len(negative_rates) / len(rates)
        
        # 判断模式
        if avg_rate > Decimal('0.0005'):  # 0.05%
            return 'high_positive'  # 持续正费率
        elif avg_rate < Decimal('-0.0005'):  # -0.05%
            return 'high_negative'  # 持续负费率
        elif volatility > Decimal('0.001'):  # 0.1%
            return 'volatile'  # 波动较大
        elif positive_ratio > 0.7:
            return 'mostly_positive'  # 多为正费率
        elif negative_ratio > 0.7:
            return 'mostly_negative'  # 多为负费率
        else:
            return 'balanced'  # 平衡模式
    
    def _calculate_prediction_confidence(self, symbol_data: List[Dict[str, Any]]) -> Decimal:
        """计算预测置信度"""
        if len(symbol_data) < 5:
            return Decimal('0.1')  # 数据不足，置信度低
        
        # 基于历史预测准确性计算置信度
        accuracy_score = Decimal('0.5')  # 基础分数
        
        # 数据越多，置信度越高
        data_factor = min(len(symbol_data) / 50, Decimal('1'))  # 最多50个数据点
        
        # 波动性越低，置信度越高
        rates = [data['funding_rate'] for data in symbol_data]
        volatility = self._calculate_volatility(rates)
        volatility_factor = max(Decimal('0.3'), Decimal('1') - volatility * 100)
        
        confidence = accuracy_score * data_factor * volatility_factor
        
        return min(confidence, Decimal('1'))
    
    def _calculate_opportunity_score(
        self,
        current_rate: Decimal,
        predicted_rate: Decimal,
        volatility: Decimal
    ) -> Decimal:
        """计算套利机会评分"""
        # 费率变化幅度
        rate_change = abs(predicted_rate - current_rate)
        
        # 波动性因子（波动性越高，机会越多但风险也越大）
        volatility_factor = min(volatility * 1000, Decimal('1'))  # 归一化
        
        # 综合评分
        score = (rate_change * 10 + volatility_factor) / Decimal('2')
        
        return min(score, Decimal('1'))
    
    def _calculate_potential_profit(
        self,
        current_rate: Decimal,
        current_price: Decimal,
        min_threshold: Decimal
    ) -> Decimal:
        """计算潜在收益"""
        # 假设一定的仓位规模计算收益
        position_value = current_price * Decimal('1000')  # 假设1000 USDT的仓位
        potential_profit = position_value * abs(current_rate)
        
        return potential_profit
    
    def _assess_arbitrage_risk(
        self,
        current_rate: Decimal,
        volatility: Decimal,
        confidence: Decimal
    ) -> Dict[str, Any]:
        """评估套利风险"""
        # 费率风险
        rate_risk = min(abs(current_rate) * 100, Decimal('1'))  # 归一化到0-1
        
        # 波动性风险
        volatility_risk = min(volatility * 1000, Decimal('1'))
        
        # 预测风险
        prediction_risk = Decimal('1') - confidence
        
        # 综合风险
        total_risk = (rate_risk + volatility_risk + prediction_risk) / Decimal('3')
        
        # 风险等级
        if total_risk < Decimal('0.3'):
            risk_level = 'LOW'
            suggested_size = Decimal('1.0')  # 满仓位
        elif total_risk < Decimal('0.6'):
            risk_level = 'MEDIUM'
            suggested_size = Decimal('0.7')  # 70%仓位
        elif total_risk < Decimal('0.8'):
            risk_level = 'HIGH'
            suggested_size = Decimal('0.5')  # 50%仓位
        else:
            risk_level = 'CRITICAL'
            suggested_size = Decimal('0.2')  # 20%仓位
        
        return {
            'level': risk_level,
            'score': total_risk,
            'suggested_size': suggested_size,
            'components': {
                'rate_risk': rate_risk,
                'volatility_risk': volatility_risk,
                'prediction_risk': prediction_risk
            }
        }
    
    def _calculate_time_sensitivity(self, settlement_time: datetime) -> Decimal:
        """计算时间敏感性"""
        now = datetime.now()
        time_to_settlement = settlement_time - now
        
        if time_to_settlement.total_seconds() <= 0:
            return Decimal('0')  # 已经结算
        
        # 时间敏感度：距离结算时间越近，敏感度越高
        hours_to_settlement = time_to_settlement.total_seconds() / 3600
        
        if hours_to_settlement <= 1:
            return Decimal('1')  # 1小时内，极高敏感度
        elif hours_to_settlement <= 4:
            return Decimal('0.8')  # 4小时内，高敏感度
        elif hours_to_settlement <= 8:
            return Decimal('0.6')  # 8小时内，中等敏感度
        else:
            return Decimal('0.3')  # 8小时外，低敏感度
    
    def _determine_arbitrage_strategy(self, current_rate: Decimal, predicted_rate: Decimal) -> str:
        """确定套利策略"""
        if current_rate > 0:
            # 正费率：做空永续，做多现货（如果预测费率会更高）
            if predicted_rate > current_rate:
                return 'funding_long_spot_short'  # 期待费率进一步上升
            else:
                return 'funding_short_spot_long'  # 期待费率回归
        else:
            # 负费率：做多永续，做空现货（如果预测费率会进一步下降）
            if predicted_rate < current_rate:
                return 'funding_short_spot_long'  # 期待费率进一步下降
            else:
                return 'funding_long_spot_short'  # 期待费率回归
    
    def _estimate_holding_period(self, current_rate: Decimal, predicted_rate: Decimal) -> int:
        """估算持仓周期（小时）"""
        rate_change = abs(predicted_rate - current_rate)
        
        # 费率变化越大，持有时间越短
        if rate_change > Decimal('0.001'):  # 0.1%
            return 4  # 4小时
        elif rate_change > Decimal('0.0005'):  # 0.05%
            return 8  # 8小时
        else:
            return 12  # 12小时
    
    def _determine_no_opportunity_reason(
        self,
        opportunity_score: Decimal,
        potential_profit: Decimal,
        risk_assessment: Dict[str, Any]
    ) -> str:
        """确定没有套利机会的原因"""
        if opportunity_score < 0.3:
            return '机会评分过低'
        elif potential_profit < Decimal('0.0001'):
            return '潜在收益不足'
        elif risk_assessment['level'] in ['HIGH', 'CRITICAL']:
            return '风险过高'
        else:
            return '条件不满足套利要求'


class FundingRateArbitrageStrategy(BaseFuturesStrategy):
    """资金费率套利策略"""
    
    def __init__(self, config: FuturesStrategyConfig, order_manager: Optional[Any] = None):
        super().__init__(config, order_manager)
        
        # 验证策略类型
        if config.strategy_type != FuturesStrategyType.ARBITRAGE:
            raise ValidationException("策略类型不匹配")
        
        self.funding_analyzer = FundingRateAnalysis()
        self.arbitrage_state = {
            'in_arbitrage': False,
            'strategy_type': 'unknown',
            'entry_time': None,
            'expected_profit': Decimal('0'),
            'target_exit_time': None
        }
        
        # 策略参数
        self.min_funding_threshold = Decimal('0.0001')  # 最小资金费率阈值
        self.max_holding_hours = 24  # 最大持仓小时
        self.profit_take_threshold = Decimal('0.001')  # 0.1%止盈阈值
        
        self.logger = logging.getLogger(f"funding_arbitrage.{config.strategy_id}")
    
    async def _initialize_specific(self):
        """初始化套利策略特定功能"""
        self.logger.info("初始化资金费率套利策略")
        
        # 启动资金费率监控任务
        self.funding_monitor_task = asyncio.create_task(self._funding_rate_monitoring_loop())
    
    async def _start_specific(self):
        """启动套利策略特定功能"""
        self.logger.info("启动资金费率套利策略")
    
    async def _pause_specific(self):
        """暂停套利策略特定功能"""
        self.logger.info("暂停资金费率套利策略")
    
    async def _resume_specific(self):
        """恢复套利策略特定功能"""
        self.logger.info("恢复资金费率套利策略")
    
    async def _stop_specific(self):
        """停止套利策略特定功能"""
        self.logger.info("停止资金费率套利策略")
        
        if hasattr(self, 'funding_monitor_task') and not self.funding_monitor_task.done():
            self.funding_monitor_task.cancel()
    
    async def get_next_orders(self, market_data: FuturesMarketData) -> List[FuturesOrderRequest]:
        """获取下一批订单"""
        try:
            if not self.state.is_trading_allowed():
                return []
            
            # 更新资金费率数据
            self.funding_analyzer.add_funding_rate_data(
                symbol=self.config.symbol,
                funding_rate=market_data.funding_rate,
                predicted_rate=market_data.funding_rate,  # 简化处理
                settlement_time=market_data.next_funding_time or datetime.now() + timedelta(hours=8),
                market_price=market_data.current_price,
                spot_price=market_data.mark_price  # 简化处理
            )
            
            # 检查套利机会
            arbitrage_opportunity = self.funding_analyzer.calculate_arbitrage_opportunity(
                symbol=self.config.symbol,
                current_rate=market_data.funding_rate,
                next_settlement_time=market_data.next_funding_time or datetime.now() + timedelta(hours=8),
                current_price=market_data.current_price,
                min_profit_threshold=self.min_funding_threshold
            )
            
            orders = []
            
            if self.arbitrage_state['in_arbitrage']:
                # 检查是否应该退出套利
                orders = await self._check_arbitrage_exit(market_data, arbitrage_opportunity)
            else:
                # 检查是否应该进入套利
                orders = await self._check_arbitrage_entry(market_data, arbitrage_opportunity)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取套利订单失败: {e}")
            return []
    
    async def _check_arbitrage_entry(self, market_data: FuturesMarketData, opportunity: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """检查套利入场机会"""
        try:
            if not opportunity['opportunity']:
                return []
            
            # 根据策略类型生成订单
            strategy_type = opportunity['strategy']
            position_size = self._calculate_arbitrage_position_size(market_data, opportunity)
            
            if position_size <= 0:
                return []
            
            orders = []
            
            if strategy_type == 'funding_long_spot_short':
                # 资金费率多头：做多永续，做空现货（或做空其他永续）
                orders = await self._execute_funding_long_strategy(market_data, position_size)
                
            elif strategy_type == 'funding_short_spot_long':
                # 资金费率空头：做空永续，做多现货（或做多其他永续）
                orders = await self._execute_funding_short_strategy(market_data, position_size)
            
            if orders:
                # 设置套利状态
                self.arbitrage_state.update({
                    'in_arbitrage': True,
                    'strategy_type': strategy_type,
                    'entry_time': datetime.now(),
                    'expected_profit': opportunity['potential_profit'],
                    'target_exit_time': datetime.now() + timedelta(hours=opportunity['expected_duration'])
                })
                
                self.logger.info(
                    f"进入资金费率套利: {strategy_type}, "
                    f"预期收益: {opportunity['potential_profit']:.6f}, "
                    f"持仓周期: {opportunity['expected_duration']}小时"
                )
            
            return orders
            
        except Exception as e:
            self.logger.error(f"检查套利入场失败: {e}")
            return []
    
    async def _check_arbitrage_exit(self, market_data: FuturesMarketData, opportunity: Dict[str, Any]) -> List[FuturesOrderRequest]:
        """检查套利出场机会"""
        try:
            orders = []
            should_exit = False
            exit_reason = ""
            
            # 检查时间退出条件
            if self.arbitrage_state['target_exit_time']:
                if datetime.now() >= self.arbitrage_state['target_exit_time']:
                    should_exit = True
                    exit_reason = "达到预期持仓时间"
            
            # 检查止盈条件（简化处理）
            current_pnl = self.state.unrealized_pnl
            if current_pnl >= self.arbitrage_state['expected_profit'] * Decimal('0.8'):  # 达到80%预期收益
                should_exit = True
                exit_reason = "达到止盈条件"
            
            # 检查亏损条件
            if current_pnl <= -self.arbitrage_state['expected_profit'] * Decimal('0.5'):  # 亏损超过50%预期收益
                should_exit = True
                exit_reason = "达到止损条件"
            
            # 检查风险条件
            if opportunity.get('risk_level') == 'CRITICAL':
                should_exit = True
                exit_reason = "市场风险过高"
            
            if should_exit:
                # 生成平仓订单
                orders = await self._execute_arbitrage_exit(market_data, exit_reason)
                
                # 重置套利状态
                self.arbitrage_state.update({
                    'in_arbitrage': False,
                    'strategy_type': 'unknown',
                    'entry_time': None,
                    'expected_profit': Decimal('0'),
                    'target_exit_time': None
                })
                
                self.logger.info(f"退出资金费率套利: {exit_reason}")
            
            return orders
            
        except Exception as e:
            self.logger.error(f"检查套利出场失败: {e}")
            return []
    
    def _calculate_arbitrage_position_size(self, market_data: FuturesMarketData, opportunity: Dict[str, Any]) -> Decimal:
        """计算套利仓位大小"""
        try:
            # 基础仓位大小
            base_size = self.config.base_quantity
            
            # 根据套利机会评分调整
            score_multiplier = min(opportunity['opportunity_score'] / Decimal('0.7'), Decimal('1.5'))
            
            # 根据风险等级调整
            risk_multiplier = opportunity['suggested_size']
            
            # 计算最终仓位大小
            final_size = base_size * score_multiplier * risk_multiplier
            
            # 限制在最大仓位内
            final_size = min(final_size, self.config.max_position_size)
            
            # 确保订单大小在允许范围内
            final_size = max(self.config.min_order_size, min(final_size, self.config.max_order_size))
            
            self.logger.debug(f"计算套利仓位: 基础={base_size}, 评分倍数={score_multiplier}, 风险倍数={risk_multiplier}, 最终={final_size}")
            return final_size
            
        except Exception as e:
            self.logger.error(f"计算套利仓位大小失败: {e}")
            return self.config.min_order_size
    
    async def _execute_funding_long_strategy(self, market_data: FuturesMarketData, position_size: Decimal) -> List[FuturesOrderRequest]:
        """执行资金费率多头策略（做多永续，做空现货或其他永续）"""
        orders = []
        
        try:
            # 做多永续合约
            futures_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_funding_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.BUY,
                quantity=position_size,
                position_side=PositionSide.LONG,
                client_order_id=f"funding_long_{int(datetime.now().timestamp())}"
            )
            orders.append(futures_order)
            
            # 简化处理：这里应该做空现货或其他永续
            # 实际实现中需要选择合适的对冲工具
            hedge_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_hedge_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,  # 实际中可能是不同的币对
                order_type=OrderType.MARKET,
                order_side=OrderSide.SELL,
                quantity=position_size,
                position_side=PositionSide.LONG,  # 对冲操作
                client_order_id=f"funding_hedge_{int(datetime.now().timestamp())}"
            )
            orders.append(hedge_order)
            
            self.logger.info(f"执行资金费率多头策略: 永续多单={position_size}, 对冲空单={position_size}")
            return orders
            
        except Exception as e:
            self.logger.error(f"执行资金费率多头策略失败: {e}")
            return []
    
    async def _execute_funding_short_strategy(self, market_data: FuturesMarketData, position_size: Decimal) -> List[FuturesOrderRequest]:
        """执行资金费率空头策略（做空永续，做多现货或其他永续）"""
        orders = []
        
        try:
            # 做空永续合约
            futures_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_funding_short_{datetime.now().timestamp()}",
                symbol=self.config.symbol,
                order_type=OrderType.MARKET,
                order_side=OrderSide.SELL,
                quantity=position_size,
                position_side=PositionSide.SHORT,
                client_order_id=f"funding_short_{int(datetime.now().timestamp())}"
            )
            orders.append(futures_order)
            
            # 简化处理：这里应该做多现货或其他永续
            hedge_order = FuturesOrderRequest(
                order_id=f"{self.config.strategy_id}_hedge_long_{datetime.now().timestamp()}",
                symbol=self.config.symbol,  # 实际中可能是不同的币对
                order_type=OrderType.MARKET,
                order_side=OrderSide.BUY,
                quantity=position_size,
                position_side=PositionSide.SHORT,  # 对冲操作
                client_order_id=f"funding_hedge_{int(datetime.now().timestamp())}"
            )
            orders.append(hedge_order)
            
            self.logger.info(f"执行资金费率空头策略: 永续空单={position_size}, 对冲多单={position_size}")
            return orders
            
        except Exception as e:
            self.logger.error(f"执行资金费率空头策略失败: {e}")
            return []
    
    async def _execute_arbitrage_exit(self, market_data: FuturesMarketData, reason: str) -> List[FuturesOrderRequest]:
        """执行套利平仓"""
        orders = []
        
        try:
            # 平仓所有持仓
            if self.state.current_position.quantity != 0:
                # 平多单
                if self.state.current_position.quantity > 0:
                    close_order = FuturesOrderRequest(
                        order_id=f"{self.config.strategy_id}_close_long_{datetime.now().timestamp()}",
                        symbol=self.config.symbol,
                        order_type=OrderType.MARKET,
                        order_side=OrderSide.SELL,
                        quantity=abs(self.state.current_position.quantity),
                        position_side=PositionSide.LONG,
                        client_order_id=f"close_long_{int(datetime.now().timestamp())}"
                    )
                    orders.append(close_order)
                
                # 平空单
                if self.state.current_position.quantity < 0:
                    close_order = FuturesOrderRequest(
                        order_id=f"{self.config.strategy_id}_close_short_{datetime.now().timestamp()}",
                        symbol=self.config.symbol,
                        order_type=OrderType.MARKET,
                        order_side=OrderSide.BUY,
                        quantity=abs(self.state.current_position.quantity),
                        position_side=PositionSide.SHORT,
                        client_order_id=f"close_short_{int(datetime.now().timestamp())}"
                    )
                    orders.append(close_order)
            
            self.logger.info(f"执行套利平仓: 原因={reason}, 订单数量={len(orders)}")
            return orders
            
        except Exception as e:
            self.logger.error(f"执行套利平仓失败: {e}")
            return []
    
    async def _funding_rate_monitoring_loop(self):
        """资金费率监控循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分钟检查一次
                
                # 这里可以添加自动监控逻辑
                # 例如：资金费率异常变化时触发警告
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"资金费率监控错误: {e}")
    
    async def process_order_result(self, order_result: FuturesOrderResult) -> bool:
        """处理订单执行结果"""
        try:
            self.update_state_after_order(order_result, self.last_market_data)
            
            # 记录资金费率成本
            if order_result.funding_rate:
                funding_cost = abs(self.state.current_position.quantity) * self.last_market_data.current_price * order_result.funding_rate
                self.state.funding_rate_paid += funding_cost
            
            self.logger.info(f"套利订单处理完成: {order_result.order_id}, 成功: {order_result.success}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理套利订单结果失败: {e}")
            self.state.error_count += 1
            self.state.last_error = str(e)
            return False
    
    def update_state_after_order(self, order_result: FuturesOrderResult, market_data: Optional[FuturesMarketData]):
        """更新策略状态（订单执行后）"""
        self.state.total_orders += 1
        
        if order_result.success:
            self.state.filled_orders += 1
            
            # 更新仓位
            if self.state.current_position:
                current_qty = self.state.current_position.quantity
                
                if any(keyword in order_result.order_id for keyword in ['funding_long', 'hedge_long']):
                    self.state.current_position.quantity += order_result.filled_quantity
                elif any(keyword in order_result.order_id for keyword in ['funding_short', 'hedge_short']):
                    self.state.current_position.quantity -= order_result.filled_quantity
                elif 'close' in order_result.order_id:
                    self.state.current_position.quantity = Decimal('0')
                
                # 更新平均价格
                if market_data:
                    total_value = (current_qty * self.state.current_position.average_price) + \
                                 (order_result.filled_quantity * order_result.average_price)
                    total_quantity = current_qty + order_result.filled_quantity
                    
                    if total_quantity != 0:
                        self.state.current_position.average_price = total_value / total_quantity
            
            # 更新盈亏
            if market_data:
                current_value = abs(self.state.current_position.quantity) * market_data.current_price
                cost_value = abs(self.state.current_position.quantity) * self.state.current_position.average_price
                self.state.current_position.unrealized_pnl = current_value - cost_value
            
            self.state.realized_pnl += order_result.average_price * order_result.filled_quantity - order_result.commission
            self.state.total_profit = self.state.realized_pnl + self.state.unrealized_pnl
            self.state.commission_paid += order_result.commission
            
        else:
            self.state.failed_orders += 1
        
        # 更新性能指标
        self.state.update_performance_metrics()
        
        # 记录历史
        self.performance_history.append({
            'timestamp': datetime.now(),
            'order_id': order_result.order_id,
            'success': order_result.success,
            'pnl': float(self.state.total_profit),
            'drawdown': float(self.state.current_drawdown)
        })
        
        # 保持历史记录在合理范围内
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]