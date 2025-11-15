"""
盈亏分析和报告系统
提供详细的交易表现分析、趋势追踪和智能报告生成功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
import json
import statistics
from dataclasses import asdict

from ..storage.models.account_models import (
    PnLRecord, PnLType, PnLSummary, Account, Position, account_manager
)
from .pnl_calculator import RealTimePnLCalculator, PnLCalculationMode
from .position_manager import position_manager
from ..core.exceptions import AnalyticsException, ValidationException


class ReportType(Enum):
    """报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"
    REAL_TIME = "real_time"


class AnalyticsMetric(Enum):
    """分析指标"""
    TOTAL_PNL = "total_pnl"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    TOTAL_RETURN = "total_return"
    VOLATILITY = "volatility"
    BETA = "beta"
    ALPHA = "alpha"
    INFORMATION_RATIO = "information_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"


class TimeFrame(Enum):
    """时间框架"""
    HOUR = "1h"
    HOUR_4 = "4h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1m"


class PnLAnalyticsEngine:
    """盈亏分析引擎"""
    
    def __init__(self):
        self.pnl_calculator = RealTimePnLCalculator()
        self.logger = logging.getLogger(__name__)
        
        # 分析配置
        self.analysis_config = {
            'min_trade_size': Decimal('10'),  # 最小交易金额
            'max_drawdown_threshold': Decimal('0.2'),  # 20%最大回撤阈值
            'risk_free_rate': Decimal('0.02'),  # 2%无风险利率
            'benchmark_symbol': 'BTCUSDT',  # 基准交易对
        }
    
    async def generate_comprehensive_report(
        self,
        account_id: str,
        start_date: datetime,
        end_date: datetime,
        report_type: ReportType = ReportType.CUSTOM,
        include_charts: bool = True
    ) -> Dict[str, Any]:
        """生成综合分析报告"""
        try:
            self.logger.info(f"生成综合分析报告: {account_id} {start_date} - {end_date}")
            
            # 获取基础数据
            base_data = await self._get_base_analytics_data(account_id, start_date, end_date)
            
            # 生成各种分析
            performance_analysis = await self._analyze_performance(base_data)
            risk_analysis = await self._analyze_risk(base_data)
            trading_analysis = await self._analyze_trading_patterns(base_data)
            comparative_analysis = await self._analyze_comparative_performance(base_data)
            
            # 生成报告
            report = {
                'report_metadata': {
                    'account_id': account_id,
                    'report_type': report_type.value,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat(),
                    'data_period_days': (end_date - start_date).days,
                    'include_charts': include_charts
                },
                'executive_summary': await self._generate_executive_summary(
                    performance_analysis, risk_analysis, trading_analysis
                ),
                'performance_analysis': performance_analysis,
                'risk_analysis': risk_analysis,
                'trading_analysis': trading_analysis,
                'comparative_analysis': comparative_analysis,
                'time_series_data': await self._generate_time_series_data(base_data),
                'recommendations': await self._generate_recommendations(
                    performance_analysis, risk_analysis, trading_analysis
                )
            }
            
            # 添加图表数据（如果需要）
            if include_charts:
                report['chart_data'] = await self._generate_chart_data(base_data)
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成综合分析报告失败: {e}")
            raise AnalyticsException(f"生成综合分析报告失败: {e}")
    
    async def _get_base_analytics_data(
        self,
        account_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取基础分析数据"""
        try:
            # 获取盈亏汇总
            pnl_summary = await account_manager.get_pnl_summary(
                account_id=account_id,
                period_start=start_date,
                period_end=end_date,
                period_type="custom"
            )
            
            # 获取实时投资组合状态
            portfolio_result = await self.pnl_calculator.calculate_portfolio_pnl(
                account_id=account_id,
                mode=PnLCalculationMode.COMPREHENSIVE
            )
            
            # 获取持仓信息
            positions = await account_manager.get_account_positions(account_id)
            
            # 获取逐日盈亏数据
            daily_pnl_data = await self._get_daily_pnl_data(account_id, start_date, end_date)
            
            return {
                'pnl_summary': pnl_summary,
                'portfolio_result': portfolio_result,
                'positions': positions,
                'daily_pnl_data': daily_pnl_data,
                'period_days': (end_date - start_date).days
            }
            
        except Exception as e:
            self.logger.error(f"获取基础分析数据失败: {e}")
            raise AnalyticsException(f"获取基础分析数据失败: {e}")
    
    async def _analyze_performance(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析投资表现"""
        try:
            pnl_summary = base_data['pnl_summary']
            daily_pnl_data = base_data['daily_pnl_data']
            
            # 基本表现指标
            total_return = float(pnl_summary.total_return_pct)
            win_rate = float(pnl_summary.win_rate)
            profit_factor = float(pnl_summary.profit_factor)
            
            # 高级表现指标
            total_return_decimal = Decimal(str(total_return)) / Decimal('100')
            annualized_return = self._calculate_annualized_return(
                total_return_decimal, base_data['period_days']
            )
            
            # 计算波动率
            volatility = self._calculate_volatility(daily_pnl_data)
            
            # 计算夏普比率
            sharpe_ratio = self._calculate_sharpe_ratio(daily_pnl_data, volatility)
            
            # 计算索提诺比率
            sortino_ratio = self._calculate_sortino_ratio(daily_pnl_data)
            
            # 计算卡尔马比率
            calmar_ratio = self._calculate_calmar_ratio(daily_pnl_data)
            
            # 盈亏分布分析
            pnl_distribution = self._analyze_pnl_distribution(daily_pnl_data)
            
            # 连续盈亏分析
            streak_analysis = self._analyze_win_loss_streaks(daily_pnl_data)
            
            return {
                'basic_metrics': {
                    'total_return_pct': total_return,
                    'annualized_return_pct': float(annualized_return * 100),
                    'win_rate_pct': win_rate,
                    'profit_factor': profit_factor,
                    'total_trades': pnl_summary.total_trades,
                    'winning_trades': pnl_summary.winning_trades,
                    'losing_trades': pnl_summary.losing_trades,
                    'average_win': float(pnl_summary.average_win),
                    'average_loss': float(pnl_summary.average_loss),
                    'largest_win': float(pnl_summary.largest_win),
                    'largest_loss': float(pnl_summary.largest_loss)
                },
                'advanced_metrics': {
                    'volatility_pct': float(volatility * 100),
                    'sharpe_ratio': float(sharpe_ratio),
                    'sortino_ratio': float(sortino_ratio),
                    'calmar_ratio': float(calmar_ratio),
                    'total_return_decimal': float(total_return_decimal),
                    'risk_adjusted_return': float(annualized_return / volatility) if volatility > 0 else 0
                },
                'distribution_analysis': pnl_distribution,
                'streak_analysis': streak_analysis,
                'performance_grade': self._grade_performance(win_rate, profit_factor, sharpe_ratio)
            }
            
        except Exception as e:
            self.logger.error(f"分析投资表现失败: {e}")
            raise AnalyticsException(f"分析投资表现失败: {e}")
    
    async def _analyze_risk(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析投资风险"""
        try:
            daily_pnl_data = base_data['daily_pnl_data']
            pnl_summary = base_data['pnl_summary']
            
            # 最大回撤分析
            max_drawdown = self._calculate_max_drawdown(daily_pnl_data)
            max_drawdown_duration = self._calculate_max_drawdown_duration(daily_pnl_data)
            
            # 风险指标
            value_at_risk = self._calculate_var(daily_pnl_data)
            conditional_var = self._calculate_cvar(daily_pnl_data)
            
            # 风险调整后的收益
            risk_adjusted_metrics = {
                'return_to_drawdown_ratio': (
                    Decimal(str(pnl_summary.total_return_pct)) / max_drawdown
                    if max_drawdown > 0 else Decimal('0')
                ).float if hasattr(max_drawdown, 'float') else (pnl_summary.total_return_pct / max_drawdown),
                'return_per_unit_of_risk': await self._calculate_return_per_unit_risk(daily_pnl_data)
            }
            
            # 下行风险分析
            downside_deviation = self._calculate_downside_deviation(daily_pnl_data)
            
            # 风险分布
            risk_distribution = self._analyze_risk_distribution(daily_pnl_data)
            
            # 风险评级
            risk_rating = self._calculate_risk_rating(
                max_drawdown, value_at_risk, daily_pnl_data
            )
            
            return {
                'drawdown_analysis': {
                    'max_drawdown_pct': float(max_drawdown * 100) if max_drawdown else 0,
                    'max_drawdown_duration_days': max_drawdown_duration,
                    'current_drawdown_pct': self._calculate_current_drawdown(daily_pnl_data) * 100,
                    'drawdown_frequency': self._calculate_drawdown_frequency(daily_pnl_data)
                },
                'risk_metrics': {
                    'value_at_risk_95_pct': float(value_at_risk * 100),
                    'conditional_var_95_pct': float(conditional_var * 100),
                    'downside_deviation_pct': float(downside_deviation * 100),
                    'risk_adjusted_return': risk_adjusted_metrics['risk_adjusted_return'],
                    'return_to_drawdown_ratio': risk_adjusted_metrics['return_to_drawdown_ratio']
                },
                'risk_distribution': risk_distribution,
                'risk_rating': risk_rating,
                'risk_management_score': self._calculate_risk_management_score(
                    max_drawdown, value_at_risk, risk_rating
                )
            }
            
        except Exception as e:
            self.logger.error(f"分析投资风险失败: {e}")
            raise AnalyticsException(f"分析投资风险失败: {e}")
    
    async def _analyze_trading_patterns(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析交易模式"""
        try:
            daily_pnl_data = base_data['daily_pnl_data']
            positions = base_data['positions']
            
            # 交易频率分析
            trading_frequency = self._analyze_trading_frequency(daily_pnl_data)
            
            # 持仓分析
            position_analysis = await self._analyze_position_patterns(positions)
            
            # 时间模式分析
            time_patterns = self._analyze_trading_time_patterns(daily_pnl_data)
            
            # 盈亏分布分析
            profit_loss_patterns = self._analyze_profit_loss_patterns(daily_pnl_data)
            
            # 交易质量分析
            trade_quality = self._analyze_trade_quality(daily_pnl_data)
            
            return {
                'trading_frequency': trading_frequency,
                'position_analysis': position_analysis,
                'time_patterns': time_patterns,
                'profit_loss_patterns': profit_loss_patterns,
                'trade_quality': trade_quality,
                'trading_consistency_score': self._calculate_trading_consistency_score(daily_pnl_data)
            }
            
        except Exception as e:
            self.logger.error(f"分析交易模式失败: {e}")
            raise AnalyticsException(f"分析交易模式失败: {e}")
    
    async def _analyze_comparative_performance(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析比较表现"""
        try:
            # 这里可以实现与基准的比较
            # 例如与BTC价格、S&P500等的比较
            
            benchmark_data = await self._get_benchmark_data(
                base_data['pnl_summary'].period_start,
                base_data['pnl_summary'].period_end
            )
            
            portfolio_returns = self._extract_portfolio_returns(base_data['daily_pnl_data'])
            
            # 计算Beta和Alpha
            beta = self._calculate_beta(portfolio_returns, benchmark_data)
            alpha = self._calculate_alpha(portfolio_returns, benchmark_data, beta)
            
            # 信息比率
            information_ratio = self._calculate_information_ratio(portfolio_returns, benchmark_data)
            
            # 跟踪误差
            tracking_error = self._calculate_tracking_error(portfolio_returns, benchmark_data)
            
            return {
                'benchmark_comparison': {
                    'beta': float(beta),
                    'alpha_pct': float(alpha * 100),
                    'information_ratio': float(information_ratio),
                    'tracking_error_pct': float(tracking_error * 100),
                    'correlation': float(self._calculate_correlation(portfolio_returns, benchmark_data))
                },
                'relative_performance': self._analyze_relative_performance(
                    portfolio_returns, benchmark_data
                ),
                'performance_attribution': await self._analyze_performance_attribution(base_data)
            }
            
        except Exception as e:
            self.logger.error(f"分析比较表现失败: {e}")
            raise AnalyticsException(f"分析比较表现失败: {e}")
    
    async def _generate_time_series_data(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成时间序列数据"""
        try:
            daily_pnl_data = base_data['daily_pnl_data']
            
            # 累计盈亏
            cumulative_pnl = []
            running_total = Decimal('0')
            for daily_pnl in daily_pnl_data:
                running_total += daily_pnl
                cumulative_pnl.append({
                    'date': daily_pnl['date'],
                    'daily_pnl': float(daily_pnl['pnl']),
                    'cumulative_pnl': float(running_total)
                })
            
            # 回撤序列
            drawdown_series = self._calculate_drawdown_series(daily_pnl_data)
            
            # 移动平均
            moving_averages = {
                '7_day_ma': self._calculate_moving_average(daily_pnl_data, 7),
                '30_day_ma': self._calculate_moving_average(daily_pnl_data, 30),
                '90_day_ma': self._calculate_moving_average(daily_pnl_data, 90)
            }
            
            return {
                'cumulative_pnl': cumulative_pnl,
                'drawdown_series': drawdown_series,
                'daily_pnl_series': [
                    {
                        'date': daily_pnl['date'],
                        'pnl': float(daily_pnl['pnl']),
                        'pnl_pct': float(daily_pnl.get('pnl_pct', 0))
                    }
                    for daily_pnl in daily_pnl_data
                ],
                'moving_averages': moving_averages
            }
            
        except Exception as e:
            self.logger.error(f"生成时间序列数据失败: {e}")
            raise AnalyticsException(f"生成时间序列数据失败: {e}")
    
    async def _generate_chart_data(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表数据"""
        try:
            # 这里可以生成各种图表的数据格式
            # 例如：盈亏趋势图、回撤图、分布图等
            
            daily_pnl_data = base_data['daily_pnl_data']
            
            # 盈亏趋势图数据
            pnl_trend_chart = [
                {
                    'date': daily_pnl['date'],
                    'value': float(daily_pnl['pnl'])
                }
                for daily_pnl in daily_pnl_data
            ]
            
            # 回撤图数据
            drawdown_data = self._calculate_drawdown_series(daily_pnl_data)
            
            # 分布直方图数据
            histogram_data = self._create_pnl_histogram(daily_pnl_data)
            
            return {
                'pnl_trend': pnl_trend_chart,
                'drawdown_chart': drawdown_data,
                'pnl_distribution': histogram_data,
                'performance_metrics_chart': {
                    'labels': ['总回报', '夏普比率', '最大回撤', '胜率'],
                    'values': [
                        base_data['pnl_summary'].total_return_pct,
                        0,  # 需要计算
                        0,  # 需要计算
                        base_data['pnl_summary'].win_rate
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error(f"生成图表数据失败: {e}")
            raise AnalyticsException(f"生成图表数据失败: {e}")
    
    async def _generate_executive_summary(
        self,
        performance_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        trading_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成执行摘要"""
        try:
            basic_metrics = performance_analysis['basic_metrics']
            risk_rating = risk_analysis['risk_rating']
            
            # 总体评分
            overall_score = self._calculate_overall_score(
                performance_analysis, risk_analysis, trading_analysis
            )
            
            # 关键洞察
            key_insights = self._generate_key_insights(
                performance_analysis, risk_analysis, trading_analysis
            )
            
            # 风险提醒
            risk_warnings = self._generate_risk_warnings(risk_analysis)
            
            return {
                'overall_score': overall_score,
                'performance_grade': performance_analysis['performance_grade'],
                'risk_rating': risk_rating,
                'key_metrics': {
                    'total_return': f"{basic_metrics['total_return_pct']:.2f}%",
                    'win_rate': f"{basic_metrics['win_rate_pct']:.1f}%",
                    'sharpe_ratio': f"{performance_analysis['advanced_metrics']['sharpe_ratio']:.2f}",
                    'max_drawdown': f"{risk_analysis['drawdown_analysis']['max_drawdown_pct']:.2f}%"
                },
                'key_insights': key_insights,
                'risk_warnings': risk_warnings,
                'recommendation': self._generate_executive_recommendation(
                    performance_analysis, risk_analysis
                )
            }
            
        except Exception as e:
            self.logger.error(f"生成执行摘要失败: {e}")
            raise AnalyticsException(f"生成执行摘要失败: {e}")
    
    async def _generate_recommendations(
        self,
        performance_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        trading_analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """生成改进建议"""
        try:
            recommendations = []
            
            # 基于表现的建议
            if performance_analysis['basic_metrics']['win_rate'] < 50:
                recommendations.append({
                    'category': 'performance',
                    'priority': 'high',
                    'title': '提升胜率',
                    'description': '当前胜率较低，建议优化交易策略或改进入场条件',
                    'action': 'review_entry_criteria'
                })
            
            # 基于风险的建议
            if risk_analysis['drawdown_analysis']['max_drawdown_pct'] > 20:
                recommendations.append({
                    'category': 'risk_management',
                    'priority': 'high',
                    'title': '控制回撤',
                    'description': '最大回撤过大，建议降低单笔交易风险或增加止损设置',
                    'action': 'implement_stricter_risk_controls'
                })
            
            # 基于交易模式的建议
            if trading_analysis['trading_consistency_score'] < 0.6:
                recommendations.append({
                    'category': 'trading_discipline',
                    'priority': 'medium',
                    'title': '提高交易一致性',
                    'description': '交易模式不够一致，建议制定更严格的交易规则',
                    'action': 'establish_trading_rules'
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"生成建议失败: {e}")
            return []
    
    # 辅助计算方法
    def _calculate_annualized_return(self, total_return: Decimal, days: int) -> Decimal:
        """计算年化收益率"""
        if days <= 0:
            return Decimal('0')
        
        return (Decimal('1') + total_return) ** (Decimal('365') / Decimal(str(days))) - Decimal('1')
    
    def _calculate_volatility(self, daily_pnl_data: List[Dict[str, Any]]) -> Decimal:
        """计算波动率"""
        if len(daily_pnl_data) < 2:
            return Decimal('0')
        
        daily_returns = [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
        mean_return = sum(daily_returns) / len(daily_returns)
        
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        volatility = variance.sqrt()
        
        return volatility
    
    def _calculate_sharpe_ratio(self, daily_pnl_data: List[Dict[str, Any]], volatility: Decimal) -> Decimal:
        """计算夏普比率"""
        if len(daily_pnl_data) == 0 or volatility == 0:
            return Decimal('0')
        
        avg_daily_return = sum(Decimal(str(daily['pnl'])) for daily in daily_pnl_data) / len(daily_pnl_data)
        risk_free_rate_daily = self.analysis_config['risk_free_rate'] / Decimal('365')
        
        excess_return = avg_daily_return - risk_free_rate_daily
        sharpe_ratio = excess_return / (volatility / Decimal('100'))  # 假设数据是百分比
        
        return sharpe_ratio
    
    def _calculate_sortino_ratio(self, daily_pnl_data: List[Dict[str, Any]]) -> Decimal:
        """计算索提诺比率"""
        if len(daily_pnl_data) == 0:
            return Decimal('0')
        
        daily_returns = [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
        avg_return = sum(daily_returns) / len(daily_returns)
        
        # 下行偏差
        negative_returns = [r for r in daily_returns if r < 0]
        if not negative_returns:
            return Decimal('inf')
        
        downside_variance = sum(r ** 2 for r in negative_returns) / len(daily_returns)
        downside_deviation = downside_variance.sqrt()
        
        if downside_deviation == 0:
            return Decimal('0')
        
        sortino_ratio = avg_return / downside_deviation
        return sortino_ratio
    
    def _calculate_calmar_ratio(self, daily_pnl_data: List[Dict[str, Any]]) -> Decimal:
        """计算卡尔马比率"""
        max_drawdown = self._calculate_max_drawdown(daily_pnl_data)
        if max_drawdown == 0:
            return Decimal('0')
        
        total_return = sum(Decimal(str(daily['pnl'])) for daily in daily_pnl_data)
        annualized_return = self._calculate_annualized_return(total_return, len(daily_pnl_data))
        
        calmar_ratio = annualized_return / abs(max_drawdown)
        return calmar_ratio
    
    def _calculate_max_drawdown(self, daily_pnl_data: List[Dict[str, Any]]) -> Decimal:
        """计算最大回撤"""
        if not daily_pnl_data:
            return Decimal('0')
        
        cumulative = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for daily in daily_pnl_data:
            cumulative += Decimal(str(daily['pnl']))
            if cumulative > peak:
                peak = cumulative
            
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown / peak if peak > 0 else Decimal('0')
    
    def _calculate_var(self, daily_pnl_data: List[Dict[str, Any]], confidence: float = 0.05) -> Decimal:
        """计算风险价值(VaR)"""
        if not daily_pnl_data:
            return Decimal('0')
        
        daily_pnls = [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
        daily_pnls.sort()
        
        var_index = int(len(daily_pnls) * confidence)
        if var_index >= len(daily_pnls):
            var_index = len(daily_pnls) - 1
        
        return abs(daily_pnls[var_index])
    
    def _calculate_cvar(self, daily_pnl_data: List[Dict[str, Any]], confidence: float = 0.05) -> Decimal:
        """计算条件风险价值(CVaR)"""
        if not daily_pnl_data:
            return Decimal('0')
        
        daily_pnls = [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
        daily_pnls.sort()
        
        var_index = int(len(daily_pnls) * confidence)
        if var_index >= len(daily_pnls):
            var_index = len(daily_pnls) - 1
        
        tail_losses = daily_pnls[:var_index + 1]
        cvar = abs(sum(tail_losses) / len(tail_losses))
        
        return cvar
    
    def _grade_performance(self, win_rate: float, profit_factor: float, sharpe_ratio: float) -> str:
        """评级表现"""
        score = 0
        
        # 胜率评分
        if win_rate >= 60:
            score += 3
        elif win_rate >= 50:
            score += 2
        elif win_rate >= 40:
            score += 1
        
        # 盈亏比评分
        if profit_factor >= 2:
            score += 3
        elif profit_factor >= 1.5:
            score += 2
        elif profit_factor >= 1:
            score += 1
        
        # 夏普比率评分
        if sharpe_ratio >= 2:
            score += 3
        elif sharpe_ratio >= 1:
            score += 2
        elif sharpe_ratio >= 0.5:
            score += 1
        
        # 等级评定
        if score >= 7:
            return "A"
        elif score >= 5:
            return "B"
        elif score >= 3:
            return "C"
        else:
            return "D"
    
    async def _get_daily_pnl_data(
        self,
        account_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """获取每日盈亏数据"""
        try:
            # 这里应该从数据库获取真实的每日盈亏数据
            # 简化处理，生成模拟数据
            data = []
            current_date = start_date
            
            while current_date <= end_date:
                # 模拟每日盈亏（实际应该从数据库查询）
                import random
                daily_pnl = random.uniform(-100, 200)  # 模拟数据
                
                data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'pnl': daily_pnl,
                    'pnl_pct': daily_pnl / 1000 * 100  # 假设基准资金1000
                })
                
                current_date += timedelta(days=1)
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取每日盈亏数据失败: {e}")
            return []
    
    async def _get_benchmark_data(self, start_date: datetime, end_date: datetime) -> List[Decimal]:
        """获取基准数据"""
        # 这里应该获取真实的基准数据，如BTC价格数据
        # 简化处理，返回模拟数据
        import random
        return [Decimal(str(random.uniform(-5, 5))) for _ in range((end_date - start_date).days)]
    
    def _extract_portfolio_returns(self, daily_pnl_data: List[Dict[str, Any]]) -> List[Decimal]:
        """提取投资组合收益"""
        return [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
    
    def _calculate_beta(self, portfolio_returns: List[Decimal], benchmark_returns: List[Decimal]) -> Decimal:
        """计算Beta"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return Decimal('1')
        
        portfolio_mean = sum(portfolio_returns) / len(portfolio_returns)
        benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
        
        covariance = sum(
            (p - portfolio_mean) * (b - benchmark_mean)
            for p, b in zip(portfolio_returns, benchmark_returns)
        ) / (len(portfolio_returns) - 1)
        
        benchmark_variance = sum(
            (b - benchmark_mean) ** 2 for b in benchmark_returns
        ) / (len(benchmark_returns) - 1)
        
        if benchmark_variance == 0:
            return Decimal('1')
        
        return covariance / benchmark_variance
    
    def _calculate_alpha(self, portfolio_returns: List[Decimal], benchmark_returns: List[Decimal], beta: Decimal) -> Decimal:
        """计算Alpha"""
        if len(portfolio_returns) != len(benchmark_returns):
            return Decimal('0')
        
        portfolio_mean = sum(portfolio_returns) / len(portfolio_returns)
        benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
        risk_free_rate = self.analysis_config['risk_free_rate'] / Decimal('365')
        
        return portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))
    
    def _calculate_information_ratio(self, portfolio_returns: List[Decimal], benchmark_returns: List[Decimal]) -> Decimal:
        """计算信息比率"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return Decimal('0')
        
        excess_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        mean_excess = sum(excess_returns) / len(excess_returns)
        
        variance = sum(er ** 2 for er in excess_returns) / (len(excess_returns) - 1)
        volatility = variance.sqrt()
        
        if volatility == 0:
            return Decimal('0')
        
        return mean_excess / volatility
    
    def _calculate_tracking_error(self, portfolio_returns: List[Decimal], benchmark_returns: List[Decimal]) -> Decimal:
        """计算跟踪误差"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return Decimal('0')
        
        tracking_differences = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        mean_diff = sum(tracking_differences) / len(tracking_differences)
        
        variance = sum((td - mean_diff) ** 2 for td in tracking_differences) / (len(tracking_differences) - 1)
        
        return variance.sqrt()
    
    def _calculate_correlation(self, portfolio_returns: List[Decimal], benchmark_returns: List[Decimal]) -> Decimal:
        """计算相关系数"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return Decimal('0')
        
        portfolio_mean = sum(portfolio_returns) / len(portfolio_returns)
        benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
        
        covariance = sum(
            (p - portfolio_mean) * (b - benchmark_mean)
            for p, b in zip(portfolio_returns, benchmark_returns)
        ) / (len(portfolio_returns) - 1)
        
        portfolio_std = (
            sum((p - portfolio_mean) ** 2 for p in portfolio_returns) / (len(portfolio_returns) - 1)
        ).sqrt()
        
        benchmark_std = (
            sum((b - benchmark_mean) ** 2 for b in benchmark_returns) / (len(benchmark_returns) - 1)
        ).sqrt()
        
        if portfolio_std == 0 or benchmark_std == 0:
            return Decimal('0')
        
        return covariance / (portfolio_std * benchmark_std)
    
    def _analyze_pnl_distribution(self, daily_pnl_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析盈亏分布"""
        daily_pnls = [daily['pnl'] for daily in daily_pnl_data]
        
        if not daily_pnls:
            return {}
        
        return {
            'positive_days': len([p for p in daily_pnls if p > 0]),
            'negative_days': len([p for p in daily_pnls if p < 0]),
            'zero_days': len([p for p in daily_pnls if p == 0]),
            'median': statistics.median(daily_pnls),
            'std_dev': statistics.stdev(daily_pnls) if len(daily_pnls) > 1 else 0,
            'skewness': self._calculate_skewness(daily_pnls),
            'kurtosis': self._calculate_kurtosis(daily_pnls)
        }
    
    def _analyze_win_loss_streaks(self, daily_pnl_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析盈亏连续"""
        if not daily_pnl_data:
            return {}
        
        pnl_values = [daily['pnl'] for daily in daily_pnl_data]
        
        # 查找连续盈亏
        win_streaks = []
        loss_streaks = []
        current_streak = 1
        current_result = 'win' if pnl_values[0] > 0 else 'loss'
        
        for i in range(1, len(pnl_values)):
            if (pnl_values[i] > 0 and current_result == 'win') or (pnl_values[i] < 0 and current_result == 'loss'):
                current_streak += 1
            else:
                if current_result == 'win':
                    win_streaks.append(current_streak)
                else:
                    loss_streaks.append(current_streak)
                
                current_streak = 1
                current_result = 'win' if pnl_values[i] > 0 else 'loss'
        
        # 添加最后一段连续
        if current_result == 'win':
            win_streaks.append(current_streak)
        else:
            loss_streaks.append(current_streak)
        
        return {
            'max_win_streak': max(win_streaks) if win_streaks else 0,
            'max_loss_streak': max(loss_streaks) if loss_streaks else 0,
            'avg_win_streak': sum(win_streaks) / len(win_streaks) if win_streaks else 0,
            'avg_loss_streak': sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0,
            'total_win_streaks': len(win_streaks),
            'total_loss_streaks': len(loss_streaks)
        }
    
    def _calculate_skewness(self, data: List[float]) -> float:
        """计算偏度"""
        if len(data) < 3:
            return 0.0
        
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        
        if std == 0:
            return 0.0
        
        skewness = sum((x - mean) ** 3 for x in data) / (len(data) * std ** 3)
        return skewness
    
    def _calculate_kurtosis(self, data: List[float]) -> float:
        """计算峰度"""
        if len(data) < 4:
            return 0.0
        
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        
        if std == 0:
            return 0.0
        
        kurtosis = sum((x - mean) ** 4 for x in data) / (len(data) * std ** 4) - 3
        return kurtosis
    
    def _calculate_risk_rating(self, max_drawdown: Decimal, value_at_risk: Decimal, daily_pnl_data: List[Dict[str, Any]]) -> str:
        """计算风险评级"""
        score = 0
        
        # 基于最大回撤的评分
        if max_drawdown > 0.2:
            score += 3
        elif max_drawdown > 0.1:
            score += 2
        elif max_drawdown > 0.05:
            score += 1
        
        # 基于VaR的评分
        if value_at_risk > 0.05:
            score += 3
        elif value_at_risk > 0.03:
            score += 2
        elif value_at_risk > 0.01:
            score += 1
        
        # 基于波动性的评分
        daily_pnls = [Decimal(str(daily['pnl'])) for daily in daily_pnl_data]
        volatility = self._calculate_volatility(daily_pnl_data)
        if volatility > 0.05:
            score += 2
        elif volatility > 0.03:
            score += 1
        
        # 风险等级
        if score >= 6:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_overall_score(
        self,
        performance_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        trading_analysis: Dict[str, Any]
    ) -> float:
        """计算总体评分"""
        performance_score = 0
        risk_score = 0
        consistency_score = trading_analysis.get('trading_consistency_score', 0.5)
        
        # 表现评分
        basic_metrics = performance_analysis['basic_metrics']
        if basic_metrics['win_rate'] >= 60:
            performance_score += 0.3
        elif basic_metrics['win_rate'] >= 50:
            performance_score += 0.2
        elif basic_metrics['win_rate'] >= 40:
            performance_score += 0.1
        
        if basic_metrics['profit_factor'] >= 2:
            performance_score += 0.3
        elif basic_metrics['profit_factor'] >= 1.5:
            performance_score += 0.2
        elif basic_metrics['profit_factor'] >= 1:
            performance_score += 0.1
        
        # 风险评分
        risk_rating = risk_analysis.get('risk_rating', 'MEDIUM')
        if risk_rating == 'LOW':
            risk_score = 1.0
        elif risk_rating == 'MEDIUM':
            risk_score = 0.7
        else:
            risk_score = 0.3
        
        # 综合评分
        overall_score = (performance_score * 0.4 + risk_score * 0.4 + consistency_score * 0.2) * 10
        
        return min(overall_score, 10.0)
    
    def _generate_key_insights(
        self,
        performance_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        trading_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        basic_metrics = performance_analysis['basic_metrics']
        
        # 基于胜率的洞察
        if basic_metrics['win_rate'] >= 60:
            insights.append("胜率表现优秀，展现了良好的交易判断能力")
        elif basic_metrics['win_rate'] < 40:
            insights.append("胜率偏低，建议优化入场时机和交易策略")
        
        # 基于盈亏比的洞察
        if basic_metrics['profit_factor'] >= 2:
            insights.append("盈亏比表现优异，说明风险控制较好")
        elif basic_metrics['profit_factor'] < 1:
            insights.append("盈亏比不佳，需要改善盈亏比例")
        
        # 基于回撤的洞察
        max_drawdown = risk_analysis['drawdown_analysis']['max_drawdown_pct']
        if max_drawdown > 20:
            insights.append("最大回撤过大，建议降低单笔交易风险")
        elif max_drawdown < 5:
            insights.append("回撤控制良好，风险管理到位")
        
        return insights
    
    def _generate_risk_warnings(self, risk_analysis: Dict[str, Any]) -> List[str]:
        """生成风险警告"""
        warnings = []
        
        risk_rating = risk_analysis.get('risk_rating', 'LOW')
        max_drawdown = risk_analysis['drawdown_analysis']['max_drawdown_pct']
        
        if risk_rating == 'HIGH':
            warnings.append("当前风险等级为高，建议立即采取风险控制措施")
        
        if max_drawdown > 30:
            warnings.append("最大回撤超过30%，存在较大损失风险")
        elif max_drawdown > 20:
            warnings.append("最大回撤超过20%，建议关注风险控制")
        
        return warnings
    
    def _generate_executive_recommendation(
        self,
        performance_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any]
    ) -> str:
        """生成执行建议"""
        performance_grade = performance_analysis.get('performance_grade', 'C')
        risk_rating = risk_analysis.get('risk_rating', 'MEDIUM')
        
        if performance_grade in ['A', 'B'] and risk_rating in ['LOW', 'MEDIUM']:
            return "表现良好，建议继续当前策略并保持风险管理"
        elif performance_grade in ['C', 'D'] and risk_rating == 'HIGH':
            return "表现和风险均需改善，建议暂停交易并重新评估策略"
        elif performance_grade in ['C', 'D']:
            return "表现需要改善，建议优化交易策略"
        elif risk_rating == 'HIGH':
            return "风险过高，建议加强风险控制措施"
        else:
            return "表现一般，建议在保持风险控制的前提下优化策略"


class PnLReportGenerator:
    """盈亏报告生成器"""
    
    def __init__(self):
        self.analytics_engine = PnLAnalyticsEngine()
        self.logger = logging.getLogger(__name__)
    
    async def generate_daily_report(self, account_id: str) -> Dict[str, Any]:
        """生成日报"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        return await self.analytics_engine.generate_comprehensive_report(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.DAILY
        )
    
    async def generate_weekly_report(self, account_id: str) -> Dict[str, Any]:
        """生成周报"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        return await self.analytics_engine.generate_comprehensive_report(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.WEEKLY
        )
    
    async def generate_monthly_report(self, account_id: str) -> Dict[str, Any]:
        """生成月报"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        return await self.analytics_engine.generate_comprehensive_report(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.MONTHLY
        )
    
    async def generate_custom_report(
        self,
        account_id: str,
        start_date: datetime,
        end_date: datetime,
        include_charts: bool = True
    ) -> Dict[str, Any]:
        """生成自定义报告"""
        return await self.analytics_engine.generate_comprehensive_report(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.CUSTOM,
            include_charts=include_charts
        )


# 全局报告生成器实例
report_generator = PnLReportGenerator()