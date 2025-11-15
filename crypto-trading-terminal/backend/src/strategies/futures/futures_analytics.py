"""
期货策略分析报告系统
提供期货交易策略的性能分析、风险评估和详细报告功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import pandas as pd
import numpy as np
from collections import defaultdict

from .base_futures_strategy import (
    FuturesMarketData, FuturesPosition, FuturesAccountBalance,
    FuturesStrategyConfig, FuturesStrategyState
)
from .margin_liquidation_manager import MarginAlert
from .leverage_manager import PositionMetrics


@dataclass
class FuturesPerformanceMetrics:
    """期货策略性能指标"""
    strategy_id: str
    symbol: str
    user_id: int
    
    # 基础指标
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # 盈亏指标
    total_pnl: Decimal = Decimal('0')
    gross_profit: Decimal = Decimal('0')
    gross_loss: Decimal = Decimal('0')
    net_profit: Decimal = Decimal('0')
    largest_winning_trade: Decimal = Decimal('0')
    largest_losing_trade: Decimal = Decimal('0')
    
    # 胜率和盈亏比
    win_rate: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')
    
    # 风险指标
    max_drawdown: Decimal = Decimal('0')
    current_drawdown: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    calmar_ratio: Decimal = Decimal('0')
    var_95: Decimal = Decimal('0')  # 95% VaR
    
    # 期货特有指标
    total_funding_fees: Decimal = Decimal('0')
    funding_fee_ratio: Decimal = Decimal('0')
    average_leverage: Decimal = Decimal('1')
    leverage_utilization: Decimal = Decimal('0')
    liquidation_count: int = 0
    margin_call_count: int = 0
    
    # 时间指标
    total_trading_days: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    # 计算时间
    calculation_time: datetime = field(default_factory=datetime.now)


@dataclass
class FuturesRiskAnalysis:
    """期货策略风险分析"""
    strategy_id: str
    symbol: str
    
    # 风险等级
    overall_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: Decimal  # 0-100分
    
    # 杠杆风险
    current_leverage: Decimal
    average_leverage: Decimal
    max_leverage_used: Decimal
    leverage_risk_score: Decimal
    
    # 清算风险
    distance_to_liquidation: Decimal
    liquidation_risk_score: Decimal
    liquidation_probability: Decimal
    
    # 保证金风险
    current_margin_ratio: Decimal
    average_margin_ratio: Decimal
    margin_risk_score: Decimal
    
    # 波动率风险
    price_volatility: Decimal
    volatility_risk_score: Decimal
    
    # 资金费率风险
    funding_rate_exposure: Decimal
    funding_cost_ratio: Decimal
    funding_risk_score: Decimal
    
    # 相关性风险
    correlation_risk: Decimal
    
    # 建议措施
    risk_recommendations: List[str] = field(default_factory=list)
    
    analysis_time: datetime = field(default_factory=datetime.now)


@dataclass
class FuturesStrategyReport:
    """期货策略综合报告"""
    strategy_id: str
    symbol: str
    user_id: int
    
    # 报告时间范围
    start_date: datetime
    end_date: datetime
    
    # 性能指标
    performance: FuturesPerformanceMetrics
    
    # 风险分析
    risk_analysis: FuturesRiskAnalysis
    
    # 交易记录
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 持仓记录
    position_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 预警记录
    alert_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 总结建议
    summary_recommendations: List[str] = field(default_factory=list)
    
    # 报告生成时间
    generated_at: datetime = field(default_factory=datetime.now)


class FuturesAnalyticsEngine:
    """期货策略分析引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_cache: Dict[str, FuturesPerformanceMetrics] = {}
        self.risk_cache: Dict[str, FuturesRiskAnalysis] = {}
    
    async def analyze_strategy_performance(
        self,
        strategy_id: str,
        symbol: str,
        user_id: int,
        trade_history: List[Dict[str, Any]],
        position_history: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> FuturesPerformanceMetrics:
        """分析策略性能"""
        try:
            # 过滤时间范围内的数据
            filtered_trades = [
                trade for trade in trade_history
                if start_date <= datetime.fromisoformat(trade['timestamp']) <= end_date
            ]
            
            filtered_positions = [
                pos for pos in position_history
                if start_date <= datetime.fromisoformat(pos['timestamp']) <= end_date
            ]
            
            # 计算基础指标
            total_trades = len(filtered_trades)
            if total_trades == 0:
                return self._create_empty_metrics(strategy_id, symbol, user_id, start_date, end_date)
            
            # 计算盈亏指标
            winning_trades = [t for t in filtered_trades if Decimal(str(t.get('pnl', '0'))) > 0]
            losing_trades = [t for t in filtered_trades if Decimal(str(t.get('pnl', '0'))) < 0]
            
            total_pnl = sum(Decimal(str(t.get('pnl', '0'))) for t in filtered_trades)
            gross_profit = sum(Decimal(str(t.get('pnl', '0'))) for t in winning_trades)
            gross_loss = abs(sum(Decimal(str(t.get('pnl', '0'))) for t in losing_trades))
            
            # 计算胜率和盈亏比
            win_rate = Decimal(str(len(winning_trades) / total_trades)) * 100
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal('0')
            average_win = gross_profit / Decimal(str(len(winning_trades))) if winning_trades else Decimal('0')
            average_loss = gross_loss / Decimal(str(len(losing_trades))) if losing_trades else Decimal('0')
            
            # 计算最大盈亏
            largest_winning_trade = max(
                (Decimal(str(t.get('pnl', '0'))) for t in winning_trades),
                default=Decimal('0')
            )
            largest_losing_trade = min(
                (Decimal(str(t.get('pnl', '0'))) for t in losing_trades),
                default=Decimal('0')
            )
            
            # 计算风险指标
            max_drawdown = self._calculate_max_drawdown(filtered_trades)
            current_drawdown = self._calculate_current_drawdown(filtered_trades)
            sharpe_ratio = self._calculate_sharpe_ratio(filtered_trades)
            calmar_ratio = self._calculate_calmar_ratio(filtered_trades)
            var_95 = self._calculate_var(filtered_trades, 0.95)
            
            # 计算期货特有指标
            total_funding_fees = sum(
                Decimal(str(t.get('funding_fee', '0'))) for t in filtered_trades
            )
            funding_fee_ratio = total_funding_fees / abs(total_pnl) if total_pnl != 0 else Decimal('0')
            
            # 计算杠杆指标
            leverage_data = [Decimal(str(pos.get('leverage', '1'))) for pos in filtered_positions]
            average_leverage = sum(leverage_data) / Decimal(str(len(leverage_data))) if leverage_data else Decimal('1')
            
            # 计算保证金使用率
            margin_ratios = [Decimal(str(pos.get('margin_ratio', '100'))) for pos in filtered_positions]
            margin_utilization = Decimal('100') - (sum(margin_ratios) / Decimal(str(len(margin_ratios)))) if margin_ratios else Decimal('0')
            
            # 统计事件
            liquidation_count = sum(1 for t in filtered_trades if t.get('liquidation', False))
            margin_call_count = sum(1 for t in filtered_trades if t.get('margin_call', False))
            
            # 构建性能指标
            metrics = FuturesPerformanceMetrics(
                strategy_id=strategy_id,
                symbol=symbol,
                user_id=user_id,
                total_trades=total_trades,
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                total_pnl=total_pnl,
                gross_profit=gross_profit,
                gross_loss=gross_loss,
                net_profit=gross_profit - gross_loss,
                largest_winning_trade=largest_winning_trade,
                largest_losing_trade=largest_losing_trade,
                win_rate=win_rate,
                profit_factor=profit_factor,
                average_win=average_win,
                average_loss=average_loss,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                var_95=var_95,
                total_funding_fees=total_funding_fees,
                funding_fee_ratio=funding_fee_ratio,
                average_leverage=average_leverage,
                leverage_utilization=margin_utilization,
                liquidation_count=liquidation_count,
                margin_call_count=margin_call_count,
                total_trading_days=(end_date - start_date).days
            )
            
            # 缓存结果
            cache_key = f"{strategy_id}_{symbol}_{user_id}"
            self.performance_cache[cache_key] = metrics
            
            self.logger.info(f"完成策略 {strategy_id} 性能分析")
            return metrics
            
        except Exception as e:
            self.logger.error(f"性能分析失败: {e}")
            return self._create_empty_metrics(strategy_id, symbol, user_id, start_date, end_date)
    
    async def analyze_strategy_risk(
        self,
        strategy_id: str,
        symbol: str,
        current_position: FuturesPosition,
        current_balance: FuturesAccountBalance,
        market_data: FuturesMarketData,
        historical_data: List[Dict[str, Any]]
    ) -> FuturesRiskAnalysis:
        """分析策略风险"""
        try:
            # 基础风险评估
            overall_risk_score = Decimal('0')
            recommendations = []
            
            # 杠杆风险评估
            current_leverage = current_position.leverage
            leverage_risk_score = self._calculate_leverage_risk_score(current_leverage)
            overall_risk_score += leverage_risk_score
            
            if leverage_risk_score > Decimal('70'):
                recommendations.append(f"当前杠杆 {current_leverage}x 过高，建议降低杠杆")
            
            # 清算风险评估
            if current_position.liquidation_price:
                if current_position.quantity > 0:  # 多头
                    liquidation_distance = ((current_position.liquidation_price - market_data.current_price) / current_position.liquidation_price) * 100
                else:  # 空头
                    liquidation_distance = ((market_data.current_price - current_position.liquidation_price) / current_position.liquidation_price) * 100
                
                liquidation_risk_score = self._calculate_liquidation_risk_score(liquidation_distance)
                overall_risk_score += liquidation_risk_score
                
                if liquidation_distance < Decimal('10'):
                    recommendations.append("距离清算价格过近，存在强制平仓风险")
            else:
                liquidation_distance = Decimal('100')
                liquidation_risk_score = Decimal('0')
            
            # 保证金风险评估
            position_value = abs(current_position.quantity * market_data.current_price)
            margin_ratio = self._calculate_margin_ratio(current_balance.wallet_balance, position_value)
            margin_risk_score = self._calculate_margin_risk_score(margin_ratio)
            overall_risk_score += margin_risk_score
            
            if margin_ratio < Decimal('110'):
                recommendations.append(f"保证金比例 {margin_ratio:.1f}% 偏低，建议增加保证金")
            
            # 波动率风险评估
            if historical_data:
                price_changes = [Decimal(str(data.get('price_change', '0'))) for data in historical_data[-24:]]  # 最近24个周期
                volatility = self._calculate_volatility(price_changes)
                volatility_risk_score = self._calculate_volatility_risk_score(volatility)
                overall_risk_score += volatility_risk_score
            else:
                volatility = Decimal('0')
                volatility_risk_score = Decimal('0')
            
            # 资金费率风险评估
            funding_cost_ratio = self._calculate_funding_cost_ratio(
                current_balance.total_funding_fee,
                current_balance.realized_pnl
            )
            funding_risk_score = self._calculate_funding_risk_score(funding_cost_ratio)
            overall_risk_score += funding_risk_score
            
            if funding_cost_ratio > Decimal('0.5'):
                recommendations.append("资金费率成本占比较高，需关注费率变化")
            
            # 相关性风险（简化计算）
            correlation_risk = self._calculate_correlation_risk(historical_data)
            
            # 整体风险等级
            if overall_risk_score > Decimal('70'):
                overall_risk_level = 'CRITICAL'
            elif overall_risk_score > Decimal('50'):
                overall_risk_level = 'HIGH'
            elif overall_risk_score > Decimal('30'):
                overall_risk_level = 'MEDIUM'
            else:
                overall_risk_level = 'LOW'
            
            # 添加通用建议
            if not recommendations:
                recommendations.append("当前风险水平可接受，继续监控")
            
            recommendations.append(f"建议定期监控风险指标，当前风险评分: {overall_risk_score:.1f}/100")
            
            # 构建风险分析
            risk_analysis = FuturesRiskAnalysis(
                strategy_id=strategy_id,
                symbol=symbol,
                overall_risk_level=overall_risk_level,
                risk_score=overall_risk_score,
                current_leverage=current_leverage,
                average_leverage=current_leverage,  # 简化处理
                max_leverage_used=current_leverage,  # 简化处理
                leverage_risk_score=leverage_risk_score,
                distance_to_liquidation=liquidation_distance,
                liquidation_risk_score=liquidation_risk_score,
                liquidation_probability=liquidation_risk_score / Decimal('100'),
                current_margin_ratio=margin_ratio,
                average_margin_ratio=margin_ratio,  # 简化处理
                margin_risk_score=margin_risk_score,
                price_volatility=volatility,
                volatility_risk_score=volatility_risk_score,
                funding_rate_exposure=current_balance.total_funding_fee,
                funding_cost_ratio=funding_cost_ratio,
                funding_risk_score=funding_risk_score,
                correlation_risk=correlation_risk,
                risk_recommendations=recommendations
            )
            
            # 缓存结果
            cache_key = f"{strategy_id}_{symbol}"
            self.risk_cache[cache_key] = risk_analysis
            
            self.logger.info(f"完成策略 {strategy_id} 风险分析")
            return risk_analysis
            
        except Exception as e:
            self.logger.error(f"风险分析失败: {e}")
            return self._create_empty_risk_analysis(strategy_id, symbol)
    
    async def generate_strategy_report(
        self,
        strategy_id: str,
        symbol: str,
        user_id: int,
        trade_history: List[Dict[str, Any]],
        position_history: List[Dict[str, Any]],
        alert_history: List[Dict[str, Any]],
        current_position: FuturesPosition,
        current_balance: FuturesAccountBalance,
        market_data: FuturesMarketData,
        report_period_days: int = 30
    ) -> FuturesStrategyReport:
        """生成策略综合报告"""
        try:
            # 计算报告时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=report_period_days)
            
            # 生成性能分析
            performance = await self.analyze_strategy_performance(
                strategy_id, symbol, user_id,
                trade_history, position_history,
                start_date, end_date
            )
            
            # 生成风险分析
            risk_analysis = await self.analyze_strategy_risk(
                strategy_id, symbol,
                current_position, current_balance, market_data,
                []  # 历史数据（简化处理）
            )
            
            # 过滤交易记录
            filtered_trades = [
                trade for trade in trade_history
                if start_date <= datetime.fromisoformat(trade['timestamp']) <= end_date
            ]
            
            # 过滤持仓记录
            filtered_positions = [
                pos for pos in position_history
                if start_date <= datetime.fromisoformat(pos['timestamp']) <= end_date
            ]
            
            # 过滤预警记录
            filtered_alerts = [
                alert for alert in alert_history
                if start_date <= datetime.fromisoformat(alert['timestamp']) <= end_date
            ]
            
            # 生成总结建议
            summary_recommendations = self._generate_summary_recommendations(
                performance, risk_analysis
            )
            
            # 构建报告
            report = FuturesStrategyReport(
                strategy_id=strategy_id,
                symbol=symbol,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                performance=performance,
                risk_analysis=risk_analysis,
                trade_history=filtered_trades,
                position_history=filtered_positions,
                alert_history=filtered_alerts,
                summary_recommendations=summary_recommendations
            )
            
            self.logger.info(f"生成策略 {strategy_id} 综合报告")
            return report
            
        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            # 返回空报告
            return self._create_empty_report(strategy_id, symbol, user_id)
    
    def export_report_to_json(self, report: FuturesStrategyReport) -> str:
        """导出报告为JSON格式"""
        try:
            report_dict = {
                'strategy_id': report.strategy_id,
                'symbol': report.symbol,
                'user_id': report.user_id,
                'start_date': report.start_date.isoformat(),
                'end_date': report.end_date.isoformat(),
                'generated_at': report.generated_at.isoformat(),
                'performance': {
                    'total_trades': report.performance.total_trades,
                    'win_rate': float(report.performance.win_rate),
                    'total_pnl': float(report.performance.total_pnl),
                    'sharpe_ratio': float(report.performance.sharpe_ratio),
                    'max_drawdown': float(report.performance.max_drawdown),
                    'profit_factor': float(report.performance.profit_factor),
                    'total_funding_fees': float(report.performance.total_funding_fees),
                    'average_leverage': float(report.performance.average_leverage),
                    'leverage_utilization': float(report.performance.leverage_utilization),
                    'liquidation_count': report.performance.liquidation_count,
                    'margin_call_count': report.performance.margin_call_count
                },
                'risk_analysis': {
                    'overall_risk_level': report.risk_analysis.overall_risk_level,
                    'risk_score': float(report.risk_analysis.risk_score),
                    'leverage_risk_score': float(report.risk_analysis.leverage_risk_score),
                    'liquidation_risk_score': float(report.risk_analysis.liquidation_risk_score),
                    'margin_risk_score': float(report.risk_analysis.margin_risk_score),
                    'volatility_risk_score': float(report.risk_analysis.volatility_risk_score),
                    'funding_risk_score': float(report.risk_analysis.funding_risk_score),
                    'recommendations': report.risk_analysis.risk_recommendations
                },
                'summary_recommendations': report.summary_recommendations,
                'statistics': {
                    'total_trades': len(report.trade_history),
                    'total_positions': len(report.position_history),
                    'total_alerts': len(report.alert_history)
                }
            }
            
            return json.dumps(report_dict, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"报告导出失败: {e}")
            return '{"error": "Export failed"}'
    
    # 辅助计算方法
    def _calculate_max_drawdown(self, trade_history: List[Dict[str, Any]]) -> Decimal:
        """计算最大回撤"""
        try:
            cumulative_pnl = Decimal('0')
            peak = Decimal('0')
            max_drawdown = Decimal('0')
            
            for trade in trade_history:
                pnl = Decimal(str(trade.get('pnl', '0')))
                cumulative_pnl += pnl
                peak = max(peak, cumulative_pnl)
                drawdown = peak - cumulative_pnl
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"最大回撤计算失败: {e}")
            return Decimal('0')
    
    def _calculate_current_drawdown(self, trade_history: List[Dict[str, Any]]) -> Decimal:
        """计算当前回撤"""
        try:
            cumulative_pnl = Decimal('0')
            peak = Decimal('0')
            
            for trade in trade_history:
                pnl = Decimal(str(trade.get('pnl', '0')))
                cumulative_pnl += pnl
                peak = max(peak, cumulative_pnl)
            
            current_drawdown = peak - cumulative_pnl
            return current_drawdown
            
        except Exception as e:
            self.logger.error(f"当前回撤计算失败: {e}")
            return Decimal('0')
    
    def _calculate_sharpe_ratio(self, trade_history: List[Dict[str, Any]]) -> Decimal:
        """计算夏普比率"""
        try:
            if len(trade_history) < 2:
                return Decimal('0')
            
            returns = [Decimal(str(trade.get('pnl', '0'))) for trade in trade_history]
            mean_return = sum(returns) / Decimal(str(len(returns)))
            
            if len(returns) == 1:
                return Decimal('0')
            
            variance = sum((r - mean_return) ** 2 for r in returns) / Decimal(str(len(returns) - 1))
            std_return = variance.sqrt()
            
            if std_return == 0:
                return Decimal('0')
            
            sharpe_ratio = mean_return / std_return
            return sharpe_ratio
            
        except Exception as e:
            self.logger.error(f"夏普比率计算失败: {e}")
            return Decimal('0')
    
    def _calculate_calmar_ratio(self, trade_history: List[Dict[str, Any]]) -> Decimal:
        """计算卡尔马比率"""
        try:
            max_dd = self._calculate_max_drawdown(trade_history)
            total_return = sum(Decimal(str(trade.get('pnl', '0'))) for trade in trade_history)
            
            if max_dd == 0:
                return Decimal('0')
            
            calmar_ratio = total_return / max_dd
            return calmar_ratio
            
        except Exception as e:
            self.logger.error(f"卡尔马比率计算失败: {e}")
            return Decimal('0')
    
    def _calculate_var(self, trade_history: List[Dict[str, Any]], confidence_level: float) -> Decimal:
        """计算风险价值(VaR)"""
        try:
            returns = [Decimal(str(trade.get('pnl', '0'))) for trade in trade_history]
            
            if not returns:
                return Decimal('0')
            
            returns.sort()
            index = int((1 - confidence_level) * len(returns))
            var_value = returns[min(index, len(returns) - 1)]
            
            return abs(var_value)
            
        except Exception as e:
            self.logger.error(f"VaR计算失败: {e}")
            return Decimal('0')
    
    def _calculate_leverage_risk_score(self, leverage: Decimal) -> Decimal:
        """计算杠杆风险评分"""
        if leverage <= Decimal('5'):
            return Decimal('10')
        elif leverage <= Decimal('10'):
            return Decimal('30')
        elif leverage <= Decimal('15'):
            return Decimal('60')
        elif leverage <= Decimal('20'):
            return Decimal('80')
        else:
            return Decimal('95')
    
    def _calculate_liquidation_risk_score(self, liquidation_distance: Decimal) -> Decimal:
        """计算清算风险评分"""
        if liquidation_distance >= Decimal('50'):
            return Decimal('5')
        elif liquidation_distance >= Decimal('25'):
            return Decimal('20')
        elif liquidation_distance >= Decimal('15'):
            return Decimal('40')
        elif liquidation_distance >= Decimal('10'):
            return Decimal('70')
        else:
            return Decimal('90')
    
    def _calculate_margin_risk_score(self, margin_ratio: Decimal) -> Decimal:
        """计算保证金风险评分"""
        if margin_ratio >= Decimal('200'):
            return Decimal('5')
        elif margin_ratio >= Decimal('150'):
            return Decimal('15')
        elif margin_ratio >= Decimal('120'):
            return Decimal('30')
        elif margin_ratio >= Decimal('110'):
            return Decimal('50')
        elif margin_ratio >= Decimal('105'):
            return Decimal('75')
        else:
            return Decimal('95')
    
    def _calculate_volatility(self, price_changes: List[Decimal]) -> Decimal:
        """计算波动率"""
        try:
            if len(price_changes) < 2:
                return Decimal('0')
            
            mean_change = sum(price_changes) / Decimal(str(len(price_changes)))
            variance = sum((change - mean_change) ** 2 for change in price_changes) / Decimal(str(len(price_changes) - 1))
            volatility = variance.sqrt()
            
            return volatility
            
        except Exception as e:
            self.logger.error(f"波动率计算失败: {e}")
            return Decimal('0')
    
    def _calculate_volatility_risk_score(self, volatility: Decimal) -> Decimal:
        """计算波动率风险评分"""
        volatility_pct = volatility * 100  # 转换为百分比
        
        if volatility_pct <= Decimal('2'):
            return Decimal('10')
        elif volatility_pct <= Decimal('5'):
            return Decimal('30')
        elif volatility_pct <= Decimal('10'):
            return Decimal('60')
        else:
            return Decimal('85')
    
    def _calculate_margin_ratio(self, wallet_balance: Decimal, position_value: Decimal) -> Decimal:
        """计算保证金比例"""
        if position_value <= 0:
            return Decimal('100')
        
        return (wallet_balance / position_value) * 100
    
    def _calculate_funding_cost_ratio(self, total_funding_fee: Decimal, realized_pnl: Decimal) -> Decimal:
        """计算资金费率成本比率"""
        if realized_pnl == 0:
            return Decimal('0')
        
        return abs(total_funding_fee / realized_pnl)
    
    def _calculate_funding_risk_score(self, funding_cost_ratio: Decimal) -> Decimal:
        """计算资金费率风险评分"""
        if funding_cost_ratio <= Decimal('0.1'):
            return Decimal('10')
        elif funding_cost_ratio <= Decimal('0.2'):
            return Decimal('30')
        elif funding_cost_ratio <= Decimal('0.5'):
            return Decimal('60')
        else:
            return Decimal('85')
    
    def _calculate_correlation_risk(self, historical_data: List[Dict[str, Any]]) -> Decimal:
        """计算相关性风险（简化）"""
        # 简化处理，返回固定值
        return Decimal('20')
    
    def _generate_summary_recommendations(
        self,
        performance: FuturesPerformanceMetrics,
        risk_analysis: FuturesRiskAnalysis
    ) -> List[str]:
        """生成总结建议"""
        recommendations = []
        
        # 性能建议
        if performance.win_rate < Decimal('40'):
            recommendations.append("胜率偏低，建议优化交易策略")
        
        if performance.max_drawdown > performance.total_pnl * Decimal('2'):
            recommendations.append("最大回撤较大，建议加强风险管理")
        
        if performance.sharpe_ratio < Decimal('1'):
            recommendations.append("夏普比率偏低，考虑调整仓位管理")
        
        # 风险建议
        recommendations.extend(risk_analysis.risk_recommendations)
        
        # 期货特有建议
        if performance.funding_fee_ratio > Decimal('0.3'):
            recommendations.append("资金费率成本较高，建议关注费率变化")
        
        if performance.liquidation_count > 0:
            recommendations.append(f"发生 {performance.liquidation_count} 次清算，需加强风险控制")
        
        return recommendations
    
    def _create_empty_metrics(
        self,
        strategy_id: str,
        symbol: str,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> FuturesPerformanceMetrics:
        """创建空性能指标"""
        return FuturesPerformanceMetrics(
            strategy_id=strategy_id,
            symbol=symbol,
            user_id=user_id,
            total_trading_days=(end_date - start_date).days
        )
    
    def _create_empty_risk_analysis(self, strategy_id: str, symbol: str) -> FuturesRiskAnalysis:
        """创建空风险分析"""
        return FuturesRiskAnalysis(
            strategy_id=strategy_id,
            symbol=symbol,
            overall_risk_level='UNKNOWN',
            risk_score=Decimal('0')
        )
    
    def _create_empty_report(
        self,
        strategy_id: str,
        symbol: str,
        user_id: int
    ) -> FuturesStrategyReport:
        """创建空报告"""
        return FuturesStrategyReport(
            strategy_id=strategy_id,
            symbol=symbol,
            user_id=user_id,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            performance=self._create_empty_metrics(strategy_id, symbol, user_id, datetime.now() - timedelta(days=30), datetime.now()),
            risk_analysis=self._create_empty_risk_analysis(strategy_id, symbol)
        )