import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../domain/ai_analysis/models.dart';

/// 分析概览卡片 - 显示整体分析状态和关键指标
class AnalysisOverviewCard extends StatelessWidget {
  final AIAnalysis analysis;

  const AnalysisOverviewCard({
    Key? key,
    required this.analysis,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题和状态
            Row(
              children: [
                Icon(
                  Icons.psychology,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'AI分析概览',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                _buildOverallConfidenceChip(theme),
              ],
            ),
            const SizedBox(height: 16),
            
            // 关键指标
            Row(
              children: [
                Expanded(
                  child: _buildMetricTile(
                    context,
                    '整体置信度',
                    '${(analysis.marketInsight.confidence * 100).toStringAsFixed(1)}%',
                    _getConfidenceColor(analysis.marketInsight.confidence),
                    Icons.trending_up,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildMetricTile(
                    context,
                    '信号强度',
                    _getSignalStrengthText(analysis.signalInsight.signalStrength),
                    _getSignalStrengthColor(analysis.signalInsight.signalStrength),
                    Icons.speed,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildMetricTile(
                    context,
                    '市场状态',
                    _getMarketRegimeText(analysis.marketInsight.regime),
                    _getMarketRegimeColor(analysis.marketInsight.regime),
                    Icons.show_chart,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 趋势和信号摘要
            _buildTrendSignalRow(context),
            const SizedBox(height: 12),
            
            // 更新时间
            Row(
              children: [
                Icon(
                  Icons.access_time,
                  size: 16,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  '更新时间: ${DateFormat('yyyy-MM-dd HH:mm').format(analysis.timestamp)}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                _buildAnalysisStatusChip(theme),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 构建指标卡片
  Widget _buildMetricTile(BuildContext context, String title, String value, 
                          Color color, IconData icon) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                icon,
                size: 20,
                color: color,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建趋势和信号行
  Widget _buildTrendSignalRow(BuildContext context) {
    final theme = Theme.of(context);
    
    return Row(
      children: [
        // 市场趋势
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              children: [
                Icon(
                  _getTrendIcon(analysis.marketInsight.trendDirection),
                  size: 16,
                  color: theme.colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '趋势: ${_getTrendText(analysis.marketInsight.trendDirection)}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        // 主要信号
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _getSignalColor(analysis.signalInsight.primarySignal),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              children: [
                Icon(
                  _getSignalIcon(analysis.signalInsight.primarySignal),
                  size: 16,
                  color: Colors.white,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '信号: ${_getSignalText(analysis.signalInsight.primarySignal)}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  /// 构建置信度状态芯片
  Widget _buildOverallConfidenceChip(ThemeData theme) {
    final confidence = (analysis.marketInsight.confidence + analysis.signalInsight.confidence) / 2;
    final color = _getConfidenceColor(confidence);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.verified,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            '${(confidence * 100).toStringAsFixed(0)}%',
            style: theme.textTheme.bodySmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建分析状态芯片
  Widget _buildAnalysisStatusChip(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.green.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.green.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.check_circle,
            size: 14,
            color: Colors.green,
          ),
          const SizedBox(width: 4),
          Text(
            '分析完成',
            style: theme.textTheme.bodySmall?.copyWith(
              color: Colors.green,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 获取置信度颜色
  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    return Colors.red;
  }

  /// 获取信号强度文本
  String _getSignalStrengthText(SignalStrength strength) {
    switch (strength) {
      case SignalStrength.veryStrong:
        return '极强';
      case SignalStrength.strong:
        return '强';
      case SignalStrength.moderate:
        return '中等';
      case SignalStrength.weak:
        return '弱';
      case SignalStrength.veryWeak:
        return '极弱';
    }
  }

  /// 获取信号强度颜色
  Color _getSignalStrengthColor(SignalStrength strength) {
    switch (strength) {
      case SignalStrength.veryStrong:
        return Colors.green;
      case SignalStrength.strong:
        return Colors.lightGreen;
      case SignalStrength.moderate:
        return Colors.orange;
      case SignalStrength.weak:
        return Colors.redAccent;
      case SignalStrength.veryWeak:
        return Colors.red;
    }
  }

  /// 获取市场状态文本
  String _getMarketRegimeText(MarketRegime regime) {
    switch (regime) {
      case MarketRegime.bullMarket:
        return '牛市';
      case MarketRegime.bearMarket:
        return '熊市';
      case MarketRegime.sideways:
        return '横盘';
      case MarketRegime.highVolatility:
        return '高波动';
      case MarketRegime.lowVolatility:
        return '低波动';
    }
  }

  /// 获取市场状态颜色
  Color _getMarketRegimeColor(MarketRegime regime) {
    switch (regime) {
      case MarketRegime.bullMarket:
        return Colors.green;
      case MarketRegime.bearMarket:
        return Colors.red;
      case MarketRegime.sideways:
        return Colors.grey;
      case MarketRegime.highVolatility:
        return Colors.orange;
      case MarketRegime.lowVolatility:
        return Colors.blue;
    }
  }

  /// 获取趋势图标
  IconData _getTrendIcon(TrendDirection trend) {
    switch (trend) {
      case TrendDirection.strongBullish:
        return Icons.trending_up;
      case TrendDirection.bullish:
        return Icons.trending_up;
      case TrendDirection.neutral:
        return Icons.trending_flat;
      case TrendDirection.bearish:
        return Icons.trending_down;
      case TrendDirection.strongBearish:
        return Icons.trending_down;
    }
  }

  /// 获取趋势文本
  String _getTrendText(TrendDirection trend) {
    switch (trend) {
      case TrendDirection.strongBullish:
        return '强势上涨';
      case TrendDirection.bullish:
        return '上涨';
      case TrendDirection.neutral:
        return '横盘';
      case TrendDirection.bearish:
        return '下跌';
      case TrendDirection.strongBearish:
        return '强势下跌';
    }
  }

  /// 获取信号图标
  IconData _getSignalIcon(SignalType signal) {
    switch (signal) {
      case SignalType.buy:
        return Icons.arrow_upward;
      case SignalType.sell:
        return Icons.arrow_downward;
      case SignalType.hold:
        return Icons.pause;
      case SignalType.weakBuy:
        return Icons.keyboard_arrow_up;
      case SignalType.weakSell:
        return Icons.keyboard_arrow_down;
    }
  }

  /// 获取信号文本
  String _getSignalText(SignalType signal) {
    switch (signal) {
      case SignalType.buy:
        return '买入';
      case SignalType.sell:
        return '卖出';
      case SignalType.hold:
        return '持有';
      case SignalType.weakBuy:
        return '谨慎买入';
      case SignalType.weakSell:
        return '谨慎卖出';
    }
  }

  /// 获取信号颜色
  Color _getSignalColor(SignalType signal) {
    switch (signal) {
      case SignalType.buy:
        return Colors.green;
      case SignalType.sell:
        return Colors.red;
      case SignalType.hold:
        return Colors.grey;
      case SignalType.weakBuy:
        return Colors.lightGreen;
      case SignalType.weakSell:
        return Colors.orangeAccent;
    }
  }
}