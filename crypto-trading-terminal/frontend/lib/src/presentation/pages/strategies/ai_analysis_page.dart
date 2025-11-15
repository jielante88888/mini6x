import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

import '../../../domain/ai_analysis/models.dart';
import '../widgets/ai_analysis/analysis_overview_card.dart';
import '../widgets/ai_analysis/market_trend_card.dart';
import '../widgets/ai_analysis/signal_strength_card.dart';
import '../widgets/ai_analysis/insights_list.dart';
import '../widgets/common/loading_indicator.dart';
import '../widgets/common/error_message.dart';

/// AI分析页面 - 展示AI驱动的市场分析和策略优化结果
class AIAnalysisPage extends ConsumerStatefulWidget {
  const AIAnalysisPage({Key? key}) : super(key: key);

  @override
  ConsumerState<AIAnalysisPage> createState() => _AIAnalysisPageState();
}

class _AIAnalysisPageState extends ConsumerState<AIAnalysisPage> {
  String _selectedSymbol = 'BTCUSDT';
  int _selectedTimeframe = 1; // 1小时
  bool _isRealTimeEnabled = true;
  
  final List<String> _symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'];
  final List<int> _timeframes = [15, 60, 240, 1440]; // 15分钟, 1小时, 4小时, 1天
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('AI智能分析'),
        backgroundColor: Theme.of(context).colorScheme.surface,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(
              _isRealTimeEnabled ? Icons.sync : Icons.sync_disabled,
              color: _isRealTimeEnabled ? Colors.green : Colors.grey,
            ),
            onPressed: _toggleRealTime,
            tooltip: _isRealTimeEnabled ? '关闭实时更新' : '开启实时更新',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshAnalysis,
            tooltip: '刷新分析',
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: _handleMenuAction,
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'export',
                child: ListTile(
                  leading: Icon(Icons.download),
                  title: Text('导出报告'),
                ),
              ),
              const PopupMenuItem(
                value: 'settings',
                child: ListTile(
                  leading: Icon(Icons.settings),
                  title: Text('分析设置'),
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          _buildControlPanel(),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refreshAnalysis,
              child: _buildAnalysisContent(),
            ),
          ),
        ],
      ),
    );
  }

  /// 构建控制面板
  Widget _buildControlPanel() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          // 交易对选择
          Expanded(
            flex: 2,
            child: DropdownButtonFormField<String>(
              value: _selectedSymbol,
              decoration: const InputDecoration(
                labelText: '交易对',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: _symbols.map((symbol) => DropdownMenuItem(
                value: symbol,
                child: Text(symbol),
              )).toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _selectedSymbol = value;
                  });
                  _refreshAnalysis();
                }
              },
            ),
          ),
          const SizedBox(width: 16),
          // 时间框架选择
          Expanded(
            flex: 2,
            child: DropdownButtonFormField<int>(
              value: _selectedTimeframe,
              decoration: const InputDecoration(
                labelText: '时间框架',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: _timeframes.map((minutes) => DropdownMenuItem(
                value: minutes,
                child: Text(_formatTimeframe(minutes)),
              )).toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _selectedTimeframe = value;
                  });
                  _refreshAnalysis();
                }
              },
            ),
          ),
          const SizedBox(width: 16),
          // 实时更新开关
          SwitchListTile(
            title: const Text('实时更新'),
            value: _isRealTimeEnabled,
            onChanged: (value) {
              setState(() {
                _isRealTimeEnabled = value;
              });
            },
            contentPadding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }

  /// 构建分析内容
  Widget _buildAnalysisContent() {
    return Consumer(
      builder: (context, ref, child) {
        final analysisAsyncValue = ref.watch(
          aiAnalysisProvider(_selectedSymbol),
        );
        
        return analysisAsyncValue.when(
          loading: () => const LoadingIndicator(),
          error: (error, stack) => ErrorMessage(
            message: '分析加载失败: ${error.toString()}',
            onRetry: _refreshAnalysis,
          ),
          data: (analysis) => _buildAnalysisView(analysis),
        );
      },
    );
  }

  /// 构建分析视图
  Widget _buildAnalysisView(AIAnalysis analysis) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 分析概览卡片
          AnalysisOverviewCard(analysis: analysis),
          const SizedBox(height: 16),
          
          // 市场趋势和信号强度卡片
          Row(
            children: [
              Expanded(
                child: MarketTrendCard(
                  marketInsight: analysis.marketInsight,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: SignalStrengthCard(
                  signalInsight: analysis.signalInsight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // AI洞察列表
          InsightsList(
            insights: analysis.insights,
            symbol: _selectedSymbol,
          ),
          const SizedBox(height: 16),
          
          // 性能图表（如果有数据）
          if (analysis.performanceData != null) _buildPerformanceChart(analysis),
          
          const SizedBox(height: 24),
          _buildLastUpdateTime(analysis.timestamp),
        ],
      ),
    );
  }

  /// 构建性能图表
  Widget _buildPerformanceChart(AIAnalysis analysis) {
    final performanceData = analysis.performanceData!;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '模型性能趋势',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: false),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 22,
                        getTitlesWidget: (value, meta) {
                          return SideTitleWidget(
                            axisSide: meta.axisSide,
                            child: Text(
                              DateFormat('HH:mm').format(
                                DateTime.fromMillisecondsSinceEpoch(
                                  value.toInt(),
                                ),
                              ),
                              style: const TextStyle(fontSize: 12),
                            ),
                          );
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        getTitlesWidget: (value, meta) {
                          return SideTitleWidget(
                            axisSide: meta.axisSide,
                            child: Text(
                              '${value.toStringAsFixed(2)}%',
                              style: const TextStyle(fontSize: 12),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: performanceData
                          .map((e) => FlSpot(
                                e.timestamp.millisecondsSinceEpoch.toDouble(),
                                e.confidence * 100,
                              ))
                          .toList(),
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
          ],
        ),
      ),
    );
  }

  /// 构建最后更新时间
  Widget _buildLastUpdateTime(DateTime timestamp) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          Icons.access_time,
          size: 16,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 4),
        Text(
          '最后更新: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(timestamp)}',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      ],
    );
  }

  /// 格式化时间框架
  String _formatTimeframe(int minutes) {
    if (minutes < 60) {
      return '${minutes}分钟';
    } else if (minutes < 1440) {
      return '${(minutes / 60).toInt()}小时';
    } else {
      return '${(minutes / 1440).toInt()}天';
    }
  }

  /// 刷新分析
  Future<void> _refreshAnalysis() async {
    await ref.refresh(aiAnalysisProvider(_selectedSymbol).future);
  }

  /// 切换实时更新
  void _toggleRealTime() {
    setState(() {
      _isRealTimeEnabled = !_isRealTimeEnabled;
    });
    
    if (_isRealTimeEnabled) {
      ref.read(aiAnalysisProvider(_selectedSymbol).notifier).startRealTimeUpdates();
    } else {
      ref.read(aiAnalysisProvider(_selectedSymbol).notifier).stopRealTimeUpdates();
    }
  }

  /// 处理菜单操作
  void _handleMenuAction(String action) {
    switch (action) {
      case 'export':
        _exportReport();
        break;
      case 'settings':
        _openSettings();
        break;
    }
  }

  /// 导出报告
  void _exportReport() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('导出功能开发中...')),
    );
  }

  /// 打开设置
  void _openSettings() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('AI分析设置'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.timer),
              title: Text('自动刷新间隔'),
              subtitle: Text('30秒'),
            ),
            ListTile(
              leading: Icon(Icons.tune),
              title: Text('置信度阈值'),
              subtitle: Text('70%'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('保存'),
          ),
        ],
      ),
    );
  }
}