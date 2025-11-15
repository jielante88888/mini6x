账户绩效可视化组件
提供各种图表和可视化组件来展示账户表现数据

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

/// 盈亏趋势图表
class PnLTrendChart extends StatelessWidget {
  final List<PnLDataPoint> data;
  final double height;
  final Color? lineColor;
  final Color? fillColor;
  final bool showTooltip;

  const PnLTrendChart({
    Key? key,
    required this.data,
    this.height = 200,
    this.lineColor,
    this.fillColor,
    this.showTooltip = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    final spots = data.asMap().entries.map((entry) {
      final index = entry.key;
      final point = entry.value;
      return FlSpot(index.toDouble(), point.pnl.toDouble());
    }).toList();

    final minY = data.map((e) => e.pnl).reduce((a, b) => a < b ? a : b);
    final maxY = data.map((e) => e.pnl).reduce((a, b) => a > b ? a : b);
    final rangeY = maxY - minY;
    final paddingY = rangeY * 0.1;

    return Container(
      height: height,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            horizontalInterval: 1,
            verticalInterval: 1,
            getDrawingHorizontalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
            getDrawingVerticalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
          ),
          titlesData: FlTitlesData(
            show: true,
            rightTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 30,
                interval: (data.length / 5).ceil().toDouble(),
                getTitlesWidget: (value, meta) {
                  final index = value.toInt();
                  if (index < 0 || index >= data.length) return Text('');
                  
                  final point = data[index];
                  return SideTitleWidget(
                    axisSide: meta.axisSide,
                    child: Text(
                      DateFormat('MM/dd').format(point.date),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.7),
                      ),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: (rangeY / 4).toDouble(),
                reservedSize: 60,
                getTitlesWidget: (value, meta) {
                  return Text(
                    NumberFormat.currency(
                      symbol: '¥',
                      decimalDigits: 0,
                    ).format(value),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(
            show: false,
          ),
          minX: 0,
          maxX: data.length.toDouble() - 1,
          minY: (minY - paddingY).toDouble(),
          maxY: (maxY + paddingY).toDouble(),
          lineTouchData: LineTouchData(
            enabled: showTooltip,
            touchCallback: (FlTouchEvent event, LineTouchResponse? touchResponse) {
              // 处理触摸事件
            },
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => theme.colorScheme.surface,
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((LineBarSpot touchedSpot) {
                  final index = touchedSpot.spotIndex;
                  final point = data[index];
                  return LineTooltipItem(
                    '${DateFormat('yyyy-MM-dd').format(point.date)}\n'
                    '盈亏: ${NumberFormat.currency(symbol: '¥', decimalDigits: 2).format(point.pnl)}',
                    theme.textTheme.bodyMedium!.copyWith(
                      color: theme.colorScheme.onPrimary,
                    ),
                  );
                }).toList();
              },
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: false,
              color: lineColor ?? theme.colorScheme.primary,
              barWidth: 2,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: true,
                getDotPainter: (spot, percent, barData, index) {
                  return FlDotCirclePainter(
                    radius: 3,
                    color: lineColor ?? theme.colorScheme.primary,
                    strokeWidth: 1,
                    strokeColor: theme.colorScheme.surface,
                  );
                },
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    (fillColor ?? theme.colorScheme.primary).withOpacity(0.3),
                    (fillColor ?? theme.colorScheme.primary).withOpacity(0.05),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 累计盈亏图表
class CumulativePnLChart extends StatelessWidget {
  final List<PnLDataPoint> data;
  final double height;
  final Color? color;

  const CumulativePnLChart({
    Key? key,
    required this.data,
    this.height = 200,
    this.color,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    // 计算累计盈亏
    double cumulative = 0;
    final cumulativeData = data.map((point) {
      cumulative += point.pnl;
      return FlSpot(point.date.millisecondsSinceEpoch.toDouble(), cumulative);
    }).toList();

    final minY = cumulativeData.map((e) => e.y).reduce((a, b) => a < b ? a : b);
    final maxY = cumulativeData.map((e) => e.y).reduce((a, b) => a > b ? a : b);
    final rangeY = maxY - minY;
    final paddingY = rangeY * 0.1;

    return Container(
      height: height,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            getDrawingVerticalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
          ),
          titlesData: FlTitlesData(
            show: false,
          ),
          borderData: FlBorderData(
            show: false,
          ),
          minX: cumulativeData.first.x,
          maxX: cumulativeData.last.x,
          minY: (minY - paddingY),
          maxY: (maxY + paddingY),
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => theme.colorScheme.surface,
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((LineBarSpot touchedSpot) {
                  final date = DateTime.fromMillisecondsSinceEpoch(touchedSpot.spot.x.toInt());
                  return LineTooltipItem(
                    '${DateFormat('yyyy-MM-dd').format(date)}\n'
                    '累计盈亏: ${NumberFormat.currency(symbol: '¥', decimalDigits: 2).format(touchedSpot.spot.y)}',
                    theme.textTheme.bodyMedium!.copyWith(
                      color: theme.colorScheme.onPrimary,
                    ),
                  );
                }).toList();
              },
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: cumulativeData,
              isCurved: false,
              color: color ?? theme.colorScheme.primary,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: false,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 回撤图表
class DrawdownChart extends StatelessWidget {
  final List<DrawdownDataPoint> data;
  final double height;
  final Color? color;

  const DrawdownChart({
    Key? key,
    required this.data,
    this.height = 150,
    this.color,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    final spots = data.asMap().entries.map((entry) {
      final index = entry.key;
      final point = entry.value;
      return FlSpot(index.toDouble(), point.drawdown.toDouble());
    }).toList();

    return Container(
      height: height,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawHorizontalLine: true,
            getDrawingHorizontalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
          ),
          titlesData: FlTitlesData(
            show: true,
            rightTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: false,
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 50,
                getTitlesWidget: (value, meta) {
                  return Text(
                    '${value.toStringAsFixed(1)}%',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(
            show: false,
          ),
          minX: 0,
          maxX: data.length.toDouble() - 1,
          minY: -100,
          maxY: 0,
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => theme.colorScheme.surface,
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((LineBarSpot touchedSpot) {
                  final index = touchedSpot.spotIndex;
                  final point = data[index];
                  return LineTooltipItem(
                    '${DateFormat('MM/dd').format(point.date)}\n'
                    '回撤: ${point.drawdown.toStringAsFixed(2)}%',
                    theme.textTheme.bodyMedium!.copyWith(
                      color: theme.colorScheme.onPrimary,
                    ),
                  );
                }).toList();
              },
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: false,
              color: color ?? theme.colorScheme.error,
              barWidth: 2,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: false,
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    (color ?? theme.colorScheme.error).withOpacity(0.3),
                    (color ?? theme.colorScheme.error).withOpacity(0.1),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 资产分布饼图
class AssetDistributionPieChart extends StatelessWidget {
  final List<AssetDistributionData> data;
  final double height;
  final bool showLabels;

  const AssetDistributionPieChart({
    Key? key,
    required this.data,
    this.height = 200,
    this.showLabels = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    return Container(
      height: height,
      child: PieChart(
        PieChartData(
          sections: data.asMap().entries.map((entry) {
            final index = entry.key;
            final item = entry.value;
            final percentage = (item.value / data.fold(0.0, (sum, item) => sum + item.value)) * 100;
            
            return PieChartSectionData(
              value: item.value,
              color: item.color ?? _getDefaultColor(index),
              radius: 80,
              title: showLabels ? '${percentage.toStringAsFixed(1)}%' : '',
              titleStyle: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onPrimary,
                fontWeight: FontWeight.bold,
              ),
              titlePositionPercentageOffset: 0.5,
            );
          }).toList(),
          centerSpaceRadius: 40,
          sectionsSpace: 2,
          pieTouchData: PieTouchData(
            enabled: true,
            touchCallback: (FlTouchEvent event, pieTouchResponse) {
              // 处理触摸事件
            },
          ),
        ),
      ),
    );
  }

  Color _getDefaultColor(int index) {
    final colors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.red,
      Colors.purple,
      Colors.cyan,
      Colors.yellow,
      Colors.pink,
    ];
    return colors[index % colors.length];
  }
}

/// 绩效指标柱状图
class PerformanceMetricsBarChart extends StatelessWidget {
  final List<PerformanceMetricData> data;
  final double height;

  const PerformanceMetricsBarChart({
    Key? key,
    required this.data,
    this.height = 200,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    final maxValue = data.map((e) => e.value).reduce((a, b) => a > b ? a : b);
    final barWidth = 40.0;
    final spacing = 20.0;

    return Container(
      height: height,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: maxValue * 1.2,
          barTouchData: BarTouchData(
            enabled: true,
            touchTooltipData: BarTouchTooltipData(
              getTooltipColor: (_) => theme.colorScheme.surface,
              getTooltipItem: (group, groupIndex, rod, rodIndex) {
                final metric = data[group.x.toInt()];
                return BarTooltipItem(
                  '${metric.label}\n${metric.value.toStringAsFixed(2)}',
                  theme.textTheme.bodyMedium!.copyWith(
                    color: theme.colorScheme.onPrimary,
                  ),
                );
              },
            ),
          ),
          titlesData: FlTitlesData(
            show: true,
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  final index = value.toInt();
                  if (index < 0 || index >= data.length) return Text('');
                  
                  final metric = data[index];
                  return SideTitleWidget(
                    axisSide: meta.axisSide,
                    child: Text(
                      metric.label,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.7),
                      ),
                      textAlign: TextAlign.center,
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 50,
                getTitlesWidget: (value, meta) {
                  return Text(
                    value.toStringAsFixed(1),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  );
                },
              ),
            ),
            rightTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
          ),
          borderData: FlBorderData(
            show: false,
          ),
          barGroups: data.asMap().entries.map((entry) {
            final index = entry.key;
            final metric = entry.value;
            
            return BarChartGroupData(
              x: index,
              barRods: [
                BarChartRodData(
                  toY: metric.value,
                  color: metric.color ?? _getDefaultColor(index),
                  width: barWidth,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(4),
                    topRight: Radius.circular(4),
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }

  Color _getDefaultColor(int index) {
    final colors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.red,
      Colors.purple,
    ];
    return colors[index % colors.length];
  }
}

/// 风险-收益散点图
class RiskReturnScatterChart extends StatelessWidget {
  final List<RiskReturnDataPoint> data;
  final double height;

  const RiskReturnScatterChart({
    Key? key,
    required this.data,
    this.height = 200,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    if (data.isEmpty) {
      return Container(
        height: height,
        child: Center(
          child: Text(
            '暂无数据',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ),
      );
    }

    final maxRisk = data.map((e) => e.risk).reduce((a, b) => a > b ? a : b);
    final maxReturn = data.map((e) => e.returnValue).reduce((a, b) => a > b ? a : b);

    return Container(
      height: height,
      child: ScatterChart(
        ScatterChartData(
          scatterSpots: data.asMap().entries.map((entry) {
            final index = entry.key;
            final point = entry.value;
            
            return ScatterSpot(
              point.x,
              point.y,
              dotPainter: (spot, percent, barData, index) => FlDotCirclePainter(
                radius: 6,
                color: point.color ?? _getDefaultColor(index),
                strokeWidth: 2,
                strokeColor: theme.colorScheme.surface,
              ),
              showTooltips: true,
            );
          }).toList(),
          scatterTouchData: ScatterTouchData(
            enabled: true,
            touchTooltipData: ScatterTouchTooltipData(
              getTooltipColor: (_) => theme.colorScheme.surface,
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((ScatterSpot touchedSpot) {
                  final index = touchedSpot.x.toInt();
                  if (index < 0 || index >= data.length) return null;
                  
                  final point = data[index];
                  return ScatterTooltipItem(
                    '${point.label}\n风险: ${point.risk.toStringAsFixed(2)}%\n收益: ${point.returnValue.toStringAsFixed(2)}%',
                    theme.textTheme.bodyMedium!.copyWith(
                      color: theme.colorScheme.onPrimary,
                    ),
                  );
                }).where((item) => item != null).cast<ScatterTooltipItem>().toList();
              },
            ),
          ),
          titlesData: FlTitlesData(
            show: true,
            rightTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 50,
                getTitlesWidget: (value, meta) {
                  return Text(
                    '收益: ${value.toStringAsFixed(1)}%',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  );
                },
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 50,
                getTitlesWidget: (value, meta) {
                  return Text(
                    '风险: ${value.toStringAsFixed(1)}%',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
          ),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            drawHorizontalLine: true,
            getDrawingVerticalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
            getDrawingHorizontalLine: (value) => FlLine(
              color: theme.dividerColor,
              strokeWidth: 0.5,
            ),
          ),
          borderData: FlBorderData(
            show: false,
          ),
          minX: 0,
          maxX: maxRisk * 1.2,
          minY: 0,
          maxY: maxReturn * 1.2,
        ),
      ),
    );
  }

  Color _getDefaultColor(int index) {
    final colors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.red,
      Colors.purple,
    ];
    return colors[index % colors.length];
  }
}

/// 数据类定义
class PnLDataPoint {
  final DateTime date;
  final double pnl;
  final double pnlPercentage;

  const PnLDataPoint({
    required this.date,
    required this.pnl,
    this.pnlPercentage = 0.0,
  });
}

class DrawdownDataPoint {
  final DateTime date;
  final double drawdown;

  const DrawdownDataPoint({
    required this.date,
    required this.drawdown,
  });
}

class AssetDistributionData {
  final String label;
  final double value;
  final Color? color;

  const AssetDistributionData({
    required this.label,
    required this.value,
    this.color,
  });
}

class PerformanceMetricData {
  final String label;
  final double value;
  final Color? color;

  const PerformanceMetricData({
    required this.label,
    required this.value,
    this.color,
  });
}

class RiskReturnDataPoint {
  final String label;
  final double risk;
  final double returnValue;
  final double x;
  final double y;
  final Color? color;

  const RiskReturnDataPoint({
    required this.label,
    required this.risk,
    required this.returnValue,
    required this.x,
    required this.y,
    this.color,
  });

  factory RiskReturnDataPoint.fromRiskReturn({
    required String label,
    required double risk,
    required double returnValue,
    Color? color,
  }) {
    return RiskReturnDataPoint(
      label: label,
      risk: risk,
      returnValue: returnValue,
      x: risk,
      y: returnValue,
      color: color,
    );
  }
}
