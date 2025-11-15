import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../domain/ai_analysis/models.dart';

/// 市场趋势卡片 - 展示市场分析结果
class MarketTrendCard extends StatelessWidget {
  final MarketInsight marketInsight;

  const MarketTrendCard({
    Key? key,
    required this.marketInsight,
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
            // 标题
            Row(
              children: [
                Icon(
                  Icons.show_chart,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '市场趋势',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 趋势状态
            _buildTrendStatus(context),
            const SizedBox(height: 16),
            
            // 置信度条
            _buildConfidenceBar(context),
            const SizedBox(height: 16),
            
            // 市场状态
            _buildMarketRegime(context),
            const SizedBox(height: 12),
            
            // 关键因素
            if (marketInsight.keyFactors.isNotEmpty) ..[
              _buildKeyFactors(context),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建趋势状态
  Widget _buildTrendStatus(BuildContext context) {
    final theme = Theme.of(context);
    final trend = marketInsight.trendDirection;
    
    Color trendColor;
    IconData trendIcon;
    String trendDescription;
    
    switch (trend) {
      case TrendDirection.strongBullish:
        trendColor = Colors.green;
        trendIcon = Icons.trending_up;
        trendDescription = '强势上涨趋势';
        break;
      case TrendDirection.bullish:
        trendColor = Colors.lightGreen;
        trendIcon = Icons.trending_up;
        trendDescription = '上涨趋势';
        break;
      case TrendDirection.neutral:
        trendColor = Colors.grey;
        trendIcon = Icons.trending_flat;
        trendDescription = '横盘整理';
        break;
      case TrendDirection.bearish:
        trendColor = Colors.orange;
        trendIcon = Icons.trending_down;
        trendDescription = '下跌趋势';
        break;
      case TrendDirection.strongBearish:
        trendColor = Colors.red;
        trendIcon = Icons.trending_down;
        trendDescription = '强势下跌趋势';
        break;
    }
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: trendColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: trendColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(
            trendIcon,
            color: trendColor,
            size: 24,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  trendDescription,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: trendColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '交易对: ${marketInsight.symbol}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 构建置信度条
  Widget _buildConfidenceBar(BuildContext context) {
    final theme = Theme.of(context);
    final confidence = marketInsight.confidence;
    final percentage = (confidence * 100).toInt();
    
    Color confidenceColor;
    if (confidence >= 0.8) {
      confidenceColor = Colors.green;
    } else if (confidence >= 0.6) {
      confidenceColor = Colors.orange;
    } else {
      confidenceColor = Colors.red;
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '分析置信度',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
            Text(
              '$percentage%',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: confidenceColor,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          height: 8,
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceVariant,
            borderRadius: BorderRadius.circular(4),
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: confidence,
            child: Container(
              decoration: BoxDecoration(
                color: confidenceColor,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// 构建市场状态
  Widget _buildMarketRegime(BuildContext context) {
    final theme = Theme.of(context);
    final regime = marketInsight.regime;
    
    Color regimeColor;
    String regimeDescription;
    
    switch (regime) {
      case MarketRegime.bullMarket:
        regimeColor = Colors.green;
        regimeDescription = '牛市环境';
        break;
      case MarketRegime.bearMarket:
        regimeColor = Colors.red;
        regimeDescription = '熊市环境';
        break;
      case MarketRegime.sideways:
        regimeColor = Colors.grey;
        regimeDescription = '横盘整理';
        break;
      case MarketRegime.highVolatility:
        regimeColor = Colors.orange;
        regimeDescription = '高波动环境';
        break;
      case MarketRegime.lowVolatility:
        regimeColor = Colors.blue;
        regimeDescription = '低波动环境';
        break;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: regimeColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: regimeColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.circle,
            size: 8,
            color: regimeColor,
          ),
          const SizedBox(width: 6),
          Text(
            regimeDescription,
            style: theme.textTheme.bodySmall?.copyWith(
              color: regimeColor,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建关键因素
  Widget _buildKeyFactors(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '关键影响因素',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: marketInsight.keyFactors
              .take(3)
              .map((factor) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      factor,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ))
              .toList(),
        ),
      ],
    );
  }
}