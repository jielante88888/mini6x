import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

import '../../../domain/ai_analysis/models.dart';

/// 洞察详情页面 - 展示详细的洞察分析和可视化
class InsightDetailsPage extends StatefulWidget {
  final List<AIInsight> insights;
  final String symbol;

  const InsightDetailsPage({
    Key? key,
    required this.insights,
    required this.symbol,
  }) : super(key: key);

  @override
  State<InsightDetailsPage> createState() => _InsightDetailsPageState();
}

class _InsightDetailsPageState extends State<InsightDetailsPage> 
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      appBar: AppBar(
        title: Text('洞察分析详情 - ${widget.symbol}'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.pie_chart), text: '类型分布'),
            Tab(icon: Icon(Icons.timeline), text: '趋势分析'),
            Tab(icon: Icon(Icons.bar_chart), text: '统计信息'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildTypeDistributionTab(),
          _buildTrendAnalysisTab(),
          _buildStatisticsTab(),
        ],
      ),
    );
  }

  /// 构建类型分布标签页
  Widget _buildTypeDistributionTab() {
    final typeStats = _getTypeStatistics();
    
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '洞察类型分布',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 24),
          
          // 类型分布饼图
          SizedBox(
            height: 300,
            child: PieChart(
              PieChartData(
                sections: _buildPieChartSections(typeStats),
                centerSpaceRadius: 50,
                sectionsSpace: 3,
              ),
            ),
          ),
          const SizedBox(height: 24),
          
          // 详细信息列表
          Expanded(
            child: ListView.builder(
              itemCount: typeStats.length,
              itemBuilder: (context, index) {
                final entry = typeStats.entries.elementAt(index);
                final percentage = (entry.value / widget.insights.length) * 100;
                
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: _getInsightColor(entry.key),
                      child: Icon(
                        _getInsightIcon(entry.key),
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    title: Text(_getInsightTypeText(entry.key)),
                    subtitle: Text('${entry.value}条洞察 (${percentage.toStringAsFixed(1)}%)'),
                    trailing: Icon(
                      Icons.chevron_right,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  /// 构建趋势分析标签页
  Widget _buildTrendAnalysisTab() {
    final trendData = _getTrendData();
    
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '洞察趋势分析',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 24),
          
          // 时间趋势线图
          SizedBox(
            height: 200,
            child: LineChart(
              LineChartData(
                gridData: const FlGridData(show: false),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      getTitlesWidget: (value, meta) {
                        return SideTitleWidget(
                          axisSide: meta.axisSide,
                          child: Text(
                            DateFormat('HH:mm').format(
                              DateTime.fromMillisecondsSinceEpoch(value.toInt()),
                            ),
                            style: const TextStyle(fontSize: 10),
                          ),
                        );
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      getTitlesWidget: (value, meta) {
                        return SideTitleWidget(
                          axisSide: meta.axisSide,
                          child: Text(
                            value.toInt().toString(),
                            style: const TextStyle(fontSize: 10),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: trendData,
                    isCurved: true,
                    color: Theme.of(context).colorScheme.primary,
                    barWidth: 3,
                    isStrokeCapRound: true,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: Theme.of(context)
                          .colorScheme
                          .primary
                          .withOpacity(0.1),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          
          // 洞察质量指标
          _buildQualityMetrics(),
        ],
      ),
    );
  }

  /// 构建统计信息标签页
  Widget _buildStatisticsTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '洞察统计信息',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.wbold,
            ),
          ),
          const SizedBox(height: 24),
          
          // 概览指标
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            childAspectRatio: 1.5,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
            children: [
              _buildStatCard(
                '总洞察数',
                widget.insights.length.toString(),
                Icons.lightbulb,
                Colors.blue,
              ),
              _buildStatCard(
                '平均置信度',
                '${_getAverageConfidence().toStringAsFixed(1)}%',
                Icons.trending_up,
                Colors.green,
              ),
              _buildStatCard(
                '高优先级',
                _getHighPriorityCount().toString(),
                Icons.warning,
                Colors.orange,
              ),
              _buildStatCard(
                '紧急洞察',
                _getCriticalCount().toString(),
                Icons.error,
                Colors.red,
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // 时间分布
          _buildTimeDistribution(),
        ],
      ),
    );
  }

  /// 构建统计卡片
  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    final theme = Theme.of(context);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 32,
              color: color,
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  /// 构建质量指标
  Widget _buildQualityMetrics() {
    final theme = Theme.of(context);
    final highConfidenceCount = widget.insights
        .where((insight) => insight.confidence >= 0.8)
        .length;
    final totalCount = widget.insights.length;
    final highConfidencePercentage = totalCount > 0 
        ? (highConfidenceCount / totalCount * 100)
        : 0.0;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '洞察质量指标',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('高质量洞察'),
                      Text(
                        '${highConfidenceCount}/${totalCount} (${highConfidencePercentage.toStringAsFixed(1)}%)',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.green,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 60,
                  height: 60,
                  child: CircularProgressIndicator(
                    value: highConfidencePercentage / 100,
                    backgroundColor: theme.colorScheme.surfaceVariant,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.green),
                    strokeWidth: 6,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 构建时间分布
  Widget _buildTimeDistribution() {
    final theme = Theme.of(context);
    final timeStats = _getTimeStatistics();
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '时间分布',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            ...timeStats.entries.map((entry) {
              final total = timeStats.values.reduce((a, b) => a + b);
              final percentage = (entry.value / total * 100);
              
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Text(entry.key, width: 80),
                    Expanded(
                      child: LinearProgressIndicator(
                        value: percentage / 100,
                        backgroundColor: theme.colorScheme.surfaceVariant,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          theme.colorScheme.primary,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${percentage.toStringAsFixed(1)}%',
                      width: 50,
                      textAlign: TextAlign.right,
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  // 辅助方法
  
  Map<InsightType, int> _getTypeStatistics() {
    final stats = <InsightType, int>{};
    for (final insight in widget.insights) {
      stats[insight.insightType] = (stats[insight.insightType] ?? 0) + 1;
    }
    return stats;
  }

  List<FlSpot> _getTrendData() {
    final groupedByHour = <String, List<AIInsight>>{};
    
    for (final insight in widget.insights) {
      final hourKey = DateFormat('HH').format(insight.timestamp);
      groupedByHour[hourKey] = (groupedByHour[hourKey] ?? [])..add(insight);
    }
    
    return groupedByHour.entries
        .map((entry) => FlSpot(
              double.parse(entry.key),
              entry.value.length.toDouble(),
            ))
        .toList()
      ..sort((a, b) => a.x.compareTo(b.x));
  }

  double _getAverageConfidence() {
    if (widget.insights.isEmpty) return 0.0;
    return widget.insights
            .map((insight) => insight.confidence * 100)
            .reduce((a, b) => a + b) /
        widget.insights.length;
  }

  int _getHighPriorityCount() {
    return widget.insights
        .where((insight) => 
            insight.priority == InsightPriority.high ||
            insight.priority == InsightPriority.critical)
        .length;
  }

  int _getCriticalCount() {
    return widget.insights
        .where((insight) => insight.priority == InsightPriority.critical)
        .length;
  }

  Map<String, int> _getTimeStatistics() {
    final stats = <String, int>{'今日': 0, '昨日': 0, '本周': 0, '更早': 0};
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));
    final thisWeekStart = today.subtract(Duration(days: today.weekday - 1));
    
    for (final insight in widget.insights) {
      final insightDate = DateTime(
        insight.timestamp.year,
        insight.timestamp.month,
        insight.timestamp.day,
      );
      
      if (insightDate == today) {
        stats['今日'] = (stats['今日'] ?? 0) + 1;
      } else if (insightDate == yesterday) {
        stats['昨日'] = (stats['昨日'] ?? 0) + 1;
      } else if (insightDate.isAfter(thisWeekStart)) {
        stats['本周'] = (stats['本周'] ?? 0) + 1;
      } else {
        stats['更早'] = (stats['更早'] ?? 0) + 1;
      }
    }
    
    return stats;
  }

  List<PieChartSectionData> _buildPieChartSections(Map<InsightType, int> stats) {
    return stats.entries.map((entry) {
      final total = stats.values.reduce((a, b) => a + b);
      final percentage = entry.value / total;
      
      return PieChartSectionData(
        value: entry.value.toDouble(),
        color: _getInsightColor(entry.key),
        radius: 60,
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

  // 获取洞察类型颜色
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

  // 获取洞察图标
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

  // 获取洞察类型文本
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