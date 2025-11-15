import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../domain/ai_analysis/models.dart';
import 'insight_details_page.dart';

/// 洞察列表 - 显示AI生成的洞察和建议
class InsightsList extends StatelessWidget {
  final List<AIInsight> insights;
  final String symbol;

  const InsightsList({
    Key? key,
    required this.insights,
    required this.symbol,
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
                  Icons.lightbulb,
                  color: theme.colorScheme.tertiary,
                ),
                const SizedBox(width: 8),
                Text(
                  'AI洞察 ($symbol)',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${insights.length}条洞察',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.analytics),
                      onPressed: () => _navigateToDetails(context),
                      tooltip: '查看详细分析',
                      iconSize: 20,
                      constraints: const BoxConstraints(
                        minWidth: 32,
                        minHeight: 32,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 洞察统计图表
          _buildInsightsStatsChart(context),
          const SizedBox(height: 16),
          
          // 洞察列表
            if (insights.isEmpty)
              _buildEmptyState(context)
            else
              ...insights.map((insight) => 
                _buildInsightCard(context, insight)
              ).toList(),
          ],
        ),
      ),
    );
  }

  /// 构建空状态
  Widget _buildEmptyState(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(32),
      child: Column(
        children: [
          Icon(
            Icons.inbox_outlined,
            size: 48,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            '暂无洞察数据',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'AI分析引擎正在生成洞察，请稍候...',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  /// 构建洞察卡片
  Widget _buildInsightCard(BuildContext context, AIInsight insight) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _getInsightColor(insight.insightType).withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _getInsightColor(insight.insightType).withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题和优先级
          Row(
            children: [
              Expanded(
                child: Text(
                  insight.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              _buildPriorityChip(context, insight.priority),
            ],
          ),
          const SizedBox(height: 8),
          
          // 描述
          Text(
            insight.summary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              height: 1.4,
            ),
          ),
          const SizedBox(height: 8),
          
          // 置信度和类型
          Row(
            children: [
              Icon(
                _getInsightIcon(insight.insightType),
                size: 16,
                color: _getInsightColor(insight.insightType),
              ),
              const SizedBox(width: 4),
              Text(
                _getInsightTypeText(insight.insightType),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: _getInsightColor(insight.insightType),
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              Text(
                '置信度: ${(insight.confidence * 100).toStringAsFixed(0)}%',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: _getInsightColor(insight.insightType),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          
          // 建议操作
          if (insight.recommendations.isNotVisible) ...[
            _buildRecommendations(context, insight.recommendations),
            const SizedBox(height: 8),
          ],
          
          // 时间和标签
          Row(
            children: [
              Icon(
                Icons.access_time,
                size: 12,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 4),
              Text(
                DateFormat('HH:mm').format(insight.timestamp),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const Spacer(),
              if (insight.tags.isNotEmpty)
                _buildTags(context, insight.tags.take(2).toList()),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建优先级芯片
  Widget _buildPriorityChip(BuildContext context, InsightPriority priority) {
    Color chipColor;
    String chipText;
    
    switch (priority) {
      case InsightPriority.critical:
        chipColor = Colors.red;
        chipText = '紧急';
        break;
      case InsightPriority.high:
        chipColor = Colors.orange;
        chipText = '重要';
        break;
      case InsightPriority.medium:
        chipColor = Colors.blue;
        chipText = '中等';
        break;
      case InsightPriority.low:
        chipColor = Colors.green;
        chipText = '低';
        break;
      case InsightPriority.info:
        chipColor = Colors.grey;
        chipText = '信息';
        break;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: chipColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: chipColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Text(
        chipText,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: chipColor,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  /// 构建建议操作
  Widget _buildRecommendations(BuildContext context, List<String> recommendations) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '建议操作:',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        ...recommendations.take(3).map((recommendation) => Padding(
          padding: const EdgeInsets.only(left: 16, bottom: 2),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '• ',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              Expanded(
                child: Text(
                  recommendation,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
        )),
        if (recommendations.length > 3)
          Text(
            '...以及其他建议',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
      ],
    );
  }

  /// 导航到洞察详情页面
  void _navigateToDetails(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => InsightDetailsPage(
          insights: insights,
          symbol: symbol,
        ),
      ),
    );
  }

  /// 构建标签
  Widget _buildTags(BuildContext context, List<String> tags) {
    return Wrap(
      spacing: 4,
      runSpacing: 2,
      children: tags.map((tag) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          tag,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            fontSize: 10,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      )).toList(),
    );
  }

  /// 获取洞察类型颜色
  Color _getInsightColor(InsightType type) {
    switch (type) {
      case InsightType.marketTrend:
        return Colors.blue;
      case InsightType.tradingSignal:
        return Colors.green;
      case InsightType.riskAlert:
        return Colors.red;
      case InsightType.opportunity:
        return Colors.orange;
      case InsightType.performance:
        return Colors.purple;
      case InsightType.strategy:
        return Colors.indigo;
      case InsightType.system:
        return Colors.grey;
    }
  }

  /// 获取洞察图标
  IconData _getInsightIcon(InsightType type) {
    switch (type) {
      case InsightType.marketTrend:
        return Icons.trending_up;
      case InsightType.tradingSignal:
        return Icons.signal_cellular_alt;
      case InsightType.riskAlert:
        return Icons.warning;
      case InsightType.opportunity:
        return Icons.lightbulb;
      case InsightType.performance:
        return Icons.analytics;
      case InsightType.strategy:
        return Icons.tune;
      case InsightType.system:
        return Icons.settings;
    }
  }

  /// 获取洞察类型文本
  String _getInsightTypeText(InsightType type) {
    switch (type) {
      case InsightType.marketTrend:
        return '市场趋势';
      case InsightType.tradingSignal:
        return '交易信号';
      case InsightType.riskAlert:
        return '风险警告';
      case InsightType.opportunity:
        return '投资机会';
      case InsightType.performance:
        return '性能分析';
      case InsightType.strategy:
        return '策略优化';
      case InsightType.system:
        return '系统信息';
    }
  }
}

  /// 构建洞察统计图表
  Widget _buildInsightsStatsChart(BuildContext context) {
    final theme = Theme.of(context);
    
    if (insights.isEmpty) {
      return const SizedBox.shrink();
    }
    
    // 统计各类洞察数量
    final typeStats = <InsightType, int>{};
    final priorityStats = <InsightPriority, int>{};
    
    for (final insight in insights) {
      typeStats[insight.insightType] = (typeStats[insight.insightType] ?? 0) + 1;
      priorityStats[insight.priority] = (priorityStats[insight.priority] ?? 0) + 1;
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '洞察分布统计',
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        
        // 类型分布饼图
        SizedBox(
          height: 120,
          child: Row(
            children: [
              Expanded(
                child: PieChart(
                  PieChartData(
                    sections: _buildPieChartSections(typeStats),
                    centerSpaceRadius: 30,
                    sectionsSpace: 2,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              // 图例
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: typeStats.entries.take(4).map((entry) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              color: _getInsightColor(entry.key),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              '${_getInsightTypeText(entry.key)} (${entry.value})',
                              style: theme.textTheme.bodySmall,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        
        // 优先级分布条形图
        _buildPriorityDistributionChart(context, priorityStats),
      ],
    );
  }

  /// 构建饼图部分
  List<PieChartSectionData> _buildPieChartSections(Map<InsightType, int> stats) {
    return stats.entries.map((entry) {
      final total = stats.values.reduce((a, b) => a + b);
      final percentage = entry.value / total;
      
      return PieChartSectionData(
        value: entry.value.toDouble(),
        color: _getInsightColor(entry.key),
        radius: 40,
        title: '${(percentage * 100).toInt()}%',
        titleStyle: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
        titlePositionPercentageOffset: 0.5,
      );
    }).toList();
  }

  /// 构建优先级分布图表
  Widget _buildPriorityDistributionChart(BuildContext context, Map<InsightPriority, int> stats) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '优先级分布',
          style: theme.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        
        // 计算最大值用于标准化
        final maxCount = stats.values.isNotEmpty ? stats.values.reduce(math.max) : 1;
        
        ...stats.entries.map((entry) {
          final percentage = entry.value / maxCount;
          
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _getPriorityText(entry.key),
                      style: theme.textTheme.bodySmall,
                    ),
                    Text(
                      '${entry.value}条',
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Container(
                  height: 6,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  child: FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: percentage,
                    child: Container(
                      decoration: BoxDecoration(
                        color: _getPriorityColor(entry.key),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  /// 获取优先级文本
  String _getPriorityText(InsightPriority priority) {
    switch (priority) {
      case InsightPriority.critical:
        return '紧急';
      case InsightPriority.high:
        return '重要';
      case InsightPriority.medium:
        return '中等';
      case InsightPriority.low:
        return '低';
      case InsightPriority.info:
        return '信息';
    }
  }

  /// 获取优先级颜色
  Color _getPriorityColor(InsightPriority priority) {
    switch (priority) {
      case InsightPriority.critical:
        return Colors.red;
      case InsightPriority.high:
        return Colors.orange;
      case InsightPriority.medium:
        return Colors.blue;
      case InsightPriority.low:
        return Colors.green;
      case InsightPriority.info:
        return Colors.grey;
    }
  }

  /// 扩展：为可空的list添加isNotEmpty方法
  extension on List {
    bool get isNotEmpty => !isEmpty;
  }
}

// 添加数学库导入
import 'dart:math' as math;