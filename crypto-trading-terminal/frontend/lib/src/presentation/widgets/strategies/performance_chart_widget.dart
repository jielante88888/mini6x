import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

import '../../providers/strategy_provider.dart';

/// 性能图表类型
enum ChartType {
  pnl('pnl', '盈亏曲线'),
  drawdown('drawdown', '回撤'),
  returns('returns', '收益率'),
  winRate('winRate', '胜率'),
  trades('trades', '交易次数');

  const ChartType(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 性能图表组件
class PerformanceChartWidget extends StatelessWidget {
  final String strategyId;
  final ChartType chartType;
  final List<StrategyPerformance> performanceData;
  final double height;

  const PerformanceChartWidget({
    super.key,
    required this.strategyId,
    required this.chartType,
    required this.performanceData,
    this.height = 300,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      height: height,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 图表标题
          Row(
            children: [
              Icon(
                _getChartIcon(chartType),
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                chartType.displayName,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 16),
          
          // 图表内容
          Expanded(
            child: _buildChart(theme),
          ),
          
          // 图表图例
          const SizedBox(height: 8),
          _buildLegend(theme),
        ],
      ),
    );
  }

  Widget _buildChart(ThemeData theme) {
    if (performanceData.isEmpty) {
      return Center(
        child: Text(
          '暂无数据',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }

    switch (chartType) {
      case ChartType.pnl:
        return _buildPnLChart();
      case ChartType.drawdown:
        return _buildDrawdownChart();
      case ChartType.returns:
        return _buildReturnsChart();
      case ChartType.winRate:
        return _buildWinRateChart();
      case ChartType.trades:
        return _buildTradesChart();
    }
  }

  Widget _buildPnLChart() {
    final spots = <FlSpot>[];
    
    for (int i = 0; i < performanceData.length; i++) {
      final data = performanceData[i];
      spots.add(FlSpot(
        data.lastUpdated.millisecondsSinceEpoch.toDouble(),
        data.netPnL,
      ));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  NumberFormat.compactCurrency(
                    decimalDigits: 0,
                  ).format(value),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    DateFormat('MM/dd').format(date),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
              reservedSize: 30,
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.green,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.green.withOpacity(0.3),
                  Colors.green.withOpacity(0.0),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDrawdownChart() {
    final spots = <FlSpot>[];
    
    for (int i = 0; i < performanceData.length; i++) {
      final data = performanceData[i];
      spots.add(FlSpot(
        data.lastUpdated.millisecondsSinceEpoch.toDouble(),
        data.currentDrawdown * 100,
      ));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${value.toStringAsFixed(1)}%',
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    DateFormat('MM/dd').format(date),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
              reservedSize: 30,
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.red,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildReturnsChart() {
    final spots = <FlSpot>[];
    
    for (int i = 0; i < performanceData.length; i++) {
      final data = performanceData[i];
      spots.add(FlSpot(
        data.lastUpdated.millisecondsSinceEpoch.toDouble(),
        data.totalReturns * 100,
      ));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${value.toStringAsFixed(1)}%',
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    DateFormat('MM/dd').format(date),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
              reservedSize: 30,
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.blue,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.blue.withOpacity(0.1),
                  Colors.blue.withOpacity(0.0),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWinRateChart() {
    final spots = <FlSpot>[];
    
    for (int i = 0; i < performanceData.length; i++) {
      final data = performanceData[i];
      spots.add(FlSpot(
        data.lastUpdated.millisecondsSinceEpoch.toDouble(),
        data.winRate * 100,
      ));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  '${value.toStringAsFixed(0)}%',
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    DateFormat('MM/dd').format(date),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
              reservedSize: 30,
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.orange,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildTradesChart() {
    final spots = <FlSpot>[];
    
    for (int i = 0; i < performanceData.length; i++) {
      final data = performanceData[i];
      spots.add(FlSpot(
        data.lastUpdated.millisecondsSinceEpoch.toDouble(),
        data.totalTrades.toDouble(),
      ));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toInt().toString(),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final date = DateTime.fromMillisecondsSinceEpoch(value.toInt());
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    DateFormat('MM/dd').format(date),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
              reservedSize: 30,
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: false,
            color: Colors.purple,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: 3,
                  color: Colors.purple,
                  strokeWidth: 1,
                  strokeColor: Colors.white,
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegend(ThemeData theme) {
    Color color;
    IconData icon;
    
    switch (chartType) {
      case ChartType.pnl:
        color = Colors.green;
        icon = Icons.trending_up;
        break;
      case ChartType.drawdown:
        color = Colors.red;
        icon = Icons.trending_down;
        break;
      case ChartType.returns:
        color = Colors.blue;
        icon = Icons.percent;
        break;
      case ChartType.winRate:
        color = Colors.orange;
        icon = Icons.winner;
        break;
      case ChartType.trades:
        color = Colors.purple;
        icon = Icons.swap_horiz;
        break;
    }

    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 8),
        Text(
          _getChartDescription(),
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  IconData _getChartIcon(ChartType type) {
    switch (type) {
      case ChartType.pnl:
        return Icons.trending_up;
      case ChartType.drawdown:
        return Icons.trending_down;
      case ChartType.returns:
        return Icons.percent;
      case ChartType.winRate:
        return Icons.winner;
      case ChartType.trades:
        return Icons.swap_horiz;
    }
  }

  String _getChartDescription() {
    switch (chartType) {
      case ChartType.pnl:
        return '策略累计净盈亏趋势';
      case ChartType.drawdown:
        return '策略回撤变化';
      case ChartType.returns:
        return '策略总收益率';
      case ChartType.winRate:
        return '策略胜率变化';
      case ChartType.trades:
        return '累计交易次数';
    }
  }
}

/// 性能指标卡片组件
class PerformanceMetricsCard extends StatelessWidget {
  final StrategyPerformance performance;
  final bool showComparison;

  const PerformanceMetricsCard({
    super.key,
    required this.performance,
    this.showComparison = false,
  });

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
            Text(
              '性能指标',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            // 指标网格
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              childAspectRatio: 2.5,
              children: [
                _buildMetricItem(
                  '总盈亏',
                  '${NumberFormat('+#,###.##;-#,###.##').format(performance.netPnL)}',
                  performance.netPnL >= 0 ? Colors.green : Colors.red,
                ),
                _buildMetricItem(
                  '胜率',
                  '${(performance.winRate * 100).toStringAsFixed(1)}%',
                  theme.colorScheme.primary,
                ),
                _buildMetricItem(
                  '交易次数',
                  performance.totalTrades.toString(),
                  theme.colorScheme.tertiary,
                ),
                _buildMetricItem(
                  '夏普比率',
                  performance.sharpeRatio.toStringAsFixed(2),
                  theme.colorScheme.secondary,
                ),
                _buildMetricItem(
                  '最大回撤',
                  '${(performance.maxDrawdown * 100).toStringAsFixed(1)}%',
                  Colors.orange,
                ),
                _buildMetricItem(
                  '总收益率',
                  '${(performance.totalReturns * 100).toStringAsFixed(1)}%',
                  performance.totalReturns >= 0 ? Colors.green : Colors.red,
                ),
                _buildMetricItem(
                  '索提诺比率',
                  performance.sortinoRatio.toStringAsFixed(2),
                  theme.colorScheme.secondary,
                ),
                _buildMetricItem(
                  '手续费',
                  NumberFormat('#,###.##').format(performance.totalCommission),
                  theme.colorScheme.error,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricItem(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}

/// 策略对比组件
class StrategyComparisonWidget extends StatelessWidget {
  final List<StrategyConfig> strategies;
  final List<StrategyPerformance> performanceData;

  const StrategyComparisonWidget({
    super.key,
    required this.strategies,
    required this.performanceData,
  });

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
                  Icons.compare_arrows,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '策略对比',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 对比表格
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columnSpacing: 16,
                horizontalMargin: 0,
                columns: [
                  const DataColumn(label: Text('策略')),
                  DataColumn(label: Text('净盈亏')),
                  DataColumn(label: Text('胜率')),
                  DataColumn(label: Text('夏普比率')),
                  DataColumn(label: Text('最大回撤')),
                  DataColumn(label: Text('总收益率')),
                ],
                rows: strategies.map((strategy) {
                  final performance = performanceData.firstWhere(
                    (p) => p.strategyId == strategy.id,
                    orElse: () => StrategyPerformance(
                      strategyId: strategy.id,
                      totalPnL: 0,
                      totalCommission: 0,
                      netPnL: 0,
                      winRate: 0,
                      profitFactor: 0,
                      maxDrawdown: 0,
                      currentDrawdown: 0,
                      sharpeRatio: 0,
                      sortinoRatio: 0,
                      totalReturns: 0,
                      totalTrades: 0,
                      lastUpdated: DateTime.now(),
                    ),
                  );
                  
                  return DataRow(
                    cells: [
                      DataCell(
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              strategy.name,
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            Text(
                              strategy.symbol,
                              style: TextStyle(
                                fontSize: 12,
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ),
                      DataCell(
                        Text(
                          NumberFormat('+#,###.##;-#,###.##').format(performance.netPnL),
                          style: TextStyle(
                            color: performance.netPnL >= 0 ? Colors.green : Colors.red,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      DataCell(
                        Text('${(performance.winRate * 100).toStringAsFixed(1)}%'),
                      ),
                      DataCell(
                        Text(performance.sharpeRatio.toStringAsFixed(2)),
                      ),
                      DataCell(
                        Text('${(performance.maxDrawdown * 100).toStringAsFixed(1)}%'),
                      ),
                      DataCell(
                        Text(
                          '${(performance.totalReturns * 100).toStringAsFixed(1)}%',
                          style: TextStyle(
                            color: performance.totalReturns >= 0 ? Colors.green : Colors.red,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}